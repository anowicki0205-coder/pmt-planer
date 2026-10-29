// Autologowanie bez Enter i bez kliknięcia: hasło znane na urządzeniu — od razu; nowe — po pauzie w pisaniu; złe po automacie — tylko łagodna podpowiedź.
// NODE_PATH=/opt/node22/lib/node_modules node testy/logowanie_auto.js
const { otworz } = require('./wspolne'); const { BackendMock } = require('./backend_mock');
(async () => {
  const B = new BackendMock(); const t = await otworz({ w: 1440, h: 900, zalogowany: false, backend: B }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const stan = () => p.evaluate(() => JSON.parse(localStorage.getItem('pmt-web-dostep-v1') || '{}'));
  const czekajLogowanie = () => p.waitForSelector('#dz-form', { state: 'attached', timeout: 60000 });
  await p.goto(t.adres + '/index.html'); await czekajLogowanie(); await p.waitForTimeout(800);

  /* 1. nowe hasło (telefon z kartoteki), bez Enter: po pauzie sam wchodzi */
  await p.fill('#dz-kod', '22222'); const t0 = Date.now(); await p.fill('#dz-haslo', '501502503');
  await p.waitForFunction(() => { try { return !!JSON.parse(localStorage.getItem('pmt-web-dostep-v1') || '{}').kod; } catch (e) { return false; } }, null, { timeout: 15000, polling: 100 });
  const dt = Date.now() - t0; ok('nowe hasło: logowanie samo, po pauzie w pisaniu (bez Enter i bez klikania)', (await stan()).kod === '22222' && dt >= 1000, `${dt} ms`);
  await p.waitForSelector('#zh-form', { timeout: 120000 });                                  // aplikacja ruszyła; telefon → propozycja własnego hasła
  await p.evaluate(() => document.querySelector('[data-zamknij]').click()); await p.waitForTimeout(800);
  await Promise.all([p.waitForNavigation(), p.evaluate(() => document.querySelector('#wyloguj').click())]); await czekajLogowanie();

  /* 2. hasło znane na tym urządzeniu: od razu, bez czekania na pauzę */
  await p.fill('#dz-kod', '22222'); const t1 = Date.now(); await p.fill('#dz-haslo', '501502503');
  await p.waitForFunction(() => { try { return !!JSON.parse(localStorage.getItem('pmt-web-dostep-v1') || '{}').kod; } catch (e) { return false; } }, null, { timeout: 15000, polling: 50 });
  const dt2 = Date.now() - t1; ok('hasło znane na urządzeniu: logowanie od razu (bez pauzy)', dt2 < 1200, `${dt2} ms`);
  await Promise.all([p.waitForNavigation(), p.evaluate(() => document.querySelector('#wyloguj').click())]).catch(async () => { await p.waitForTimeout(1500); });
  await p.waitForSelector('#aplikacja', { state: 'attached' }); await p.waitForTimeout(500);
  if (!(await p.locator('#dz-form').count())) { await p.evaluate(() => document.querySelector('#wyloguj').click()); await czekajLogowanie(); }

  /* 3. złe hasło po automacie: łagodna podpowiedź, tekst zostaje */
  await czekajLogowanie(); await p.fill('#dz-kod', '12345'); await p.fill('#dz-haslo', 'zlehaslo1');
  await p.waitForFunction(() => /Dokończ wpisywanie/.test((document.querySelector('#dz-info') || {}).textContent || ''), null, { timeout: 20000, polling: 100 });
  ok('złe hasło po automacie: tylko podpowiedź „dokończ wpisywanie”, bez czerwonego błędu', !(await p.locator('#dz-info.zle').count()) && (await p.inputValue('#dz-haslo')) === 'zlehaslo1' && !(await stan()).kod);
  const prob = B.log.filter(l => l.kod === '12345').length; await p.waitForTimeout(2500);
  ok('ta sama para nie jest sprawdzana drugi raz', B.log.filter(l => l.kod === '12345').length === prob);

  /* 4. brak sieci po automacie: komunikat pokazany (to nie jest „dokończ wpisywanie”) */
  B.martwy = true; await p.fill('#dz-haslo', 'cokolwiek12');
  await p.waitForFunction(() => /połączyć|internet|serwer/i.test((document.querySelector('#dz-info') || {}).textContent || ''), null, { timeout: 40000, polling: 150 });
  ok('brak sieci po automacie: komunikat o połączeniu, nie podpowiedź', (await p.locator('#dz-info.zle').count()) === 1);
  B.martwy = false;
  /* 5. Enter i przycisk działają jak dotąd */
  await p.fill('#dz-haslo', 'haslo123'); await p.keyboard.press('Enter'); await p.waitForFunction(() => { try { return JSON.parse(localStorage.getItem('pmt-web-dostep-v1') || '{}').kod === '12345'; } catch (e) { return false; } }, null, { timeout: 30000, polling: 100 });
  ok('Enter nadal loguje', (await stan()).kod === '12345');
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('BŁĄD TESTU', e); process.exit(2); });
