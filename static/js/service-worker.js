/* INDPNS Market — service worker. Hors-ligne : pages statiques uniquement.
   Jamais de cache pour : comptes, dashboard, fichiers acheteurs, paiements, admin, API. */
const VERSION = "indpns-v1";
const PRECACHE = ["/offline/", "/static/css/tokens.css", "/static/css/base.css", "/static/css/public.css"];
const NEVER = [/^\/dashboard/, /^\/accounts/, /^\/files/, /^\/payments/, /^\/checkout/, /^\/api/, /^\/admin/, /^\/media/];

self.addEventListener("install", (e) => { e.waitUntil(caches.open(VERSION).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin || NEVER.some((r) => r.test(url.pathname))) return;
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); return res; })));
    return;
  }
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match("/offline/")));
  }
});
