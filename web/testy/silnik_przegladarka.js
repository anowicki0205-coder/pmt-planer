// Test: silnik w prawdziwej przeglądarce (Chromium) — start, kontrola, generowanie, PDF-y. Uruchom: NODE_PATH=/opt/node22/lib/node_modules node silnik_przegladarka.js
const { chromium } = require('playwright'); const http = require('http'), fs = require('fs'), path = require('path');
const KORZEN = path.resolve(__dirname, '..');
const TYPY = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.zip': 'application/zip', '.whl': 'application/zip', '.ttf': 'font/ttf', '.py': 'text/plain', '.css': 'text/css' };
const serwer = http.createServer((q, o) => {
  const u = decodeURIComponent(q.url.split('?')[0]);
  if (u === '/menedzer.txt') { o.writeHead(200, { 'content-type': 'text/plain' }); return o.end('Kierownik Testowy\n'); }
  const f = path.join(KORZEN, u); if (!f.startsWith(KORZEN) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { o.writeHead(404); return o.end(); }
  o.writeHead(200, { 'content-type': TYPY[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(o);
}).listen(0, async () => {
  const port = serwer.address().port; let kod = 0;
  const b = await chromium.launch(); const ctx = await b.newContext(); const p = await ctx.newPage();
  p.on('pageerror', e => console.log('PAGEERR', e.message)); p.on('console', m => { if (m.type() === 'error') console.log('KONSOLA', m.text().slice(0, 200)); });
  await p.route(/nominatim|osrm|openstreetmap/, r => r.abort());       // bez sieci: silnik ma swoje szacunki
  await p.goto(`http://127.0.0.1:${port}/testy/harness.html`); await p.waitForFunction('window.gotowe');
  const dane = { imie: 'Jan Testowy', pesel: '90010112349', adres: 'ul. Testowa 1, 00-001 Warszawa', kwota: 3095.26, rok: 2026, miesiac: 9, tryb: 'wieczory', silnik_powyzej_900: true, wolne: [21, 22, 23, 24, 25, 26], stanowisko: 'Merchandiser' };
  const w = await p.evaluate(d => uruchom(d), dane);
  const sprawdz = (opis, ok, szcz = '') => { console.log((ok ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!ok) kod = 1; };
  sprawdz('kontrola przed generowaniem przeszła', w.przyg.ok, JSON.stringify(w.przyg).slice(0, 160));
  sprawdz('stawka 1,15 zł/km dla silnika powyżej 900 cm³', w.przyg.stawka === 1.15);
  sprawdz('limit dnia 587,19 zł i dokumentu 986,34 zł z silnika', w.stale.limit_dnia === 587.19 && w.stale.limit_dokumentu === 986.34);
  sprawdz('suma dni = zamówiona kwota co do grosza', Math.abs(w.wynik.suma - 3095.26) < 0.005, String(w.wynik.suma));
  sprawdz('żaden dzień ponad limit dnia', w.wynik.dni.every(d => d.suma <= 587.19 + 0.005));
  sprawdz('4 polecenia + rozliczenie = 5 plików PDF', w.pdf.length === 5, w.pdf.map(x => x.nazwa).join(' | '));
  sprawdz('każdy plik to PDF', w.pdf.every(x => x.naglowek === '%PDF-' && x.bajtow > 5000));
  sprawdz('żaden dzień w niedzielę ani w dniach wolnych użytkownika', w.wynik.dni.every(d => { const t = new Date(d.data + 'T12:00:00'); return t.getDay() !== 0 && ![21,22,23,24,25,26].includes(t.getDate()); }));
  sprawdz('dokumenty: 4 polecenia, każde do 986,34 zł, razem = suma', w.wynik.dokumenty.length === 4 && w.wynik.dokumenty.every(d => d.kw <= 986.34 + 0.005) && Math.abs(w.wynik.dokumenty.reduce((a, d) => a + d.kw, 0) - 3095.26) < 0.01, JSON.stringify(w.wynik.dokumenty.map(d => [d.od, d.do, d.kw])));
  sprawdz('każdy dzień ma kilometry, etapy i punkty trasy', w.wynik.dni.every(d => d.km > 0 && d.etapy.length >= 2 && d.punkty.length === d.etapy.length + 1 && d.dokument >= 1));
  sprawdz('kwota nie jest niepełna', !w.wynik.niepelna);
  console.log(`  czas: start silnika ${w.czasStart} ms, generowanie ${w.czasGen} ms; dni: ${w.wynik.dni.length}; źródło km: ${w.wynik.zrodlo.etykieta}`);
  await b.close(); serwer.close(); process.exit(kod);
});
