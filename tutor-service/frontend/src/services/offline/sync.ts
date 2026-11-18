/**
 * Background Sync Service for Offline-First PWA
 * Handles queuing mutations and syncing when online
 */

import { db, PendingMutation, getPendingMutations, removeMutation, retryMutation } from './db';

// =============================================================================
// Types
// =============================================================================

export interface SyncResult {
  success: boolean;
  synced: number;
  failed: number;
  errors: string[];
}

export interface SyncStatus {
  isOnline: boolean;
  isSyncing: boolean;
  lastSync: number | null;
  pendingCount: number;
  nextRetry: number | null;
}

// =============================================================================
// State
// =============================================================================

let syncStatus: SyncStatus = {
  isOnline: navigator.onLine,
  isSyncing: false,
  lastSync: null,
  pendingCount: 0,
  nextRetry: null,
};

const statusListeners: Set<(status: SyncStatus) => void> = new Set();
let syncInterval: ReturnType<typeof setInterval> | null = null;
const SYNC_INTERVAL = 30000; // 30 seconds
const MAX_RETRIES = 3;

// =============================================================================
// Public API
// =============================================================================

export function getSyncStatus(): SyncStatus {
  return { ...syncStatus };
}

export function subscribeToSyncStatus(listener: (status: SyncStatus) => void): () => void {
  statusListeners.add(listener);
  listener(syncStatus);
  return () => statusListeners.delete(listener);
}

export async function startSyncScheduler(): Promise<void> {
  if (syncInterval) return;

  // Initial sync
  await performSync();

  // Periodic sync
  syncInterval = setInterval(() => {
    if (syncStatus.isOnline && !syncStatus.isSyncing) {
      performSync();
    }
  }, SYNC_INTERVAL);

  // Listen for online/offline events
  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);

  // Listen for visibility change (sync when tab becomes visible)
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && syncStatus.isOnline && !syncStatus.isSyncing) {
      performSync();
    }
  });
}

export function stopSyncScheduler(): void {
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
  }
  window.removeEventListener('online', handleOnline);
  window.removeEventListener('offline', handleOffline);
}

export async function forceSync(): Promise<SyncResult> {
  if (!syncStatus.isOnline) {
    return { success: false, synced: 0, failed: 0, errors: ['Offline'] };
  }
  return performSync();
}

export async function queueForSync(
  type: PendingMutation['type'],
  url: string,
  method: string,
  body: any,
  headers: Record<string, string> = {}
): Promise<number> {
  const token = localStorage.getItem('access_token');
  const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};

  return db.pendingMutations.add({
    type,
    url,
    method,
    headers: { ...authHeaders, 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
    timestamp: Date.now(),
    retry_count: 0,
  });
}

// =============================================================================
// Core Sync Logic
// =============================================================================

async function performSync(): Promise<SyncResult> {
  if (syncStatus.isSyncing || !syncStatus.isOnline) {
    return { success: false, synced: 0, failed: 0, errors: ['Already syncing or offline'] };
  }

  updateSyncStatus({ isSyncing: true });

  const mutations = await getPendingMutations();
  const result: SyncResult = {
    success: true,
    synced: 0,
    failed: 0,
    errors: [],
  };

  for (const mutation of mutations) {
    if (!navigator.onLine) {
      updateSyncStatus({ isOnline: false });
      break;
    }

    try {
      const response = await fetch(mutation.url, {
        method: mutation.method,
        headers: mutation.headers,
        body: mutation.body,
      });

      if (response.ok) {
        await removeMutation(mutation.id!);
        result.synced++;
      } else if (response.status === 401) {
        // Token expired - clear auth and stop syncing
        await clearAuthToken();
        result.errors.push('Authentication expired');
        result.failed++;
        break;
      } else if (response.status >= 500) {
        // Server error - retry later
        await retryMutation(mutation.id!);
        result.errors.push(`Server error: ${response.status}`);
        result.failed++;
      } else {
        // Client error (4xx) - don't retry, remove
        await removeMutation(mutation.id!);
        result.errors.push(`Client error: ${response.status}`);
        result.failed++;
      }
    } catch (error) {
      // Network error - retry later
      await retryMutation(mutation.id!);
      result.errors.push(`Network error: ${error instanceof Error ? error.message : 'Unknown'}`);
      result.failed++;
    }
  }

  // Clean up old failed mutations (exceeded max retries)
  const allMutations = await getPendingMutations();
  for (const mutation of allMutations) {
    if (mutation.retry_count >= MAX_RETRIES) {
      await removeMutation(mutation.id!);
      result.errors.push(`Max retries exceeded for ${mutation.type}`);
    }
  }

  updateSyncStatus({
    isSyncing: false,
    lastSync: Date.now(),
    pendingCount: (await getPendingMutations()).length,
    nextRetry: Date.now() + SYNC_INTERVAL,
  });

  return result;
}

