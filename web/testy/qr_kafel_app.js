// Kafel „Na telefon” przy uruchomieniu z komputera lokalnego (localhost): gdy serwer lokalny podaje adres komputera w sieci (serwer_lokalny.py → /__adres.json),
// kod QR jest widoczny OD RAZU; bez tego serwera kafel prosi o wpisanie adresu. Gdy w adres_aplikacji.txt stoi stały adres publiczny, kod prowadzi ZAWSZE tam —
// niezależnie od komputera (adres komputera w sieci jest wtedy pomijany, a w oknie nie ma pola na adres IP). Kod jest odczytywany dekoderem (dekoduj_qr.py, OpenCV): musi zawierać dokładnie ten adres.
// NODE_PATH=/opt/node22/lib/node_modules QR_PYTHON=/tmp/qrvenv/bin/python node qr_kafel_app.js
const { otworz } = require('./wspolne'); const { spawnSync } = require('child_process');
const DEKODER = process.env.QR_PYTHON || '';      // interpreter z OpenCV (venv): bez niego sprawdzamy tylko adres przekazany do kodu, nie sam rysunek
const odczytaj = async (p, sel, plik) => { if (!DEKODER) return null; await p.locator(sel).screenshot({ path: plik }); const r = spawnSync(DEKODER, [__dirname + '/dekoduj_qr.py', plik], { encoding: 'utf8' }); return r.status === 0 ? r.stdout.trim() : '(nie odczytano)'; };
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const PUB = 'https://planer.example.pl/pmt/';
  for (const [nazwa, opcje] of [['z adresem w sieci', { adresSieci: '192.168.0.12' }], ['bez adresu w sieci', {}], ['ze stałym adresem publicznym (niezależnie od komputera)', { adresSieci: '192.168.0.12', adresPubliczny: PUB }], ['z błędnym adresem w adres_aplikacji.txt', { adresPubliczny: 'javascript:alert(1)' }]]) {
    const t = await otworz({ w: 1440, h: 900, opcjeSerwera: opcje, przyklad: true }); const p = t.p;
    await p.goto(t.adres + '/index.html'); await p.waitForFunction(() => !document.querySelector('#ladowanie.widoczny') && !document.querySelector('#aplikacja.czeka'), null, { timeout: 120000 }).catch(() => {});
    await p.waitForTimeout(3500);
    const port = new URL(t.adres).port;
    if (opcje.adresPubliczny === PUB) {
      await p.waitForSelector('#qr-kafel svg', { timeout: 20000 });
      const r = await p.evaluate(() => { const b = document.querySelector('#qr-kafel'); return { adres: b.dataset.adres, lokalny: b.dataset.lokalny, w: b.querySelector('svg').getBoundingClientRect().width }; });
      ok(`${nazwa}: kod QR jest od razu, a prowadzi pod adres z pliku — nie pod adres komputera`, r.adres === PUB && !r.lokalny && r.w >= 60 && !/192\.168/.test(r.adres), JSON.stringify(r));
      const odczyt = await odczytaj(p, '#qr-kafel svg', '/tmp/qr_kafel_pub.png');
      if (odczyt !== null) ok(`${nazwa}: kod odczytany dekoderem zawiera dokładnie ten adres`, odczyt === PUB, odczyt);
      await p.click('#qr-kafel'); await p.waitForSelector('#inst-qr svg', { timeout: 20000 }); await p.waitForTimeout(500);
      ok(`${nazwa}: okno „Zainstaluj na telefonie” pokazuje ten sam adres i nie prosi o adres IP`, (await p.locator('#inst-adres').innerText()) === PUB && (await p.locator('#inst-ip').count()) === 0, await p.locator('#inst-adres').innerText());
      const odczyt2 = await odczytaj(p, '#inst-qr svg', '/tmp/qr_okno_pub.png');
      if (odczyt2 !== null) ok(`${nazwa}: kod w oknie też zawiera ten adres`, odczyt2 === PUB, odczyt2);
    } else if (opcje.adresPubliczny) {
      await p.waitForSelector('#qr-kafel', { timeout: 20000 });
      ok(`${nazwa}: niepoprawny wpis jest pomijany (kafel prosi o adres komputera, jak bez pliku)`, /wpisz adres/.test(await p.locator('#qr-kafel').innerText()) && (await p.locator('#qr-kafel svg').count()) === 0);
    } else if (opcje.adresSieci) {
      await p.waitForSelector('#qr-kafel svg', { timeout: 20000 });
      const r = await p.evaluate(() => { const k = document.querySelector('#kQ'), b = document.querySelector('#qr-kafel'), s = b.querySelector('svg').getBoundingClientRect(), kk = k.getBoundingClientRect(); return { adres: b.dataset.adres, lokalny: b.dataset.lokalny, w: s.width, h: s.height, wTile: s.left >= kk.left && s.right <= kk.right && s.top >= kk.top && s.bottom <= kk.bottom, ukryty: k.hidden, tekst: k.innerText.replace(/\n/g, ' | ') }; });
      ok(`${nazwa}: kod QR jest widoczny od razu, bez wpisywania adresu`, !r.ukryty && r.w >= 60 && r.h >= 60 && r.wTile && !r.lokalny, JSON.stringify(r));
      ok(`${nazwa}: kod prowadzi pod adres komputera w sieci (http://192.168.0.12:${port}/index.html)`, r.adres === `http://192.168.0.12:${port}/index.html`, r.adres);
      const odczytSieci = await odczytaj(p, '#qr-kafel svg', '/tmp/qr_kafel_siec.png');
      if (odczytSieci !== null) ok(`${nazwa}: kod odczytany dekoderem zawiera adres komputera w sieci`, odczytSieci === `http://192.168.0.12:${port}/index.html`, odczytSieci);
      await p.click('#qr-kafel'); await p.waitForSelector('#inst-qr svg', { timeout: 20000 }); await p.waitForTimeout(500);
      ok(`${nazwa}: okno „Zainstaluj na telefonie” też ma od razu kod i adres`, (await p.locator('#inst-adres').innerText()) === `http://192.168.0.12:${port}/index.html` && (await p.locator('#inst-ip').inputValue()) === '192.168.0.12', await p.locator('#inst-adres').innerText());
    } else {
      await p.waitForSelector('#qr-kafel', { timeout: 20000 });
      ok(`${nazwa}: kafel prosi o adres komputera (kodu nie da się ułożyć bez adresu)`, /wpisz adres/.test(await p.locator('#qr-kafel').innerText()) && (await p.locator('#qr-kafel svg').count()) === 0);
    }
    await p.screenshot({ path: `/tmp/qr_kafel_${opcje.adresPubliczny === PUB ? 'publiczny' : opcje.adresSieci ? 'jest' : 'brak'}.png` });
    console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 4))); if (t.bledy.length) kod = 1;
    await t.zamknij();
  }
  /* aplikacja ZAINSTALOWANA (okno bez paska adresu, display-mode: standalone): na komputerze kafel z kodem QR zostaje (stąd telefon i tak się zaczyna),
     na telefonie znika (aplikacja już na nim jest). Wcześniej znikał w każdej zainstalowanej aplikacji, także na komputerze. */
  for (const [nazwa, ua, widoczny] of [['zainstalowana na komputerze', null, true], ['zainstalowana na telefonie (Android)', 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36', false], ['zwykła przeglądarka na komputerze', 'zwykla', true]]) {
    const t = await otworz({ w: 1440, h: 900, opcjeSerwera: { adresPubliczny: PUB }, przyklad: true }); const p = t.p;
    await t.ctx.addInitScript(({ ua, std }) => {
      if (ua && ua !== 'zwykla') Object.defineProperty(navigator, 'userAgent', { get: () => ua });
      if (std) { const m = window.matchMedia.bind(window); window.matchMedia = q => /display-mode:\s*standalone/.test(q) ? { matches: true, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, onchange: null, dispatchEvent: () => false } : m(q); }
    }, { ua, std: ua !== 'zwykla' });
    await p.goto(t.adres + '/index.html'); await p.waitForFunction(() => !document.querySelector('#ladowanie.widoczny') && !document.querySelector('#aplikacja.czeka'), null, { timeout: 120000 }).catch(() => {});
    await p.waitForTimeout(3500);
    const stan = await p.evaluate(() => ({ kafel: !document.querySelector('#kQ').hidden, klasa: document.documentElement.classList.contains('ma-qr'), standalone: matchMedia('(display-mode: standalone)').matches }));
    ok(`kafel „Na telefon” — ${nazwa}: ${widoczny ? 'jest' : 'nie ma'}`, stan.kafel === widoczny && stan.klasa === widoczny && (ua === 'zwykla' ? !stan.standalone : stan.standalone), JSON.stringify(stan));
    await t.zamknij();
  }
  process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
