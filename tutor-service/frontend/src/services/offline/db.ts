/**
 * IndexedDB Service for Offline-First PWA
 * Uses Dexie.js for type-safe IndexedDB operations
 */

import Dexie, { Table } from 'dexie';

// =============================================================================
// Types
// =============================================================================

export interface CachedLesson {
  id: number;
  language: string;
  level: string;
  lesson_number: number;
  title: string;
  content: any; // Full lesson content
  cached_at: number;
  expires_at: number;
}

export interface CachedVocabulary {
  id: number;
  lesson_id: number;
  language: string;
  word: string;
  translation: string;
  audio_url?: string;
  audio_blob?: Blob;
  difficulty: number;
  cached_at: number;
}

export interface CachedUserProgress {
  user_id: number;
  xp: number;
  level: number;
  streak: number;
  gems: number;
  language_progress: Record<string, any>;
  last_synced: number;
}

export interface CachedAudio {
  url: string;
  blob: Blob;
  language: string;
  cached_at: number;
  expires_at: number;
}

export interface PendingMutation {
  id?: number;
  type: 'lesson_progress' | 'vocabulary' | 'practice_session' | 'achievement' | 'streak' | 'xp' | 'settings';
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string;
  timestamp: number;
  retry_count: number;
}

export interface OfflineSettings {
  key: string;
  value: any;
  updated_at: number;
}

export interface CachedPracticeSession {
  id: number;
  user_id: number;
  language: string;
  session_type: string;
  data: any;
  started_at: number;
  completed_at?: number;
  synced: boolean;
}

// =============================================================================
// Database Class
// =============================================================================

export class TutorDB extends Dexie {
  lessons!: Table<CachedLesson, number>;
  vocabulary!: Table<CachedVocabulary, number>;
  userProgress!: Table<CachedUserProgress, number>;
  audio!: Table<CachedAudio, string>;
  pendingMutations!: Table<PendingMutation, number>;
  settings!: Table<OfflineSettings, string>;
  practiceSessions!: Table<CachedPracticeSession, number>;

  constructor() {
    super('TutorPWA');

    this.version(1).stores({
      lessons: 'id, language, level, lesson_number, cached_at, expires_at',
      vocabulary: 'id, lesson_id, language, word, cached_at',
      userProgress: 'user_id, last_synced',
      audio: 'url, language, cached_at, expires_at',
      pendingMutations: '++id, type, timestamp, retry_count',
      settings: 'key, updated_at',
      practiceSessions: 'id, user_id, language, started_at, synced',
    });
  }
}

// =============================================================================
// Singleton Instance
// =============================================================================

export const db = new TutorDB();

// =============================================================================
// Constants
// =============================================================================

const CACHE_DURATION = 7 * 24 * 60 * 60 * 1000; // 7 days
const AUDIO_CACHE_DURATION = 30 * 24 * 60 * 60 * 1000; // 30 days
const MAX_RETRIES = 3;
const MAX_AUDIO_CACHE_SIZE = 100 * 1024 * 1024; // 100MB

// =============================================================================
// Lessons Cache
// =============================================================================

export async function cacheLesson(lesson: Omit<CachedLesson, 'cached_at' | 'expires_at'>): Promise<void> {
  const now = Date.now();
  await db.lessons.put({
    ...lesson,
    cached_at: now,
    expires_at: now + CACHE_DURATION,
  });
}

export async function getCachedLesson(id: number): Promise<CachedLesson | undefined> {
  const lesson = await db.lessons.get(id);
  if (lesson && lesson.expires_at > Date.now()) {
    return lesson;
  }
  if (lesson) {
    await db.lessons.delete(id); // Expired
  }
  return undefined;
}

export async function getCachedLessonsByLanguage(language: string, level?: string): Promise<CachedLesson[]> {
  let query = db.lessons.where('language').equals(language);
  if (level) {
    query = query.and((lesson) => lesson.level === level);
  }
  const lessons = await query.toArray();
  return lessons.filter((l) => l.expires_at > Date.now());
}

export async function getAllCachedLessons(): Promise<CachedLesson[]> {
  const lessons = await db.lessons.toArray();
  return lessons.filter((l) => l.expires_at > Date.now());
}

export async function clearExpiredLessons(): Promise<void> {
  const now = Date.now();
  await db.lessons.where('expires_at').below(now).delete();
}

export async function clearLanguageCache(language: string): Promise<void> {
  await db.lessons.where('language').equals(language).delete();
  await db.vocabulary.where('language').equals(language).delete();
}

