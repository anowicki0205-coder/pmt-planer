// Zmiana motywu Noc/Dzień bez View Transitions (Firefox, starsze Safari/iOS): fala z pierścieniem światła, niebo nowego motywu, potem odsłonięcie interfejsu.
// NODE_PATH=/opt/node22/lib/node_modules node motyw_app.js
const { otworz } = require('./wspolne');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const t = await otworz({ w: 1440, h: 900, bezVT: true }); const p = t.p;
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 }); await p.waitForTimeout(4000);
  const motyw = () => p.evaluate(() => document.documentElement.dataset.theme || 'auto');
  const poczatek = await motyw();
  for (const [kier, opis] of [['light', 'Noc → Dzień'], ['dark', 'Dzień → Noc']]) {
    await p.click('#motyw');
    if (await p.evaluate(() => document.documentElement.classList.contains('spokojne'))) {      // animacje wyłączone: motyw zmienia się od razu, bez fali
      await p.waitForFunction(k => document.documentElement.dataset.theme === k, kier, { timeout: 30000, polling: 100 });
      ok(`${opis}: motyw zmienia się od razu na „${kier}” (tryb spokojny, bez fali)`, (await motyw()) === kier && !(await p.evaluate(() => !!document.querySelector('.motyw-fala'))));
      continue;
    }
    await p.waitForSelector('.motyw-fala', { state: 'attached', timeout: 60000 });
    ok(`${opis}: pojawia się fala (niebo nowego motywu) z pierścieniem światła`, await p.evaluate(() => !!document.querySelector('.motyw-fala') && !!document.querySelector('.fala-pierscien')));
    await p.waitForFunction(k => document.documentElement.dataset.theme === k, kier, { timeout: 90000, polling: 200 });
    ok(`${opis}: motyw zmienia się na „${kier}”`, (await motyw()) === kier);
    await p.waitForFunction(() => !document.querySelector('.motyw-fala'), null, { timeout: 90000, polling: 200 });
    ok(`${opis}: niebo znika i odsłania interfejs, bez śladów (fala i pierścień usunięte)`, await p.evaluate(() => !document.querySelector('.motyw-fala') && !document.querySelector('.fala-pierscien')));
  }
  ok('motyw zapamiętany na urządzeniu', await p.evaluate(() => localStorage.getItem('pmt-ui-motyw') === 'dark'));
  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
