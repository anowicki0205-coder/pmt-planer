// Adres w „Moich danych”: użytkownik wpisuje SAMĄ nazwę ulicy (program dopisuje „ul.”), wybiera rodzaj (Ulica / Miejscowość bez ulicy), program pokazuje, jak adres wydrukuje się na dokumentach, podpowiada przy znanej
// nazwie wsi, sprawdza pola i adres na mapie (literówki), a potem potwierdzenie danych przed generowaniem. Mapa (OpenStreetMap) jest w teście podstawiona (trybGeo: jest / brak / siec).
// NODE_PATH=/opt/node22/lib/node_modules node adres_app.js
const { otworz, wpiszAdres } = require('./wspolne');
(async () => {
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p; let kod = 0;
  const ok = (opis, warunek, szcz = '') => { console.log((warunek ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!warunek) kod = 1; };
  const czekaj = (f, arg, ms = 60000) => p.waitForFunction(f, arg, { timeout: ms, polling: 200 });
  const tekst = id => p.locator(id).innerText();
  const podglad = () => tekst('#adres-podglad'), mapaTxt = () => tekst('#adres-mapa'), podp = () => tekst('#adres-podp');
  const malyTekst = id => p.locator(id).locator('xpath=..').locator('small').innerText();
  const aktywny = () => p.evaluate(() => { const b = [...document.querySelectorAll('.adres-typ [data-typ]')].find(x => x.getAttribute('aria-pressed') === 'true'); return b ? b.dataset.typ : null; });
  const czekajPodglad = re => czekaj(r => new RegExp(r).test(document.querySelector('#adres-podglad').textContent), re.source, 30000);
  const profilZapisany = () => p.evaluate(() => { try { return window.__pmtDane.czytaj().profil; } catch (e) { return null; } });
  const otworzDane = async () => { await p.click('#konto'); await p.waitForTimeout(600); await p.click('#moje-dane'); await p.waitForSelector('#d-ulica', { timeout: 60000 }); await p.waitForTimeout(600); };
  const zamknijOkno = async () => { await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(500); };
  /* mapa podstawiona: 'jest' (serwer zna adres), 'brak' (serwer odpowiada, że nie zna), 'siec' (bez połączenia) */
  let trybGeo = 'siec'; const geoZapytania = [];
  await p.route(/nominatim\.openstreetmap\.org/, r => {
    geoZapytania.push(decodeURIComponent(r.request().url()));
    if (trybGeo === 'siec') return r.abort();
    return r.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: trybGeo === 'jest' ? '[{"lat":"52.2297","lon":"21.0122"}]' : '[]' });
  });

  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349');

  /* ---------- sama nazwa ulicy, „ul.” dopisuje program ---------- */
  ok('na starcie wybrany jest rodzaj „Ulica”, pole nazywa się „Nazwa ulicy” i podpowiada „Polna” (bez „ul.”)', (await aktywny()) === 'ulica' && /Nazwa ulicy/.test(await p.textContent('#a-ulica-et')) && (await p.getAttribute('#d-ulica', 'placeholder')) === 'Polna');
  await wpiszAdres(p, 'ul. Polna 5, 00-001 Warszawa'); await czekajPodglad(/Na dokumentach/);
  ok('w polu ulicy stoi sama nazwa („Polna”), a podgląd mówi, jak adres wydrukuje się na dokumencie: „ul. Polna 5, 00-001 Warszawa”, start i meta trasy: Warszawa', (await p.inputValue('#d-ulica')) === 'Polna' && /Na dokumentach: ul\. Polna 5, 00-001 Warszawa/.test(await podglad()) && /start i meta trasy: Warszawa/.test(await podglad()), await podglad());
  await p.fill('#d-ulica', 'polna'); await czekajPodglad(/ul\. Polna 5/);
  ok('nazwa wpisana małymi literami dostaje wielką literę w podglądzie („polna” → „ul. Polna”)', /Na dokumentach: ul\. Polna 5, 00-001 Warszawa/.test(await podglad()), await podglad());
  await p.fill('#d-ulica', 'al. mickiewicza'); await czekajPodglad(/al\. Mickiewicza/);
  ok('wpisany przedrostek jest respektowany: „al. mickiewicza” → „al. Mickiewicza 5, 00-001 Warszawa” (bez dopisywania „ul.”)', /Na dokumentach: al\. Mickiewicza 5, 00-001 Warszawa/.test(await podglad()), await podglad());
  await p.fill('#d-ulica', 'ulica Długa'); await czekajPodglad(/ul\. Długa/);
  ok('„ulica Długa” → „ul. Długa” (przedrostek ujednolicony, nie podwojony)', /Na dokumentach: ul\. Długa 5/.test(await podglad()) && !/ul\. ul\./.test(await podglad()), await podglad());
  await p.fill('#d-ulica', 'Polna');

  /* ---------- wieś bez ulicy ---------- */
  await p.click('.adres-typ [data-typ="wies"]');
  ok('po wyborze „Miejscowość bez ulicy (wieś)” pole nazywa się „Nazwa wsi (bez ulicy)” i podpowiada „Dębowa Wola”', (await aktywny()) === 'wies' && /Nazwa wsi/.test(await p.textContent('#a-ulica-et')) && (await p.getAttribute('#d-ulica', 'placeholder')) === 'Dębowa Wola');
  await wpiszAdres(p, 'Dębowa Wola 12, 26-660 Jedlińsk', 'wies'); await czekajPodglad(/Dębowa Wola 12/);
  ok('wieś: na dokumencie sama nazwa wsi, BEZ „ul.” („Dębowa Wola 12, 26-660 Jedlińsk”); start i meta trasy to nazwa wsi, nie poczta', /Na dokumentach: Dębowa Wola 12, 26-660 Jedlińsk/.test(await podglad()) && /start i meta trasy: Dębowa Wola/.test(await podglad()) && !/ul\./.test(await podglad()), await podglad());
  await p.click('.adres-typ [data-typ="ulica"]'); await czekajPodglad(/ul\. Dębowa Wola 12/);
  ok('ten sam wpis w trybie „Ulica” to „ul. Dębowa Wola 12…”, start trasy z powrotem na pocztę (Jedlińsk)', /Na dokumentach: ul\. Dębowa Wola 12, 26-660 Jedlińsk/.test(await podglad()) && /start i meta trasy: Jedlińsk/.test(await podglad()), await podglad());
  await wpiszAdres(p, 'Goszczyn 12, 05-600 Grójec'); await czekaj(() => /miejscowości/.test(document.querySelector('#adres-podp').textContent), null, 30000);
  ok('znana miejscowość wpisana jako ulica (Goszczyn): podpowiedź „to nazwa miejscowości — wybierz Miejscowość bez ulicy” (tylko podpowiedź, nic nie blokuje)', /„Goszczyn” to nazwa miejscowości/.test(await podp()) && /Miejscowość bez ulicy/.test(await podp()), await podp());
  await p.click('.adres-typ [data-typ="wies"]'); await czekajPodglad(/Na dokumentach: Goszczyn 12/);
  ok('po przełączeniu na wieś podpowiedź znika, a adres jest „Goszczyn 12, 05-600 Grójec” (start i meta: Goszczyn)', (await podp()) === '' && /start i meta trasy: Goszczyn/.test(await podglad()), await podglad());
  await wpiszAdres(p, 'Krzyżówki 3, 26-660 Jedlińsk', 'wies'); await czekajPodglad(/Krzyżówki 3/);
  ok('jednowyrazowa wieś spoza listy (Krzyżówki) działa po wybraniu „wieś” — użytkownik decyduje, nie zgadywanie silnika', /Na dokumentach: Krzyżówki 3, 26-660 Jedlińsk/.test(await podglad()) && /start i meta trasy: Krzyżówki/.test(await podglad()), await podglad());

  /* ---------- błędy przy polach ---------- */
  await wpiszAdres(p, 'Dębowa Wola 12, 26-660 Jedlińsk', 'wies'); await p.fill('#d-nr', ''); await p.click('#zapisz-dane'); await p.waitForTimeout(1500);
  ok('adres bez numeru budynku: błąd stoi przy POLU numeru („Podaj numer budynku”), reszta pól bez błędów, okno zostaje', /numer budynku/i.test(await malyTekst('#d-nr')) && (await malyTekst('#d-ulica')) === '' && (await malyTekst('#d-kod')) === '' && (await malyTekst('#d-miasto')) === '' && await p.locator('#arkusz-tlo.otwarty').count() === 1, await malyTekst('#d-nr'));
  await p.fill('#d-ulica', ''); await p.fill('#d-kod', '123'); await p.fill('#d-miasto', ''); await p.fill('#d-lokal', 'x!'); await p.click('#zapisz-dane'); await p.waitForTimeout(1200);
  ok('puste albo złe pola dostają własne komunikaty: wieś („Podaj nazwę wsi”), numer budynku, numer mieszkania, kod pocztowy, miejscowość (bez cyfr)', /nazwę wsi/i.test(await malyTekst('#d-ulica')) && /numer budynku/i.test(await malyTekst('#d-nr')) && /mieszkania/i.test(await malyTekst('#d-lokal')) && /00-000/.test(await malyTekst('#d-kod')) && /miejscowość/i.test(await malyTekst('#d-miasto')));
  /* cyfry w polach ulicy i miejscowości są odrzucane już przy pisaniu i wklejaniu (numer budynku i mieszkania mają własne pola); wyjątek: nazwa ulicy zaczynająca się liczbą („3 Maja”) */
  await p.click('#d-miasto'); await p.keyboard.type('Jedliński2'); const miasto = await p.inputValue("#d-miasto"), podpM = await malyTekst("#d-miasto");
  ok('miejscowość: wpisana cyfra znika od razu („Jedliński2” → „Jedliński”), a pod polem jest krótkie wyjaśnienie', miasto === 'Jedliński' && /cyfr/i.test(podpM), miasto + " / " + podpM);
  await p.fill('#d-miasto', 'Zielona Góra 65'); ok('miejscowość: cyfry wklejone razem z tekstem też znikają', (await p.inputValue('#d-miasto')) === 'Zielona Góra ', await p.inputValue('#d-miasto'));
  await p.fill('#d-miasto', "Bielsko-Biała"); ok('miejscowość: myślnik, spacja i polskie litery zostają', (await p.inputValue('#d-miasto')) === 'Bielsko-Biała');
  await p.click('#d-ulica'); await p.fill('#d-ulica', ''); await p.keyboard.type('Polna 5'); const ul1 = await p.inputValue('#d-ulica');
  ok('ulica: numer domu dopisany po nazwie („Polna 5”) znika — numer jest w osobnym polu, a pod polem jest wyjaśnienie', ul1.trim() === 'Polna' && /numer budynku/i.test(await malyTekst('#d-ulica')), JSON.stringify(ul1));
  await p.fill('#d-ulica', ''); await p.keyboard.type('3 Maja'); ok('ulica: nazwa zaczynająca się liczbą („3 Maja”, „11 Listopada”) jest dozwolona', (await p.inputValue('#d-ulica')) === '3 Maja', await p.inputValue('#d-ulica'));
  await p.fill('#d-ulica', 'al. Róż 12a'); ok('ulica: przedrostek zostaje, numer (także z literą) znika („al. Róż 12a” → „al. Róż”)', (await p.inputValue('#d-ulica')).trim() === 'al. Róż', await p.inputValue('#d-ulica'));
  await p.click('.adres-typ [data-typ="ulica"]'); await p.click('#zapisz-dane'); await p.waitForTimeout(900);
  ok('w trybie ulicy komunikat przy nazwie brzmi „Podaj nazwę ulicy”', /nazwę ulicy/i.test(await malyTekst('#d-ulica')), await malyTekst('#d-ulica'));
  await p.fill('#d-kod', ''); await p.click('#d-kod'); await p.keyboard.type('26660');
  ok('kod pocztowy: po wpisaniu pięciu cyfr myślnik wstawia się sam („26660” → „26-660”)', (await p.inputValue('#d-kod')) === '26-660', await p.inputValue('#d-kod'));

  /* ---------- sprawdzanie adresu na mapie (literówki) ---------- */
  trybGeo = 'brak'; await wpiszAdres(p, 'ul. Polna 5, 00-001 Warszawa'); await p.click('#d-imie');
  await czekaj(() => /Nie znalazłem takiego adresu na mapie/.test(document.querySelector('#adres-mapa').textContent), null, 30000);
  ok('adres, którego mapa nie zna (literówka w ulicy): ostrzeżenie „Nie znalazłem takiego adresu na mapie — sprawdź pisownię…” już po wyjściu z pola', /sprawdź pisownię/.test(await mapaTxt()) && (await p.locator('#adres-mapa.zle').count()) === 1, await mapaTxt());
  await p.click('#zapisz-dane'); await p.waitForTimeout(1500);
  ok('pierwsze „Zapisz” przy takim adresie NIE zapisuje: okno zostaje, przycisk zmienia się na „Zapisz mimo to”', await p.locator('#arkusz-tlo.otwarty').count() === 1 && (await tekst('#zapisz-dane')) === 'Zapisz mimo to', await tekst('#zapisz-dane'));
  await p.fill('#d-ulica', 'Pol'); ok('edycja adresu zdejmuje ostrzeżenie i przywraca przycisk „Zapisz”', (await tekst('#zapisz-dane')) === 'Zapisz' && (await mapaTxt()) === '');
  trybGeo = 'jest'; await p.fill('#d-ulica', 'Marszałkowska'); await p.click('#d-imie');
  await czekaj(() => /Adres znaleziony na mapie/.test(document.querySelector('#adres-mapa').textContent), null, 30000);
  ok('adres znany mapie: „Adres znaleziony na mapie.” (zielony), zapis bez dodatkowych pytań', (await p.locator('#adres-mapa.ok').count()) === 1);
  trybGeo = 'siec'; await p.fill('#d-ulica', 'Siecowa'); await p.click('#d-imie');
  await czekaj(() => /Nie sprawdziłem adresu na mapie/.test(document.querySelector('#adres-mapa').textContent), null, 30000);
  ok('bez połączenia z mapą: spokojna informacja „Nie sprawdziłem adresu na mapie (brak połączenia)”, bez ostrzeżenia i bez blokowania zapisu', (await p.locator('#adres-mapa.zle').count()) === 0 && /brak połączenia/.test(await mapaTxt()));

  /* ---------- zapis: ulica i „Zapisz mimo to” ---------- */
  trybGeo = 'brak'; await wpiszAdres(p, 'ul. Zzzxqy 5, 00-001 Warszawa'); await p.click('#zapisz-dane'); await p.waitForTimeout(1500);
  ok('literówka w ulicy: pierwsze „Zapisz” ostrzega i nie zapisuje', (await tekst('#zapisz-dane')) === 'Zapisz mimo to' && await p.locator('#arkusz-tlo.otwarty').count() === 1);
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 });
  let pr = await profilZapisany();
  ok('drugie kliknięcie („Zapisz mimo to”) zapisuje: profil ma adres „ul. Zzzxqy 5, 00-001 Warszawa”, rodzaj „ulica” i części (sama nazwa w polu ulicy)', pr && pr.adres === 'ul. Zzzxqy 5, 00-001 Warszawa' && pr.typ_adresu === 'ulica' && pr.adres_czesci && pr.adres_czesci.ulica === 'Zzzxqy' && pr.adres_czesci.typ === 'ulica', JSON.stringify(pr && { adres: pr.adres, typ: pr.typ_adresu, czesci: pr.adres_czesci }));
  await p.waitForTimeout(3500);

  /* ---------- zapis wsi i pamięć rodzaju ---------- */
  trybGeo = 'siec'; await otworzDane();
  await wpiszAdres(p, 'Dębowa Wola 12, 26-660 Jedlińsk', 'wies'); await czekajPodglad(/Dębowa Wola 12/);
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 });
  pr = await profilZapisany();
  ok('profil zapamiętuje rodzaj adresu „wieś” i adres bez „ul.”', pr && pr.typ_adresu === 'wies' && pr.adres === 'Dębowa Wola 12, 26-660 Jedlińsk' && pr.adres_czesci.typ === 'wies', JSON.stringify(pr && { adres: pr.adres, typ: pr.typ_adresu }));
  await p.waitForTimeout(4500);
  await otworzDane();
  ok('„Moje dane” po ponownym otwarciu: wybrana „wieś”, w polu sama nazwa wsi, numer, kod i miejscowość; numer mieszkania pusty', (await aktywny()) === 'wies' && (await p.inputValue('#d-ulica')) === 'Dębowa Wola' && (await p.inputValue('#d-nr')) === '12' && (await p.inputValue('#d-lokal')) === '' && (await p.inputValue('#d-kod')) === '26-660' && (await p.inputValue('#d-miasto')) === 'Jedlińsk');
  await zamknijOkno();

  /* potwierdzenie przed generowaniem (i przekazanie rodzaju adresu do silnika) */
  await p.fill('#kwota-in', '1500'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
  await p.click('#podpisz'); await p.waitForSelector('#potwierdz-gen', { timeout: 60000 }); await p.waitForTimeout(600);
  ok('przed generowaniem jest arkusz „Sprawdź, zanim wygeneruję” z kwotą', /1\s?500,00/.test(await tekst('#potw-kwota')), await tekst('#potw-kwota'));
  ok('arkusz potwierdzenia pokazuje start i metę z rozstrzygnięcia „miejscowość bez ulicy”', (await tekst('#potw-baza')) === 'Dębowa Wola', await tekst('#potw-baza'));
  ok('arkusz potwierdzenia pokazuje PEŁNY adres startu i mety (do sprawdzenia)', /Dębowa Wola 12, 26-660 Jedlińsk/.test(await tekst('#potw-adres')), await tekst('#potw-adres'));
  ok('arkusz potwierdzenia pokazuje PESEL (do sprawdzenia)', (await tekst('#potw-pesel')) === '90010112349', await tekst('#potw-pesel'));
  ok('arkusz potwierdzenia pokazuje kto jest na dokumentach i dni pracy', /Jan Testowy/.test(await tekst('.potw-lista')) && /dni pracy/i.test(await tekst('.potw-lista')));
  ok('arkusz potwierdzenia nie pokazuje stawek ani przeliczników (to sprawa programu, nie użytkownika)', !/zł\s*\/\s*km|×/.test(await tekst('#arkusz')), (await tekst('.potw-lista')).replace(/\n/g, ' | '));
  await p.screenshot({ path: '/tmp/adres_potwierdzenie.png' });
  await p.click('#arkusz [data-zamknij]'); await p.waitForTimeout(1500);
  ok('„Popraw” zamyka arkusz bez generowania', await p.locator('#kA.po-gen').count() === 0 && !(await p.locator('#podpisz.zbiera').count()));

  /* profil sprzed zmiany (bez rodzaju adresu): pytanie pojawia się przy generowaniu */
  await p.evaluate(() => { const d = window.__pmtDane.czytaj(); delete d.profil.typ_adresu; delete d.profil.adres_czesci; window.__pmtDane.zapisz(d); });
  await p.reload(); await p.waitForTimeout(8000);
  await czekaj(() => document.querySelector('#kA') && !document.querySelector('#aplikacja').classList.contains('czeka'), null, 120000);
  await p.fill('#kwota-in', '1500'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
  await p.click('#podpisz'); await p.waitForSelector('[data-typ-adresu]', { timeout: 60000 });
  ok('stary profil: przy generowaniu aplikacja pyta, czy „Dębowa Wola” to ulica, czy miejscowość', /Dębowa Wola/.test(await tekst('#arkusz')));
  await p.click('[data-typ-adresu="ulica"]'); await p.waitForSelector('#potwierdz-gen', { timeout: 60000 }); await p.waitForTimeout(600);
  ok('po odpowiedzi „To ulica” start trasy to Jedlińsk (poczta) — decyzja trafiła do silnika', (await tekst('#potw-baza')) === 'Jedlińsk', await tekst('#potw-baza'));
  ok('odpowiedź jest zapamiętana w profilu (kolejne generowania nie pytają)', (await profilZapisany()).typ_adresu === 'ulica');
  await p.click('#arkusz [data-zamknij]'); await p.waitForTimeout(800);

  /* ---------- numer mieszkania i migracja starych profili ---------- */
  trybGeo = 'siec'; await otworzDane();
  await wpiszAdres(p, 'ul. Polna 5, 00-001 Warszawa'); await p.fill('#d-lokal', '12'); await czekajPodglad(/ul\. Polna 5\/12/);
  ok('numer mieszkania wchodzi do adresu po ukośniku w podglądzie: „ul. Polna 5/12, 00-001 Warszawa”', /Na dokumentach: ul\. Polna 5\/12, 00-001 Warszawa/.test(await podglad()), await podglad());
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 });
  pr = await profilZapisany();
  ok('profil: adres z ukośnikiem, części (z numerem mieszkania) i rodzaj „ulica”', pr && pr.adres === 'ul. Polna 5/12, 00-001 Warszawa' && pr.adres_czesci.lokal === '12' && pr.adres_czesci.ulica === 'Polna' && pr.adres_czesci.nr === '5' && pr.typ_adresu === 'ulica', JSON.stringify(pr && { adres: pr.adres, czesci: pr.adres_czesci }));
  await p.waitForTimeout(3000); await otworzDane();
  ok('po ponownym otwarciu pola mają dokładnie to, co wpisano: „Polna”, 5, 12, 00-001, Warszawa (rodzaj Ulica)', (await aktywny()) === 'ulica' && (await p.inputValue('#d-ulica')) === 'Polna' && (await p.inputValue('#d-nr')) === '5' && (await p.inputValue('#d-lokal')) === '12' && (await p.inputValue('#d-kod')) === '00-001' && (await p.inputValue('#d-miasto')) === 'Warszawa');
  await zamknijOkno();
  const odtworz = async (zmiana, opis, warunek) => {
    await p.evaluate(z => { const d = window.__pmtDane.czytaj(); delete d.profil.adres_czesci; Object.assign(d.profil, z); window.__pmtDane.zapisz(d); }, zmiana);
    await p.reload(); await p.waitForTimeout(8000); await czekaj(() => document.querySelector('#kA') && !document.querySelector('#aplikacja').classList.contains('czeka'), null, 120000);
    await otworzDane(); ok(opis, await warunek()); await zamknijOkno();
  };
  await odtworz({ adres: 'ul. Stara 7/3, 61-100 Poznań', typ_adresu: 'ulica' }, 'profil sprzed zmiany (jeden napis): adres sam rozdziela się na pola — „Stara” (bez „ul.”), 7, 3, 61-100, Poznań, rodzaj Ulica', async () => (await aktywny()) === 'ulica' && (await p.inputValue('#d-ulica')) === 'Stara' && (await p.inputValue('#d-nr')) === '7' && (await p.inputValue('#d-lokal')) === '3' && (await p.inputValue('#d-kod')) === '61-100' && (await p.inputValue('#d-miasto')) === 'Poznań' && (await tekst('#adres-uwaga')) === '');
  await odtworz({ adres: 'Dębowa Wola 12, 26-660 Jedlińsk', typ_adresu: 'wies' }, 'stary profil z wsią (adres bez „ul.”, rodzaj „wies”): przełącznik na „wieś”, w polu sama nazwa wsi', async () => (await aktywny()) === 'wies' && (await p.inputValue('#d-ulica')) === 'Dębowa Wola' && (await p.inputValue('#d-miasto')) === 'Jedlińsk');
  await odtworz({ adres: 'Dziwny adres bez numeru' }, 'zapisany adres, którego nie da się rozdzielić: pola puste, a pod nimi uwaga z tym adresem — nic nie jest zgadywane', async () => (await p.inputValue('#d-ulica')) === '' && (await p.inputValue('#d-miasto')) === '' && /Dziwny adres bez numeru/.test(await tekst('#adres-uwaga')));

  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 4)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
