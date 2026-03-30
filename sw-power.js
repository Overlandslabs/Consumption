// LC76 Power Budget Calculator — Service Worker
// Cache-first strategy for offline use in the field
const CACHE = 'lc76-power-v1';
const ASSETS = [
  './LC76_LiFePO4_Calculator.html',
  './manifest-power.json',
  './icon-power-192.svg',
  './icon-power-512.svg',
  'https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;500;600;700&display=swap'
];

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE).then(function(cache) {
      return cache.addAll(ASSETS.map(url => new Request(url, {mode: 'no-cors'})))
        .catch(function() {
          // Fonts may fail offline — cache rest only
          return cache.addAll([
            './LC76_LiFePO4_Calculator.html',
            './manifest-power.json',
            './icon-power-192.svg',
            './icon-power-512.svg'
          ]);
        });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE; })
            .map(function(k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  e.respondWith(
    caches.match(e.request).then(function(cached) {
      if (cached) return cached;
      return fetch(e.request).then(function(response) {
        if (!response || response.status !== 200) return response;
        var clone = response.clone();
        caches.open(CACHE).then(function(cache) { cache.put(e.request, clone); });
        return response;
      }).catch(function() {
        // Offline fallback — return cached calculator
        return caches.match('./LC76_LiFePO4_Calculator.html');
      });
    })
  );
});
