const CACHE = 'lc76-range-v1';
const ASSETS = [
  './LC76_Fuel_Range_Calculator.html',
  './manifest.json',
  'https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;500;600;700&display=swap'
];

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE).then(function(cache) {
      // Cache the core files; Google Fonts may fail offline — that's fine
      return cache.addAll([
        './LC76_Fuel_Range_Calculator.html',
        './manifest.json'
      ]);
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
      return cached || fetch(e.request).catch(function() {
        // If offline and not cached, return the main app
        return caches.match('./LC76_Fuel_Range_Calculator.html');
      });
    })
  );
});
