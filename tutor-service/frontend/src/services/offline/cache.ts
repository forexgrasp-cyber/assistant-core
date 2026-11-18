/**
 * Cache Management Service for Offline-First PWA
 * Handles strategic caching of lessons, vocabulary, audio, and assets
 */

import { db, CachedLesson, CachedVocabulary, getCacheStats, clearAllCache } from './db';

// =============================================================================
// Types
// =============================================================================

export interface CacheStrategy {
  lessons: boolean;
  vocabulary: boolean;
  audio: boolean;
  images: boolean;
  maxSizeMB: number;
}

export interface PreloadOptions {
  language: string;
  level?: string;
  lessonCount?: number;
  includeAudio?: boolean;
  includeImages?: boolean;
}

export interface CacheProgress {
  total: number;
  completed: number;
  current: string;
  phase: 'lessons' | 'vocabulary' | 'audio' | 'images' | 'complete';
}

// =============================================================================
// State
// =============================================================================

const progressListeners: Set<(progress: CacheProgress) => void> = new Set();
let isPreloading = false;

// =============================================================================
// Public API
// =============================================================================

export function subscribeToCacheProgress(listener: (progress: CacheProgress) => void): () => void {
  progressListeners.add(listener);
  return () => progressListeners.delete(listener);
}

export async function preloadLanguageContent(options: PreloadOptions): Promise<void> {
  if (isPreloading) {
    console.warn('[Cache] Preload already in progress');
    return;
  }

  isPreloading = true;
  const { language, level, lessonCount = 20, includeAudio = true, includeImages = true } = options;

  try {
    // Phase 1: Lessons
    emitProgress({ total: lessonCount, completed: 0, current: 'Fetching lessons...', phase: 'lessons' });
    await preloadLessons(language, level, lessonCount);

    // Phase 2: Vocabulary
    emitProgress({ total: lessonCount * 15, completed: 0, current: 'Fetching vocabulary...', phase: 'vocabulary' });
    await preloadVocabulary(language, level, lessonCount);

    // Phase 3: Audio (if enabled)
    if (includeAudio) {
      emitProgress({ total: lessonCount * 10, completed: 0, current: 'Caching audio...', phase: 'audio' });
      await preloadAudio(language, level, lessonCount);
    }

    // Phase 4: Images (if enabled)
    if (includeImages) {
      emitProgress({ total: lessonCount * 5, completed: 0, current: 'Caching images...', phase: 'images' });
      await preloadImages(language, level, lessonCount);
    }

    emitProgress({ total: 1, completed: 1, current: 'Complete', phase: 'complete' });
  } finally {
    isPreloading = false;
  }
}

export async function cacheCurrentLesson(lessonId: number): Promise<void> {
  try {
    const lesson = await fetchLesson(lessonId);
    if (lesson) {
      await cacheLessonWithContent(lesson);
    }
  } catch (error) {
    console.error('[Cache] Failed to cache current lesson:', error);
  }
}

export async function cacheLessonWithContent(lesson: any): Promise<void> {
  // Cache lesson metadata
  await db.lessons.put({
    id: lesson.id,
    language: lesson.language,
    level: lesson.level,
    lesson_number: lesson.lesson_number,
    title: lesson.title,
    content: lesson,
    cached_at: Date.now(),
    expires_at: Date.now() + 7 * 24 * 60 * 60 * 1000,
  });

  // Cache vocabulary
  if (lesson.vocabulary) {
    for (const vocab of lesson.vocabulary) {
      await db.vocabulary.put({
        id: vocab.id,
        lesson_id: lesson.id,
        language: lesson.language,
        word: vocab.word,
        translation: vocab.translation,
        audio_url: vocab.audio_url,
        difficulty: vocab.difficulty || 1,
        cached_at: Date.now(),
      });

      // Preload audio if available
      if (vocab.audio_url) {
        cacheAudioFromUrl(vocab.audio_url, lesson.language).catch(console.error);
      }
    }
  }

  // Cache pronunciation exercises audio
  if (lesson.pronunciation_exercises) {
    for (const exercise of lesson.pronunciation_exercises) {
      if (exercise.audio_url) {
        cacheAudioFromUrl(exercise.audio_url, lesson.language).catch(console.error);
      }
    }
  }
}

export async function cacheAudioFromUrl(url: string, language: string): Promise<void> {
  try {
    // Check if already cached
    const existing = await db.audio.get(url);
    if (existing && existing.expires_at > Date.now()) {
      return;
    }

    const response = await fetch(url);
    if (response.ok) {
      const blob = await response.blob();
      await db.audio.put({
        url,
        blob,
        language,
        cached_at: Date.now(),
        expires_at: Date.now() + 30 * 24 * 60 * 60 * 1000,
      });
    }
  } catch (error) {
    console.warn('[Cache] Failed to cache audio:', url, error);
  }
}

