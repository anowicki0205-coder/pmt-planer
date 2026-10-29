// PMT Planer (web) — service worker: aplikacja działa bez internetu po pierwszym uruchomieniu.
// Plik sw.js jest GENEROWANY (narzedzia/zbuduj_sw.py): lista plików i wersja wynikają z zawartości katalogu.
const WERSJA = 'b8554f70c6ca';
const CACHE = 'pmt-web-' + WERSJA;
const PLIKI = [
 "./",
 "./css/aplikacja.css",
 "./ikony/ikona-180.png",
 "./ikony/ikona-maskable-192.png",
 "./ikony/ikona-maskable-512.png",
 "./ikony/logo-128.webp",
 "./ikony/logo-192.png",
 "./ikony/logo-512.png",
 "./index.html",
 "./js/aplikacja.js",
 "./js/dostep.js",
 "./js/krypto_js.js",
 "./js/magazyn.js",
 "./js/pliki.js",
 "./js/podpis.js",
 "./js/podpis_reczny.js",
 "./js/pomoc.js",
 "./js/sejf.js",
 "./js/silnik.js",
 "./js/silnik.worker.js",
 "./js/weryfikacja.js",
 "./js/zywe.js",
 "./manifest.webmanifest",
 "./przyklad/miesiac.json",
 "./przyklad/plan.json",
 "./silnik/boot.py",
 "./silnik/fonty/LiberationSans-Bold.ttf",
 "./silnik/fonty/LiberationSans-Regular.ttf",
 "./silnik/most.py",
 "./silnik/pmt_silnik.py",
 "./silnik/sieci_cel.txt",
 "./vendor/czcionki/geist-latin-ext-wght-normal.woff2",
 "./vendor/czcionki/geist-latin-wght-normal.woff2",
 "./vendor/paczki/defusedxml-0.7.1-py2.py3-none-any.whl",
 "./vendor/paczki/et_xmlfile-2.0.0-py3-none-any.whl",
 "./vendor/paczki/fonttools-4.56.0-py3-none-any.whl",
 "./vendor/paczki/fpdf2-2.8.9-py3-none-any.whl",
 "./vendor/paczki/openpyxl-3.1.5-py2.py3-none-any.whl",
 "./vendor/paczki/pillow-11.3.0-cp313-cp313-pyodide_2025_0_wasm32.whl",
 "./vendor/pyodide/pyodide-lock.json",
 "./vendor/pyodide/pyodide.asm.js",
 "./vendor/pyodide/pyodide.asm.wasm",
 "./vendor/pyodide/pyodide.mjs",
 "./vendor/pyodide/python_stdlib.zip",
 "./vendor/qr/qrcode.mjs"
];
self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await Promise.all(PLIKI.map(async u => { try { await c.add(new Request(u, { cache: 'reload' })); } catch (err) { /* brak pojedynczego pliku nie blokuje instalacji */ } }));
    self.skipWaiting();
  })());
});
self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith('pmt-web-') && k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});
/* Kod aplikacji (strona, skrypty, style, silnik) pobieramy NAJPIERW z sieci — dzięki temu po aktualizacji od razu widać nową wersję, a bez internetu działa kopia z pamięci.
   Duże, rzadko zmieniane pliki (silnik Pythona w przeglądarce, czcionki, ikony) idą z pamięci od razu. */
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
      try { const r = await ZSieci(c, q, trafienie ? 4000 : 20000); if (r.ok || !trafienie) return r; } catch (err) { /* bez sieci albo za wolno: kopia z pamięci */ }
      return trafienie || new Response('Brak połączenia', { status: 503 });
    }
    if (trafienie) return trafienie;
    try { const r = await fetch(q); if (r.ok) c.put(q, r.clone()); return r; } catch (err) { return new Response('Brak połączenia', { status: 503 }); }
  })());
});
