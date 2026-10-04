const CACHE = 'play-web-station-v3';
const CORE = ['/', '/index.html', '/Play.js', '/Play.wasm', '/vendor/playjs/main.js', '/vendor/playjs/main.css', '/manifest.webmanifest'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => cache.addAll(CORE))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) return;

  event.respondWith((async () => {
    try {
      const cached = await caches.match(event.request);
      if (cached) return cached;
    } catch (_) {
      // CacheStorage can reject for some browser-managed requests; use the network.
    }

    const response = await fetch(event.request);
    if (response && response.ok) {
      try {
        const copy = response.clone();
        const cache = await caches.open(CACHE);
        await cache.put(event.request, copy);
      } catch (_) {
        // Caching is optional; never block the page or emulator on it.
      }
    }
    return response;
  })());
});