// =============================================================================
// Event Handlers
// =============================================================================

function handleOnline(): void {
  console.log('[Sync] Back online');
  updateSyncStatus({ isOnline: true });
  performSync();
}

function handleOffline(): void {
  console.log('[Sync] Gone offline');
  updateSyncStatus({ isOnline: false });
}

function updateSyncStatus(partial: Partial<SyncStatus>): void {
  syncStatus = { ...syncStatus, ...partial };
  statusListeners.forEach((listener) => listener(syncStatus));
}

// =============================================================================
// Specific Mutation Helpers
// =============================================================================

export async function queueLessonProgress(
  lessonId: number,
  progress: {
    completed: boolean;
    score: number;
    time_spent: number;
    answers: any[];
  }
): Promise<void> {
  await queueForSync('lesson_progress', `/api/v1/progress/lessons/${lessonId}`, 'PUT', progress);
}

export async function queueVocabularyReview(
  vocabId: number,
  data: {
    correct: boolean;
    response_time: number;
  }
): Promise<void> {
  await queueForSync('vocabulary', `/api/v1/vocabulary/${vocabId}/review`, 'POST', data);
}

export async function queuePracticeSession(
  session: {
    language: string;
    session_type: string;
    exercises: any[];
    score: number;
    duration: number;
  }
): Promise<void> {
  await queueForSync('practice_session', '/api/v1/practice/sessions', 'POST', session);
}

export async function queueStreakUpdate(
  userId: number,
  activityDate: string
): Promise<void> {
  await queueForSync('streak', `/api/v1/gamification/streak/activity`, 'POST', { activity_date: activityDate });
}

export async function queueXPAward(
  userId: number,
  amount: number,
  source: string
): Promise<void> {
  await queueForSync('xp', `/api/v1/gamification/xp/award`, 'POST', { amount, source });
}

export async function queueAchievementUnlock(
  achievementId: string
): Promise<void> {
  await queueForSync('achievement', `/api/v1/gamification/achievements/check`, 'POST', {});
}

export async function queueSettingsUpdate(
  settings: Record<string, any>
): Promise<void> {
  await queueForSync('settings', '/api/v1/users/me/settings', 'PUT', settings);
}

// =============================================================================
// Retry Logic with Exponential Backoff
// =============================================================================

export function scheduleRetry(attempt: number): number {
  // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
  const delays = [1000, 2000, 4000, 8000, 16000, 30000];
  return delays[Math.min(attempt, delays.length - 1)];
}

// =============================================================================
// Auth Token Helpers
// =============================================================================

function getAuthTokenFromStorage(): string | null {
  return localStorage.getItem('access_token');
}

async function clearAuthToken(): Promise<void> {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  // Redirect to login if needed
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

// =============================================================================
// Register Background Sync (Service Worker)
// =============================================================================

export async function registerBackgroundSync(tag: string): Promise<void> {
  if ('serviceWorker' in navigator && 'sync' in (navigator as any).serviceWorker?.registration) {
    const registration = await navigator.serviceWorker.ready;
    try {
      await (registration as any).sync.register(tag);
      console.log('[Sync] Registered background sync:', tag);
    } catch (error) {
      console.error('[Sync] Failed to register background sync:', error);
    }
  }
}

// =============================================================================
// Initialize
// =============================================================================

// Auto-start sync scheduler when module loads (in browser)
if (typeof window !== 'undefined') {
  // Defer to avoid blocking main thread
  setTimeout(() => {
    startSyncScheduler().catch(console.error);
  }, 1000);
}