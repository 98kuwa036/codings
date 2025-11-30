/**
 * Service Worker for Login App
 * ログインアプリ用サービスワーカー
 */

const CACHE_VERSION = 'v1.0.0';
const CACHE_NAME = `warehouse-login-${CACHE_VERSION}`;

// キャッシュするリソース
const STATIC_CACHE_URLS = [
  '/login/',
  '/login/index.html',
  '/login/manifest.json',
  '/shared/icons/warehouse-icon.svg',
  '/shared/js/offline-db.js',
  '/shared/js/network-status.js'
];

// 動的にキャッシュするリソースのパターン
const CACHE_PATTERNS = {
  images: /\.(png|jpg|jpeg|svg|gif|webp)$/i,
  scripts: /\.js$/i,
  styles: /\.css$/i,
  fonts: /\.(woff|woff2|ttf|eot)$/i
};

/**
 * インストールイベント
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...', CACHE_VERSION);

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static resources');
        return cache.addAll(STATIC_CACHE_URLS);
      })
      .then(() => {
        console.log('[SW] Installation complete');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Installation failed:', error);
      })
  );
});

/**
 * アクティベーションイベント
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...', CACHE_VERSION);

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              return name.startsWith('warehouse-login-') && name !== CACHE_NAME;
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[SW] Activation complete');
        return self.clients.claim();
      })
  );
});

/**
 * フェッチイベント
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // GASリクエストはキャッシュしない
  if (url.hostname.includes('script.google.com') ||
      url.hostname.includes('script.googleusercontent.com')) {
    return;
  }

  // POST リクエストはキャッシュしない
  if (request.method !== 'GET') {
    return;
  }

  event.respondWith(
    caches.match(request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          updateCache(request);
          return cachedResponse;
        }

        return fetch(request)
          .then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              cacheResource(request, networkResponse.clone());
            }
            return networkResponse;
          })
          .catch((error) => {
            console.error('[SW] Fetch failed:', error);
            return getOfflineFallback(request);
          });
      })
  );
});

/**
 * バックグラウンドでキャッシュ更新
 */
function updateCache(request) {
  fetch(request)
    .then((response) => {
      if (response && response.status === 200) {
        cacheResource(request, response);
      }
    })
    .catch(() => {});
}

/**
 * リソースをキャッシュ
 */
function cacheResource(request, response) {
  const url = new URL(request.url);

  const shouldCache = Object.values(CACHE_PATTERNS).some(pattern =>
    pattern.test(url.pathname)
  );

  if (shouldCache || url.pathname.startsWith('/login/')) {
    caches.open(CACHE_NAME).then((cache) => {
      cache.put(request, response);
    });
  }
}

/**
 * オフライン時のフォールバック
 */
function getOfflineFallback(request) {
  const url = new URL(request.url);

  if (request.headers.get('accept').includes('text/html')) {
    return caches.match('/login/index.html');
  }

  if (CACHE_PATTERNS.images.test(url.pathname)) {
    return new Response(
      '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect fill="#f0f0f0" width="200" height="200"/><text x="50%" y="50%" text-anchor="middle" fill="#999">オフライン</text></svg>',
      { headers: { 'Content-Type': 'image/svg+xml' } }
    );
  }

  return new Response('オフラインです', {
    status: 503,
    statusText: 'Service Unavailable',
    headers: new Headers({
      'Content-Type': 'text/plain'
    })
  });
}

/**
 * メッセージイベント
 */
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.delete(CACHE_NAME)
        .then(() => {
          console.log('[SW] Cache cleared');
          event.ports[0].postMessage({ success: true });
        })
    );
  }
});

console.log('[SW] Service Worker loaded', CACHE_VERSION);
