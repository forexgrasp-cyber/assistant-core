/**
 * Providers for the app
 */

'use client';

import { ReactNode, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { useAppStore } from '@/store';
import { ThemeProvider } from 'next-themes';

export function Providers({ children }: { children: ReactNode }) {
  const { theme, setTheme, isAuthenticated, user } = useAppStore();
  
  // Apply theme on mount
  useEffect(() => {
    if (theme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.classList.toggle('dark', prefersDark);
    } else {
      document.documentElement.classList.toggle('dark', theme === 'dark');
    }
  }, [theme]);

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'var(--background)',
            color: 'var(--foreground)',
            border: '1px solid var(--border)',
            borderRadius: '0.5rem',
            padding: '1rem',
          },
          success: {
            iconTheme: {
              primary: '#22c55e',
              secondary: 'white',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: 'white',
            },
          },
        }}
      />
    </ThemeProvider>
  );
}