// PMT Planer (web) — service worker: aplikacja działa bez internetu po pierwszym uruchomieniu.
// Plik sw.js jest GENEROWANY (narzedzia/zbuduj_sw.py): lista plików i wersja wynikają z zawartości katalogu.
const WERSJA = '__WERSJA__';
const CACHE = 'pmt-web-' + WERSJA;
const PLIKI = __LISTA__;
const SKROTY = __SKROTY__;
/* Poprzednie pamięci z mapą skrótów (zapisaną na końcu udanej instalacji): plik o tym samym skrócie jest identyczny, więc można go skopiować. */
async function pamieciPoprzednie() {
  const w = [];
  for (const k of await caches.keys()) {
    if (!k.startsWith('pmt-web-') || k === CACHE) continue;
    const c = await caches.open(k), r = await c.match('./__skroty.json');
    if (r) { try { w.push({ c, skroty: await r.json() }); } catch (err) { /* uszkodzona mapa: tej pamięci nie używamy */ } }
  }
  return w;
}
/* Instalacja jest NIEPODZIELNA: nowa wersja trafia do pamięci cała albo wcale. Brak któregoś pliku przerywa instalację — poprzedni service worker zostaje
   z kompletem (dawniej błąd był połykany, a aktywacja kasowała starą pamięć, więc bez zasięgu silnik nie wstawał). Niezmienione pliki są kopiowane ze starej pamięci. */
self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE), stare = await pamieciPoprzednie();
    await Promise.all(PLIKI.map(async u => {
      for (const s of stare) if (SKROTY[u] && s.skroty[u] === SKROTY[u]) { const r = await s.c.match(u); if (r) { await c.put(u, r); return; } }
      await c.add(new Request(u, { cache: 'reload' }));
    }));
    try { await c.add(new Request('./sekret.txt', { cache: 'reload' })); } catch (err) { /* plik dokłada dopiero wdrożenie (web-pages.yml); bez niego zapytania idą bez podpisu */ }
    await c.put('./__skroty.json', new Response(JSON.stringify(SKROTY), { headers: { 'content-type': 'application/json' } }));
    self.skipWaiting();
  })());
});
self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith('pmt-web-') && k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});
/* Kod aplikacji (strona, skrypty, style, silnik) idzie z pamięci TEJ wersji: wszystkie moduły pochodzą z jednego wydania. Dawniej każdy plik szedł najpierw z sieci
   z limitem 4 s, więc na wolnym łączu po wdrożeniu mieszały się nowe i stare moduły (SyntaxError przy imporcie). Nową wersję przynosi w całości nowy service worker
   (wersja zmienia się z każdym plikiem), a aplikacja prosi wtedy o odświeżenie. Sieć tylko, gdy pliku w pamięci nie ma. */
const KOD = /\/(index\.html|manifest\.webmanifest|css\/[^/]+|js\/[^/]+|silnik\/[^/]+\.py)?$/;
async function ZSieci(c, q, limitMs) {
  const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), limitMs);
  try { const r = await fetch(q, { cache: 'no-cache', signal: ctl.signal }); if (r.ok) c.put(q, r.clone()); return r; } finally { clearTimeout(t); }
}
self.addEventListener('fetch', e => {
  const q = e.request; if (q.method !== 'GET') return;
  const u = new URL(q.url); if (u.origin !== location.origin) return;       // sieć zewnętrzna (drogi, współrzędne) idzie prosto do internetu
  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    const trafienie = await c.match(q, { ignoreSearch: true });
    if (/\/__adres\.json$/.test(u.pathname)) { try { return await fetch(q, { cache: 'no-store' }); } catch (err) { return new Response('{"adres":""}', { status: 200, headers: { 'content-type': 'application/json' } }); } }      // adres komputera w sieci zmienia się: nigdy z pamięci
    if (/\/(menedzer|sekret|odbiorca|uwagi|adres_aplikacji)\.txt(\.txt)?$/.test(u.pathname)) { try { return await ZSieci(c, q, 8000) } catch (err) {} return trafienie || new Response('', { status: 404 }); }      // pliki ustawień: zawsze najpierw z sieci (zmiana adresu/odbiorcy działa od razu), kopia tylko bez internetu
    if (KOD.test(u.pathname) && !/\/vendor\//.test(u.pathname)) {
      if (trafienie) return trafienie;
      try { return await fetch(q, { cache: 'no-cache' }); } catch (err) { return new Response('Brak połączenia', { status: 503 }); }      // bez zapisu do pamięci: nie dokładamy do niej pliku z innego wydania
    }
    if (trafienie) return trafienie;
    try { const r = await fetch(q); if (r.ok) c.put(q, r.clone()); return r; } catch (err) { return new Response('Brak połączenia', { status: 503 }); }
  })());
});
