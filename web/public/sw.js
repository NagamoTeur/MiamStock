/* MiamStock — service worker.
 *
 * Objectif volontairement limité : l'app s'installe et s'ouvre instantanément,
 * même sans réseau. Les écritures (bips) ne sont PAS mises en file d'attente :
 * elles passent par le réseau ou échouent franchement, et l'interface affiche
 * un bandeau « hors ligne ». Un faux succès sur un bip serait pire qu'une erreur.
 */

const VERSION = 'miamstock-v1';
const SHELL = [
  '/',
  '/manifest.webmanifest',
  '/icon-192.png',
  '/icon-512.png',
  '/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(VERSION)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // L'API n'est jamais servie depuis le cache : un stock périmé affiché comme
  // frais ferait prendre de mauvaises décisions devant le frigo.
  if (url.pathname.startsWith('/api/')) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(async () => {
        const cache = await caches.open(VERSION);
        return (await cache.match('/')) ?? Response.error();
      }),
    );
    return;
  }

  event.respondWith(
    caches.open(VERSION).then(async (cache) => {
      const hit = await cache.match(request);
      if (hit) return hit;
      const response = await fetch(request);
      // Les bundles Vite portent un hash dans leur nom : les cacher est sûr.
      if (response.ok && response.type === 'basic') cache.put(request, response.clone());
      return response;
    }),
  );
});
