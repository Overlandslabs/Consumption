/* sw-fuellog.js — RETIRED 13 Oct 2026 (OI-118).
   This calculator used to install its own offline worker from the library
   root, which replaced the library's sw.js for every page. Phones that still
   hold this worker fetch this file on their next visit; it now simply runs
   the library's worker, so those phones move onto it with no gap. Every page,
   this calculator included, registers ./sw.js. Safe to delete once old
   installs have updated. */
importScripts('./sw.js');
