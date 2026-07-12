// LC76 Overland Reference Library — library-wide service worker
// Caches the ENTIRE library for offline field use. Cache-first with
// background revalidation (stale-while-revalidate). Offline navigation
// falls back to the library index, never to an unrelated page.
// Bump CACHE (v1 -> v2 ...) whenever library files change to force refresh.
//
// CROSS-ORIGIN MAP ASSETS (added 7 Jul 2026): the interactive Leaflet maps
// in Profiles 007/008/009 depend on the Leaflet library (cdnjs.cloudflare.com)
// and raster basemap tiles (tile.openstreetmap.org for 007/008/009)
// (CartoDB dark basemap removed — all profiles now use OSM). These are cross-origin and were previously invisible to
// this worker (see the old same-origin-only guard below), so the map showed
// solid black offline. CDN_HOSTS below allowlists exactly those hosts for
// cache-first-with-revalidate treatment, same as same-origin files. Tile/CDN
// responses from these hosts are typically OPAQUE (status 0, unreadable body)
// because the browser fetches <img>/<script>/<link> cross-origin subresources
// in no-cors mode by default — opaque responses can still be cached and
// replayed correctly, they just can't be inspected for a true/false success
// code. This is an accepted, standard trade-off for offline tile caching.
// PRECACHE below includes the Leaflet library files plus a fixed 3×3 tile
// grid around each map's DEFAULT view (computed via the standard slippy-map
// tile formula) — panning/zooming beyond that grid still needs connectivity,
// but any tiles fetched successfully while online are cached opportunistically
// for later offline reuse via the same runtime fetch handler.

const CACHE = 'lc76-library-v21';

const CDN_HOSTS = [
  'cdnjs.cloudflare.com',
  'a.tile.openstreetmap.org', 'b.tile.openstreetmap.org', 'c.tile.openstreetmap.org'
];

