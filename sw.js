// LC76 Overland Reference Library — library-wide service worker
// Caches the ENTIRE library for offline field use. Cache-first with
// background revalidation (stale-while-revalidate). Offline navigation
// falls back to the library index, never to an unrelated page.
// Bump CACHE (v1 -> v2 ...) whenever library files change to force refresh.

const CACHE = 'lc76-library-v2';

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
  './LC76_Aux_Battery_Care.html',
  './LC76_Battery_Longevity_Report.html',
  './LC76_Battery_Training_Guide.html',
  './LC76_Border_Crossings_Guide.html',
  './LC76_Bush_Mechanics_Guide.html',
  './LC76_Comms_Navigation_Guide.html',
  './LC76_Cooling_System_Guide.html',
  './LC76_Crank_Battery_Care.html',
  './LC76_Cross_Reference_Index.html',
  './LC76_Departure_Checklist.html',
  './LC76_Drivetrain_Training_Guide.html',
  './LC76_Driving_Conditions_Guide.html',
  './LC76_Electrical_Wiring_Guide.html',
  './LC76_Emergency_Procedures_Guide.html',
  './LC76_Engine_Training.html',
  './LC76_Fuel_Log_Analyser.html',
  './LC76_Fuel_Range_Calculator.html',
  './LC76_Fuel_System_Guide.html',
  './LC76_Health_Hygiene_Guide.html',
  './LC76_Insurance_Medevac.html',
  './LC76_Kalahari_Profile_2026-04.html',
  './LC76_Karoo_Winter_Loop_2026.html',
  './LC76_LiFePO4_Calculator.html',
  './LC76_LiFePO4_System_Report.html',
  './LC76_Packing_Optimisation_Guide.html',
  './LC76_Pre_Trip_Prep_Protocol.html',
  './LC76_Reference_Card.html',
  './LC76_Seal_Gasket_Atlas.html',
  './LC76_Service_History.html',
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
  './Namibia_Overland_Profile_2026-04.html',
  './Tanzania_Overland_Profile_2026-05.html',
  './Zambia_Overland_Profile_2026-04.html',
];

// Install: precache every file individually so one missing/renamed file
// cannot abort the whole precache (cache.addAll is all-or-nothing).
self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return Promise.allSettled(
        PRECACHE.map(function (url) {
          return cache.add(new Request(url, { cache: 'reload' })).catch(function (err) {
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

// Fetch: same-origin GET only. Cache-first for instant offline load, with a
// background network refresh. If both cache and network fail on a navigation,
// fall back to the library index.
self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  e.respondWith(
    caches.open(CACHE).then(function (cache) {
      return cache.match(req).then(function (cached) {
        var network = fetch(req).then(function (resp) {
          if (resp && resp.status === 200 && resp.type === 'basic') {
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
