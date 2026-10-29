// menedzer.txt: brak pliku, zła nazwa (menedzer.txt.txt), dołożenie pliku PO uruchomieniu aplikacji — bez odświeżania strony.
// NODE_PATH=/opt/node22/lib/node_modules node menedzer_app.js
const { otworz } = require('./wspolne');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const op = { bezMenedzera: true, podwojoneTxt: true };
  const t = await otworz({ w: 1440, h: 900, opcjeSerwera: op }); const p = t.p;
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 30000 }); await p.waitForTimeout(3500);
  await p.fill('#kwota-in', '1500'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
  await p.click('#podpisz'); await p.waitForSelector('#menedzer-ponow', { timeout: 120000 });
  const tekst = () => p.locator('#arkusz').innerText();
  ok('bez menedzer.txt aplikacja pokazuje konkretną diagnozę, a nie ogólny komunikat', /Brakuje pliku menedzer\.txt/.test(await tekst()));
  ok('wykrywa typową pomyłkę „menedzer.txt.txt”', /menedzer\.txt\.txt/.test(await tekst()));
  ok('podaje, gdzie szukała i jaka była odpowiedź serwera', /HTTP 404/.test(await tekst()) && /127\.0\.0\.1/.test(await tekst()), (await tekst()).split('\n').filter(x => /Szukałem/.test(x)).join(' '));
  op.podwojoneTxt = false;
  await p.click('#menedzer-ponow');
  await p.waitForFunction(() => { const a = document.querySelector('#arkusz'); return a && /Brakuje pliku menedzer\.txt/.test(a.innerText) && !/Znalazłem plik/.test(a.innerText); }, null, { timeout: 60000, polling: 200 }).catch(() => {});
  ok('po „Sprawdź ponownie” bez pliku diagnoza wraca (już bez podpowiedzi o podwójnym .txt)', /Brakuje pliku menedzer\.txt/.test(await tekst()) && !/Znalazłem plik/.test(await tekst()));
  await p.waitForSelector('#menedzer-ponow');
  op.bezMenedzera = false;           // użytkownik dokłada plik, strony NIE odświeża
  await p.click('#menedzer-ponow'); await p.waitForSelector('#potwierdz-gen', { timeout: 60000 });
  ok('po dołożeniu pliku „Sprawdź ponownie” działa bez odświeżania strony (jest arkusz potwierdzenia)', true);
  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
