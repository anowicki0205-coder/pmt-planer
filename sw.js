/* PMT Wizyty — service worker
   Zadania: (1) aplikacja startuje offline (cache powloki),
            (2) powiadomienia dzialaja na Androidzie,
            (3) aktualizacje HTML zawsze swieze przy zasiegu (network-first). */
const WERSJA = "pmt-v1";
const POWLOKA = ["./pmt_wizyty.html", "./manifest.webmanifest", "./pwa_192.png", "./pwa_512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(WERSJA).then((c) => c.addAll(POWLOKA)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((klucze) => Promise.all(klucze.filter((k) => k !== WERSJA).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;                 // POST do backendu: bez ingerencji
  if (url.origin !== self.location.origin) return;        // obce domeny: bez ingerencji
  // HTML: najpierw siec (swieze aktualizacje), przy braku zasiegu — cache
  if (e.request.mode === "navigate" || url.pathname.endsWith(".html")) {
    e.respondWith(
      fetch(e.request)
        .then((odp) => { const kopia = odp.clone();
          caches.open(WERSJA).then((c) => c.put(e.request, kopia)); return odp; })
        .catch(() => caches.match(e.request).then((r) => r || caches.match("./pmt_wizyty.html")))
    );
    return;
  }
  // reszta powloki (ikony, manifest): najpierw cache
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});

/* powiadomienia zlecane przez aplikacje */
self.addEventListener("message", (e) => {
  const d = e.data || {};
  if (d.typ === "powiadom") {
    self.registration.showNotification(d.tytul || "PMT Wizyty", {
      body: d.tresc || "", icon: "./pwa_192.png", badge: "./pwa_192.png", vibrate: [180]
    });
  }
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(clients.matchAll({ type: "window" }).then((okna) => {
    for (const w of okna) { if ("focus" in w) return w.focus(); }
    return clients.openWindow("./pmt_wizyty.html");
  }));
});
