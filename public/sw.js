// Precache the shell and every clip so the board works offline.
// Bump VERSION when clips change (tools/fetch.py does this).
const VERSION = '8d407f43';
self.window = self;
importScripts('clips.js');
const SHELL = ['./', 'index.html', 'clips.js', 'manifest.webmanifest', 'icon.svg', 'icon-192.png', 'icon-512.png', 'og.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION)
    .then(c => c.addAll([...SHELL, ...(self.CLIPS || []).map(x => x.file)]))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.pathname.includes('/clips/')) {
    e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request)));
    return;
  }
  // Shell: network first so new clips show up, cache when offline.
  e.respondWith(fetch(e.request)
    .then(res => { const copy = res.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); return res; })
    .catch(() => caches.match(e.request)));
});