export async function getCachedLessonContent(lessonId: number): Promise<any | null> {
  const lesson = await db.lessons.get(lessonId);
  if (lesson && lesson.expires_at > Date.now()) {
    return lesson.content;
  }
  return null;
}

export async function getCachedVocabularyForLesson(lessonId: number): Promise<any[]> {
  const vocab = await db.vocabulary.where('lesson_id').equals(lessonId).toArray();
  return vocab.map((v) => ({
    id: v.id,
    word: v.word,
    translation: v.translation,
    audio_url: v.audio_url,
    difficulty: v.difficulty,
  }));
}

export async function getCachedAudioBlob(url: string): Promise<Blob | null> {
  const audio = await db.audio.get(url);
  if (audio && audio.expires_at > Date.now()) {
    return audio.blob;
  }
  return null;
}

export async function createAudioObjectUrl(url: string): Promise<string | null> {
  const blob = await getCachedAudioBlob(url);
  if (blob) {
    return URL.createObjectURL(blob);
  }
  return null;
}

// =============================================================================
// Preload Implementation
// =============================================================================

async function preloadLessons(language: string, level?: string, count: number = 20): Promise<void> {
  try {
    const params = new URLSearchParams({ language, limit: count.toString() });
    if (level) params.append('level', level);

    const token = localStorage.getItem('access_token');
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`/api/v1/lessons?${params}`, { headers });
    if (!response.ok) throw new Error('Failed to fetch lessons');

    const data = await response.json();
    const lessons = data.lessons || data;

    let completed = 0;
    for (const lesson of lessons.slice(0, count)) {
      await cacheLessonWithContent(lesson);
      completed++;
      emitProgress({ total: count, completed, current: `Cached: ${lesson.title}`, phase: 'lessons' });
    }
  } catch (error) {
    console.error('[Cache] Failed to preload lessons:', error);
  }
}

async function preloadVocabulary(language: string, level?: string, lessonCount: number = 20): Promise<void> {
  try {
    // Get lessons first to know which vocabulary to fetch
    const lessons = await db.lessons
      .where('language')
      .equals(language)
      .and((l) => !level || l.level === level)
      .limit(lessonCount)
      .toArray();

    let totalVocab = 0;
    let completed = 0;

    for (const lesson of lessons) {
      if (lesson.content?.vocabulary) {
        totalVocab += lesson.content.vocabulary.length;
      }
    }

    emitProgress({ total: totalVocab, completed: 0, current: 'Caching vocabulary...', phase: 'vocabulary' });

    for (const lesson of lessons) {
      if (lesson.content?.vocabulary) {
        for (const vocab of lesson.content.vocabulary) {
          await db.vocabulary.put({
            id: vocab.id,
            lesson_id: lesson.id,
            language: lesson.language,
            word: vocab.word,
            translation: vocab.translation,
            audio_url: vocab.audio_url,
            difficulty: vocab.difficulty || 1,
            cached_at: Date.now(),
          });

          if (vocab.audio_url) {
            cacheAudioFromUrl(vocab.audio_url, language).catch(console.error);
          }

          completed++;
          emitProgress({ total: totalVocab, completed, current: `Cached: ${vocab.word}`, phase: 'vocabulary' });
        }
      }
    }
  } catch (error) {
    console.error('[Cache] Failed to preload vocabulary:', error);
  }
}

async function preloadAudio(language: string, level?: string, lessonCount: number = 20): Promise<void> {
  try {
    const lessons = await db.lessons
      .where('language')
      .equals(language)
      .and((l) => !level || l.level === level)
      .limit(lessonCount)
      .toArray();

    const audioUrls = new Set<string>();

    for (const lesson of lessons) {
      if (lesson.content) {
        // Vocabulary audio
        lesson.content.vocabulary?.forEach((v: any) => v.audio_url && audioUrls.add(v.audio_url));
        // Pronunciation exercises
        lesson.content.pronunciation_exercises?.forEach((e: any) => e.audio_url && audioUrls.add(e.audio_url));
        // Dialogue audio
        lesson.content.dialogue?.forEach((d: any) => d.audio_url && audioUrls.add(d.audio_url));
      }
    }

    const urls = Array.from(audioUrls);
    let completed = 0;

    emitProgress({ total: urls.length, completed: 0, current: 'Caching audio...', phase: 'audio' });

    for (const url of urls) {
      await cacheAudioFromUrl(url, language);
      completed++;
      emitProgress({ total: urls.length, completed, current: `Cached audio ${completed}/${urls.length}`, phase: 'audio' });
    }
  } catch (error) {
    console.error('[Cache] Failed to preload audio:', error);
  }
}

