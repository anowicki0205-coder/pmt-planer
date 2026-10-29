// Przerwanie generowania, błąd bez menedzer.txt, „Wygeneruj od nowa", nawigacja miesięcy. NODE_PATH=/opt/node22/lib/node_modules node przerwanie_i_od_nowa.js
const { otworz, generuj } = require('./wspolne');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  // A) brak menedzer.txt blokuje generowanie z czytelnym komunikatem
  let t = await otworz({ w: 1440, h: 900, opcjeSerwera: { bezMenedzera: true } }); let p = t.p;
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '1500'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
  await p.click('#podpisz'); await p.waitForSelector('#menedzer-ponow', { timeout: 60000 });
  ok('bez menedzer.txt: jasny komunikat (okno z diagnozą) i brak generowania', /Brakuje pliku menedzer\.txt/.test(await p.locator('#arkusz').innerText()) && (await p.locator('#kA.po-gen').count()) === 0);
  await t.zamknij();
  // B) przerwanie + ponowne generowanie + od nowa + miesiące
  t = await otworz({ w: 1440, h: 900 }); p = t.p;
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
  await p.click('#podpisz'); await p.waitForSelector('#potwierdz-gen'); await p.click('#potwierdz-gen'); await p.waitForFunction(() => document.querySelector('#podpisz.zbiera'), null, { timeout: 20000, polling: 100 });
  await p.waitForTimeout(600); await p.click('#podpisz', { force: true }); await p.waitForTimeout(2500);
  ok('przerwanie: komunikat i brak zapisanych dokumentów', /Przerwano/.test(await p.locator('#toast-tekst').innerText()) && (await p.locator('#kA.po-gen').count()) === 0);
  ok('po przerwaniu przycisk znów pozwala generować', !(await p.locator('#podpisz.zbiera').count()));
  await p.waitForTimeout(9000);
  await generuj(p); await p.waitForTimeout(3000);
  ok('po przerwaniu kolejne generowanie się udaje', (await p.locator('#b-kwota-w').getAttribute('aria-label')).replace(/\s/g, '') === '3095,26zł');
  const czekaj = (re, ms = 40000) => p.waitForFunction(r => new RegExp(r, 'i').test(document.querySelector('#status').textContent + '|' + document.querySelector('#m-nazwa').textContent), re, { timeout: ms, polling: 200 }).then(() => true, () => false);
  await p.click('#m-wstecz');
  ok('poprzedni miesiąc jest pusty (do wygenerowania)', await czekaj('Do wygenerowania\\|Sierpień'));
  await p.click('#m-dalej');
  ok('powrót do miesiąca z dokumentami', await czekaj('Wygenerowane\\|Wrzesień'));
  await p.waitForTimeout(3000);
  // przejście między miesiącami (View Transitions) przez chwilę przechwytuje kliknięcia; na wolnej grafice programowej trwa dłużej niż 3 s — klikamy do skutku
  for (let i = 0; i < 12 && !(await p.locator('#od-nowa-tak').count()); i++) { await p.click('#od-nowa', { force: true }); await p.waitForTimeout(2500); }
  await p.waitForSelector('#od-nowa-tak'); await p.click('#od-nowa-tak');
  const wrocil = await czekaj('Do wygenerowania', 60000); await p.waitForTimeout(1500);
  const wart = await p.locator('#kwota-in').inputValue();
  ok('„Wygeneruj od nowa" wraca do ustawień z zachowaną kwotą', wrocil && wart.replace(/\s/g, '') === '3095,26', 'stan ' + (await p.locator('#status').innerText()) + ', kwota „' + wart + '"');
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 6))); if (t.bledy.length) kod = 1;
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
