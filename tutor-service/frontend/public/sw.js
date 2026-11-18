/* Service Worker for Offline-First PWA */
/* Generated with Workbox patterns - caches assets, API responses, and enables background sync */

const CACHE_NAME = 'tutor-pwa-v1';
const STATIC_CACHE = 'tutor-static-v1';
const API_CACHE = 'tutor-api-v1';
const AUDIO_CACHE = 'tutor-audio-v1';
const IMAGE_CACHE = 'tutor-images-v1';

// Cache strategies
const CACHE_STRATEGIES = {
  // Cache first - for static assets (JS, CSS, fonts)
  static: ['/assets/', '/fonts/', '/favicon.ico', '/manifest.json'],
  // Network first - for API calls
  api: ['/api/v1/'],
  // Stale while revalidate - for lessons content
  lessons: ['/api/v1/lessons/', '/api/v1/generation/'],
  // Cache first - for audio files (TTS, pronunciation)
  audio: ['/api/v1/voice/preview', '/api/v1/lessons/', '.mp3', '.wav', '.ogg', '.webm'],
  // Cache first - for images
  images: ['/images/', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.avif'],
};

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll([
        '/',
        '/index.html',
        '/manifest.json',
        '/offline.html',
      ]);
    }).then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => !name.startsWith('tutor-'))
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http(s) requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Determine cache strategy based on URL
  const strategy = getCacheStrategy(url.pathname, url.search);

  switch (strategy) {
    case 'cache-first':
      event.respondWith(cacheFirst(request, STATIC_CACHE));
      break;
    case 'network-first':
      event.respondWith(networkFirst(request, API_CACHE));
      break;
    case 'stale-while-revalidate':
      event.respondWith(staleWhileRevalidate(request, API_CACHE));
      break;
    case 'audio-cache':
      event.respondWith(cacheFirst(request, AUDIO_CACHE));
      break;
    case 'image-cache':
      event.respondWith(cacheFirst(request, IMAGE_CACHE));
      break;
    default:
      event.respondWith(networkFirst(request, API_CACHE));
  }
});

// Background Sync for offline mutations
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-lesson-progress') {
    event.waitUntil(syncLessonProgress());
  } else if (event.tag === 'sync-vocabulary') {
    event.waitUntil(syncVocabulary());
  } else if (event.tag === 'sync-practice-session') {
    event.waitUntil(syncPracticeSession());
  } else if (event.tag === 'sync-achievement') {
    event.waitUntil(syncAchievements());
  }
});

// Push notifications
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body || 'New update from Tutor!',
    icon: data.icon || '/icons/icon-192.png',
    badge: '/icons/badge-72.png',
    vibrate: [100, 50, 100],
    data: data.data || {},
    actions: data.actions || [
      { action: 'open', title: 'Open App' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
    requireInteraction: data.requireInteraction || false,
    tag: data.tag || 'tutor-notification',
    renotify: true,
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'Tutor', options)
  );
});

// Notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

// =============================================================================
// Cache Strategy Implementations
// =============================================================================

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }
    throw error;
  }
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }
    // Return mock response for API calls
    return new Response(JSON.stringify({ error: 'Offline', cached: false }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request).then((response) => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => cached);

  return cached || fetchPromise;
}

function getCacheStrategy(pathname, search) {
  // Static assets
  if (CACHE_STRATEGIES.static.some((p) => pathname.startsWith(p))) {
    return 'cache-first';
  }

  // Audio files
  if (CACHE_STRATEGIES.audio.some((p) => pathname.includes(p) || search.includes(p))) {
    return 'audio-cache';
  }

  // Images
  if (CACHE_STRATEGIES.images.some((p) => pathname.includes(p))) {
    return 'image-cache';
  }

  // Lessons content (stale while revalidate)
  if (CACHE_STRATEGIES.lessons.some((p) => pathname.startsWith(p))) {
    return 'stale-while-revalidate';
  }

  // API calls (network first)
  if (CACHE_STRATEGIES.api.some((p) => pathname.startsWith(p))) {
    return 'network-first';
  }

  // Default: network first
  return 'network-first';
}

// =============================================================================
// Background Sync Functions
// =============================================================================

async function syncLessonProgress() {
  const db = await openIndexedDB();
  const tx = db.transaction('pending_mutations', 'readwrite');
  const store = tx.objectStore('pending_mutations');

  const mutations = await getAllFromStore(store, 'lesson_progress');

  for (const mutation of mutations) {
    try {
      const response = await fetch(mutation.url, {
        method: mutation.method,
        headers: mutation.headers,
        body: mutation.body,
      });

      if (response.ok) {
        await deleteFromStore(store, mutation.id);
        console.log('[SW] Synced lesson progress:', mutation.id);
      }
    } catch (error) {
      console.error('[SW] Failed to sync lesson progress:', error);
    }
  }

  await tx.done;
}

async function syncVocabulary() {
  const db = await openIndexedDB();
  const tx = db.transaction('pending_mutations', 'readwrite');
  const store = tx.objectStore('pending_mutations');

  const mutations = await getAllFromStore(store, 'vocabulary');

  for (const mutation of mutations) {
    try {
      const response = await fetch(mutation.url, {
        method: mutation.method,
        headers: mutation.headers,
        body: mutation.body,
      });

      if (response.ok) {
        await deleteFromStore(store, mutation.id);
        console.log('[SW] Synced vocabulary:', mutation.id);
      }
    } catch (error) {
      console.error('[SW] Failed to sync vocabulary:', error);
    }
  }

  await tx.done;
}

