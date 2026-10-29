// Pierwsze uruchomienie: zamiast pustego programu — przykładowy, w pełni wygenerowany miesiąc (przyklad/*.json), który znika przy pierwszym własnym kroku.
// NODE_PATH=/opt/node22/lib/node_modules node przyklad_app.js
const { otworz } = require('./wspolne'); const fs = require('fs');
(async () => {
  const wyj = process.env.WYJ || '/tmp/przyklad_zrzuty'; fs.mkdirSync(wyj, { recursive: true });
  const t = await otworz({ w: 1440, h: 900, przyklad: true }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const czekaj = (f, arg, ms = 60000) => p.waitForFunction(f, arg, { timeout: ms, polling: 250 });
  const lsKlucz = () => p.evaluate(() => { const d = window.__pmtDane.czytaj(); return Object.keys(d).length ? d : null; });
  await p.goto(t.adres + '/index.html');
  await czekaj(() => document.documentElement.classList.contains('przyklad'), null, 120000); await p.waitForTimeout(6000);

  /* ---- przykład zamiast pustego programu ---- */
  ok('pierwsze uruchomienie pokazuje przykład, a nie okno „Moje dane”', !(await p.locator('#arkusz-tlo.otwarty').count()));
  ok('stan oznaczony jako „Przykład”', (await p.locator('#status').innerText()).includes('Przykład'));
  ok('główny przycisk zaprasza do wpisania własnej kwoty', /Wpisz swoją kwotę/.test(await p.locator('#kropla-napis').innerText()), await p.locator('#kropla-napis').innerText());
  ok('duża kwota przykładu wygląda na klikalną i ma podpowiedź dla czytników', await p.locator('#b-kwota-w .b-edytuj').isVisible() && await p.locator('#b-kwota-w').getAttribute('role') === 'button' && /wpisać własną kwotę/.test(await p.locator('#b-kwota-w').getAttribute('title')));
  ok('hero pokazuje kwotę przykładowego miesiąca', /3\s?684,30/.test(await p.locator('#b-kwota-w').getAttribute('aria-label')), await p.locator('#b-kwota-w').getAttribute('aria-label'));
  ok('kalendarz ma dni z trasami', (await p.locator('#siatka .dz.trasa').count()) >= 10, String(await p.locator('#siatka .dz.trasa').count()));
  ok('trasa dnia pokazuje mapę i oś podróży', (await p.locator('#dzien-tresc .mapka svg').count()) === 1 && (await p.locator('#dzien-tresc .podroz .pr').count()) >= 5);
  ok('dokumenty: probówki poleceń i rozliczenia', (await p.locator('#fiolki .fiolka').count()) >= 5, String(await p.locator('#fiolki .fiolka').count()));
  ok('kafel Dziś ma listę wizyt przykładowego planu', (await p.locator('#przystanki .przystanek').count()) >= 5 && /Przykład/.test(await p.locator('#d-tyt').innerText()), (await p.locator('#d-tyt').innerText()).replace(/\n/g, ' '));
  ok('termin i „Wygeneruj od nowa” są ukryte (nie dotyczą przykładu)', !(await p.locator('#termin').isVisible()) && !(await p.locator('#od-nowa').isVisible()));
  ok('wyjaśnienie, że to przykład, jest widoczne', await p.locator('#przyklad-nota').isVisible());
  await p.screenshot({ path: wyj + '/1_przyklad.png' });
  ok('przykład nie zapisał niczego w danych użytkownika', await p.evaluate(() => { const d = window.__pmtDane.czytaj(); return !d.profil && !Object.keys(d.miesiace || {}).length && !d.plan; }));

  /* ---- przykład żyje: ▶, odhaczanie, fanfary — bez zapisu ---- */
  await p.click('#e-graj'); await czekaj(() => document.querySelector('.mapka.gra'), null, 30000);
  ok('▶ w przykładzie odtwarza dzień na mapie', true); await p.click('#e-graj');
  await p.click('#przystanki .p-znak >> nth=0', { force: true }); await czekaj(() => /^1\//.test(document.querySelector('#d-pier-t').textContent), null, 30000);
  ok('odhaczenie wizyty w przykładzie działa', /^1\//.test(await p.locator('#d-pier-t').innerText()));
  ok('odhaczenie z przykładu NIE trafia do zapisanych danych', await p.evaluate(() => { return !Object.keys(window.__pmtDane.czytaj().wizyty || {}).length; }));
  await p.waitForTimeout(4000);      // przejście po odhaczeniu (View Transitions) przez chwilę przechwytuje kliknięcia
  await p.click('#fiolki .fiolka >> nth=0', { force: true }); await p.waitForTimeout(700);
  ok('przycisk dokumentów w przykładzie odsyła do własnych danych (bez okna podpisu)', /To przykład/.test(await p.locator('#toast-tekst').innerText()) && !(await p.locator('#arkusz-tlo.otwarty').count()), await p.locator('#toast-tekst').innerText());
  await p.click('#dzwonek'); await p.waitForTimeout(500);
  ok('dzwonek mówi, że to przykład', /To jest przykład/.test(await p.locator('#powiadomienia').innerText())); await p.keyboard.press('Escape'); await p.click('#aplikacja', { position: { x: 5, y: 5 }, force: true }).catch(() => {}); await p.waitForTimeout(400);

  /* ---- własna kwota od pierwszego ekranu: klik w dużą kwotę, wpisanie, dane osobowe dopiero przy generowaniu ---- */
  await p.click('#b-kwota-w'); await czekaj(() => !document.documentElement.classList.contains('przyklad') && /Do wygenerowania/.test(document.querySelector('#status').textContent), null, 90000); await p.waitForTimeout(1500);
  ok('klik w kwotę opuszcza przykład i pokazuje własny miesiąc (bez okna „Moje dane”)', !(await p.locator('#arkusz-tlo.otwarty').count()) && (await p.locator('#status').innerText()).includes('Do wygenerowania'));
  ok('kursor stoi od razu w polu kwoty', await p.evaluate(() => document.activeElement && document.activeElement.id === 'kwota-in'));
  await p.keyboard.type('3500'); await p.waitForTimeout(400);
  ok('kwotę da się wpisać z klawiatury', (await p.locator('#kwota-in').inputValue()) === '3500', await p.locator('#kwota-in').inputValue());
  await p.keyboard.press('Enter'); await p.waitForTimeout(700);
  ok('po Enterze kwota jest zapamiętana na urządzeniu', await p.evaluate(() => { const u = window.__pmtDane.czytaj().ustawienia || {}; return Object.entries(u).some(([n, v]) => /^kwota-/.test(n) && Number(v) === 3500); }));
  ok('brak danych osobowych jest podpowiedziany pod kwotą (nie blokuje wpisywania)', /Najpierw uzupełnij Moje dane/.test(await p.locator('#par-info').innerText()), await p.locator('#par-info').innerText());
  await p.screenshot({ path: wyj + '/2a_kwota_wpisana.png' });
  await p.click('#podpisz'); await p.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 30000 });
  ok('dopiero „Generuj dokumenty” prosi o dane osobowe', (await p.locator('#arkusz [data-zamknij]').count()) === 1);   // jedynie krzyżyk — to pierwsze uzupełnienie
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 }); await p.waitForTimeout(3000);
  ok('po zapisaniu danych wpisana kwota nadal jest w polu', /^3500(,00)?$/.test((await p.locator('#kwota-in').inputValue()).replace(/\s/g, '')), await p.locator('#kwota-in').inputValue());
  ok('program pokazuje prawdziwy miesiąc do wygenerowania', (await p.locator('#status').innerText()).includes('Do wygenerowania') && /Generuj dokumenty/.test(await p.locator('#kropla-napis').innerText()), (await p.locator('#status').innerText()) + ' | ' + await p.locator('#kropla-napis').innerText());
  ok('nie ma już dni z przykładowymi trasami', (await p.locator('#siatka .dz.trasa').count()) === 0 && (await p.locator('#kwota-in').count()) === 1);
  ok('kafel Dziś nie pokazuje wizyt przykładu (brak własnego planu)', (await p.locator('#przystanki .przystanek').count()) === 0);
  await p.screenshot({ path: wyj + '/2_po_zapisie.png' });
  const dane = await lsKlucz(); ok('zapisany jest tylko profil i kwota — żadnych danych przykładowych', dane && dane.profil && !Object.keys(dane.miesiace || {}).length && !dane.plan && !Object.keys(dane.wizyty || {}).length);

  /* ---- kolejne uruchomienie bez przykładu; powrót do przykładu z menu ---- */
  await p.reload(); await p.waitForSelector('#kwota-in'); await p.waitForTimeout(3500);
  ok('po odświeżeniu (jest profil) przykład się nie pojawia', await p.evaluate(() => !document.documentElement.classList.contains('przyklad')) && !(await p.locator('#arkusz-tlo.otwarty').count()));
  await p.click('#konto'); await p.waitForTimeout(500); ok('menu konta ma „Pokaż przykładowy miesiąc”', await p.locator('#pokaz-przyklad').isVisible());
  await p.click('#pokaz-przyklad'); await czekaj(() => document.documentElement.classList.contains('przyklad'), null, 60000); await p.waitForTimeout(2500);
  ok('przykład można obejrzeć ponownie; przycisk wraca do własnego miesiąca', /Wróć do swojego miesiąca/.test(await p.locator('#kropla-napis').innerText()), await p.locator('#kropla-napis').innerText());
  await p.click('#podpisz'); await czekaj(() => !document.documentElement.classList.contains('przyklad') && /Do wygenerowania/.test(document.querySelector('#status').textContent), null, 90000); await p.waitForTimeout(1500);
  ok('„Wróć do swojego miesiąca” wraca do prawdziwego miesiąca z kursorem w polu kwoty', (await p.locator('#status').innerText()).includes('Do wygenerowania') && (await p.locator('#kwota-in').count()) === 1 && await p.evaluate(() => document.activeElement && document.activeElement.id === 'kwota-in'));
  ok('dane użytkownika bez zmian po obejrzeniu przykładu', await p.evaluate(() => { const d = window.__pmtDane.czytaj(); return !!d.profil && !Object.keys(d.miesiace || {}).length && !d.plan; }));

  /* ---- po pierwszym wygenerowaniu program pokazuje już tylko dane użytkownika: przykład znika także z menu i palety ---- */
  await p.evaluate(async () => {      // udajemy własny, wygenerowany miesiąc (rekord jak po generowaniu), bez uruchamiania silnika
    const r = await (await fetch('przyklad/miesiac.json')).json(); const d = window.__pmtDane.czytaj();
    d.miesiace = { [`${r.rok}-${String(r.mies).padStart(2, '0')}`]: { params: r.params, wynik: r.wynik, podpisane: [], wyslane: false } }; d.ustawienia = { ...(d.ustawienia || {}), 'ostatni-miesiac': { rok: r.rok, mies: r.mies } }; window.__pmtDane.zapisz(d);
  });
  await p.reload(); await czekaj(() => document.querySelector('#kA.po-gen'), null, 120000); await p.waitForTimeout(2500);
  await p.click('#konto'); await p.waitForTimeout(500);
  ok('po wygenerowaniu dokumentów w menu konta nie ma już „Pokaż przykładowy miesiąc”', !(await p.locator('#pokaz-przyklad').isVisible()));
  await p.keyboard.press('Escape'); await p.click('#szukaj'); await p.waitForSelector('.paleta input, #pal-we', { timeout: 15000 }).catch(() => {}); await p.keyboard.type('przykład'); await p.waitForTimeout(700);
  ok('ani w palecie poleceń', !/Pokaż przykładowy miesiąc/.test(await p.locator('.paleta').innerText()));
  await p.keyboard.press('Escape'); await p.waitForTimeout(500);
  ok('program pokazuje wyłącznie dane z wygenerowanych dokumentów (bez znacznika „Przykład”)', !(await p.evaluate(() => document.documentElement.classList.contains('przyklad'))) && !/Przykład/.test(await p.locator('#status').innerText()));

  /* ---- po wygenerowaniu: klik w kwotę pozwala ją zmienić (kasuje dokumenty za potwierdzeniem) ---- */
  ok('duża kwota gotowego miesiąca jest klikalna', await p.locator('#b-kwota-w').getAttribute('role') === 'button' && /Zmień kwotę/.test(await p.locator('#b-kwota-w').getAttribute('title')), await p.locator('#b-kwota-w').getAttribute('title'));
  await p.click('#b-kwota-w'); await p.waitForSelector('#od-nowa-tak', { timeout: 15000 });
  ok('klik w kwotę pyta „Zmienić kwotę?” i zapowiada skutki', /Zmienić kwotę\?/.test(await p.locator('#ark-tyt').innerText()) && /Usuń i wpisz nową kwotę/.test(await p.locator('#od-nowa-tak').innerText()));
  await p.click('#arkusz [data-zamknij] >> nth=-1', { force: true }).catch(() => {}); await p.keyboard.press('Escape'); await p.waitForTimeout(800);
  ok('„Zostaw jak jest” nic nie usuwa', await p.evaluate(() => document.querySelector('#kA').classList.contains('po-gen')));
  await p.click('#b-kwota-w'); await p.waitForSelector('#od-nowa-tak'); await p.click('#od-nowa-tak');
  await czekaj(() => /Do wygenerowania/.test(document.querySelector('#status').textContent) && document.activeElement && document.activeElement.id === 'kwota-in', null, 90000); await p.waitForTimeout(800);
  ok('po potwierdzeniu: wracam do wpisania kwoty, kursor w polu, poprzednia kwota podpowiedziana', /^3\s?684,30$/.test((await p.locator('#kwota-in').inputValue()).trim()), await p.locator('#kwota-in').inputValue());
  await p.keyboard.type('4000'); await p.waitForTimeout(300);
  ok('nową kwotę da się wpisać (zaznaczona stara wartość jest zastępowana)', (await p.locator('#kwota-in').inputValue()) === '4000', await p.locator('#kwota-in').inputValue());
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 6))); if (t.bledy.length) kod = 1;
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