const PRECACHE = [
  './',
  './index.html',
  './manifest.json',
  './manifest-index.json',
  './icon-index-192.svg',
  './Angola_Overland_Profile_2026-04.html',
  './Botswana_Overland_Profile_2026-04.html',
  './LC76_1HZ_Troubleshooting_Guide.html',
  './LC76_AT_Tyre_Review_R19.html',
  './LC76_Battery_Training_Guide.html',
  './LC76_Border_Crossings_Guide.html',
  './LC76_Brake_System_Guide.html',
  './LC76_Bush_Mechanics_Guide.html',
  './LC76_Comms_Navigation_Guide.html',
  './LC76_Cooling_System_Guide.html',
  './LC76_Crank_Battery_Care.html',
  './LC76_Crew_Readiness_Training_Register.html',
  './LC76_Cross_Reference_Index.html',
  './LC76_Departure_Checklist.html',
  './LC76_Drivetrain_Training_Guide.html',
  './LC76_Driving_Conditions_Guide.html',
  './LC76_Electrical_Wiring_Guide.html',
  './LC76_Emergency_Procedures_Guide.html',
  './LC76_Expedition_Operations_Plan.html',
  './LC76_Expedition_Documentation_Money_Guide.html',
  './LC76_Wheel_Tyre_Field_Procedures.html',
  './LC76_Expedition_Systems_Map.html',
  './LC76_Engine_Training.html',
  './LC76_Fuel_Log_Analyser.html',
  './LC76_Fuel_Range_Calculator.html',
  './LC76_Fuel_System_Guide.html',
  './LC76_Health_Hygiene_Guide.html',
  './LC76_History_of_Overlanding.html',
  './LC76_Insurance_Medevac.html',
  './LC76_Kalahari_Profile_2026-04.html',
  './LC76_Karoo_Winter_Loop_2026.html',
  './LC76_LiFePO4_Calculator.html',
  './LC76_LiFePO4_System_Report.html',
  './LC76_Overlanders_Manifesto.html',
  './LC76_Overlanders_Manifesto_Commentary.html',
  './LC76_Packing_Optimisation_Guide.html',
  './LC76_Pre_Trip_Prep_Protocol.html',
  './LC76_Reference_Card.html',
  './LC76_Seal_Gasket_Atlas.html',
  './LC76_Security_Fire_Guide.html',
  './LC76_Service_Checklist.html',
  './LC76_Service_History.html',
  './LC76_Service_Ledger_Archive.html',
  './LC76_Service_Ledger_Current.html',
  './LC76_Spares_Tools.html',
  './LC76_Suspension_Steering_Guide.html',
  './LC76_Trip_Fuel_Planner.html',
  './LC76_Turbo_Operations_Guide.html',
  './LC76_Tyre_Management_Guide.html',
  './LC76_Tyre_Pressure_Calculator.html',
  './LC76_Upgrade_Assessment.html',
  './LC76_Vehicle_Recovery_Guide.html',
  './LC76_Water_Budget_Calculator.html',
  './LC76_Water_Management_Guide.html',
  './LC76_Wildlife_Camp_Safety_Guide.html',
  './Namibia_Overland_Profile_2026-04.html',
  './Tanzania_Overland_Profile_2026-05.html',
  './Mozambique_Overland_Profile_2026-07.html',
  './Malawi_Overland_Profile_2026-07.html',
  './Zimbabwe_Overland_Profile_2026-07.html',
  './Kenya_Overland_Profile_2026-07.html',
  './Zambia_Overland_Profile_2026-04.html',
  // ── Cross-origin map assets (Leaflet lib + default-view tile grids) ──
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
  // OSM tiles — Profile 007 (Mozambique) + Profile 008 (Malawi) default views
  'https://a.tile.openstreetmap.org/6/37/35.png',
  'https://a.tile.openstreetmap.org/6/38/34.png',
  'https://a.tile.openstreetmap.org/6/38/37.png',
  'https://a.tile.openstreetmap.org/6/39/33.png',
  'https://a.tile.openstreetmap.org/6/39/36.png',
  'https://a.tile.openstreetmap.org/7/74/73.png',
  'https://a.tile.openstreetmap.org/7/75/66.png',
  'https://a.tile.openstreetmap.org/7/75/69.png',
  'https://a.tile.openstreetmap.org/7/75/72.png',
  'https://a.tile.openstreetmap.org/7/76/68.png',
  'https://a.tile.openstreetmap.org/7/76/74.png',
  'https://a.tile.openstreetmap.org/7/77/67.png',
  'https://a.tile.openstreetmap.org/7/77/70.png',
  'https://b.tile.openstreetmap.org/6/37/33.png',
  'https://b.tile.openstreetmap.org/6/37/36.png',
  'https://b.tile.openstreetmap.org/6/38/35.png',
  'https://b.tile.openstreetmap.org/6/39/34.png',
  'https://b.tile.openstreetmap.org/6/39/37.png',
  'https://b.tile.openstreetmap.org/7/74/74.png',
  'https://b.tile.openstreetmap.org/7/75/67.png',
  'https://b.tile.openstreetmap.org/7/75/70.png',
  'https://b.tile.openstreetmap.org/7/75/73.png',
  'https://b.tile.openstreetmap.org/7/76/66.png',
  'https://b.tile.openstreetmap.org/7/76/69.png',
  'https://b.tile.openstreetmap.org/7/76/72.png',
  'https://b.tile.openstreetmap.org/7/77/68.png',
  'https://c.tile.openstreetmap.org/6/37/34.png',
  'https://c.tile.openstreetmap.org/6/37/37.png',
  'https://c.tile.openstreetmap.org/6/38/33.png',
  'https://c.tile.openstreetmap.org/6/38/36.png',
  'https://c.tile.openstreetmap.org/6/39/35.png',
  'https://c.tile.openstreetmap.org/7/74/72.png',
  'https://c.tile.openstreetmap.org/7/75/68.png',
  'https://c.tile.openstreetmap.org/7/75/74.png',
  'https://c.tile.openstreetmap.org/7/76/67.png',
  'https://c.tile.openstreetmap.org/7/76/70.png',
  'https://c.tile.openstreetmap.org/7/76/73.png',
  'https://c.tile.openstreetmap.org/7/77/66.png',
  'https://c.tile.openstreetmap.org/7/77/69.png',
  // Kenya 010 map (z6, -0.5/37.5) 3x3 OSM grid
  'https://c.tile.openstreetmap.org/6/37/31.png',
  'https://a.tile.openstreetmap.org/6/37/32.png',
  'https://b.tile.openstreetmap.org/6/37/33.png',
  'https://a.tile.openstreetmap.org/6/38/31.png',
  'https://b.tile.openstreetmap.org/6/38/32.png',
  'https://c.tile.openstreetmap.org/6/38/33.png',
  'https://b.tile.openstreetmap.org/6/39/31.png',
  'https://c.tile.openstreetmap.org/6/39/32.png',
  'https://a.tile.openstreetmap.org/6/39/33.png',
  // OSM tiles — Profile 009 (Zimbabwe) default view (x=36 column only;
  // the remaining 6 tiles at x=37/38 already appear in the 007/008 grids above)
  'https://a.tile.openstreetmap.org/6/36/33.png',
  'https://b.tile.openstreetmap.org/6/36/34.png',
  'https://c.tile.openstreetmap.org/6/36/35.png',
];

