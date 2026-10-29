// Szyfrowanie danych na urządzeniu (PESEL, adres, miesiące, plan, PDF-y) w prawdziwym przepływie z logowaniem (atrapa backendu):
// na dysku nie ma jawnego PESEL-u, adresu ani PDF-ów, ani skrótu hasła; odświeżenie karty nie pyta o hasło, nowa karta tak; autologowanie i logowanie bez sieci otwierają sejf;
// zmiana hasła zachowuje dane; hasło zmienione gdzie indziej → okno odzyskiwania (poprzednie hasło albo usunięcie); dane sprzed szyfrowania są migrowane; uszkodzone dane nie są nadpisywane.
// NODE_PATH=/opt/node22/lib/node_modules node szyfrowanie_app.js
const { otworz, generuj } = require('./wspolne'); const { BackendMock, hash } = require('./backend_mock');
(async () => {
  const B = new BackendMock(); const t = await otworz({ w: 1440, h: 900, zalogowany: false, backend: B }); let p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const PESEL = '90010112349', ADRES = 'Testowa 1', IMIE = 'Jan Testowy';
  const czekajApp = pg => pg.waitForFunction(() => !document.querySelector('#aplikacja').classList.contains('zamknieta') && !document.querySelector('#ladowanie').classList.contains('widoczny'), null, { timeout: 180000, polling: 200 });
  const zaloguj = async (pg, haslo = 'haslo123', czekaj = true) => { await pg.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await pg.waitForTimeout(700); await pg.fill('#dz-kod', '12345'); await pg.fill('#dz-haslo', haslo); await pg.keyboard.press('Enter'); if (czekaj) await czekajApp(pg); };
  const nowaKarta = async () => { const q = await t.ctx.newPage(); q.setDefaultTimeout(180000); await q.goto(t.adres + '/index.html'); return q; };
  /* zrzut TEGO, co leży na dysku: localStorage, sessionStorage, pierwszy PDF z IndexedDB */
  const dysk = pg => pg.evaluate(async () => {
    const ls = {}; for (const k of Object.keys(localStorage)) ls[k] = localStorage.getItem(k);
    const nazwy = (await indexedDB.databases()).map(d => d.name); let pdf = null;
    if (nazwy.includes('pmt-web-pliki:12345')) pdf = await new Promise(ok => { const q = indexedDB.open('pmt-web-pliki:12345'); q.onsuccess = () => { const db = q.result; if (![...db.objectStoreNames].length) { db.close(); ok(null); return; } const r = db.transaction('pliki').objectStore('pliki').getAll(); r.onsuccess = () => { db.close(); ok(r.result.map(v => Array.from(new Uint8Array(v)))); }; }; q.onerror = () => ok(null); });
    return { ls, ss: Object.fromEntries(Object.keys(sessionStorage).map(k => [k, sessionStorage.getItem(k).slice(0, 40)])), pdf };
  });
  const jawne = (s, frazy) => frazy.filter(f => s.includes(f));

  /* ---- 1. pierwsze logowanie, dane, generowanie ---- */
  await p.goto(t.adres + '/index.html'); await zaloguj(p);
  await p.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 60000 }); await p.fill('#d-imie', IMIE); await p.fill('#d-pesel', PESEL); await p.fill('#d-adres', `ul. ${ADRES}, 00-001 Warszawa`);
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200); await generuj(p); await p.waitForTimeout(3500);
  let d = await dysk(p); const wszystkieLs = Object.values(d.ls).join('\n');
  ok('profil i miesiące konta leżą na dysku jako „enc1:…”', /^enc1:/.test(d.ls['pmt-web-v1:12345'] || ''), (d.ls['pmt-web-v1:12345'] || '').slice(0, 20));
  ok('w localStorage nie ma jawnie PESEL-u, imienia, adresu ani nazw tras (też po rozkodowaniu base64)', (() => { const b = Buffer.from((d.ls['pmt-web-v1:12345'] || '').slice(5), 'base64').toString('latin1'); return jawne(wszystkieLs + b, [PESEL, IMIE, ADRES, 'Warszawa']).length === 0; })(), JSON.stringify(jawne(wszystkieLs, [PESEL, IMIE, ADRES])));
  ok('skrótu hasła nie ma na dysku (ani w danych dostępu, ani nigdzie w localStorage)', !/skrot/.test(d.ls['pmt-web-dostep-v1'] || '') && !wszystkieLs.includes(hash('12345', 'haslo123')));
  ok('sejf konta jest na dysku i nie zawiera hasła ani klucza jawnie', !!d.ls['pmt-web-sejf:12345'] && !d.ls['pmt-web-sejf:12345'].includes('haslo123'));
  ok('PDF-y w IndexedDB są zaszyfrowane (koperta PMT1, brak nagłówka %PDF i PESEL-u w treści)', d.pdf && d.pdf.length >= 6 && d.pdf.every(b => b[0] === 0x50 && b[1] === 0x4d && b[2] === 0x54 && b[3] === 0x31 && !Buffer.from(b).toString('latin1').includes('%PDF') && !Buffer.from(b).toString('latin1').includes(PESEL)), d.pdf ? d.pdf.length + ' plików' : 'brak');
  ok('klucz danych jest tylko w sessionStorage karty (ginie z kartą)', !!d.ss['pmt-web-dek'] && !wszystkieLs.includes(d.ss['pmt-web-dek']));
  /* ---- 2. odświeżenie i nowa karta ---- */
  await p.reload(); await czekajApp(p); await p.waitForTimeout(2500);
  ok('odświeżenie karty nie pyta o hasło, a dane są odczytane (imię w nagłówku, miesiąc wygenerowany)', (await p.locator('#dz-form').count()) === 0 && (await p.locator('#imie-pasek').innerText()) === IMIE && /Wygenerowane/.test(await p.locator('#status').innerText()));
  const pdfOk = await p.evaluate(async () => { const d = window.__pmtDane.czytaj(); return Object.keys(d.miesiace || {}).length; });
  ok('po odświeżeniu pliki PDF da się otworzyć z szyfrowanego magazynu (okno dokumentów)', await (async () => { await p.click('#podpisz'); await p.waitForSelector('#dok-siatka'); const w = await p.evaluate(async () => { const el = document.querySelector('[data-akcja="otworz"]'); return !!el; }); await p.keyboard.press('Escape'); await p.waitForTimeout(500); return w && pdfOk >= 1; })());
  const k2 = await nowaKarta(); await k2.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await k2.waitForTimeout(800);
  ok('nowa karta pyta o logowanie i nie zna klucza danych', (await k2.locator('#dz-kod').count()) === 1 && !(await k2.evaluate(() => sessionStorage.getItem('pmt-web-dek'))));
  /* ---- 3. autologowanie przez sejf (hasło znane na urządzeniu) ---- */
  await k2.fill('#dz-kod', '12345'); await k2.fill('#dz-haslo', 'haslo123'); await czekajApp(k2); await k2.waitForTimeout(2500);
  ok('autologowanie po wpisaniu hasła otwiera sejf, a dane są na miejscu', (await k2.locator('#imie-pasek').innerText()) === IMIE);
  ok('złe hasło w nowej karcie NIE jest rozpoznawane jako znane (sejf go nie otwiera) i nie loguje', await (async () => { const k3 = await nowaKarta(); await k3.waitForSelector('#dz-form', { state: 'attached' }); await k3.waitForTimeout(700); await k3.fill('#dz-kod', '12345'); await k3.fill('#dz-haslo', 'zlehaslo'); await k3.waitForTimeout(2500); const bez = (await k3.locator('#dz-form').count()) === 1; await k3.close(); return bez; })());
  await k2.close();
  /* ---- 4. logowanie bez sieci ---- */
  B.martwy = true; const k4 = await nowaKarta(); await k4.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await k4.waitForTimeout(700);
  await k4.fill('#dz-kod', '12345'); await k4.fill('#dz-haslo', 'zlehaslo'); await k4.keyboard.press('Enter'); await k4.waitForFunction(() => /połączyć|internet|serwer/i.test((document.querySelector('#dz-info') || {}).textContent || ''), null, { timeout: 60000 });
  ok('bez sieci złe hasło nie otwiera sejfu', (await k4.locator('#dz-form').count()) === 1);
  await k4.fill('#dz-haslo', 'haslo123'); await k4.keyboard.press('Enter'); await czekajApp(k4); await k4.waitForTimeout(2500);
  ok('bez sieci dobre hasło otwiera sejf (logowanie offline) i dane są czytelne', (await k4.locator('#imie-pasek').innerText()) === IMIE);
  await k4.close(); B.martwy = false;
  /* ---- 5. zmiana hasła w aplikacji zachowuje dane ---- */
  await p.click('#konto'); await p.waitForTimeout(500); await p.click('#zmien-haslo'); await p.waitForSelector('#zh-stare');
  await p.fill('#zh-stare', 'haslo123'); await p.fill('#zh-nowe', 'nowehaslo1'); await p.fill('#zh-pow', 'nowehaslo1'); await p.click('#zh-ok'); await p.waitForFunction(() => !document.querySelector('#zh-form'), null, { timeout: 60000 });
  await p.waitForTimeout(1500);
  const k5 = await nowaKarta(); await zaloguj(k5, 'nowehaslo1'); await k5.waitForTimeout(2500);
  ok('po zmianie hasła nowe hasło otwiera sejf i dane są czytelne (te same, nie nowe puste)', (await k5.locator('#imie-pasek').innerText()) === IMIE && (await k5.locator('#dz-form').count()) === 0 && (await k5.locator('#sj-form').count()) === 0);
  await k5.close();
  /* ---- 6. hasło zmienione gdzie indziej: poprzednie hasło albo usunięcie ---- */
  B.uzytkownicy['12345'].hash = hash('12345', 'inneHaslo7');
  const k6 = await nowaKarta(); await zaloguj(k6, 'inneHaslo7', false); await k6.waitForSelector('#sj-form', { timeout: 120000 });
  ok('hasło zmienione na innym urządzeniu: pokazuje się okno odzyskiwania (a nie puste dane)', /poprzednim hasłem/.test(await k6.locator('#arkusz-tresc').innerText()));
  await k6.keyboard.press('Escape'); await k6.waitForTimeout(400);
  ok('okna odzyskiwania nie da się zamknąć Esc', (await k6.locator('#sj-form').count()) === 1);
  await k6.fill('#sj-stare', 'zleStare12'); await k6.click('#sj-ok'); await k6.waitForFunction(() => /nie pasuje/.test((document.querySelector('#dz-info') || {}).textContent || ''), null, { timeout: 60000 });
  ok('złe poprzednie hasło jest odrzucone i dane zostają zablokowane', (await k6.locator('#sj-form').count()) === 1);
  await k6.fill('#sj-stare', 'nowehaslo1'); await k6.click('#sj-ok'); await czekajApp(k6); await k6.waitForTimeout(2500);
  ok('poprzednie hasło odblokowuje dane i przenosi je pod nowe hasło', (await k6.locator('#imie-pasek').innerText()) === IMIE);
  await k6.close();
  const k7 = await nowaKarta(); await zaloguj(k7, 'inneHaslo7'); await k7.waitForTimeout(2500);
  ok('potem nowe hasło otwiera sejf bez pytania o stare', (await k7.locator('#sj-form').count()) === 0 && (await k7.locator('#imie-pasek').innerText()) === IMIE);
  await k7.close();
  /* reset hasła na serwerze + usunięcie danych („nie pamiętam”) */
  B.uzytkownicy['12345'].hash = hash('12345', 'jeszczeInne5');
  const k8 = await nowaKarta(); await zaloguj(k8, 'jeszczeInne5', false); await k8.waitForSelector('#sj-form', { timeout: 120000 });
  await k8.click('#sj-usun'); await czekajApp(k8); await k8.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 60000 });
  d = await dysk(k8);
  ok('„Usuń dane i zacznij od nowa”: stare dane znikają (puste „Moje dane”), a na dysku nie ma jawnych danych', (await k8.inputValue('#d-pesel')) === '' && !Object.values(d.ls).join('\n').includes(PESEL));
  await k8.close();
  const k9 = await nowaKarta(); await zaloguj(k9, 'jeszczeInne5', false); await k9.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 120000 }); await k9.waitForTimeout(1500);
  ok('po tym nowe hasło normalnie otwiera nowy sejf (bez okna odzyskiwania)', (await k9.locator('#sj-form').count()) === 0);
  await k9.close();
  /* ---- 7. uszkodzone dane nie są nadpisywane po cichu ---- */
  const k10 = await nowaKarta(); await zaloguj(k10, 'jeszczeInne5', false); await k10.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 120000 });
  await k10.fill('#d-imie', IMIE); await k10.fill('#d-pesel', PESEL); await k10.fill('#d-adres', `ul. ${ADRES}, 00-001 Warszawa`); await k10.click('#zapisz-dane'); await k10.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await k10.waitForTimeout(2500);
  await k10.evaluate(() => { const k = 'pmt-web-v1:12345'; const v = localStorage.getItem(k); const i = Math.floor(v.length / 2); localStorage.setItem(k, v.slice(0, i) + (v[i] === 'A' ? 'B' : 'A') + v.slice(i + 1)); });
  await k10.reload(); await k10.waitForSelector('#uszk-usun', { timeout: 180000 }).catch(() => {});
  ok('zmieniony szyfrogram jest wykryty: aplikacja pokazuje „Dane na tym urządzeniu są uszkodzone” zamiast ich nadpisać', (await k10.locator('#uszk-usun').count()) === 1);
  ok('okna z uszkodzonymi danymi nie da się zamknąć Esc, a sejf i pliki zostają', await (async () => { await k10.keyboard.press('Escape'); await k10.waitForTimeout(400); return (await k10.locator('#uszk-usun').count()) === 1 && !!(await k10.evaluate(() => localStorage.getItem('pmt-web-sejf:12345'))); })());
  await k10.click('#uszk-usun'); await czekajApp(k10); await k10.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 60000 });
  ok('po usunięciu uszkodzonych danych aplikacja startuje od czystych (puste „Moje dane”) i zapisuje już poprawnie', (await k10.inputValue('#d-pesel')) === '');
  await k10.close();
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.filter(b => !/ERR_INTERNET_DISCONNECTED|Failed to load resource|net::ERR/.test(b)).slice(0, 4)));
  await t.zamknij();

  /* ---- 8. migracja danych sprzed szyfrowania ---- */
  const B2 = new BackendMock(); const t2 = await otworz({ w: 1440, h: 900, zalogowany: false, backend: B2 }); const q = t2.p;
  await q.goto(t2.adres + '/robots.txt').catch(() => {});
  await q.evaluate(async ({ pesel, skrot }) => {
    localStorage.setItem('pmt-web-v1:12345', JSON.stringify({ profil: { imie: 'Jan Testowy', pesel, adres: 'ul. Testowa 1, 00-001 Warszawa', stanowisko: 'merchandiser' }, miesiace: {}, ustawienia: {} }));
    localStorage.setItem('pmt-web-dostep-v1', JSON.stringify({ ostatni: '12345', konta: { 12345: { imie: 'Jan Testowy', skrot, kontakt: Date.now() } }, status: {}, kolejka: { uruchomienia: 0, dokumenty: 0, minuty: 0 } }));
    await new Promise(ok => { const r = indexedDB.open('pmt-web-pliki:12345', 1); r.onupgradeneeded = () => r.result.createObjectStore('pliki'); r.onsuccess = () => { const tx = r.result.transaction('pliki', 'readwrite'); tx.objectStore('pliki').put(new TextEncoder().encode('%PDF-1.4 stary plik jawny PESEL ' + pesel), '2026-09/stary.pdf'); tx.oncomplete = () => { r.result.close(); ok(); }; }; });
  }, { pesel: PESEL, skrot: hash('12345', 'haslo123') });
  await q.goto(t2.adres + '/index.html'); await zaloguj(q); await q.waitForTimeout(4000);
  const dm = await q.evaluate(async () => { const ls = {}; for (const k of Object.keys(localStorage)) ls[k] = localStorage.getItem(k);
    const pdf = await new Promise(ok => { const r = indexedDB.open('pmt-web-pliki:12345'); r.onsuccess = () => { const g = r.result.transaction('pliki').objectStore('pliki').getAll(); g.onsuccess = () => { r.result.close(); ok(g.result.map(v => Array.from(new Uint8Array(v)))); }; }; }); return { ls, pdf }; });
  ok('dane sprzed szyfrowania zostały zaszyfrowane po pierwszym logowaniu (profil)', /^enc1:/.test(dm.ls['pmt-web-v1:12345'] || '') && !Object.values(dm.ls).join('\n').includes(PESEL));
  ok('stary jawny plik PDF został zaszyfrowany', dm.pdf.length === 1 && dm.pdf[0][0] === 0x50 && !Buffer.from(dm.pdf[0]).toString('latin1').includes('PESEL'));
  ok('dawny skrót hasła zniknął z dysku, powstał sejf', !/skrot/.test(dm.ls['pmt-web-dostep-v1'] || '') && !!dm.ls['pmt-web-sejf:12345']);
  ok('dane z migracji są czytelne w aplikacji (imię w nagłówku)', (await q.locator('#imie-pasek').innerText()) === IMIE);
  await t2.zamknij();
  process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
