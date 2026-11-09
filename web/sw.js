// PMT Planer (web) — service worker: aplikacja działa bez internetu po pierwszym uruchomieniu.
// Plik sw.js jest GENEROWANY (narzedzia/zbuduj_sw.py): lista plików i wersja wynikają z zawartości katalogu.
const WERSJA = '3ace61ba43cc';
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
 "./js/adres.js",
 "./js/aplikacja.js",
 "./js/dokument_atrapa.js",
 "./js/dostep.js",
 "./js/dzwiek.js",
 "./js/folder.js",
 "./js/karuzela.js",
 "./js/krypto_js.js",
 "./js/magazyn.js",
 "./js/ms_powrot.js",
 "./js/outlook.js",
 "./js/pliki.js",
 "./js/poczta.js",
 "./js/podpis.js",
 "./js/podpis_reczny.js",
 "./js/pomoc.js",
 "./js/przeniesienie.js",
 "./js/sejf.js",
 "./js/silnik.js",
 "./js/silnik.worker.js",
 "./js/weryfikacja.js",
 "./js/widowisko.js",
 "./js/zipaes.js",
 "./js/zipklasyczny.js",
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
const SKROTY = {
 "./css/aplikacja.css": "0f19faf83956d27c",
 "./ikony/ikona-180.png": "18889881dd7c13bd",
 "./ikony/ikona-maskable-192.png": "cb65f20940d626f2",
 "./ikony/ikona-maskable-512.png": "dbd3a136a5efdb96",
 "./ikony/logo-128.webp": "b6d1105a5f46f0b2",
 "./ikony/logo-192.png": "6f1af7c8a362f1aa",
 "./ikony/logo-512.png": "d14d554fd2207fee",
 "./index.html": "2d450148e86455db",
 "./js/adres.js": "9d2ac5ab705e450f",
 "./js/aplikacja.js": "6b4c774d953d79b3",
 "./js/dokument_atrapa.js": "dd6c781d71e04fc8",
 "./js/dostep.js": "f0e47d1ee7403bc8",
 "./js/dzwiek.js": "10c1e87b432e6721",
 "./js/folder.js": "b706cb1ab7b81f8c",
 "./js/karuzela.js": "d64507d7e8c41a91",
 "./js/krypto_js.js": "d5adbfd578434c89",
 "./js/magazyn.js": "4b50220968cf07cf",
 "./js/ms_powrot.js": "e82d612397a0cdf0",
 "./js/outlook.js": "628a29d72aadfc9e",
 "./js/pliki.js": "631ce377322eca94",
 "./js/poczta.js": "f5d318bd1a8e1ddd",
 "./js/podpis.js": "4ef1b9bff68656bc",
 "./js/podpis_reczny.js": "0edb49491ca0bb87",
 "./js/pomoc.js": "14a7187c8781a211",
 "./js/przeniesienie.js": "6a373490ec3038b5",
 "./js/sejf.js": "c9969d31c10a7ed6",
 "./js/silnik.js": "2c8d41b56cd270bf",
 "./js/silnik.worker.js": "5a9fdea97540dc37",
 "./js/weryfikacja.js": "3f3d2ed71b5ded1e",
 "./js/widowisko.js": "ab48b81882fc992c",
 "./js/zipaes.js": "c1dee26cba7fd40e",
 "./js/zipklasyczny.js": "7e7f284e5079f43d",
 "./js/zywe.js": "b7c037cc4ddf41f6",
 "./manifest.webmanifest": "6ee157d9cfb7b428",
 "./przyklad/miesiac.json": "2c799e98b3922cc8",
 "./przyklad/plan.json": "7de1a4627f7fe5e5",
 "./silnik/boot.py": "3016d346355bb8ed",
 "./silnik/fonty/LiberationSans-Bold.ttf": "3973aa5054fb467d",
 "./silnik/fonty/LiberationSans-Regular.ttf": "4659bc0c58c5028d",
 "./silnik/most.py": "18359571375958ef",
 "./silnik/pmt_silnik.py": "a0f0b50324f8ad45",
 "./silnik/sieci_cel.txt": "d252e908cd50d2e5",
 "./vendor/czcionki/geist-latin-ext-wght-normal.woff2": "824f485b5d26e2f2",
 "./vendor/czcionki/geist-latin-wght-normal.woff2": "19f9c92546aa300c",
 "./vendor/paczki/defusedxml-0.7.1-py2.py3-none-any.whl": "a352e7e428770286",
 "./vendor/paczki/et_xmlfile-2.0.0-py3-none-any.whl": "7a91720bc7568435",
 "./vendor/paczki/fonttools-4.56.0-py3-none-any.whl": "1088182f68c303b5",
 "./vendor/paczki/fpdf2-2.8.9-py3-none-any.whl": "6e1d94af6d631195",
 "./vendor/paczki/openpyxl-3.1.5-py2.py3-none-any.whl": "5282c12b107bffee",
 "./vendor/paczki/pillow-11.3.0-cp313-cp313-pyodide_2025_0_wasm32.whl": "7e1168616481f685",
 "./vendor/pyodide/pyodide-lock.json": "3256ffc76388de0e",
 "./vendor/pyodide/pyodide.asm.js": "1263f02b5b26099b",
 "./vendor/pyodide/pyodide.asm.wasm": "e2f4ee75b325e35e",
 "./vendor/pyodide/pyodide.mjs": "23213d27e9dacbda",
 "./vendor/pyodide/python_stdlib.zip": "4298b6ee445cb724",
 "./vendor/qr/qrcode.mjs": "86e07bd03bcfd50b",
 "./": "2d450148e86455db"
};
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
    if (/\/ms_powrot\.html$/.test(u.pathname)) return fetch(q, { cache: 'no-store' });      // strona powrotu po logowaniu Microsoft: w adresie jest jednorazowy kod — nigdy do pamięci podręcznej
    if (/\/(menedzer|sekret|odbiorca|uwagi|adres_aplikacji|poczta_microsoft)\.txt(\.txt)?$/.test(u.pathname)) { try { return await ZSieci(c, q, 8000) } catch (err) {} return trafienie || new Response('', { status: 404 }); }      // pliki ustawień: zawsze najpierw z sieci (zmiana adresu/odbiorcy działa od razu), kopia tylko bez internetu
    if (KOD.test(u.pathname) && !/\/vendor\//.test(u.pathname)) {
      if (trafienie) return trafienie;
      try { return await fetch(q, { cache: 'no-cache' }); } catch (err) { return new Response('Brak połączenia', { status: 503 }); }      // bez zapisu do pamięci: nie dokładamy do niej pliku z innego wydania
    }
    if (trafienie) return trafienie;
    try { const r = await fetch(q); if (r.ok) c.put(q, r.clone()); return r; } catch (err) { return new Response('Brak połączenia', { status: 503 }); }
  })());
});