// Install: precache every file individually so one missing/renamed file
// cannot abort the whole precache (cache.addAll is all-or-nothing).
self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return Promise.allSettled(
        PRECACHE.map(function (url) {
          // Cross-origin CDN assets (Leaflet lib, map tiles) must be requested
          // in no-cors mode — a plain cache.add() defaults to 'cors' mode for
          // absolute URLs, which fails outright against servers (tile CDNs)
          // that don't send CORS headers. no-cors yields a cacheable opaque
          // response instead, which is what the browser needs to replay an
          // <img>/<script>/<link> tag from cache.
          var isCrossOrigin = /^https?:\/\//i.test(url);
          var reqInit = isCrossOrigin
            ? { mode: 'no-cors', cache: 'reload' }
            : { cache: 'reload' };
          return cache.add(new Request(url, reqInit)).catch(function (err) {
            console.warn('[sw] precache miss:', url, err && err.message);
          });
        })
      );
    })
  );
  self.skipWaiting();
});

// Activate: drop old caches.
self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE; })
            .map(function (k) { return caches.delete(k); })
      );
    }).then(function () { return self.clients.claim(); })
  );
});

// Fetch: same-origin GET, PLUS the allowlisted cross-origin CDN hosts (map
// library + tiles) via CDN_HOSTS above. Everything else cross-origin is left
// alone (this worker never touches it). Cache-first for instant offline load,
// with a background network refresh. If both cache and network fail on a
// navigation, fall back to the library index.
self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  var sameOrigin = (url.origin === self.location.origin);
  var isAllowedCdn = CDN_HOSTS.indexOf(url.hostname) !== -1;
  if (!sameOrigin && !isAllowedCdn) return;

  e.respondWith(
    caches.open(CACHE).then(function (cache) {
      return cache.match(req).then(function (cached) {
        var network = fetch(req).then(function (resp) {
          // Same-origin: only cache clean 200/basic responses (unchanged
          // behaviour). Cross-origin CDN: these arrive opaque (status 0,
          // unreadable) because the browser fetches them in no-cors mode —
          // opaque responses are still valid to cache and replay, we just
          // can't verify their status code, so accept type 'opaque' too.
          var cacheable = (resp && resp.status === 200 && resp.type === 'basic')
                        || (resp && resp.type === 'opaque');
          if (cacheable) {
            cache.put(req, resp.clone());
          }
          return resp;
        }).catch(function () { return null; });

        // Serve cache immediately if present; otherwise wait for network.
        if (cached) { return cached; }
        return network.then(function (resp) {
          if (resp) { return resp; }
          if (req.mode === 'navigate') { return cache.match('./index.html'); }
          return new Response('', { status: 504, statusText: 'Offline' });
        });
      });
    })
  );
});
