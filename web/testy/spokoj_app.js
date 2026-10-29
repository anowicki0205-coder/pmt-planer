// Spokojny tryb (czasowo: animacje wyłączone dla wszystkich, test płynności): w spoczynku nic się nie rusza, kursor nie uruchamia żadnych efektów,
// a wszystkie funkcje działają jak dotąd (okna, zmiana miesiąca/dnia, generowanie). Oraz: liczba klatek/s w spoczynku (informacyjnie).
// NODE_PATH=/opt/node22/lib/node_modules node spokoj_app.js
const { otworz, generuj } = require('./wspolne');
(async () => {
  // bez „życia” kalendarza i fiolek (bezZycia) — ono ma osobny test: zycie_app.js
  const t = await otworz({ w: 1440, h: 900, pelnaZorza: true, bezZycia: true }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3500);
  ok('aplikacja startuje w trybie spokojnym (klasa html.spokojne)', await p.evaluate(() => document.documentElement.classList.contains('spokojne')));
  const stan = () => p.evaluate(() => ({ nazwy: document.getAnimations().filter(a => a.playState === 'running' && !(a instanceof CSSTransition)).map(a => (a.animationName || a.transitionProperty || '?') + '@' + ((a.effect && a.effect.target && (a.effect.target.id || a.effect.target.className)) || '')), ruchome: document.getAnimations().filter(a => a.playState === 'running' && !(a instanceof CSSTransition)).length, ciagle: document.getAnimations().filter(a => a.effect && a.effect.getComputedTiming().iterations === Infinity).length, zorza: window.__zorzaKlatki || 0 }));
  const a = await stan(); await p.waitForTimeout(2500); const b = await stan();
  ok('w spoczynku nie działa ŻADNA animacja (poza krótkimi przejściami po najechaniu myszą)', a.ruchome === 0 && a.ciagle === 0, JSON.stringify(a));
  ok('zorza w tle nie jest przerysowywana (narysowana raz, nieruchomo)', a.zorza === b.zorza, a.zorza + ' → ' + b.zorza);

  // kursor: przejazd po kafelkach nie włącza światła kafli, przechylania, magnesu ani iskier
  const swiatlo = () => p.evaluate(() => [...document.querySelectorAll('.kafel')].map(k => k.style.getPropertyValue('--lx') + '/' + k.style.getPropertyValue('--ly')).join('|'));
  const sw0 = await swiatlo();
  for (let i = 0; i < 40; i++) { await p.mouse.move(100 + i * 30, 150 + (i % 7) * 90); }
  await p.waitForTimeout(500);
  const kursor = await p.evaluate(() => ({ przechyl: [...document.querySelectorAll('.kafel')].filter(k => k.style.transform).length, iskry: document.querySelectorAll('.iskra').length, magnes: [...document.querySelectorAll('.przycisk,.kropla')].filter(e => e.style.translate).length, pylek: (document.querySelector('#pylek') || { style: {} }).style.transform || '' }));
  ok('ruch kursora nie uruchamia efektów (światło kafli, przechylanie, magnes, iskry)', (await swiatlo()) === sw0 && kursor.przechyl === 0 && kursor.iskry === 0 && kursor.magnes === 0, JSON.stringify(kursor));

  // aplikacja na grafice programowej (testy) potrafi pokazać jednorazowe okno „Animacje mogą być wolne” — zamykamy je jak użytkownik, zanim zaczniemy klikać
  const zamknijInfo = async () => { if (await p.locator('#arkusz-tlo.otwarty').count()) { await p.keyboard.press('Escape'); await p.waitForFunction(() => !document.querySelector('#arkusz-tlo.otwarty'), null, { timeout: 5000, polling: 100 }).catch(() => {}); } };
  await zamknijInfo();
  // funkcje bez zmian
  await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await zamknijInfo(); await generuj(p); await p.waitForTimeout(2500);
  ok('generowanie dokumentów działa', (await p.locator('#fiolki .fiolka').count()) >= 3);
  ok('cyfry kwoty od razu pokazują wynik (bez staczania)', (await p.locator('#b-kwota-w').getAttribute('aria-label')).replace(/\s/g, '') === '3095,26zł' && (await p.locator('#kwota .slot').count()) >= 5);
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka', { timeout: 20000 });
  ok('okno dokumentów otwiera się', true); await p.keyboard.press('Escape'); await p.waitForFunction(() => !document.querySelector('#arkusz-tlo.otwarty'), null, { timeout: 5000, polling: 100 });
  ok('i zamyka się od razu (bez czekania na animację)', true);
  const dzien0 = await p.locator('#e-tyt').innerText(); await p.click('#e-dalej'); await p.waitForTimeout(400);
  ok('zmiana dnia działa natychmiast', (await p.locator('#e-tyt').innerText()) !== dzien0, dzien0 + ' → ' + await p.locator('#e-tyt').innerText());
  const fin = await stan(); ok('po całej pracy nadal brak animacji CSS i zorza stoi', fin.ruchome === 0 && fin.ciagle === 0 && fin.zorza === a.zorza, JSON.stringify(fin));
  const fps = await p.evaluate(() => new Promise(ok => { let n = 0; const t0 = performance.now(); const f = x => { n++; if (x - t0 < 5000) requestAnimationFrame(f); else ok(n / ((x - t0) / 1000)); }; requestAnimationFrame(f); }));
  console.log('  info: klatek/s w spoczynku (grafika programowa, wartość względna):', fps.toFixed(1));
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 6))); if (t.bledy.length) kod = 1;
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
