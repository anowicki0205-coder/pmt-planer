// Adres bez ulicy (wieś), pytanie o rodzaj adresu i potwierdzenie danych przed generowaniem.
// NODE_PATH=/opt/node22/lib/node_modules node adres_app.js
const { otworz } = require('./wspolne');
(async () => {
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p; let kod = 0;
  const ok = (opis, warunek, szcz = '') => { console.log((warunek ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!warunek) kod = 1; };
  const czekaj = (f, arg, ms = 60000) => p.waitForFunction(f, arg, { timeout: ms, polling: 200 });
  const opis = () => p.locator('#typ-opis').innerText();
  const wcisniety = () => p.evaluate(() => { const b = [...document.querySelectorAll('#typ-adresu [data-typ]')].find(x => x.getAttribute('aria-pressed') === 'true'); return b ? b.dataset.typ : null; });
  const wpisz = async a => { await p.fill('#d-adres', a); await czekaj(() => !document.querySelector('#typ-adresu').hidden && document.querySelector('#typ-opis').textContent.length > 3, null, 30000); await p.waitForTimeout(700); };
  const profilZapisany = () => p.evaluate(() => { try { return window.__pmtDane.czytaj().profil; } catch (e) { return null; } });

  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349');

  await wpisz('ul. Polna 5, 00-001 Warszawa');
  ok('adres z ulicą: rodzaj rozpoznany jako „Ulica”', (await wcisniety()) === 'ulica', await opis());
  ok('adres z ulicą: start i meta trasy to miejscowość z poczty', /Start i meta trasy: Warszawa/.test(await opis()), await opis());

  await p.fill('#d-adres', 'Dębowa Wola 12, 26-660 Jedlińsk'); await czekaj(() => /ulicy czy miejscowości/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('adres bez ulicy i niejednoznaczna nazwa: aplikacja pyta, czy to ulica, czy miejscowość', (await wcisniety()) === null && /Dębowa Wola/.test(await opis()), await opis());
  await p.click('#zapisz-dane'); await p.waitForTimeout(1500);
  ok('bez rozstrzygnięcia dane się nie zapisują (okno zostaje, pytanie podświetlone)', await p.locator('#arkusz-tlo.otwarty').count() === 1 && await p.locator('#typ-opis.zle').count() === 1);
  await p.click('#typ-adresu [data-typ="wies"]'); await czekaj(() => /Miejscowość bez ulicy\. Start i meta trasy: Dębowa Wola/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('po wyborze „Miejscowość bez ulicy” start i meta trasy to nazwa wsi, nie poczta', true, await opis());
  await p.click('#typ-adresu [data-typ="ulica"]'); await czekaj(() => /Start i meta trasy: Jedlińsk/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('wybór „Ulica” zmienia start trasy z powrotem na pocztę (Jedlińsk)', true, await opis());
  await p.click('#typ-adresu [data-typ="wies"]'); await czekaj(() => /Dębowa Wola\./.test(document.querySelector('#typ-opis').textContent), null, 30000);

  await p.fill('#d-adres', 'Krzyżówki 3, 26-660 Jedlińsk'); await czekaj(() => /Start i meta trasy: Jedlińsk/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('jednowyrazowa wieś jest na start brana za ulicę (jak w programie)…', (await wcisniety()) === 'ulica', await opis());
  await p.click('#typ-adresu [data-typ="wies"]'); await czekaj(() => /Start i meta trasy: Krzyżówki/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('…ale użytkownik może to jednym kliknięciem poprawić na miejscowość', true, await opis());

  await p.fill('#d-adres', 'Dębowa Wola, 26-660 Jedlińsk'); await p.click('#zapisz-dane'); await p.waitForTimeout(1500);
  ok('adres bez numeru domu: komunikat podpowiada też adres bez ulicy', /bez ulicy/.test(await p.locator('#d-adres').locator('xpath=..').locator('small').innerText()), await p.locator('#d-adres').locator('xpath=..').locator('small').innerText());

  await p.fill('#d-adres', 'Dębowa Wola 12, 26-660 Jedlińsk'); await czekaj(() => /ulicy czy miejscowości/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  await p.click('#typ-adresu [data-typ="wies"]'); await czekaj(() => /Dębowa Wola\./.test(document.querySelector('#typ-opis').textContent), null, 30000);
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 });
  const pr = await profilZapisany();
  ok('profil zapamiętuje rodzaj adresu', pr && pr.typ_adresu === 'wies' && /Dębowa Wola 12/.test(pr.adres), JSON.stringify(pr && { adres: pr.adres, typ: pr.typ_adresu }));
  await p.waitForTimeout(4500);

  /* ponowne otwarcie „Moich danych” pamięta wybór */
  await p.click('#konto'); await p.waitForTimeout(600); await p.click('#moje-dane'); await p.waitForSelector('#typ-adresu:not([hidden])', { timeout: 60000 }); await p.waitForTimeout(800);
  ok('„Moje dane” po ponownym otwarciu pokazują zapamiętany rodzaj adresu', (await wcisniety()) === 'wies', await opis());
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(500);

  /* potwierdzenie przed generowaniem (i przekazanie rodzaju adresu do silnika) */
  await p.fill('#kwota-in', '1500'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
  await p.click('#podpisz'); await p.waitForSelector('#potwierdz-gen', { timeout: 60000 }); await p.waitForTimeout(600);
  ok('przed generowaniem jest arkusz „Sprawdź, zanim wygeneruję” z kwotą', /1\s?500,00/.test(await p.locator('#potw-kwota').innerText()), await p.locator('#potw-kwota').innerText());
  ok('arkusz potwierdzenia pokazuje start i metę z rozstrzygnięcia „miejscowość bez ulicy”', (await p.locator('#potw-baza').innerText()) === 'Dębowa Wola', await p.locator('#potw-baza').innerText());
  ok('arkusz potwierdzenia pokazuje PEŁNY adres startu i mety (do sprawdzenia)', /Dębowa Wola 12, 26-660 Jedlińsk/.test(await p.locator('#potw-adres').innerText()), await p.locator('#potw-adres').innerText());
  ok('arkusz potwierdzenia pokazuje PESEL (do sprawdzenia)', (await p.locator('#potw-pesel').innerText()) === '90010112349', await p.locator('#potw-pesel').innerText());
  ok('arkusz potwierdzenia pokazuje kto jest na dokumentach i dni pracy', /Jan Testowy/.test(await p.locator('.potw-lista').innerText()) && /dni pracy/i.test(await p.locator('.potw-lista').innerText()));
  ok('arkusz potwierdzenia nie pokazuje stawek ani przeliczników (to sprawa programu, nie użytkownika)', !/zł\s*\/\s*km|×/.test(await p.locator('#arkusz').innerText()), (await p.locator('.potw-lista').innerText()).replace(/\n/g, ' | '));
  await p.screenshot({ path: '/tmp/adres_potwierdzenie.png' });
  await p.click('#arkusz [data-zamknij]'); await p.waitForTimeout(1500);
  ok('„Popraw” zamyka arkusz bez generowania', await p.locator('#kA.po-gen').count() === 0 && !(await p.locator('#podpisz.zbiera').count()));

  /* profil sprzed zmiany (bez rodzaju adresu): pytanie pojawia się przy generowaniu */
  await p.evaluate(() => { const d = window.__pmtDane.czytaj(); delete d.profil.typ_adresu; window.__pmtDane.zapisz(d); });
  await p.reload(); await p.waitForTimeout(8000);
  await czekaj(() => document.querySelector('#kA') && !document.querySelector('#aplikacja').classList.contains('czeka'), null, 120000);
  await p.fill('#kwota-in', '1500'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
  await p.click('#podpisz'); await p.waitForSelector('[data-typ-adresu]', { timeout: 60000 });
  ok('stary profil: przy generowaniu aplikacja pyta, czy „Dębowa Wola” to ulica, czy miejscowość', /Dębowa Wola/.test(await p.locator('#arkusz').innerText()));
  await p.click('[data-typ-adresu="ulica"]'); await p.waitForSelector('#potwierdz-gen', { timeout: 60000 }); await p.waitForTimeout(600);
  ok('po odpowiedzi „To ulica” start trasy to Jedlińsk (poczta) — decyzja trafiła do silnika', (await p.locator('#potw-baza').innerText()) === 'Jedlińsk', await p.locator('#potw-baza').innerText());
  ok('odpowiedź jest zapamiętana w profilu (kolejne generowania nie pytają)', (await profilZapisany()).typ_adresu === 'ulica');
  await p.click('#arkusz [data-zamknij]'); await p.waitForTimeout(800);

  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 4)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
