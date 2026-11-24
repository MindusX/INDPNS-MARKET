/* INDPNS Market — service worker. Hors-ligne : pages statiques uniquement.
   Jamais de cache pour : comptes, dashboard, fichiers acheteurs, paiements, admin, API. */
const VERSION = "indpns-v2";
const PRECACHE = ["/offline/"];
const NEVER = [/^\/dashboard/, /^\/accounts/, /^\/files/, /^\/payments/, /^\/checkout/, /^\/api/, /^\/admin/, /^\/media/, /^\/healthz/];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(VERSION).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((k) => Promise.all(k.filter((x) => x !== VERSION).map((x) => caches.delete(x)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin || NEVER.some((r) => r.test(url.pathname))) return;
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => { if (res.ok) { const c = res.clone(); caches.open(VERSION).then((x) => x.put(req, c)); } return res; })));
    return;
  }
  if (req.mode === "navigate") e.respondWith(fetch(req).catch(() => caches.match("/offline/")));
});
