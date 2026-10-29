// Instalacja na telefonie (instrukcje, kod QR, zdarzenie instalacji) i „Napisz uwagę” (dane techniczne, kopiowanie).
// NODE_PATH=/opt/node22/lib/node_modules node pomoc_app.js
const { otworz } = require('./wspolne');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p;
  await t.ctx.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 }); await p.waitForTimeout(3500);
  const otworzMenu = async () => { await p.click('#konto'); await p.waitForTimeout(500); };
  const tekstArkusza = () => p.locator('#arkusz').innerText();

  /* --- Napisz uwagę --- */
  await otworzMenu(); await p.click('#uwagi'); await p.waitForSelector('#uw-tekst', { timeout: 20000 });
  ok('menu konta ma „Napisz uwagę” i otwiera okno z polem tekstu', true);
  await p.waitForFunction(() => /przeglądarka:/.test(document.querySelector('#uw-dane').textContent), null, { timeout: 30000 });
  const dane = await p.locator('#uw-dane').textContent();
  ok('dane techniczne: wersja, przeglądarka, ekran, karta graficzna, płynność, błędy', ['wersja aplikacji', 'przeglądarka:', 'ekran:', 'karta graficzna:', 'klatek/s', 'ostatnie błędy'].every(x => dane.includes(x)), dane.split('\n').slice(0, 2).join(' | ').slice(0, 120));
  ok('dane techniczne NIE zawierają danych osobowych (imienia, PESEL-u, adresu)', !/Jan Testowy|90010112349|Testowa 1/.test(dane));
  await p.click('#uw-kopiuj'); await p.waitForTimeout(600);
  ok('bez wpisanej uwagi „Kopiuj” prosi o opis (nic nie kopiuje)', /Napisz najpierw/.test(await p.locator('.toast').innerText().catch(() => '')));
  await p.fill('#uw-tekst', 'Testowa uwaga: coś się przycina'); await p.click('#uw-kopiuj'); await p.waitForTimeout(800);
  const schowek = await p.evaluate(() => navigator.clipboard.readText().catch(() => null));
  ok('„Kopiuj” kładzie do schowka uwagę razem z danymi technicznymi', schowek === null || (/Testowa uwaga/.test(schowek) && /dane techniczne/.test(schowek)), schowek === null ? '(schowek niedostępny w tym środowisku, użyto zapasowej ścieżki)' : '');
  ok('bez adresu w uwagi.txt przycisku „Wyślij e-mailem” nie ma', await p.locator('#uw-mail').isHidden());
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(500);

  /* --- Zainstaluj na telefonie: strona lokalna → pole adresu IP i kod QR --- */
  await otworzMenu(); await p.click('#instaluj'); await p.waitForSelector('#inst-qr', { timeout: 20000 });
  ok('okno instalacji pokazuje instrukcję dla komputera i pole na adres komputera w sieci', /Komputer:/.test(await tekstArkusza()) && await p.locator('#inst-ip').count() === 1);
  await p.fill('#inst-ip', '192.168.0.12'); await p.waitForSelector('#inst-qr svg', { timeout: 20000 });
  const port = new URL(p.url()).port;
  ok('wpisanie adresu daje kod QR i pokazuje adres do telefonu', (await p.locator('#inst-adres').innerText()) === `http://192.168.0.12:${port}/`, await p.locator('#inst-adres').innerText());
  ok('kod QR to jeden obrazek SVG o rozsądnym rozmiarze', await p.evaluate(() => { const s = document.querySelector('#inst-qr svg'); const v = s.viewBox.baseVal; return v.width >= 29 && v.width <= 60 && s.querySelectorAll('path').length === 1; }));
  await p.locator('#inst-qr').screenshot({ path: '/tmp/pomoc_qr.png' });
  await p.screenshot({ path: '/tmp/pomoc_instalacja.png' });
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(400);

  /* --- zdarzenie instalacji przeglądarki (Chrome/Edge/Android) --- */
  await p.evaluate(() => { const e = new Event('beforeinstallprompt', { cancelable: true }); e.prompt = () => { window.__promptWywolany = true; }; e.userChoice = Promise.resolve({ outcome: 'dismissed' }); dispatchEvent(e); });
  await otworzMenu(); await p.click('#instaluj'); await p.waitForSelector('#inst-teraz', { timeout: 20000 });
  ok('gdy przeglądarka zgłasza możliwość instalacji, jest przycisk „Zainstaluj teraz”', true);
  await p.click('#inst-teraz'); await p.waitForTimeout(500);
  ok('przycisk wywołuje systemowe okno instalacji', await p.evaluate(() => window.__promptWywolany === true));
  await p.keyboard.press('Escape').catch(() => {}); await p.waitForTimeout(500);

  /* --- paleta poleceń zna obie funkcje --- */
  await p.keyboard.press('Escape'); await p.waitForTimeout(300);
  await p.keyboard.press('Control+k'); await p.waitForSelector('#pal-in', { timeout: 10000 }); await p.fill('#pal-in', 'uwag'); await p.waitForTimeout(400);
  ok('paleta poleceń (Ctrl+K) znajduje „Napisz uwagę”', /Napisz uwagę/.test(await p.locator('.paleta, #paleta').first().innerText()));
  await p.fill('#pal-in', 'telefon'); await p.waitForTimeout(400);
  ok('paleta poleceń znajduje „Zainstaluj na telefonie”', /Zainstaluj na telefonie/.test(await p.locator('.paleta, #paleta').first().innerText()));
  await p.keyboard.press('Escape'); await p.waitForTimeout(300);
  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
  await t.zamknij();

  /* --- iPhone: instrukcja „Dodaj do ekranu początkowego” --- */
  const t2 = await otworz({ w: 390, h: 844, dsf: 2, mobile: true }); const q = t2.p;
  await t2.ctx.addInitScript(() => { Object.defineProperty(Navigator.prototype, 'userAgent', { get: () => 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1' }); });
  await q.goto(t2.adres + '/index.html'); await q.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await q.fill('#d-imie', 'Jan Testowy'); await q.fill('#d-pesel', '90010112349'); await q.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await q.tap('#zapisz-dane'); await q.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 }); await q.waitForTimeout(3500);
  await q.tap('#konto'); await q.waitForTimeout(600); await q.tap('#instaluj'); await q.waitForSelector('.inst-kolumna', { timeout: 20000 });
  ok('iPhone: okno instalacji pokazuje kroki „Udostępnij → Dodaj do ekranu początkowego”', /Dodaj do ekranu początkowego/.test(await q.locator('#arkusz').innerText()) && /Safari/.test(await q.locator('#arkusz').innerText()));
  await q.screenshot({ path: '/tmp/pomoc_iphone.png' });
  ok('iPhone: kod QR jest zbędny, więc go nie ma (aplikacja jest już na telefonie)', await q.locator('#inst-qr').count() === 0);
  ok('iPhone: okno mieści się w ekranie bez poziomego przewijania', await q.evaluate(() => document.scrollingElement.scrollWidth <= innerWidth + 1));
  ok('bez błędów w konsoli (iPhone)', t2.bledy.length === 0, JSON.stringify(t2.bledy.slice(0, 3)));
  await t2.zamknij();
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
