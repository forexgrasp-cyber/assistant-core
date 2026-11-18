/**
 * React Hooks for Offline-First PWA
 * Provides offline status, cache management, and sync state
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getSyncStatus, subscribeToSyncStatus, forceSync, startSyncScheduler, stopSyncScheduler } from '../services/offline/sync';
import { subscribeToCacheProgress, CacheProgress, getCacheInfo } from '../services/offline/cache';
import { db, getCacheStats } from '../services/offline/db';

// =============================================================================
// Types
// =============================================================================

export interface OfflineState {
  isOnline: boolean;
  isSyncing: boolean;
  lastSync: Date | null;
  pendingCount: number;
  nextRetry: Date | null;
}

export interface CacheState {
  lessons: number;
  vocabulary: number;
  audio: number;
  audioSizeMB: number;
  mutations: number;
  totalSizeMB: number;
  languages: string[];
  levels: string[];
}

export interface UseOfflineReturn extends OfflineState {
  syncNow: () => Promise<void>;
  clearCache: () => Promise<void>;
  cacheStats: CacheState;
  refreshCacheStats: () => Promise<void>;
  preloadLanguage: (language: string, level?: string) => Promise<void>;
  isPreloading: boolean;
  preloadProgress: CacheProgress | null;
}

// =============================================================================
// Hooks
// =============================================================================

export function useOffline(): UseOfflineReturn {
  const [state, setState] = useState<OfflineState>({
    isOnline: navigator.onLine,
    isSyncing: false,
    lastSync: null,
    pendingCount: 0,
    nextRetry: null,
  });

  const [cacheStats, setCacheStats] = useState<CacheState>({
    lessons: 0,
    vocabulary: 0,
    audio: 0,
    audioSizeMB: 0,
    mutations: 0,
    totalSizeMB: 0,
    languages: [],
    levels: [],
  });

  const [isPreloading, setIsPreloading] = useState(false);
  const [preloadProgress, setPreloadProgress] = useState<CacheProgress | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const cacheUnsubscribeRef = useRef<(() => void) | null>(null);

  // Initialize
  useEffect(() => {
    // Start sync scheduler
    startSyncScheduler();

    // Subscribe to sync status
    unsubscribeRef.current = subscribeToSyncStatus((status) => {
      setState({
        isOnline: status.isOnline,
        isSyncing: status.isSyncing,
        lastSync: status.lastSync ? new Date(status.lastSync) : null,
        pendingCount: status.pendingCount,
        nextRetry: status.nextRetry ? new Date(status.nextRetry) : null,
      });
    });

    // Subscribe to cache progress
    cacheUnsubscribeRef.current = subscribeToCacheProgress((progress) => {
      setPreloadProgress(progress);
      setIsPreloading(progress.phase !== 'complete');
    });

    // Initial cache stats
    refreshCacheStats();

    // Listen for online/offline
    const handleOnline = () => setState((s) => ({ ...s, isOnline: true }));
    const handleOffline = () => setState((s) => ({ ...s, isOnline: false }));
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      stopSyncScheduler();
      unsubscribeRef.current?.();
      cacheUnsubscribeRef.current?.();
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const syncNow = useCallback(async () => {
    await forceSync();
  }, []);

  const clearCache = useCallback(async () => {
    await Promise.all([
      db.lessons.clear(),
      db.vocabulary.clear(),
      db.audio.clear(),
      db.practiceSessions.clear(),
    ]);
    await refreshCacheStats();
  }, []);

  const refreshCacheStats = useCallback(async () => {
    const info = await getCacheInfo();
    setCacheStats({
      lessons: info.stats.lessons,
      vocabulary: info.stats.vocabulary,
      audio: info.stats.audio,
      audioSizeMB: info.stats.audioSizeMB,
      mutations: info.stats.mutations,
      totalSizeMB: info.stats.totalSizeMB,
      languages: info.languages,
      levels: info.levels,
    });
  }, []);

  const preloadLanguage = useCallback(async (language: string, level?: string) => {
    setIsPreloading(true);
    setPreloadProgress({ total: 1, completed: 0, current: 'Starting...', phase: 'lessons' });
    try {
      const { preloadLanguageContent } = await import('../services/offline/cache');
      await preloadLanguageContent({ language, level });
    } finally {
      setIsPreloading(false);
      setPreloadProgress(null);
      await refreshCacheStats();
    }
  }, [refreshCacheStats]);

  return {
    ...state,
    syncNow,
    clearCache,
    cacheStats,
    refreshCacheStats,
    preloadLanguage,
    isPreloading,
    preloadProgress,
  };
}

// =============================================================================
// Specialized Hooks
// =============================================================================

export function useOnlineStatus(): boolean {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

export function useSyncStatus(): OfflineState {
  const [status, setStatus] = useState<OfflineState>({
    isOnline: navigator.onLine,
    isSyncing: false,
    lastSync: null,
    pendingCount: 0,
    nextRetry: null,
  });

  useEffect(() => {
    const unsubscribe = subscribeToSyncStatus((s) => {
      setStatus({
        isOnline: s.isOnline,
        isSyncing: s.isSyncing,
        lastSync: s.lastSync ? new Date(s.lastSync) : null,
        pendingCount: s.pendingCount,
        nextRetry: s.nextRetry ? new Date(s.nextRetry) : null,
      });
    });
    return unsubscribe;
  }, []);

  return status;
}

export function useCacheStats(): CacheState & { refresh: () => Promise<void> } {
  const [stats, setStats] = useState<CacheState>({
    lessons: 0,
    vocabulary: 0,
    audio: 0,
    audioSizeMB: 0,
    mutations: 0,
    totalSizeMB: 0,
    languages: [],
    levels: [],
  });

  const refresh = useCallback(async () => {
    const info = await getCacheInfo();
    setStats({
      lessons: info.stats.lessons,
      vocabulary: info.stats.vocabulary,
      audio: info.stats.audio,
      audioSizeMB: info.stats.audioSizeMB,
      mutations: info.stats.mutations,
      totalSizeMB: info.stats.totalSizeMB,
      languages: info.languages,
      levels: info.levels,
    });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { ...stats, refresh };
}

export function usePreloadLanguage(): {
  preload: (language: string, level?: string) => Promise<void>;
  isPreloading: boolean;
  progress: CacheProgress | null;
} {
  const [isPreloading, setIsPreloading] = useState(false);
  const [progress, setProgress] = useState<CacheProgress | null>(null);

  const preload = useCallback(async (language: string, level?: string) => {
    setIsPreloading(true);
    setProgress({ total: 1, completed: 0, current: 'Starting...', phase: 'lessons' });

    try {
      const { preloadLanguageContent } = await import('../services/offline/cache');
      const { subscribeToCacheProgress } = await import('../services/offline/cache');

      const unsubscribe = subscribeToCacheProgress((p) => {
        setProgress(p);
        setIsPreloading(p.phase !== 'complete');
      });

      await preloadLanguageContent({ language, level });
      unsubscribe();
    } finally {
      setIsPreloading(false);
      setProgress(null);
    }
  }, []);

  return { preload, isPreloading, progress };
}

export function useOfflineLesson(lessonId: number): {
  lesson: any | null;
  isLoading: boolean;
  error: Error | null;
} {
  const [lesson, setLesson] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const isOnline = useOnlineStatus();

  useEffect(() => {
    let mounted = true;

    async function loadLesson() {
      setIsLoading(true);
      setError(null);

      try {
        if (isOnline) {
          // Try network first
          try {
            const token = localStorage.getItem('access_token');
            const headers: HeadersInit = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const response = await fetch(`/api/v1/lessons/${lessonId}`, { headers });
            if (response.ok) {
              const data = await response.json();
              if (mounted) setLesson(data);
              // Cache for offline
              const { cacheLessonWithContent } = await import('../services/offline/cache');
              await cacheLessonWithContent(data);
              return;
            }
          } catch (netError) {
            console.warn('[Offline] Network fetch failed, trying cache:', netError);
          }
        }

        // Fallback to cache
        const { getOfflineLesson } = await import('../services/offline/cache');
        const cached = await getOfflineLesson(lessonId);
        if (mounted) {
          if (cached) {
            setLesson(cached);
          } else {
            setError(new Error('Lesson not available offline'));
          }
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err : new Error('Failed to load lesson'));
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    loadLesson();

    return () => {
      mounted = false;
    };
  }, [lessonId, isOnline]);

  return { lesson, isLoading, error };
}

export function useOfflineVocabulary(lessonId: number): {
  vocabulary: any[];
  isLoading: boolean;
} {
  const [vocabulary, setVocabulary] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const isOnline = useOnlineStatus();

  useEffect(() => {
    let mounted = true;

    async function loadVocabulary() {
      setIsLoading(true);

      try {
        if (isOnline) {
          try {
            const token = localStorage.getItem('access_token');
            const headers: HeadersInit = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const response = await fetch(`/api/v1/lessons/${lessonId}/vocabulary`, { headers });
            if (response.ok) {
              const data = await response.json();
              if (mounted) setVocabulary(data.vocabulary || data);
              return;
            }
          } catch (netError) {
            console.warn('[Offline] Network fetch failed, trying cache:', netError);
          }
        }

        const { getOfflineVocabulary } = await import('../services/offline/cache');
        const cached = await getOfflineVocabulary(lessonId);
        if (mounted) setVocabulary(cached);
      } catch (err) {
        console.error('[Offline] Failed to load vocabulary:', err);
        if (mounted) setVocabulary([]);
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    loadVocabulary();

    return () => {
      mounted = false;
    };
  }, [lessonId, isOnline]);

  return { vocabulary, isLoading };
}

export function useOfflineAudio(audioUrl: string): {
  audioUrl: string | null;
  isLoading: boolean;
  play: () => Promise<void>;
} {
  const [cachedAudioUrl, setCachedAudioUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const isOnline = useOnlineStatus();

  const loadAudio = useCallback(async () => {
    setIsLoading(true);
    try {
      const { createAudioObjectUrl, cacheAudioFromUrl } = await import('../services/offline/cache');

      // Try cache first
      let url = await createAudioObjectUrl(audioUrl);

      if (!url && isOnline) {
        // Fetch and cache
        try {
          const response = await fetch(audioUrl);
          if (response.ok) {
            const blob = await response.blob();
            await cacheAudioFromUrl(audioUrl, 'unknown');
            url = URL.createObjectURL(blob);
          }
        } catch (err) {
          console.warn('[Offline] Failed to fetch audio:', err);
        }
      }

      setCachedAudioUrl(url);
    } finally {
      setIsLoading(false);
    }
  }, [audioUrl, isOnline]);

  const play = useCallback(async () => {
    if (cachedAudioUrl) {
      const audio = new Audio(cachedAudioUrl);
      await audio.play();
    } else {
      await loadAudio();
      if (cachedAudioUrl) {
        const audio = new Audio(cachedAudioUrl);
        await audio.play();
      }
    }
  }, [cachedAudioUrl, loadAudio]);

  useEffect(() => {
    loadAudio();
    return () => {
      if (cachedAudioUrl) URL.revokeObjectURL(cachedAudioUrl);
    };
  }, [audioUrl]);

  return { audioUrl: cachedAudioUrl, isLoading, play };
}

// =============================================================================
// Utility Hook for Components that Need Offline Awareness
// =============================================================================

export function useOfflineAware<T>(
  onlineFn: () => Promise<T>,
  offlineFn: () => Promise<T | null>,
  deps: any[] = []
): { data: T | null; isLoading: boolean; error: Error | null; isOnline: boolean } {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const isOnline = useOnlineStatus();

  useEffect(() => {
    let mounted = true;

    async function execute() {
      setIsLoading(true);
      setError(null);

      try {
        if (isOnline) {
          try {
            const result = await onlineFn();
            if (mounted) setData(result);
            return;
          } catch (netError) {
            console.warn('[OfflineAware] Online function failed:', netError);
          }
        }

        const result = await offlineFn();
        if (mounted) setData(result);
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err : new Error('Operation failed'));
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    execute();

    return () => {
      mounted = false;
    };
  }, [isOnline, ...deps]);

  return { data, isLoading, error, isOnline };
}