async function preloadImages(language: string, level?: string, lessonCount: number = 20): Promise<void> {
  // Images are typically cached by the service worker automatically
  // This is a placeholder for any specific image preloading logic
  console.log('[Cache] Image preloading handled by Service Worker');
}

// =============================================================================
// Fetch Helpers
// =============================================================================

async function fetchLesson(lessonId: number): Promise<any | null> {
  try {
    const token = localStorage.getItem('access_token');
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`/api/v1/lessons/${lessonId}`, { headers });
    if (response.ok) {
      return response.json();
    }
  } catch (error) {
    console.error('[Cache] Failed to fetch lesson:', error);
  }
  return null;
}

// =============================================================================
// Cache Management
// =============================================================================

export async function getCacheInfo(): Promise<{
  stats: Awaited<ReturnType<typeof getCacheStats>>;
  languages: string[];
  levels: string[];
  oldestCache: number | null;
  newestCache: number | null;
}> {
  const stats = await getCacheStats();

  const lessons = await db.lessons.toArray();
  const languages = [...new Set(lessons.map((l) => l.language))];
  const levels = [...new Set(lessons.map((l) => l.level))];

  const cachedAt = lessons.map((l) => l.cached_at);
  const oldestCache = cachedAt.length > 0 ? Math.min(...cachedAt) : null;
  const newestCache = cachedAt.length > 0 ? Math.max(...cachedAt) : null;

  return { stats, languages, levels, oldestCache, newestCache };
}

export async function clearCacheForLanguage(language: string): Promise<void> {
  await db.lessons.where('language').equals(language).delete();
  await db.vocabulary.where('language').equals(language).delete();
  await db.audio.where('language').equals(language).delete();
}

export async function clearCacheForLevel(level: string): Promise<void> {
  const lessons = await db.lessons.where('level').equals(level).toArray();
  const lessonIds = lessons.map((l) => l.id);

  await db.lessons.where('level').equals(level).delete();
  await db.vocabulary.where('lesson_id').anyOf(lessonIds).delete();
  // Audio is shared, don't delete by level
}

export async function enforceCacheLimit(maxSizeMB: number = 500): Promise<void> {
  const { stats } = await getCacheInfo();
  if (stats.totalSizeMB > maxSizeMB) {
    // Remove oldest cached content first
    const lessons = await db.lessons.orderBy('cached_at').toArray();
    const toRemove = lessons.slice(0, Math.ceil(lessons.length * 0.3)); // Remove 30% oldest

    for (const lesson of toRemove) {
      await db.lessons.delete(lesson.id);
      await db.vocabulary.where('lesson_id').equals(lesson.id).delete();
    }
  }
}

// =============================================================================
// Smart Caching (Based on User Behavior)
// =============================================================================

export async function recordLessonAccess(lessonId: number): Promise<void> {
  // Track which lessons user accesses for predictive caching
  const key = 'lesson_access_history';
  const history = (await db.settings.get(key))?.value || [];
  history.unshift({ lessonId, timestamp: Date.now() });
  // Keep last 100
  await db.settings.put({ key, value: history.slice(0, 100), updated_at: Date.now() });
}

export async function predictAndPreload(): Promise<void> {
  const history = (await db.settings.get('lesson_access_history'))?.value || [];
  if (history.length < 3) return;

  // Simple prediction: cache next lesson in sequence
  const recent = history.slice(0, 5);
  const lessonIds = recent.map((h: any) => h.lessonId);

  // Find patterns (simplified)
  for (let i = 0; i < lessonIds.length - 1; i++) {
    const current = lessonIds[i];
    const next = lessonIds[i + 1];
    // If user consistently goes from lesson N to N+1, preload N+1
    if (next === current + 1) {
      const cached = await db.lessons.get(next);
      if (!cached || cached.expires_at < Date.now()) {
        cacheCurrentLesson(next).catch(console.error);
      }
    }
  }
}

// =============================================================================
// Progress Emission
// =============================================================================

function emitProgress(progress: CacheProgress): void {
  progressListeners.forEach((listener) => listener(progress));
}

// =============================================================================
// Offline Fallback API
// =============================================================================

export async function getOfflineLesson(lessonId: number): Promise<any | null> {
  return getCachedLessonContent(lessonId);
}

export async function getOfflineVocabulary(lessonId: number): Promise<any[]> {
  return getCachedVocabularyForLesson(lessonId);
}

export async function playOfflineAudio(url: string): Promise<HTMLAudioElement | null> {
  const blob = await getCachedAudioBlob(url);
  if (blob) {
    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);
    return audio;
  }
  return null;
}

// =============================================================================
// Export for Service Worker Communication
// =============================================================================

export async function sendToSW(type: string, data: any): Promise<void> {
  if ('serviceWorker' in navigator) {
    const registration = await navigator.serviceWorker.ready;
    registration.active?.postMessage({ type, ...data });
  }
}