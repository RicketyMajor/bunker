// Service worker for the Transmisor. Network-first for the shell, cache as fallback.
//
// This file is rendered by the Django template engine so it can be served from /movil/ and
// therefore scoped to it. It has no template variables, and it must not grow any `{{` or
// `{%` sequence — the engine would eat it silently.
//
// ponytail: network-first, not cache-first. You are almost always reachable when you open
// this at home, so an edited file is picked up without a version dance; the cache only
// serves when there is no route. The ceiling: a slow-but-alive network makes the shell wait
// for the timeout. Swap to stale-while-revalidate if that ever bites.
//
// The `cache: 'no-store'` below is what makes that true, and it was measured, not assumed:
// a plain fetch(event.request) is still served by the browser's own HTTP cache, so an edited
// queue.js kept executing the previous version with transferSize 0 and no error anywhere.
// Network-first has to mean the network, or the second cache silently defeats the first.
const CACHE = 'transmisor-v1';
// The BUNDLE, not the sources. `app.html:423` loads `movil/dist/main.js` and has done since
// esbuild landed on 2026-08-21; this list kept naming `app.js` and `queue.js`, which the page
// never requests. All three answer 200 — 42471, 8365 and 24501 bytes measured 2026-08-24 —
// so nothing looked wrong, and that is the same trap as the APK manifest that served the
// unbundled module: compare bodies, not statuses.
//
// The handler below is network-first and caches every successful GET, so an install that has
// loaded once online is fine either way. What this list is FOR is the install that goes
// offline before that: it had the shell and no JS at all, which is the one case the whole
// offline PWA exists for.
const SHELL = ['/movil/', '/movil/manifest.json', '/static/movil/dist/main.js'];

self.addEventListener('install', (event) => {
  // Cached one by one rather than with addAll: addAll is atomic, so a single 404 rejects the
  // whole install and leaves the app with no offline shell at all. A missing file should cost
  // that file, not the installation.
  event.waitUntil(
    caches.open(CACHE)
      .then((c) => Promise.all(SHELL.map((u) => c.add(u).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  // Captures must never be served from cache: they are writes, and the queue owns retrying.
  if (event.request.method !== 'GET') return;
  // Only the shell. This also keeps /api/movil/estado/ out of the cache, which matters: a
  // stale inventory would offer books already finished and habits already marked.
  if (!url.pathname.startsWith('/movil/') && !url.pathname.startsWith('/static/movil/')) return;

  event.respondWith(
    fetch(event.request, { cache: 'no-store' })
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((c) => c.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request).then((hit) => hit || caches.match('/movil/')))
  );
});
