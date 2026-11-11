// Aktualizacja aplikacji (js/aplikacja.js, koniec: rejestracja service workera): nowa wersja wchodzi dopiero po odświeżeniu, więc telefon długo pokazywał STARĄ wersję. Teraz:
//  • gdy aplikacja nic nie robi (żadne okno nie jest otwarte), po przejęciu strony przez nową wersję odświeża się sama (z krótkim komunikatem),
//  • gdy coś jest otwarte (np. okno „Moje dane”), zostaje stały pasek „Jest nowa wersja aplikacji” z przyciskiem „Odśwież”,
//  • jedno samoczynne odświeżenie na minutę (kolejna zmiana w tej minucie pokazuje pasek, nie odświeża).
// NODE_PATH=/opt/node22/lib/node_modules node aktualizacja_app.js
const { otworz } = require('./wspolne');
(async () => {
  const t = await otworz({ w: 1200, h: 800 }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const zmianaWersji = () => p.evaluate(() => navigator.serviceWorker.dispatchEvent(new Event('controllerchange')));
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });      // pierwsze uruchomienie: otwarte okno „Moje dane”
  await p.waitForFunction(() => !!navigator.serviceWorker.controller, null, { timeout: 60000 });
  await p.reload(); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });      // po odświeżeniu strona ma już service workera (mielSw)
  await p.waitForTimeout(1500);

  /* ---------- okno otwarte: pasek zamiast samoczynnego odświeżenia ---------- */
  let przeladowania = 0; p.on('framenavigated', f => { if (f === p.mainFrame()) przeladowania++; });
  await zmianaWersji(); await p.waitForSelector('#nowa-wersja', { timeout: 5000 });
  await p.waitForTimeout(2500);
  ok('gdy okno jest otwarte, aplikacja się NIE odświeża sama, tylko zostawia stały pasek „Jest nowa wersja aplikacji” z przyciskiem „Odśwież”', przeladowania === 0 && /Jest nowa wersja aplikacji/.test(await p.locator('#nowa-wersja').innerText()) && (await p.locator('#nowa-wersja-odswiez').count()) === 1);
  await zmianaWersji(); ok('kolejna zmiana wersji nie dokłada drugiego paska', (await p.locator('#nowa-wersja').count()) === 1);
  await Promise.all([p.waitForNavigation({ timeout: 60000 }), p.click('#nowa-wersja-odswiez')]);
  await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  ok('przycisk „Odśwież” przeładowuje stronę (pasek znika)', (await p.locator('#nowa-wersja').count()) === 0);

  /* ---------- nic nie jest otwarte: odświeża się samo (raz na minutę) ---------- */
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); await p.waitForTimeout(800);
  await p.evaluate(() => document.activeElement && document.activeElement.blur && document.activeElement.blur());
  await zmianaWersji(); await p.waitForSelector('#toast.widoczny', { timeout: 5000 });
  const komunikat = await p.locator('#toast-tekst').innerText();
  await p.waitForNavigation({ timeout: 15000 }).catch(() => {}); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 }); await p.waitForTimeout(1500);      // aplikacja wstała (okno „Moje dane”)
  ok('gdy nic nie jest otwarte, aplikacja pokazuje „Aktualizuję aplikację…” i po chwili odświeża się sama (bez klikania)', /Aktualizuję aplikację/.test(komunikat) && (await p.evaluate(() => performance.getEntriesByType('navigation')[0].type)) === 'reload', komunikat);
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); await p.waitForTimeout(800);
  await zmianaWersji(); await p.waitForTimeout(2500);
  ok('druga zmiana wersji w ciągu minuty NIE odświeża po raz drugi (ochrona przed pętlą): zamiast tego jest pasek z przyciskiem', (await p.locator('#nowa-wersja').count()) === 1);
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
