const CACHE = 'lc76-range-v2';

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE).then(function(cache) {
      return cache.addAll(['./LC76_Fuel_Range_Calculator.html', './manifest.json']);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  // Delete all old caches on activate
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
  // Network-first: always try network, fall back to cache only if offline
  e.respondWith(
    fetch(e.request).then(function(response) {
      // Update cache with fresh response
      var clone = response.clone();
      caches.open(CACHE).then(function(cache) {
        cache.put(e.request, clone);
      });
      return response;
    }).catch(function() {
      // Offline fallback
      return caches.match(e.request).then(function(cached) {
        return cached || caches.match('./LC76_Fuel_Range_Calculator.html');
      });
    })
  );
});
