// Wspólne dla testów przeglądarkowych: serwer plików z katalogu web/, uruchomienie Chromium z WebGL (SwiftShader).
const { chromium } = require('playwright'); const { BackendMock, hash } = require('./backend_mock'); const http = require('http'), fs = require('fs'), path = require('path');
const KORZEN = process.env.PMT_KORZEN ? path.resolve(process.env.PMT_KORZEN) : path.resolve(__dirname, '..');      // PMT_KORZEN=<katalog>: test na gotowej paczce strony (np. po kroku „Przygotuj paczkę strony” z .github/workflows/web-pages.yml)
const TYPY = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.zip': 'application/zip', '.whl': 'application/zip', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.py': 'text/plain; charset=utf-8', '.css': 'text/css', '.webp': 'image/webp', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
function serwer(opcje = {}) {
  return new Promise(ok => {
    const s = http.createServer((q, o) => {
      const u = decodeURIComponent(q.url.split('?')[0]);
      if (u === '/sekret.txt') { if (!opcje.sekret) { o.writeHead(404); return o.end(); } o.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); return o.end(opcje.sekret + '\n'); }
      if (u === '/odbiorca.txt') { if (!opcje.odbiorca) { o.writeHead(404); return o.end(); } o.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); return o.end('# adres Kierownika regionu\n' + opcje.odbiorca + '\n'); }
      if (u === '/adres_aplikacji.txt' && opcje.adresPubliczny !== undefined) { o.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); return o.end('# stały adres aplikacji\n' + opcje.adresPubliczny + '\n'); }      // opcja adresPubliczny: zawartość adres_aplikacji.txt (bez niej serwer oddaje pusty plik z repozytorium)
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
const ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
async function otworz({ w = 1440, h = 900, dsf = 1, motyw = 'dark', mobile = false, bezSieci = true, opcjeSerwera, zalogowany = true, backend, bezVT = false, ruch = 'no-preference', pelnaZorza = false, wycieczka = false, przyklad = false, bezZycia = process.env.ZYCIE !== 'tak' } = {}) {
  backend = backend || new BackendMock();
  const op = opcjeSerwera || {}; if (op.sekret === undefined) op.sekret = 'SEKRET-TESTOWY'; const host = process.env.HTTP_HOST || '';      // HTTP_HOST=pmt.example: aplikacja otwarta pod zwykłym adresem http (nie localhost) — jak na serwerze bez https: brak Web Crypto, service workera i instalacji
  const sv = await serwer(op); if (host) sv.adres = 'http://' + host + ':' + sv.port; const b = await chromium.launch({ args: host ? [...ARGS, `--host-resolver-rules=MAP ${host} 127.0.0.1`] : ARGS });      // obiekt opcji można zmieniać w trakcie testu (np. dołożyć menedzer.txt)
  const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: dsf, colorScheme: motyw, isMobile: mobile, hasTouch: mobile, acceptDownloads: true, reducedMotion: ruch });
  await backend.podepnij(ctx);
  if (zalogowany) {                                  // domyślnie: konto 12345 już zalogowane na tym urządzeniu (testy logowania ustawiają zalogowany:false)
    const ziarno = { kod: '12345', ostatni: '12345', konta: { 12345: { imie: 'Jan Testowy', kontakt: Date.now() } }, status: {}, kolejka: { uruchomienia: 0, dokumenty: 0, minuty: 0 } };      // skrótu hasła na dysku już nie ma (sejf)
    await ctx.addInitScript(z => { try { if (!localStorage.getItem('pmt-web-dostep-v1')) localStorage.setItem('pmt-web-dostep-v1', JSON.stringify(z)); sessionStorage.setItem('pmt-web-sesja-karty', '12345'); sessionStorage.setItem('pmt-web-dek', z.dek); sessionStorage.setItem('pmt-web-skrot', JSON.stringify({ kod: '12345', skrot: z.skrot })); } catch (e) {} }, { ...ziarno, dek: Buffer.from(new Uint8Array(32).map((_, i) => i * 7 + 3)).toString('base64'), skrot: hash('12345', 'haslo123') });      // sessionStorage: zalogowano już na tej karcie (logowanie jest wymagane przy każdym uruchomieniu)
  }
  await ctx.addInitScript(() => { window.__testy = true; });      // udostępnia testom jawny odczyt/zapis obiektu konta (window.__pmtDane) mimo szyfrowania magazynu
  if (!przyklad) await ctx.addInitScript(() => { try { localStorage.setItem('pmt-ui-przyklad', 'nie'); } catch (e) {} });      // pierwsze uruchomienie bez przykładowego miesiąca (jak dawniej: od razu „Moje dane”); test przykładu prosi o niego opcją przyklad: true
  if (process.env.RUCH === 'pelny') await ctx.addInitScript(() => { window.__ruchPelny = true; });      // aplikacja domyślnie jest spokojna (bez animacji); testy ruchu włączają pełny ruch: RUCH=pelny
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
module.exports = { otworz, serwer, KORZEN, generuj, wieczory };