// =============================================================================
// Vocabulary Cache
// =============================================================================

export async function cacheVocabulary(vocab: Omit<CachedVocabulary, 'cached_at'>): Promise<void> {
  await db.vocabulary.put({
    ...vocab,
    cached_at: Date.now(),
  });
}

export async function getCachedVocabulary(lessonId: number): Promise<CachedVocabulary[]> {
  return db.vocabulary.where('lesson_id').equals(lessonId).toArray();
}

export async function getCachedVocabularyByLanguage(language: string): Promise<CachedVocabulary[]> {
  return db.vocabulary.where('language').equals(language).toArray();
}

export async function cacheVocabularyAudio(vocabId: number, audioBlob: Blob): Promise<void> {
  await db.vocabulary.update(vocabId, { audio_blob: audioBlob });
}

export async function getVocabularyAudio(vocabId: number): Promise<Blob | undefined> {
  const vocab = await db.vocabulary.get(vocabId);
  return vocab?.audio_blob;
}

// =============================================================================
// User Progress Cache
// =============================================================================

export async function cacheUserProgress(progress: Omit<CachedUserProgress, 'last_synced'>): Promise<void> {
  await db.userProgress.put({
    ...progress,
    last_synced: Date.now(),
  });
}

export async function getCachedUserProgress(userId: number): Promise<CachedUserProgress | undefined> {
  return db.userProgress.get(userId);
}

export async function updateUserProgressPartial(userId: number, partial: Partial<CachedUserProgress>): Promise<void> {
  const existing = await db.userProgress.get(userId);
  if (existing) {
    await db.userProgress.put({ ...existing, ...partial, last_synced: Date.now() });
  }
}

// =============================================================================
// Audio Cache
// =============================================================================

export async function cacheAudio(url: string, blob: Blob, language: string): Promise<void> {
  // Check cache size before adding
  await enforceAudioCacheLimit();

  const now = Date.now();
  await db.audio.put({
    url,
    blob,
    language,
    cached_at: now,
    expires_at: now + AUDIO_CACHE_DURATION,
  });
}

export async function getCachedAudio(url: string): Promise<Blob | undefined> {
  const audio = await db.audio.get(url);
  if (audio && audio.expires_at > Date.now()) {
    return audio.blob;
  }
  if (audio) {
    await db.audio.delete(url);
  }
  return undefined;
}

export async function getCachedAudioByLanguage(language: string): Promise<CachedAudio[]> {
  const audios = await db.audio.where('language').equals(language).toArray();
  return audios.filter((a) => a.expires_at > Date.now());
}

async function enforceAudioCacheLimit(): Promise<void> {
  const audios = await db.audio.toArray();
  let totalSize = audios.reduce((sum, a) => sum + a.blob.size, 0);

  if (totalSize > MAX_AUDIO_CACHE_SIZE) {
    // Sort by oldest first and remove until under limit
    audios.sort((a, b) => a.cached_at - b.cached_at);
    for (const audio of audios) {
      if (totalSize <= MAX_AUDIO_CACHE_SIZE * 0.8) break; // Keep 80% buffer
      totalSize -= audio.blob.size;
      await db.audio.delete(audio.url);
    }
  }
}

// =============================================================================
// Pending Mutations (Background Sync)
// =============================================================================

export async function queueMutation(mutation: Omit<PendingMutation, 'id' | 'timestamp' | 'retry_count'>): Promise<number> {
  return db.pendingMutations.add({
    ...mutation,
    timestamp: Date.now(),
    retry_count: 0,
  });
}

export async function getPendingMutations(type?: PendingMutation['type']): Promise<PendingMutation[]> {
  let query = db.pendingMutations.orderBy('timestamp');
  if (type) {
    query = query.filter((m) => m.type === type);
  }
  return query.toArray();
}

export async function retryMutation(id: number): Promise<void> {
  await db.pendingMutations.update(id, (mut: PendingMutation) => ({ retry_count: mut.retry_count + 1 }));
}

export async function removeMutation(id: number): Promise<void> {
  await db.pendingMutations.delete(id);
}

export async function clearSyncedMutations(): Promise<void> {
  // This would be called after successful sync
  // For now, we remove by ID in the sync process
}

// =============================================================================
// Practice Sessions Cache
// =============================================================================

