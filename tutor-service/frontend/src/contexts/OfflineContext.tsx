/**
 * Offline Context Provider
 * Provides offline state and actions to the entire app
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { useOffline, useOnlineStatus } from '../hooks/useOffline';

// =============================================================================
// Types
// =============================================================================

interface OfflineContextType {
  // State
  isOnline: boolean;
  isSyncing: boolean;
  lastSync: Date | null;
  pendingCount: number;
  cacheStats: {
    lessons: number;
    vocabulary: number;
    audio: number;
    audioSizeMB: number;
    mutations: number;
    totalSizeMB: number;
    languages: string[];
    levels: string[];
  };
  isPreloading: boolean;
  preloadProgress: {
    total: number;
    completed: number;
    current: string;
    phase: 'lessons' | 'vocabulary' | 'audio' | 'images' | 'complete';
  } | null;

  // Actions
  syncNow: () => Promise<void>;
  clearCache: () => Promise<void>;
  refreshCacheStats: () => Promise<void>;
  preloadLanguage: (language: string, level?: string) => Promise<void>;
  installApp: () => Promise<void>;
  canInstall: boolean;
}

// =============================================================================
// Context
// =============================================================================

const OfflineContext = createContext<OfflineContextType | null>(null);

// =============================================================================
// Provider
// =============================================================================

export function OfflineProvider({ children }: { children: ReactNode }) {
  const {
    isOnline,
    isSyncing,
    lastSync,
    pendingCount,
    cacheStats,
    refreshCacheStats,
    syncNow,
    clearCache,
    preloadLanguage,
    isPreloading,
    preloadProgress,
  } = useOffline();

  // Force re-render when online status changes
  const [, setTick] = useState(0);
  useEffect(() => {
    const handleOnline = () => setTick(t => t + 1);
    const handleOffline = () => setTick(t => t + 1);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Expose install prompt
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const installApp = useCallback(async () => {
    if (installPrompt) {
      await installPrompt.prompt();
      const choice = await installPrompt.userChoice;
      if (choice.outcome === 'accepted') {
        setInstallPrompt(null);
      }
    }
  }, [installPrompt]);

  return (
    <OfflineContext.Provider value={{
      isOnline,
      isSyncing,
      lastSync,
      pendingCount,
      cacheStats,
      isPreloading,
      preloadProgress,
      syncNow,
      clearCache,
      refreshCacheStats,
      preloadLanguage,
      installApp,
      canInstall: !!installPrompt,
    }}>
      {children}
    </OfflineContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

export function useOfflineContext(): OfflineContextType {
  const context = useContext(OfflineContext);
  if (!context) {
    throw new Error('useOfflineContext must be used within an OfflineProvider');
  }
  return context;
}

// =============================================================================
// Type for install prompt
// =============================================================================

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}