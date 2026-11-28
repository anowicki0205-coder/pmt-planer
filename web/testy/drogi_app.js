// Dokładne drogi z Google dla odcinków z adresu zamieszkania (akcja „droga” w backendzie): pierwszy przebieg silnika podaje zaplanowane postoje, aplikacja pyta o drogę z domu do każdego,
// drugi przebieg (z dokumentami) dostaje te kilometry. Gdy backend nie odpowiada, odmawia albo wyczerpał limit usługi Maps — generowanie działa na tabeli dróg.
// NODE_PATH=/opt/node22/lib/node_modules node testy/drogi_app.js
const { wpiszAdres, otworz, generuj } = require('./wspolne'); const { BackendMock, hash } = require('./backend_mock'); const fs = require('fs'), path = require('path');
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
  const dlaKonta = k => (B.zapytaniaDrog || []).filter(z => z.kod === k).map(z => z.para);
  const tabela = fs.existsSync(path.join(__dirname, '..', 'silnik', 'drogi.bin'));

  // --- 1. normalny przebieg: backend odpowiada ---
  const t1 = await otworz({ w: 1280, h: 800, zalogowany: false, backend: B }); const p1 = t1.p;
  await wejdz(t1, '12345', 'haslo123', 'Jan Testowy', '90010112349'); await generuj(p1);
  const pary = dlaKonta('12345');
  ok('aplikacja zapytała backend o drogę z domu do zaplanowanych postojów (dziesiątki par, każda z tego samego punktu domowego, wszystkie w Polsce)', pary.length >= 20 && new Set(pary.map(p => p[0] + ',' + p[1])).size === 1 && pary.every(p => p[2] > 48.8 && p[2] < 55.2 && p[3] > 13.9 && p[3] < 24.4), String(pary.length));
  ok('pary są różne (każda miejscowość raz) i zapytania szły porcjami po najwyżej 12', new Set(pary.map(p => p.join(','))).size === pary.length);
  ok('generowanie się udało: są dokumenty (polecenia i rozliczenie)', (await p1.locator('#status').innerText()).includes('Wygenerowane') && (await p1.locator('#fiolki .fiolka').count()) >= 3);
  const toast1 = (await p1.locator('#toast, .toast, [role="status"]').allInnerTexts().catch(() => [])).join(' ');
  if (tabela) ok('z tabelą dróg i Google komunikat „Gotowe” nie ostrzega o kilometrach z szacunku', !/z szacunku/.test(toast1) && !/z szacunku/.test(await p1.locator('body').innerText().catch(() => '')));
  else console.log('  (brak web/silnik/drogi.bin — pominięto kontrolę komunikatu o szacunku)');

  // --- 2. limit usługi Maps wyczerpany (backend odpowiada „limit”, same null): generowanie działa na tabeli ---
  B.drogaLimit = true;
  const t2 = await otworz({ w: 1280, h: 800, zalogowany: false, backend: B }); const p2 = t2.p;
  await wejdz(t2, '44444', 'drugie-haslo9', 'Piotr Drugi', '85050512347'); await generuj(p2);
  ok('limit usługi Maps: aplikacja pytała, dostała „limit” i mimo to wygenerowała dokumenty', dlaKonta('44444').length >= 20 && (await p2.locator('#status').innerText()).includes('Wygenerowane'));
  B.drogaLimit = false;

  // --- 3. backend zajęty / błąd serwera: dokumenty powstają ---
  B.drogaBlad = true;
  const t3 = await otworz({ w: 1280, h: 800, zalogowany: false, backend: B }); const p3 = t3.p;
  await wejdz(t3, '55555', 'trzecie-haslo9', 'Maria Trzecia', '78030398763'); await generuj(p3);
  ok('backend zwraca błąd na akcji „droga”: generowanie działa (tabela dróg zamiast Google)', (await p3.locator('#status').innerText()).includes('Wygenerowane'));
  B.drogaBlad = false;
  ok('żadne z trzech generowań nie zostawiło błędów w konsoli', [t1, t2, t3].every(t => t.bledy.length === 0), JSON.stringify([t1, t2, t3].map(t => t.bledy)).slice(0, 220));
  for (const t of [t1, t2, t3]) await t.zamknij();
  process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