export async function cachePracticeSession(session: Omit<CachedPracticeSession, 'synced'>): Promise<void> {
  await db.practiceSessions.put({
    ...session,
    synced: false,
  });
}

export async function getUnsyncedPracticeSessions(userId: number): Promise<CachedPracticeSession[]> {
  return db.practiceSessions
    .where('user_id')
    .equals(userId)
    .and((s) => !s.synced)
    .toArray();
}

export async function markPracticeSessionSynced(id: number): Promise<void> {
  await db.practiceSessions.update(id, { synced: true });
}

// =============================================================================
// Settings Cache
// =============================================================================

export async function setSetting(key: string, value: any): Promise<void> {
  await db.settings.put({
    key,
    value,
    updated_at: Date.now(),
  });
}

export async function getSetting<T>(key: string): Promise<T | undefined> {
  const setting = await db.settings.get(key);
  return setting?.value as T;
}

export async function getAllSettings(): Promise<Record<string, any>> {
  const settings = await db.settings.toArray();
  return settings.reduce((acc, s) => ({ ...acc, [s.key]: s.value }), {});
}

// =============================================================================
// Selective Sync (User chooses what to cache)
// =============================================================================

export interface SyncPreferences {
  languages: string[]; // Language codes to cache
  levels: string[]; // CEFR levels to cache
  cacheAudio: boolean;
  cacheImages: boolean;
  maxCacheSizeMB: number;
}

export async function getSyncPreferences(): Promise<SyncPreferences> {
  return (await getSetting<SyncPreferences>('sync_preferences')) || {
    languages: [],
    levels: [],
    cacheAudio: true,
    cacheImages: true,
    maxCacheSizeMB: 500,
  };
}

export async function setSyncPreferences(prefs: SyncPreferences): Promise<void> {
  await setSetting('sync_preferences', prefs);
}

export async function shouldCacheLanguage(language: string): Promise<boolean> {
  const prefs = await getSyncPreferences();
  return prefs.languages.length === 0 || prefs.languages.includes(language);
}

export async function shouldCacheLevel(level: string): Promise<boolean> {
  const prefs = await getSyncPreferences();
  return prefs.levels.length === 0 || prefs.levels.includes(level);
}

// =============================================================================
// Cache Management
// =============================================================================

export async function getCacheStats(): Promise<{
  lessons: number;
  vocabulary: number;
  audio: number;
  audioSizeMB: number;
  mutations: number;
  totalSizeMB: number;
}> {
  const [lessons, vocabulary, audio, mutations] = await Promise.all([
    db.lessons.count(),
    db.vocabulary.count(),
    db.audio.toArray(),
    db.pendingMutations.count(),
  ]);

  const audioSizeMB = audio.reduce((sum, a) => sum + a.blob.size, 0) / (1024 * 1024);

  // Estimate total size (rough)
  const totalSizeMB = audioSizeMB + (lessons * 0.05) + (vocabulary * 0.01);

  return {
    lessons,
    vocabulary,
    audio: audio.length,
    audioSizeMB: Math.round(audioSizeMB * 100) / 100,
    mutations,
    totalSizeMB: Math.round(totalSizeMB * 100) / 100,
  };
}

export async function clearAllCache(): Promise<void> {
  await Promise.all([
    db.lessons.clear(),
    db.vocabulary.clear(),
    db.audio.clear(),
    db.practiceSessions.clear(),
  ]);
}

export async function clearUserData(userId: number): Promise<void> {
  await Promise.all([
    db.userProgress.delete(userId),
    db.practiceSessions.where('user_id').equals(userId).delete(),
  ]);
}

// =============================================================================
// Conflict Resolution (Last-write-wins with server reconciliation)
// =============================================================================

export interface ConflictResolutionResult {
  resolved: boolean;
  serverWins: boolean;
  mergedData?: any;
}

export async function resolveConflict(
  localData: any,
  serverData: any,
  lastModifiedField: string = 'updated_at'
): Promise<ConflictResolutionResult> {
  const localTime = localData[lastModifiedField] || 0;
  const serverTime = serverData[lastModifiedField] || 0;

  if (serverTime > localTime) {
    // Server is newer - server wins
    return { resolved: true, serverWins: true };
  } else if (localTime > serverTime) {
    // Local is newer - local wins (will be synced)
    return { resolved: true, serverWins: false };
  } else {
    // Same timestamp - merge if possible
    const merged = { ...serverData, ...localData };
    return { resolved: true, serverWins: false, mergedData: merged };
  }
}