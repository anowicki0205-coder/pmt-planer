// Wspólne dla testów przeglądarkowych: serwer plików z katalogu web/, uruchomienie Chromium z WebGL (SwiftShader).
const { chromium } = require('playwright'); const { BackendMock, hash } = require('./backend_mock'); const http = require('http'), fs = require('fs'), path = require('path');
const KORZEN = process.env.PMT_KORZEN ? path.resolve(process.env.PMT_KORZEN) : path.resolve(__dirname, '..');      // PMT_KORZEN=<katalog>: test na gotowej paczce strony (np. po kroku „Przygotuj paczkę strony” z .github/workflows/web-pages.yml)
const TYPY = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.zip': 'application/zip', '.whl': 'application/zip', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.py': 'text/plain; charset=utf-8', '.css': 'text/css', '.webp': 'image/webp', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
function serwer(opcje = {}) {
  return new Promise(ok => {
    const s = http.createServer((q, o) => {
      const u = decodeURIComponent(q.url.split('?')[0]);
      if (opcje.dziennik) opcje.dziennik.push(u);      // opcja dziennik: [] — lista pobranych ścieżek (test service workera)
      if (opcje.zepsute && opcje.zepsute.includes(u)) { o.writeHead(500); return o.end(); }      // opcja zepsute: ścieżki, których serwer nie oddaje (zerwane pobieranie)
      if (u === '/sekret.txt') { if (!opcje.sekret) { o.writeHead(404); return o.end(); } o.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); return o.end(opcje.sekret + '\n'); }
      if (u === '/odbiorca.txt') { if (!opcje.odbiorca) { o.writeHead(404); return o.end(); } o.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); return o.end('# adres Kierownika regionu\n' + opcje.odbiorca + '\n'); }
      if (u === '/adres_aplikacji.txt' && opcje.adresPubliczny !== undefined) { o.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); return o.end('# stały adres aplikacji\n' + opcje.adresPubliczny + '\n'); }      // opcja adresPubliczny: zawartość adres_aplikacji.txt (bez niej serwer oddaje pusty plik z repozytorium)
      if (u === '/poczta_microsoft.txt' && opcje.pocztaMs !== undefined) { if (!opcje.pocztaMs) { o.writeHead(404); return o.end(); } o.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); return o.end('# identyfikator aplikacji Microsoft (test)\n' + opcje.pocztaMs + '\n'); }      // opcja pocztaMs: identyfikator aplikacji Microsoft do szkicu w Outlooku (pusty = brak pliku); jak sekret, zmienna w trakcie testu
      if (u === '/__adres.json') { o.writeHead(200, { 'content-type': 'application/json' }); return o.end(JSON.stringify({ adres: opcje.adresSieci ? `http://${opcje.adresSieci}:${(q.headers.host || '').split(':')[1] || 80}/index.html` : '' })); }      // jak serwer_lokalny.py: adres komputera w sieci (do kodu QR)
      if (u === '/menedzer.txt.txt' && opcje.podwojoneTxt) { o.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); return o.end('Kierownik Testowy\n'); }
      if (u === '/menedzer.txt') { if (opcje.bezMenedzera) { o.writeHead(404); return o.end(); } o.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); return o.end('Kierownik Testowy\n'); }
      if (opcje.wstrzyknij && (u === '/' || u === '/index.html')) { let h = fs.readFileSync(path.join(KORZEN, 'index.html'), 'utf8'); h = h.replace('<head>', '<head><script>' + opcje.wstrzyknij + '</script>'); o.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' }); return o.end(h); }
      let f = path.join(KORZEN, u === '/' ? 'index.html' : u);
      if (!f.startsWith(KORZEN) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { o.writeHead(404); return o.end(); }
      o.writeHead(200, { 'content-type': TYPY[path.extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); fs.createReadStream(f).pipe(o);
    }).listen(0, '127.0.0.1', () => ok({ s, port: s.address().port, adres: 'http://127.0.0.1:' + s.address().port }));
  });
}
/** „Dzisiaj” w testach: stałe (PMT_DZIEN albo 15.10.2026 12:00) — i dla aplikacji (new Date() w stronie), i dla testów liczących dni po stronie Node. */
const dzisTestow = () => new Date(process.env.PMT_DZIEN || '2026-10-15T12:00:00');
const ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
async function otworz({ folder = false, muzykaDomyslna = '0', pocztaDomyslna = 'plik', widokDok = 'lista', w = 1440, h = 900, dsf = 1, motyw = 'dark', mobile = false, bezSieci = true, opcjeSerwera, zalogowany = true, backend, bezVT = false, ruch = 'no-preference', pelnaZorza = false, wycieczka = false, przyklad = false, bezZycia = process.env.ZYCIE !== 'tak' } = {}) {
  backend = backend || new BackendMock();
  const op = opcjeSerwera || {}; if (op.sekret === undefined) op.sekret = 'SEKRET-TESTOWY'; const host = process.env.HTTP_HOST || '';      // HTTP_HOST=pmt.example: aplikacja otwarta pod zwykłym adresem http (nie localhost) — jak na serwerze bez https: brak Web Crypto, service workera i instalacji
  const sv = await serwer(op); if (host) sv.adres = 'http://' + host + ':' + sv.port; const b = await chromium.launch({ args: host ? [...ARGS, `--host-resolver-rules=MAP ${host} 127.0.0.1`] : ARGS });      // obiekt opcji można zmieniać w trakcie testu (np. dołożyć menedzer.txt)
  const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: dsf, colorScheme: motyw, isMobile: mobile, hasTouch: mobile, acceptDownloads: true, reducedMotion: ruch });
  await backend.podepnij(ctx);
  if (zalogowany) {                                  // domyślnie: konto 12345 już zalogowane na tym urządzeniu (testy logowania ustawiają zalogowany:false)
    const ziarno = { kod: '12345', ostatni: '12345', konta: { 12345: { imie: 'Jan Testowy', kontakt: Date.now() } }, status: {}, kolejka: { uruchomienia: 0, dokumenty: 0, minuty: 0 } };      // skrótu hasła na dysku już nie ma (sejf)
    await ctx.addInitScript(z => { try {      // zalogowano już na tej karcie: sesja żyje w pamięci strony, a do nowej strony przechodzi tylko przekazaniem przy przeładowaniu (js/dostep.js) — tu każde wejście udaje F5 ze świeżym przekazaniem
      if (!localStorage.getItem('pmt-web-dostep-v1')) localStorage.setItem('pmt-web-dostep-v1', JSON.stringify(z));
      sessionStorage.setItem('pmt-web-przekaz', JSON.stringify({ t: Date.now(), karta: '12345', skrot: { kod: '12345', skrot: z.skrot }, imie: '', dek: z.dek }));
      Object.defineProperty(PerformanceNavigationTiming.prototype, 'type', { configurable: true, get: () => 'reload' });
    } catch (e) {} }, { ...ziarno, dek: Buffer.from(new Uint8Array(32).map((_, i) => i * 7 + 3)).toString('base64'), skrot: hash('12345', 'haslo123') });
  }
  await ctx.addInitScript(dzien => {      // „dzisiaj” dla aplikacji jest stałe (domyślnie 15.10.2026 → program otwiera się na wrześniu, jak w całym zestawie testów): testy opisują konkretne dni września i nie mogą zależeć od dnia uruchomienia
    const R = Date, przesuniecie = new R(dzien).getTime() - R.now();
    globalThis.Date = class extends R { constructor(...a) { if (a.length === 0) super(R.now() + przesuniecie); else super(...a); } };      // tylko new Date() bez argumentów; Date.now() zostaje prawdziwe (podpisy czasowe wobec atrapy backendu, odstęp do 10 minut)
  }, dzisTestow().toISOString());
  await ctx.addInitScript(() => { window.__testy = true; });      // udostępnia testom jawny odczyt/zapis obiektu konta (window.__pmtDane) mimo szyfrowania magazynu
  if (!przyklad) await ctx.addInitScript(() => { try { localStorage.setItem('pmt-ui-przyklad', 'nie'); } catch (e) {} });      // pierwsze uruchomienie bez przykładowego miesiąca (jak dawniej: od razu „Moje dane”); test przykładu prosi o niego opcją przyklad: true
  if (process.env.RUCH === 'pelny') await ctx.addInitScript(() => { window.__ruchPelny = true; });      // aplikacja domyślnie jest spokojna (bez animacji); testy ruchu włączają pełny ruch: RUCH=pelny
  // okno „Dokumenty do podpisu” w aplikacji otwiera się domyślnie w widoku 3D; zestaw testów od dawna opisuje listę kart, więc domyślnie ustawiamy „Karty” (tylko gdy wyboru jeszcze nie ma —
  // wybór zrobiony w teście przeżywa przeładowanie); widokDok: null = bez ustawiania (prawdziwy domyślny widok), '3d' = widok 3D
  if (widokDok) await ctx.addInitScript(v => { try { if (localStorage.getItem('pmt-ui-widok-dok') === null) localStorage.setItem('pmt-ui-widok-dok', v); } catch (e) {} }, widokDok);
  // sposób wysyłki dokumentów: aplikacja domyślnie otwiera na komputerze program pocztowy (mailto:); zestaw testów od dawna opisuje plik .eml, więc domyślnie ustawiamy „plik”
  // (tylko gdy wyboru jeszcze nie ma); pocztaDomyslna: null = bez ustawiania (prawdziwy domyślny sposób), 'poczta' / 'outlook' = wybrany sposób
  // podkład muzyczny jest w aplikacji domyślnie WŁĄCZONY (rusza przy pierwszym kliknięciu); reszta zestawu testów nie ma go słuchać (obciąża procesor i nic nie sprawdza), więc domyślnie ustawiamy „wyłączony”
  // (tylko gdy wyboru jeszcze nie ma); muzykaDomyslna: null = bez ustawiania (prawdziwy domyślny stan: włączony), '1' = włączony jawnie
  if (muzykaDomyslna !== null) await ctx.addInitScript(v => { try { if (localStorage.getItem('pmt-ui-muzyka') === null) localStorage.setItem('pmt-ui-muzyka', v); } catch (e) {} }, muzykaDomyslna);
  if (pocztaDomyslna) await ctx.addInitScript(v => { try { localStorage.setItem('pmt-ui-poczta-v', '3'); if (localStorage.getItem('pmt-ui-poczta') === null) localStorage.setItem('pmt-ui-poczta', v); } catch (e) {} }, pocztaDomyslna);
  // natywne okno „Zapisz jako” (showSaveFilePicker) nie daje się obsłużyć w przeglądarce bez interfejsu, więc w testach go nie ma — aplikacja wtedy nie oferuje sposobu „pulpit”; test tego sposobu podstawia atrapę
  await ctx.addInitScript(() => { try { Object.defineProperty(window, 'showSaveFilePicker', { value: undefined, writable: true, configurable: true }); } catch (e) {} });
  // folder roboczy na pulpicie (showDirectoryPicker): okna systemowego nie da się obsłużyć w przeglądarce bez interfejsu, więc domyślnie go nie ma (aplikacja działa wtedy po staremu: pobieranie plików i ręczne wgrywanie);
  // folder: true podstawia w jego miejsce folder z prywatnej pamięci przeglądarki (OPFS) — ten sam interfejs uchwytów, bez okna, więc test może zapisywać „podpisane pliki” do folderu, a aplikacja ma je zauważyć
  // Uwaga: odczyt uchwytu z prywatnej pamięci przeglądarki (OPFS) z IndexedDB wywala bezgłowego Chromium (uchwyty z prawdziwego okna wyboru folderu działają normalnie), więc w teście do IndexedDB trafia tylko znacznik,
  // a sam uchwyt czeka w pamięci strony (i jest odtwarzany po odświeżeniu z localStorage) — aplikacja i tak widzi ten sam przepływ: zapamiętaj → wczytaj → sprawdź zgodę.
  if (folder) await ctx.addInitScript(() => {
    window.showDirectoryPicker = async () => { const k = await navigator.storage.getDirectory(); return k.getDirectoryHandle('pmt-folder-testowy', { create: true }); };
    // drugie ograniczenie prywatnej pamięci przeglądarki (OPFS) w Chromium: katalog o nazwie z polskimi znakami („wrzesień 2026”) zachowuje się jak katalog NADRZĘDNY (pliki lądują o piętro wyżej) — na prawdziwym dysku tak nie jest,
    // więc w teście nazwy katalogów są zamieniane na ASCII („wrzesien 2026”); aplikacja i test używają tej samej, polskiej nazwy
    const fold = n => String(n).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l').replace(/Ł/g, 'L'), gdh = FileSystemDirectoryHandle.prototype.getDirectoryHandle;
    FileSystemDirectoryHandle.prototype.getDirectoryHandle = function (n, o) { return gdh.call(this, fold(n), o); };
    const H = window.__opfsH = {}, put = IDBObjectStore.prototype.put, get = IDBObjectStore.prototype.get;
    IDBObjectStore.prototype.put = function (v, key) { if (typeof FileSystemHandle !== 'undefined' && v instanceof FileSystemHandle) { H[key] = v; try { localStorage.setItem('__opfs_' + key, v.name); } catch (e) {} return put.call(this, { opfs: v.name }, key); } return put.call(this, v, key); };
    IDBObjectStore.prototype.get = function (key) { const r = get.call(this, key); if (H[key]) Object.defineProperty(r, 'result', { get: () => H[key], configurable: true }); return r; };
    navigator.storage.getDirectory().then(async k => { for (let i = 0; i < localStorage.length; i++) { const n = localStorage.key(i); if (n && n.startsWith('__opfs_')) H[n.slice(7)] = await k.getDirectoryHandle(localStorage.getItem(n)); } }).catch(() => {});
  });
  else await ctx.addInitScript(() => { try { Object.defineProperty(window, 'showDirectoryPicker', { value: undefined, writable: true, configurable: true }); } catch (e) {} });
  if (!wycieczka) await ctx.addInitScript(() => { try { localStorage.setItem('pmt-ui-wycieczka', '1'); } catch (e) {} });      // wycieczka po aplikacji (pierwsze uruchomienie) nie zasłania testów; test wycieczki prosi o nią wprost
  if (!pelnaZorza) await ctx.addInitScript(() => { window.__zorzaRzadko = true; });      // testy na grafice programowej: zorza odświeża się rzadko (aplikacja produkcyjna go nie ustawia)
  if (bezZycia) await ctx.addInitScript(() => { window.__bezZycia = true; });      // „życie” kalendarza i fiolek (koniec css/aplikacja.css) domyślnie wyłączone w testach: Playwright nie klika elementów, które się poruszają („element is not stable”); test zycie_app.js włącza je jawnie (bezZycia: false), a ZYCIE=tak włącza je w każdym teście
  if (bezVT) await ctx.addInitScript(() => { try { Document.prototype.startViewTransition = undefined; delete document.startViewTransition; } catch (e) {} });   // jak Firefox: bez View Transitions
  const p = await ctx.newPage(); p.setDefaultTimeout(180000); const bledy = [];
  p.on('pageerror', e => bledy.push('PAGEERR ' + e.message + ' @ ' + String(e.stack || '').split('\n').slice(1, 3).map(x => x.trim().replace(/^at /, '')).join(' < ')));
  p.on('console', m => { if (m.type() === 'error') bledy.push('KONSOLA ' + m.text().slice(0, 240)); });
  if (bezSieci) await p.route(/nominatim|osrm|openstreetmap|googleapis/, r => r.abort());
  return { sv, b, ctx, p, bledy, backend, adres: sv.adres, host, zamknij: async () => { await b.close(); sv.s.close(); } };
}
/** Generowanie z potwierdzeniem: klik „Generuj”, sprawdzenie danych w arkuszu, „Potwierdzam i generuję”, czekanie na wynik. */
async function generuj(p, { tap = false, czekaj = 240000 } = {}) {
  await (tap ? p.tap('#podpisz') : p.click('#podpisz'));
  await p.waitForSelector('#potwierdz-gen', { timeout: 60000 });
  await (tap ? p.tap('#potwierdz-gen') : p.click('#potwierdz-gen'));
  await p.waitForFunction(() => document.querySelector('#kA.po-gen'), null, { timeout: czekaj, polling: 300 });
}
/** Aplikacja zaczyna od trybu „Tydzień”; testy, które opisują wieczory (dni wolne 21–26 wrz. itd.), wybierają „Wieczory” tak jak użytkownik. */
async function wieczory(p, { tap = false } = {}) {
  await (tap ? p.tap('#parametry [data-tryb="wieczory"]') : p.click('#parametry [data-tryb="wieczory"]'));
  await p.waitForFunction(() => document.querySelector('#parametry [data-tryb="wieczory"]').getAttribute('aria-pressed') === 'true', null, { timeout: 30000, polling: 200 });
  await p.waitForTimeout(600);
}
/** „Moje dane”: adres jest w pięciu polach (nazwa ulicy, nr budynku, nr mieszkania, kod, miejscowość) i ma przełącznik rodzaju („Ulica” / „Miejscowość bez ulicy (wieś)”). Pomocnik przyjmuje adres jako jeden napis
 *  („ul. Testowa 1, 00-001 Warszawa”) i wypełnia pola tak, jak zrobiłby to użytkownik: w polu ulicy ląduje SAMA nazwa („Testowa” — „ul.” dopisuje program). Rodzaj: jawny przedrostek = ulica; napis bez
 *  przedrostka to domyślnie ulica, a wieś trzeba wskazać trzecim argumentem ('wies'). Napisu, którego nie da się rozdzielić (test błędnych adresów), nie zgaduje — wpisuje całość w pole nazwy. */
async function wpiszAdres(p, adres, typ) {
  const A = await import(require('url').pathToFileURL(path.join(KORZEN, 'js', 'adres.js')).href);
  const c = A.rozbierzAdres(adres, typ || 'ulica') || { typ: typ || 'ulica', ulica: String(adres), nr: '', lokal: '', kod: '', miasto: '' };
  if ((await p.getAttribute(`.adres-typ [data-typ="${c.typ}"]`, 'aria-pressed')) !== 'true') await p.click(`.adres-typ [data-typ="${c.typ}"]`);
  for (const [sel, k] of [['#d-ulica', 'ulica'], ['#d-nr', 'nr'], ['#d-lokal', 'lokal'], ['#d-kod', 'kod'], ['#d-miasto', 'miasto']]) await p.fill(sel, c[k]);
}
module.exports = { otworz, serwer, KORZEN, generuj, wieczory, dzisTestow, wpiszAdres };
