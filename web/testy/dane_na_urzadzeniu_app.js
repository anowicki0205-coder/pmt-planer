// Dane na urządzeniu: pamięć silnika (współrzędne adresów i trasy) leży zaszyfrowana w magazynie konta, nie w jawnej bazie „/home/pyodide”, i wraca do silnika po starcie;
// wylogowanie, zmiana konta i „Usuń dane z urządzenia” nie zostawiają śladów cudzych adresów,
// a usunięcie danych kasuje profil z PESEL-em, miesiące, PDF-y i zapamiętane konto. Oraz: pliki ustawień (adres_aplikacji.txt, odbiorca.txt) idą z sieci, nie z pamięci.
// NODE_PATH=/opt/node22/lib/node_modules node dane_na_urzadzeniu_app.js
const { otworz, generuj } = require('./wspolne'); const { BackendMock } = require('./backend_mock');
(async () => {
  const B = new BackendMock(); const t = await otworz({ w: 1440, h: 900, zalogowany: false, backend: B }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const czekajAplikacje = () => p.waitForFunction(() => !document.querySelector('#aplikacja').classList.contains('zamknieta') && !document.querySelector('#ladowanie').classList.contains('widoczny'), null, { timeout: 180000, polling: 200 });
  const zaloguj = async () => { await p.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await p.waitForTimeout(800); await p.fill('#dz-kod', '12345'); await p.fill('#dz-haslo', 'haslo123'); await p.keyboard.press('Enter'); await czekajAplikacje(); };
  const pamiec = () => p.evaluate(async () => {
    const baza = n => new Promise(ok => { const q = indexedDB.open(n); q.onsuccess = () => { const db = q.result, o = {}; const nazwy = [...db.objectStoreNames]; if (!nazwy.length) { db.close(); ok([]); return; } const r = db.transaction(nazwy[0]).objectStore(nazwy[0]).getAllKeys(); r.onsuccess = () => { db.close(); ok(r.result.map(String)); }; r.onerror = () => ok([]); }; q.onerror = () => ok([]); });
    const nazwy = (await indexedDB.databases()).map(d => d.name);
    const konta = nazwy.includes('pmt-web-pliki:12345') ? await baza('pmt-web-pliki:12345') : [];
    const wartosc = k => new Promise(ok => { const q = indexedDB.open('pmt-web-pliki:12345'); q.onsuccess = () => { const db = q.result, r = db.transaction('pliki').objectStore('pliki').get(k); r.onsuccess = () => { db.close(); ok(Array.from(new Uint8Array(r.result || []))); }; }; });
    const silnikKonta = []; for (const k of konta.filter(x => x.startsWith('__silnik/'))) silnikKonta.push({ k, b: await wartosc(k) });
    return { bazy: nazwy, silnik: nazwy.includes('/home/pyodide') ? (await baza('/home/pyodide')).filter(x => /\.pmt_|menedzer/.test(x)) : [], pdf: konta.length, silnikKonta,
      ls: Object.keys(localStorage), dostep: JSON.parse(localStorage.getItem('pmt-web-dostep-v1') || '{}') };
  });

  await p.route(/nominatim\.openstreetmap\.org\/search/, r => r.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: '[{"lat":"52.2297","lon":"21.0122"}]' }));      // współrzędne domu trafiają do pamięci silnika (reszta sieci zablokowana)
  await p.goto(t.adres + '/index.html'); await zaloguj();
  await p.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 60000 }); await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200); await generuj(p); await p.waitForTimeout(3500);
  let m = await pamiec();
  ok('po generowaniu: profil i PDF-y są na urządzeniu', m.ls.includes('pmt-web-v1:12345') && m.pdf >= 6, JSON.stringify({ pdf: m.pdf }));
  ok('pamięci silnika nie ma w jawnej bazie „/home/pyodide” (IDBFS)', !m.bazy.includes('/home/pyodide'), JSON.stringify(m.bazy));
  ok('pamięć silnika leży w magazynie konta jako zaszyfrowana koperta (bez jawnego adresu)', m.silnikKonta.length >= 1 && m.silnikKonta.every(x => x.b[0] === 0x50 && x.b[1] === 0x4d && x.b[2] === 0x54 && x.b[3] === 0x31 && !/testowa|warszawa/i.test(Buffer.from(x.b).toString('latin1'))), JSON.stringify(m.silnikKonta.map(x => x.k + ':' + x.b.length)));
  const pamiecSilnika = () => p.evaluate(async () => (await window.__pmtSilnik.eksportPamieci()).pliki.map(x => x.nazwa + ':' + new TextDecoder().decode(x.bajty)).sort().join('|'));
  const przed = await pamiecSilnika();
  ok('silnik zapamiętał, do kogo należy jego pamięć', await p.evaluate(() => localStorage.getItem('pmt-silnik-wlasciciel')) === '12345');

  /* zmiana konta: pamięć silnika należała do innego konta — po starcie jest czyszczona */
  await p.evaluate(() => localStorage.setItem('pmt-silnik-wlasciciel', '99999'));
  await p.keyboard.press('F5').catch(() => {}); await p.reload(); await czekajAplikacje(); await p.waitForTimeout(3000);
  m = await pamiec();
  ok('po zmianie konta ślady silnika poprzedniego użytkownika są skasowane, a dane bieżącego konta zostają', m.silnik.length === 0 && m.ls.includes('pmt-web-v1:12345') && m.pdf >= 6, JSON.stringify({ silnik: m.silnik, pdf: m.pdf }));
  ok('właścicielem pamięci silnika jest teraz bieżące konto', await p.evaluate(() => localStorage.getItem('pmt-silnik-wlasciciel')) === '12345');
  ok('po starcie silnik dostał z powrotem swoją pamięć z magazynu konta (te same pliki i treść, z adresem domu)', /testowa 1/.test(przed) && await pamiecSilnika() === przed, przed.slice(0, 160));

  /* wylogowanie czyści pamięć silnika, ale nie dane konta */
  await generuj(p, {}).catch(() => {}); await p.waitForTimeout(500);
  await p.evaluate(() => document.querySelector('#wyloguj').click());
  await p.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await p.waitForTimeout(1500);
  m = await pamiec();
  ok('po wylogowaniu pamięć silnika jest pusta, a dane konta zostają (po ponownym logowaniu są na miejscu)', m.silnik.length === 0 && m.ls.includes('pmt-web-v1:12345') && m.pdf >= 6, JSON.stringify({ silnik: m.silnik, pdf: m.pdf }));
  await zaloguj(); await p.waitForTimeout(2000);
  ok('po ponownym zalogowaniu dane konta wróciły', (await p.locator('#imie-pasek').innerText()) === 'Jan Testowy');

  /* „Usuń dane z urządzenia” */
  await p.click('#konto'); await p.waitForTimeout(500); await p.click('#moje-dane'); await p.waitForSelector('#usun-dane', { timeout: 20000 });
  await p.click('#usun-dane'); await p.waitForSelector('#usun-dane-tak'); await p.waitForTimeout(400);
  ok('okno potwierdzenia mówi, co zostanie usunięte i że nie da się tego cofnąć', /PESEL/.test(await p.locator('#arkusz-tresc').innerText()) && /Nie da się tego cofnąć/.test(await p.locator('#arkusz-tresc').innerText()));
  await p.click('[data-zamknij]'); await p.waitForTimeout(600);
  ok('„Zostaw dane” niczego nie usuwa', (await pamiec()).ls.includes('pmt-web-v1:12345'));
  await p.click('#konto'); await p.waitForTimeout(500); await p.click('#moje-dane'); await p.waitForSelector('#usun-dane'); await p.click('#usun-dane'); await p.waitForSelector('#usun-dane-tak'); await p.click('#usun-dane-tak');
  await p.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await p.waitForTimeout(2000);
  m = await pamiec();
  ok('po usunięciu: brak profilu (PESEL), miesięcy i PDF-ów konta', !m.ls.includes('pmt-web-v1:12345') && !m.bazy.includes('pmt-web-pliki:12345'), JSON.stringify({ ls: m.ls, bazy: m.bazy }));
  ok('po usunięciu: brak śladów silnika', m.silnik.length === 0, JSON.stringify(m.silnik));
  ok('po usunięciu: konto zapomniane (brak skrótu hasła i sesji), okno logowania nie podpowiada loginu', !m.dostep.konta || !m.dostep.konta['12345'], JSON.stringify(Object.keys(m.dostep.konta || {})));
  ok('okno logowania jest puste (nie podpowiada usuniętego loginu)', (await p.inputValue('#dz-kod')) === '');
  await zaloguj(); await p.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 60000 });
  ok('po ponownym zalogowaniu aplikacja startuje od czystych danych („Moje dane” puste)', (await p.inputValue('#d-pesel')) === '' && (await p.inputValue('#d-adres')) === '');
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 4))); if (t.bledy.length) kod = 1;
  await t.zamknij();

  /* pliki ustawień idą z sieci: zmiana adresu/odbiorcy działa od razu (service worker nie trzyma starej kopii) */
  const op = { adresPubliczny: 'https://pierwszy.example.pl/', odbiorca: 'stary@firma.pl' };
  const t2 = await otworz({ w: 1200, h: 800, opcjeSerwera: op, przyklad: true }); const q = t2.p;
  await q.goto(t2.adres + '/index.html'); await q.waitForFunction(() => navigator.serviceWorker && navigator.serviceWorker.controller, null, { timeout: 60000 }).catch(() => {}); await q.waitForTimeout(3000);
  const czytaj = plik => q.evaluate(async p => (await (await fetch(p)).text()).split('\n').filter(l => l && !l.startsWith('#'))[0], plik);
  const sw = await q.evaluate(() => !!(navigator.serviceWorker && navigator.serviceWorker.controller));
  ok('service worker jest aktywny w tym teście (inaczej test niczego by nie sprawdzał)', sw);
  const a1 = await czytaj('adres_aplikacji.txt'), o1 = await czytaj('odbiorca.txt'); await q.waitForTimeout(500);
  op.adresPubliczny = 'https://drugi.example.pl/'; op.odbiorca = 'nowy@firma.pl';
  const a2 = await czytaj('adres_aplikacji.txt'), o2 = await czytaj('odbiorca.txt');
  ok('zmiana adresu aplikacji na serwerze działa od razu (service worker nie podaje starej kopii)', a1 === 'https://pierwszy.example.pl/' && a2 === 'https://drugi.example.pl/', a1 + ' → ' + a2);
  ok('zmiana adresu odbiorcy działa od razu', o1 === 'stary@firma.pl' && o2 === 'nowy@firma.pl', o1 + ' → ' + o2);
  await t2.zamknij();
  process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