async function syncPracticeSession() {
  const db = await openIndexedDB();
  const tx = db.transaction('pending_mutations', 'readwrite');
  const store = tx.objectStore('pending_mutations');

  const mutations = await getAllFromStore(store, 'practice_session');

  for (const mutation of mutations) {
    try {
      const response = await fetch(mutation.url, {
        method: mutation.method,
        headers: mutation.headers,
        body: mutation.body,
      });

      if (response.ok) {
        await deleteFromStore(store, mutation.id);
        console.log('[SW] Synced practice session:', mutation.id);
      }
    } catch (error) {
      console.error('[SW] Failed to sync practice session:', error);
    }
  }

  await tx.done;
}

async function syncAchievements() {
  const db = await openIndexedDB();
  const tx = db.transaction('pending_mutations', 'readwrite');
  const store = tx.objectStore('pending_mutations');

  const mutations = await getAllFromStore(store, 'achievement');

  for (const mutation of mutations) {
    try {
      const response = await fetch(mutation.url, {
        method: mutation.method,
        headers: mutation.headers,
        body: mutation.body,
      });

      if (response.ok) {
        await deleteFromStore(store, mutation.id);
        console.log('[SW] Synced achievement:', mutation.id);
      }
    } catch (error) {
      console.error('[SW] Failed to sync achievement:', error);
    }
  }

  await tx.done;
}

// =============================================================================
// IndexedDB Helpers
// =============================================================================

function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('TutorPWA', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // Lessons cache
      if (!db.objectStoreNames.contains('lessons')) {
        db.createObjectStore('lessons', { keyPath: 'id' });
      }

      // Vocabulary cache
      if (!db.objectStoreNames.contains('vocabulary')) {
        const vocabStore = db.createObjectStore('vocabulary', { keyPath: 'id' });
        vocabStore.createIndex('lesson_id', 'lesson_id', { unique: false });
        vocabStore.createIndex('language', 'language', { unique: false });
      }

      // User progress cache
      if (!db.objectStoreNames.contains('user_progress')) {
        db.createObjectStore('user_progress', { keyPath: 'user_id' });
      }

      // Audio cache
      if (!db.objectStoreNames.contains('audio')) {
        db.createObjectStore('audio', { keyPath: 'url' });
      }

      // Pending mutations for background sync
      if (!db.objectStoreNames.contains('pending_mutations')) {
        const mutStore = db.createObjectStore('pending_mutations', { keyPath: 'id', autoIncrement: true });
        mutStore.createIndex('type', 'type', { unique: false });
        mutStore.createIndex('timestamp', 'timestamp', { unique: false });
      }

      // Settings cache
      if (!db.objectStoreNames.contains('settings')) {
        db.createObjectStore('settings', { keyPath: 'key' });
      }
    };
  });
}

function getAllFromStore(store, type) {
  return new Promise((resolve, reject) => {
    const index = store.index('type');
    const request = index.getAll(type);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function deleteFromStore(store, id) {
  return new Promise((resolve, reject) => {
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// =============================================================================
// Message Handling (for communication with main thread)
// =============================================================================

self.addEventListener('message', (event) => {
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  } else if (event.data.type === 'CACHE_LESSON') {
    cacheLesson(event.data.lesson);
  } else if (event.data.type === 'CACHE_VOCABULARY') {
    cacheVocabulary(event.data.vocabulary);
  } else if (event.data.type === 'CACHE_AUDIO') {
    cacheAudio(event.data.url, event.data.blob);
  } else if (event.data.type === 'QUEUE_MUTATION') {
    queueMutation(event.data.mutation);
  } else if (event.data.type === 'GET_CACHED_LESSONS') {
    getCachedLessons().then((lessons) => {
      event.ports[0].postMessage({ lessons });
    });
  }
});

async function cacheLesson(lesson) {
  const db = await openIndexedDB();
  const tx = db.transaction('lessons', 'readwrite');
  const store = tx.objectStore('lessons');
  store.put(lesson);
  await tx.done;
}

async function cacheVocabulary(vocab) {
  const db = await openIndexedDB();
  const tx = db.transaction('vocabulary', 'readwrite');
  const store = tx.objectStore('vocabulary');
  store.put(vocab);
  await tx.done;
}

async function cacheAudio(url, blob) {
  const db = await openIndexedDB();
  const tx = db.transaction('audio', 'readwrite');
  const store = tx.objectStore('audio');
  store.put({ url, blob, timestamp: Date.now() });
  await tx.done;
}

async function queueMutation(mutation) {
  const db = await openIndexedDB();
  const tx = db.transaction('pending_mutations', 'readwrite');
  const store = tx.objectStore('pending_mutations');
  store.add({
    ...mutation,
    timestamp: Date.now(),
  });
  await tx.done;

  // Register background sync
  if ('serviceWorker' in navigator && 'sync' in self.registration) {
    self.registration.sync.register(`sync-${mutation.type}`);
  }
}

async function getCachedLessons() {
  const db = await openIndexedDB();
  const tx = db.transaction('lessons', 'readonly');
  const store = tx.objectStore('lessons');
  return new Promise((resolve, reject) => {
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

console.log('[SW] Service Worker loaded');