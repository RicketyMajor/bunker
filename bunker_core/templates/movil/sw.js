// Service worker for the Transmisor. Network-first for the shell, cache as fallback.
//
// This file is rendered by the Django template engine so it can be served from /movil/ and
// therefore scoped to it. It has no template variables, and it must not grow any `{{` or
// `{%` sequence — the engine would eat it silently.
//
// ponytail: network-first, not cache-first. You are almost always reachable when you open
// this at home, so an edited template is picked up without a version dance; the cache only
// serves when there is no route. The ceiling: a slow-but-alive network makes the shell wait
// for the timeout. Swap to stale-while-revalidate if that ever bites.
const CACHE = 'transmisor-v1';
const SHELL = ['/movil/', '/movil/manifest.json', '/static/movil/queue.js', '/static/movil/app.js'];

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
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((c) => c.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request).then((hit) => hit || caches.match('/movil/')))
  );
});
