// Service worker на Лихвомер.
//
// Урок, платен в продукция: предишната версия кешираше и HTML страниците. При
// ново внедряване браузърът зареждаше стария HTML от кеша, той сочеше към стари
// пакети и в страницата вървяха два комплекта код едновременно — новият викаше
// правилния адрес, а старият още търсеше localhost. Затова тук се кешират само
// файлове с хеш в името, а документите винаги идват от мрежата.
//
// Версията в името на кеша ТРЯБВА да се вдига при промяна на стратегията —
// така старите кешове се изтриват при активиране.
const CACHE = "lihvomer-v2";

// Съдържание, което може да се кешира без риск: адресът му се сменя при всяка
// промяна, защото носи хеш.
const IMMUTABLE = ["/_next/static/", "/icons/"];

const OFFLINE_FALLBACK = "/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(["/manifest.webmanifest"]))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  );
});

function isImmutable(pathname) {
  return IMMUTABLE.some((prefix) => pathname.startsWith(prefix));
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Чужди адреси не ни касаят.
  if (url.origin !== self.location.origin) return;

  // Лихвите и прогнозите никога не се кешират: остаряло число е по-лошо от
  // липсващо, защото изглежда достоверно.
  if (url.pathname.startsWith("/api/")) return;

  // Документите и данните за навигация винаги идват от мрежата, за да не се
  // случи отново старият пакет да оживее след внедряване.
  const isDocument =
    request.mode === "navigate" ||
    request.destination === "document" ||
    url.searchParams.has("_rsc");

  if (isDocument) {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match(OFFLINE_FALLBACK).then((hit) => hit || Response.error()),
      ),
    );
    return;
  }

  // Файловете с хеш се вземат от кеша, ако ги има — те не се променят.
  if (isImmutable(url.pathname)) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((response) => {
            if (response.ok) {
              const copy = response.clone();
              caches.open(CACHE).then((cache) => cache.put(request, copy));
            }
            return response;
          }),
      ),
    );
    return;
  }

  // Останалото минава направо през мрежата.
});
