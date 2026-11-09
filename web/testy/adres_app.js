// Adres w osobnych polach (ulica, nr budynku, nr mieszkania, kod, miejscowość), adres bez ulicy (wieś), pytanie o rodzaj adresu i potwierdzenie danych przed generowaniem.
// NODE_PATH=/opt/node22/lib/node_modules node adres_app.js
const { otworz, wpiszAdres } = require('./wspolne');
(async () => {
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p; let kod = 0;
  const ok = (opis, warunek, szcz = '') => { console.log((warunek ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!warunek) kod = 1; };
  const czekaj = (f, arg, ms = 60000) => p.waitForFunction(f, arg, { timeout: ms, polling: 200 });
  const opis = () => p.locator('#typ-opis').innerText();
  const wcisniety = () => p.evaluate(() => { const b = [...document.querySelectorAll('#typ-adresu [data-typ]')].find(x => x.getAttribute('aria-pressed') === 'true'); return b ? b.dataset.typ : null; });
  const wpisz = async a => { await wpiszAdres(p, a); await czekaj(() => !document.querySelector('#typ-adresu').hidden && document.querySelector('#typ-opis').textContent.length > 3, null, 30000); await p.waitForTimeout(700); };
  const profilZapisany = () => p.evaluate(() => { try { return window.__pmtDane.czytaj().profil; } catch (e) { return null; } });

  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349');

  await wpisz('ul. Polna 5, 00-001 Warszawa');
  ok('adres z ulicą: rodzaj rozpoznany jako „Ulica”', (await wcisniety()) === 'ulica', await opis());
  ok('adres z ulicą: start i meta trasy to miejscowość z poczty', /Start i meta trasy: Warszawa/.test(await opis()), await opis());

  await wpiszAdres(p, 'Dębowa Wola 12, 26-660 Jedlińsk'); await czekaj(() => /ulicy czy miejscowości/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('adres bez ulicy i niejednoznaczna nazwa: aplikacja pyta, czy to ulica, czy miejscowość', (await wcisniety()) === null && /Dębowa Wola/.test(await opis()), await opis());
  await p.click('#zapisz-dane'); await p.waitForTimeout(1500);
  ok('bez rozstrzygnięcia dane się nie zapisują (okno zostaje, pytanie podświetlone)', await p.locator('#arkusz-tlo.otwarty').count() === 1 && await p.locator('#typ-opis.zle').count() === 1);
  await p.click('#typ-adresu [data-typ="wies"]'); await czekaj(() => /Miejscowość bez ulicy\. Start i meta trasy: Dębowa Wola/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('po wyborze „Miejscowość bez ulicy” start i meta trasy to nazwa wsi, nie poczta', true, await opis());
  await p.click('#typ-adresu [data-typ="ulica"]'); await czekaj(() => /Start i meta trasy: Jedlińsk/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('wybór „Ulica” zmienia start trasy z powrotem na pocztę (Jedlińsk)', true, await opis());
  await p.click('#typ-adresu [data-typ="wies"]'); await czekaj(() => /Dębowa Wola\./.test(document.querySelector('#typ-opis').textContent), null, 30000);

  await wpiszAdres(p, 'Krzyżówki 3, 26-660 Jedlińsk'); await czekaj(() => /Start i meta trasy: Jedlińsk/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('jednowyrazowa wieś jest na start brana za ulicę (jak w programie)…', (await wcisniety()) === 'ulica', await opis());
  await p.click('#typ-adresu [data-typ="wies"]'); await czekaj(() => /Start i meta trasy: Krzyżówki/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  ok('…ale użytkownik może to jednym kliknięciem poprawić na miejscowość', true, await opis());

  await wpiszAdres(p, 'Dębowa Wola 12, 26-660 Jedlińsk'); await p.fill('#d-nr', ''); await p.click('#zapisz-dane'); await p.waitForTimeout(1500);
  const malyTekst = id => p.locator(id).locator('xpath=..').locator('small').innerText();
  ok('adres bez numeru budynku: błąd stoi przy POLU numeru („Podaj numer budynku”), reszta pól bez błędów, okno zostaje', /numer budynku/i.test(await malyTekst('#d-nr')) && (await malyTekst('#d-ulica')) === '' && (await malyTekst('#d-kod')) === '' && (await malyTekst('#d-miasto')) === '' && await p.locator('#arkusz-tlo.otwarty').count() === 1, await malyTekst('#d-nr'));
  await p.fill('#d-ulica', ''); await p.fill('#d-kod', '123'); await p.fill('#d-miasto', ''); await p.fill('#d-lokal', 'x!'); await p.click('#zapisz-dane'); await p.waitForTimeout(1200);
  ok('puste albo złe pola dostają własne komunikaty: ulica, numer budynku, numer mieszkania, kod pocztowy, miejscowość', /ulicę albo/i.test(await malyTekst('#d-ulica')) && /numer budynku/i.test(await malyTekst('#d-nr')) && /mieszkania/i.test(await malyTekst('#d-lokal')) && /00-000/.test(await malyTekst('#d-kod')) && /miejscowość/i.test(await malyTekst('#d-miasto')));
  await p.fill('#d-kod', ''); await p.click('#d-kod'); await p.keyboard.type('26660');
  ok('kod pocztowy: po wpisaniu pięciu cyfr myślnik wstawia się sam („26660” → „26-660”)', (await p.inputValue('#d-kod')) === '26-660', await p.inputValue('#d-kod'));
  await p.fill('#d-lokal', '');

  await wpiszAdres(p, 'Dębowa Wola 12, 26-660 Jedlińsk'); await czekaj(() => /ulicy czy miejscowości/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  await p.click('#typ-adresu [data-typ="wies"]'); await czekaj(() => /Dębowa Wola\./.test(document.querySelector('#typ-opis').textContent), null, 30000);
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 });
  const pr = await profilZapisany();
  ok('profil zapamiętuje rodzaj adresu', pr && pr.typ_adresu === 'wies' && /Dębowa Wola 12/.test(pr.adres), JSON.stringify(pr && { adres: pr.adres, typ: pr.typ_adresu }));
  await p.waitForTimeout(4500);

  /* ponowne otwarcie „Moich danych” pamięta wybór */
  await p.click('#konto'); await p.waitForTimeout(600); await p.click('#moje-dane'); await p.waitForSelector('#typ-adresu:not([hidden])', { timeout: 60000 }); await p.waitForTimeout(800);
  ok('„Moje dane” po ponownym otwarciu pokazują zapamiętany rodzaj adresu', (await wcisniety()) === 'wies', await opis());
  ok('…i zapamiętany adres w osobnych polach (nazwa wsi w polu ulicy, numer, kod, miejscowość; numer mieszkania pusty)', (await p.inputValue('#d-ulica')) === 'Dębowa Wola' && (await p.inputValue('#d-nr')) === '12' && (await p.inputValue('#d-lokal')) === '' && (await p.inputValue('#d-kod')) === '26-660' && (await p.inputValue('#d-miasto')) === 'Jedlińsk');
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

  /* numer mieszkania (opcjonalny): dochodzi do adresu po ukośniku, a pola wracają po ponownym otwarciu okna */
  await p.click('#konto'); await p.waitForTimeout(600); await p.click('#moje-dane'); await p.waitForSelector('#d-ulica', { timeout: 60000 });
  await wpiszAdres(p, 'ul. Polna 5, 00-001 Warszawa'); await p.fill('#d-lokal', '12'); await czekaj(() => !document.querySelector('#typ-adresu').hidden && /Start i meta trasy: Warszawa/.test(document.querySelector('#typ-opis').textContent), null, 30000);
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 });
  const pm = await profilZapisany();
  ok('numer mieszkania trafia do adresu po ukośniku (jak dotąd drukowany adres: „ul. Polna 5/12, 00-001 Warszawa”), a części są zapamiętane', pm && pm.adres === 'ul. Polna 5/12, 00-001 Warszawa' && pm.adres_czesci && pm.adres_czesci.lokal === '12' && pm.adres_czesci.ulica === 'ul. Polna' && pm.adres_czesci.nr === '5', JSON.stringify(pm && { adres: pm.adres, czesci: pm.adres_czesci }));
  await p.waitForTimeout(3000);
  await p.click('#konto'); await p.waitForTimeout(600); await p.click('#moje-dane'); await p.waitForSelector('#d-ulica', { timeout: 60000 }); await p.waitForTimeout(600);
  ok('po ponownym otwarciu pola mają dokładnie to, co wpisano (z numerem mieszkania)', (await p.inputValue('#d-ulica')) === 'ul. Polna' && (await p.inputValue('#d-nr')) === '5' && (await p.inputValue('#d-lokal')) === '12' && (await p.inputValue('#d-kod')) === '00-001' && (await p.inputValue('#d-miasto')) === 'Warszawa');
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(500);
  /* profil sprzed zmiany (tylko jeden napis adresu, bez części): pola wypełniają się z niego; napis nie do rozdzielenia → pola puste i uwaga */
  await p.evaluate(() => { const d = window.__pmtDane.czytaj(); delete d.profil.adres_czesci; d.profil.adres = 'ul. Stara 7/3, 61-100 Poznań'; window.__pmtDane.zapisz(d); });
  await p.reload(); await p.waitForTimeout(8000); await czekaj(() => document.querySelector('#kA') && !document.querySelector('#aplikacja').classList.contains('czeka'), null, 120000);
  await p.click('#konto'); await p.waitForTimeout(600); await p.click('#moje-dane'); await p.waitForSelector('#d-ulica', { timeout: 60000 }); await p.waitForTimeout(600);
  ok('profil sprzed zmiany: adres z jednego napisu sam rozdziela się na pola (ulica, numer, mieszkanie, kod, miejscowość)', (await p.inputValue('#d-ulica')) === 'ul. Stara' && (await p.inputValue('#d-nr')) === '7' && (await p.inputValue('#d-lokal')) === '3' && (await p.inputValue('#d-kod')) === '61-100' && (await p.inputValue('#d-miasto')) === 'Poznań' && (await p.locator('#adres-uwaga').innerText()) === '');
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(500);
  await p.evaluate(() => { const d = window.__pmtDane.czytaj(); delete d.profil.adres_czesci; d.profil.adres = 'Dziwny adres bez numeru'; window.__pmtDane.zapisz(d); });
  await p.reload(); await p.waitForTimeout(8000); await czekaj(() => document.querySelector('#kA') && !document.querySelector('#aplikacja').classList.contains('czeka'), null, 120000);
  await p.click('#konto'); await p.waitForTimeout(600); await p.click('#moje-dane'); await p.waitForSelector('#d-ulica', { timeout: 60000 }); await p.waitForTimeout(600);
  ok('zapisany adres, którego nie da się rozdzielić: pola puste, a pod nimi uwaga z tym adresem — nic nie jest zgadywane', (await p.inputValue('#d-ulica')) === '' && (await p.inputValue('#d-miasto')) === '' && /Dziwny adres bez numeru/.test(await p.locator('#adres-uwaga').innerText()));
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(500);
  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 4)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
