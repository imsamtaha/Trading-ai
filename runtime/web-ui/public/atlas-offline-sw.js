const CACHE = "atlas-offline-contact-v1";
const PAGE = "/offline-contact.html";
self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.add(PAGE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener("fetch", (event) => {
  if (event.request.mode !== "navigate" || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith(fetch(event.request).catch(async () => {
    const cache = await caches.open(CACHE);
    return (await cache.match(PAGE)) || Response.error();
  }));
});
