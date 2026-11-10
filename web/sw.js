/* Cache only immutable/public UI assets. NEVER cache /api, tokens, photos, video, or responses. */
const CACHE = 'vega-public-ui-v0.9';
const ASSETS = ['/assets/style.css', '/assets/app.js','/assets/icon-192.png','/assets/icon-512.png','/assets/manifest.webmanifest'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch', e => {
  const url=new URL(e.request.url);
  if(e.request.method!=='GET' || url.origin!==self.location.origin || !url.pathname.startsWith('/assets/')) return;
  e.respondWith(caches.match(e.request).then(cached => cached || fetch(e.request)));
});
