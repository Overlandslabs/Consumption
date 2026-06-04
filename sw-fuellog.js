/* LC76 Fuel Log Analyser — Service Worker v1.0 */
var CACHE = 'lc76-fuellog-v1';
var ASSETS = [
  './LC76_Fuel_Log_Analyser.html',
  './manifest-fuellog.json',
  './icon-fuellog-192.svg',
  './icon-fuellog-512.svg',
  'https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@400;600&family=Oswald:wght@300;400;500;600;700&display=swap'
];
self.addEventListener('install', function(e){
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(ASSETS); }));
  self.skipWaiting();
});
self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(k){ return k!==CACHE; }).map(function(k){ return caches.delete(k); }));
  }));
  self.clients.claim();
});
self.addEventListener('fetch', function(e){
  e.respondWith(caches.match(e.request).then(function(cached){
    if(cached) return cached;
    return fetch(e.request).then(function(resp){
      if(!resp || resp.status!==200 || resp.type==='opaque') return resp;
      var clone = resp.clone();
      caches.open(CACHE).then(function(c){ c.put(e.request, clone); });
      return resp;
    }).catch(function(){ return caches.match('./LC76_Fuel_Log_Analyser.html'); });
  }));
});
