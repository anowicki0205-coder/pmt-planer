// Wspólny rejestr miejscowości w aplikacji: każdy użytkownik ma własną trasę. Dwie osoby (dwie przeglądarki, jeden zamiennik backendu) z tej samej okolicy generują po kolei:
// druga omija miejscowości pierwszej. Do tego: zapis czeka w kolejce, gdy serwer nie działa (i idzie po powrocie sieci), „od nowa” zwalnia miejscowości,
// a bez rejestru (brak sieci) generowanie działa po staremu. NODE_PATH=/opt/node22/lib/node_modules node testy/rejestr_app.js
const { wpiszAdres, otworz, generuj } = require('./wspolne'); const { BackendMock, hash } = require('./backend_mock');
(async () => {
  const B = new BackendMock(); let kod = 0;
  B.uzytkownicy['44444'] = { imie: 'Piotr Drugi', telefon: '611222333', hash: hash('44444', 'drugie-haslo9'), wazne_do: '2099-12-31' };
  B.uzytkownicy['55555'] = { imie: 'Maria Trzecia', telefon: '622333444', hash: hash('55555', 'trzecie-haslo9'), wazne_do: '2099-12-31' };
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const czekajAplikacje = p => p.waitForFunction(() => !document.querySelector('#aplikacja').classList.contains('zamknieta') && !document.querySelector('#ladowanie').classList.contains('widoczny'), null, { timeout: 180000, polling: 200 });
  const wejdz = async (t, kodKonta, haslo, imie, pesel) => {
    const p = t.p; await p.goto(t.adres + '/index.html'); await p.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await p.waitForTimeout(800);
    await p.fill('#dz-kod', kodKonta); await p.fill('#dz-haslo', haslo); await p.keyboard.press('Enter'); await czekajAplikacje(p);
    await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
    await p.fill('#d-imie', imie); await p.fill('#d-pesel', pesel); await wpiszAdres(p, 'ul. Testowa 1, 26-600 Radom');
    await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 30000 }); await p.waitForTimeout(3500);
    await p.fill('#kwota-in', '2500'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  };
  const wpisRejestru = (kodKonta) => Object.entries(B.rejestr || {}).filter(([k]) => k.endsWith('|' + kodKonta)).map(([, l]) => l)[0] || null;
  const pobrania = kodKonta => (B.zapytaniaRejestru || []).filter(z => z.op === 'pobierz' && z.kod === kodKonta);

  // --- dwie osoby z jednej okolicy (Radom), kolejno ---
  const t1 = await otworz({ w: 1280, h: 800, zalogowany: false, backend: B }); const p1 = t1.p;
  await wejdz(t1, '12345', 'haslo123', 'Jan Testowy', '90010112349'); await generuj(p1);
  const a = wpisRejestru('12345');
  ok('pierwsza osoba przed generowaniem pytała rejestr o miejscowości innych (pusto)', pobrania('12345').length >= 1);
  ok('po wygenerowaniu jej miejscowości trafiły do wspólnego rejestru (kilkadziesiąt różnych, bez bazy)', !!a && a.length >= 25 && new Set(a.map(x => x.toLowerCase())).size === a.length && !a.some(x => x.toLowerCase() === 'radom'), a ? String(a.length) : 'brak wpisu');
  await p1.waitForTimeout(1500);
  const t2 = await otworz({ w: 1280, h: 800, zalogowany: false, backend: B }); const p2 = t2.p;
  await wejdz(t2, '44444', 'drugie-haslo9', 'Piotr Drugi', '85050512347'); await generuj(p2);
  const b2 = wpisRejestru('44444');
  ok('druga osoba przed generowaniem pobrała zajęte miejscowości pierwszej', pobrania('44444').length >= 1);
  ok('druga osoba ma swoje miejscowości w rejestrze (mniej niż pierwsza: bliskie były zajęte, więc skoki dłuższe)', !!b2 && b2.length >= 10, b2 ? String(b2.length) : 'brak wpisu');
  const wspolne = a && b2 ? b2.filter(x => a.map(y => y.toLowerCase()).includes(x.toLowerCase())) : ['?'];
  ok('trasy obu osób z tej samej okolicy nie mają ani jednej wspólnej miejscowości', wspolne.length === 0, wspolne.join(', '));
  ok('komunikat „Gotowe” nie mówi o wspólnych miejscowościach, bo wolnych starczyło', !/też na dokumentach innych osób/.test(await p2.locator('#toast, .toast, [role="status"]').allInnerTexts().then(t => t.join(' ')).catch(() => '')));

  // --- „od nowa” oddaje miejscowości do puli ---
  await p1.click('#od-nowa'); await p1.waitForSelector('#od-nowa-tak', { timeout: 30000 }); await p1.click('#od-nowa-tak'); await p1.waitForTimeout(2500);
  ok('„Usuń i zacznij od nowa” zwalnia miejscowości pierwszej osoby w rejestrze', wpisRejestru('12345') === null && wpisRejestru('44444') !== null, JSON.stringify(Object.keys(B.rejestr || {})));

  // --- serwer nie działa: generowanie idzie po staremu, zapis czeka w kolejce i dochodzi po powrocie sieci ---
  const t3 = await otworz({ w: 1280, h: 800, zalogowany: false, backend: B }); const p3 = t3.p;
  await wejdz(t3, '55555', 'trzecie-haslo9', 'Maria Trzecia', '78030398763');
  B.martwy = true; const przed = (B.zapytaniaRejestru || []).length;
  await generuj(p3);
  const kolejka = await p3.evaluate(() => JSON.parse(localStorage.getItem('pmt-web-dostep-v1') || '{}').rejestr || null);
  ok('bez serwera generowanie się udało (dokumenty są), a rejestr nie dostał niczego', (await p3.locator('#status').innerText()).includes('Wygenerowane') && wpisRejestru('55555') === null && (B.zapytaniaRejestru || []).length === przed);
  ok('zapis miejscowości czeka w kolejce na urządzeniu (po kodzie konta i miesiącu)', !!kolejka && !!kolejka['55555'] && Object.values(kolejka['55555']).some(w => w.op === 'zapisz' && w.lista.length >= 10), JSON.stringify(kolejka).slice(0, 120));
  B.martwy = false;
  await p3.evaluate(() => dispatchEvent(new KeyboardEvent('keydown', { key: 'F5' }))).catch(() => {}); await p3.reload(); await czekajAplikacje(p3);
  await p3.waitForFunction(() => !JSON.parse(localStorage.getItem('pmt-web-dostep-v1') || '{}').rejestr, null, { timeout: 60000, polling: 300 }).catch(() => {});
  ok('po powrocie serwera kolejka zostaje wysłana (pierwszy puls po starcie), a miejscowości są w rejestrze', !!wpisRejestru('55555') && wpisRejestru('55555').length >= 10, JSON.stringify(Object.keys(B.rejestr || {})));
  ok('żaden z przebiegów nie zostawił błędów w konsoli', [t1, t2, t3].every(t => t.bledy.filter(x => !/ERR_INTERNET_DISCONNECTED/.test(x)).length === 0), JSON.stringify([t1, t2, t3].map(t => t.bledy.filter(x => !/ERR_INTERNET_DISCONNECTED/.test(x)))).slice(0, 200));      // ERR_INTERNET_DISCONNECTED: celowo wyłączony serwer w trzecim przebiegu
  for (const t of [t1, t2, t3]) await t.zamknij();
  process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
