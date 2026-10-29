// Żywy interfejs (js/zywe.js): suwak kwoty, podgląd cieczy, malowanie dni, teatr trasy, paleta poleceń, wycieczka, fiolki, przesuwanie zakładek.
// NODE_PATH=/opt/node22/lib/node_modules node zywe_app.js [katalog-zrzutow]      ETAP=plan|gotowe|wycieczka|telefon zawęża do jednej części (domyślnie wszystkie)
// Grafika jest tu liczona procesorem, więc klatek jest mało — kroki czekają na WARUNKI (nie na stałe czasy).
const { otworz, generuj, wieczory } = require('./wspolne'); const fs = require('fs');
const liczba = t => Number(String(t).replace(/[^\d,]/g, '').replace(',', '.'));
const ETAP = process.env.ETAP || '';
const chce = e => !ETAP || ETAP === e;
(async () => {
  const wyj = process.argv[2] || '/tmp/zywe_zrzuty'; fs.mkdirSync(wyj, { recursive: true }); let kod = 0;
  const ok = (opis, warunek, szcz = '') => { console.log((warunek ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!warunek) kod = 1; };
  const czekaj = (p, f, arg, ms = 150000) => p.waitForFunction(f, arg, { timeout: ms, polling: 250 });
  const profil = async (p, tap = false) => {
    await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
    await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
    await (tap ? p.tap('#zapisz-dane') : p.click('#zapisz-dane')); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 30000 });
  };
  /** wybiera dzień z trasą o danym numerze kolejnym i czeka, aż widok trasy naprawdę się przełączy (View Transition bywa wolny) */
  const wybierzDzien = async (p, nr) => {
    const d = Number(await p.locator('#siatka button.dz.trasa').nth(nr).getAttribute('data-d'));
    await p.locator('#siatka button.dz.trasa').nth(nr).click({ force: true });
    await czekaj(p, n => new RegExp('\\b' + n + ' września').test(document.querySelector('#e-tyt').textContent) && !document.querySelector('#e-graj').disabled && document.querySelector('.tr-slad') !== null, d);
    await p.waitForTimeout(800); return d;
  };

  if (chce('plan') || chce('gotowe')) {
    const t = await otworz({ w: 1440, h: 900 }); const p = t.p;
    await p.goto(t.adres + '/index.html'); await profil(p); await p.waitForTimeout(4500);
    if (chce('plan')) {
      ok('suwak kwoty jest wyłączony — kwotę się wpisuje', await p.locator('#tuner').count() === 0);
      await p.fill('#kwota-in', '99999'); await p.press('#kwota-in', 'Enter');
      await czekaj(p, () => /maksimum to/.test(document.querySelector('#par-info').textContent), null, 90000);
      const maks = liczba((await p.locator('#par-info').innerText()).match(/maksimum to ([\d\s\u00a0]+)/)[1]);
      ok('kwota ponad maksimum: komunikat i kalendarz zmienia barwę na ostrzegawczą', maks > 1000 && await p.locator('#siatka.ponad').count() === 1, `maks ${maks}`);
      await p.fill('#kwota-in', String(Math.round(maks / 2))); await p.press('#kwota-in', 'Enter');
      await czekaj(p, () => { const v = parseFloat(getComputedStyle(document.querySelector('#siatka')).getPropertyValue('--podglad')); return v > .4 && v < .6 && !document.querySelector('#siatka').classList.contains('ponad'); }, null, 30000);
      ok('wpisana kwota napełnia dni cieczą proporcjonalnie do maksimum', true);
      await czekaj(p, () => { const l = document.querySelector('#siatka .dz.przelacz .pl'); return l && l.getBoundingClientRect().height / l.parentElement.getBoundingClientRect().height > .2; }, null, 30000);
      ok('ciecz w dniu faktycznie widać (wysokość > 20 % komórki)', true);
      await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
      await p.screenshot({ path: wyj + '/1_kwota.png' });
      ok('pusty stan trasy pokazuje „ducha” (mapka z krążącym punktem)', await p.locator('#dzien-tresc .duch .duch-poj').count() === 1);
      ok('pusty stan dokumentów pokazuje puste probówki', await p.locator('#fiolki .duch-fiolki i').count() === 5);
      ok('kafle mają własne akcenty (kropka przy tytule)', await p.evaluate(() => ['.k-dzis', '.k-kal', '.k-dzien', '.k-dok'].every(k => getComputedStyle(document.querySelector(k + ' .tyt'), '::before').content !== 'none')));
      ok('akcenty kafli są różne', await p.evaluate(() => new Set(['.k-dzis', '.k-kal', '.k-dzien', '.k-dok'].map(k => getComputedStyle(document.querySelector(k)).getPropertyValue('--akc').trim())).size === 4));

      /* lupa */
      const c18 = await p.locator('#siatka .dz[data-d="18"]').boundingBox();
      await p.mouse.move(c18.x + c18.width / 2, c18.y + c18.height / 2, { steps: 4 }); await p.waitForTimeout(500);
      const sk = await p.evaluate(() => ({ g: parseFloat(document.querySelector('#siatka .dz[data-d="18"]').style.scale || '1'), d: parseFloat(document.querySelector('#siatka .dz[data-d="30"]').style.scale || '1') }));
      if (await p.evaluate(() => document.documentElement.classList.contains('spokojne'))) ok('lupa (tryb spokojny): dzień pod kursorem NIE rośnie', sk.g === 1 && sk.d === 1, JSON.stringify(sk));
      else ok('lupa: dzień pod kursorem rośnie, daleki dzień nie', sk.g > 1.1 && sk.d === 1, JSON.stringify(sk));
      await p.mouse.move(700, 450, { steps: 3 }); await p.waitForTimeout(500);
      ok('po zjechaniu kursorem kalendarz wraca do rozmiaru', await p.evaluate(() => [...document.querySelectorAll('#siatka .dz')].every(e => !e.style.scale)));

      /* malowanie (tryb Wieczory: robocze są też soboty, więc pas 14–19 to 6 dni) */
      await wieczory(p);
      const a = await p.locator('#siatka .dz[data-d="14"]').boundingBox(), b = await p.locator('#siatka .dz[data-d="19"]').boundingBox();
      const przed = await p.locator('#siatka .dz.urlop').count();
      await p.mouse.move(a.x + a.width / 2, a.y + a.height / 2); await p.mouse.down(); await p.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 14 }); await p.waitForTimeout(500);
      ok('podczas malowania dni pokazują zaznaczenie', await p.locator('#siatka.maluje .dz.maluj-w').count() >= 5, String(await p.locator('#siatka .dz.maluj-w').count()));
      await p.screenshot({ path: wyj + '/2_malowanie.png' });
      await p.mouse.up(); await czekaj(p, n => document.querySelectorAll('#siatka .dz.urlop').length - n === 6, przed, 30000);
      ok('puszczenie myszy zapisuje cały pas dni wolnych (14–19 = 6 dni)', true);
      ok('tytuł kalendarza liczy dni robocze po malowaniu', /20 dni roboczych/.test(await p.locator('#c-tyt').innerText()), await p.locator('#c-tyt').innerText());
      const c14 = await p.locator('#siatka .dz[data-d="14"]').boundingBox();
      await p.mouse.move(c14.x + c14.width / 2, c14.y + c14.height / 2); await p.mouse.down(); await p.mouse.move(c14.x + c14.width * 2.5, c14.y + c14.height / 2, { steps: 8 }); await p.mouse.up();
      await czekaj(p, n => document.querySelectorAll('#siatka .dz.urlop').length < n + 6, przed, 30000);
      ok('malowanie od dnia wolnego przywraca dni do pracy', true, String(await p.locator('#siatka .dz.urlop').count()));
      await p.waitForTimeout(1500); await p.mouse.move(700, 450, { steps: 3 }); await p.waitForTimeout(800);      // kalendarz po przebudowie i bez lupy
      const c9 = await p.locator('#siatka .dz[data-d="9"]').boundingBox(); const przed2 = await p.locator('#siatka .dz.urlop').count();
      await p.mouse.move(c9.x + c9.width / 2, c9.y + c9.height / 2, { steps: 3 }); await p.waitForTimeout(500);
      await p.mouse.click(c9.x + c9.width / 2, c9.y + c9.height / 2); await czekaj(p, n => document.querySelectorAll('#siatka .dz.urlop').length === n + 1, przed2, 30000);
      ok('zwykłe kliknięcie nadal przełącza pojedynczy dzień', true);
      await p.mouse.click(c9.x + c9.width / 2, c9.y + c9.height / 2); await czekaj(p, n => document.querySelectorAll('#siatka .dz.urlop').length === n, przed2, 30000);

      /* paleta (przed generowaniem) */
      await p.mouse.move(700, 300); await p.keyboard.press('Control+k'); await p.waitForSelector('.paleta-tlo.otwarta', { timeout: 5000 }); await p.waitForTimeout(600);
      ok('Ctrl+K otwiera paletę poleceń z fokusem w polu', await p.evaluate(() => document.activeElement && document.activeElement.id === 'pal-in'));
      ok('aplikacja pod paletą jest nieaktywna (fokus nie ucieka)', await p.evaluate(() => document.querySelector('#aplikacja').inert === true));
      await p.keyboard.type('3200'); await p.waitForTimeout(500);
      ok('liczba ≥ 50 podpowiada ustawienie kwoty', /Ustaw kwotę 3\s?200,00 zł/.test(await p.locator('#pal-lista li').first().innerText()), (await p.locator('#pal-lista li').first().innerText()).replace(/\n/g, ' | '));
      await p.keyboard.press('Enter'); await czekaj(p, () => document.querySelector('.paleta-tlo').hidden, null, 10000);
      await czekaj(p, () => /^3\D?200/.test(document.querySelector('#kwota-in').value.replace(/\s/g, '')) || document.querySelector('#kwota-in').value.replace(/\s/g, '').startsWith('3200'), null, 20000);
      ok('polecenie z palety ustawia kwotę w polu', liczba(await p.inputValue('#kwota-in')) === 3200, await p.inputValue('#kwota-in'));
      ok('po zamknięciu palety aplikacja jest aktywna', await p.evaluate(() => document.querySelector('#aplikacja').inert === false));
      await p.locator('#siatka .dz[data-d="9"]').focus();
      await p.keyboard.press('/'); await p.waitForSelector('.paleta-tlo.otwarta', { timeout: 5000 }); await p.keyboard.type('lut'); await p.waitForTimeout(500);
      ok('wpisanie „lut” znajduje miesiąc luty (skrót „/”)', /Luty 2026/.test(await p.locator('#pal-lista li').first().innerText()), (await p.locator('#pal-lista li').first().innerText()).replace(/\n/g, ' | '));
      await p.screenshot({ path: wyj + '/3_paleta.png' });
      await p.keyboard.press('Escape'); await czekaj(p, () => document.querySelector('.paleta-tlo').hidden, null, 10000);
      ok('Esc zamyka paletę', true);
      await p.keyboard.press('Control+k'); await p.waitForSelector('.paleta-tlo.otwarta'); await p.keyboard.type('zzzzqq'); await p.waitForTimeout(400);
      ok('brak wyników: czytelny komunikat zamiast pustki', /Nic takiego/.test(await p.locator('#pal-lista').innerText()));
      await p.keyboard.press('Escape'); await czekaj(p, () => document.querySelector('.paleta-tlo').hidden, null, 10000);
      await p.click('#szukaj'); await p.waitForSelector('.paleta-tlo.otwarta', { timeout: 5000 });
      ok('przycisk lupy w nagłówku też otwiera paletę', true); await p.keyboard.press('Escape'); await czekaj(p, () => document.querySelector('.paleta-tlo').hidden, null, 10000);
      if (!chce('gotowe') || ETAP === 'plan') { ok('część „plan” bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 4))); }
    }

    /* ---------- po wygenerowaniu ---------- */
    if (chce('gotowe')) {
      if (ETAP === 'gotowe') { await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500); }
      await generuj(p); await p.waitForTimeout(5000);
      ok('probówki mają bąbelki', await p.locator('#fiolki .f-ciecz .babel').count() >= 12, String(await p.locator('#fiolki .f-ciecz .babel').count()));
      const fb = await p.locator('#fiolki').boundingBox();
      await p.mouse.move(fb.x + 10, fb.y + fb.height * .5); await p.mouse.move(fb.x + fb.width - 10, fb.y + fb.height * .5, { steps: 6 }); await p.waitForTimeout(120);
      { const kolysze = await p.evaluate(() => [...document.querySelectorAll('.fiolka')].some(f => f.style.rotate)), spokojnie = await p.evaluate(() => document.documentElement.classList.contains('spokojne'));
        ok(spokojnie ? 'chlupot (tryb spokojny): probówki nie kołyszą się za kursorem' : 'chlupot: ruch kursora po probówkach je kołysze', spokojnie ? !kolysze : kolysze); }
      const sklep = await p.locator('#siatka .dz.trasa').count();
      ok('po generowaniu kalendarz ma dni z trasą (bez podglądu cieczy)', sklep >= 10 && await p.locator('#siatka .dz.przelacz').count() === 0);
      await p.hover('#ko-lista li >> nth=1'); await p.waitForTimeout(300);
      ok('najechanie na „Dzień ≤ limit” zaznacza najdroższy dzień', await p.locator('#siatka .dz.swiec').count() === 1);
      await p.hover('#ko-lista li >> nth=2'); await p.waitForTimeout(300);
      ok('najechanie na „Polecenie ≤ limit” zaznacza najpełniejszą probówkę', await p.locator('#fiolki .fiolka.swiec').count() === 1);
      await p.mouse.move(700, 100); await p.waitForTimeout(300);

      /* teatr trasy */
      await wybierzDzien(p, 2);
      ok('przycisk ▶ jest aktywny dla dnia z trasą', !(await p.locator('#e-graj').isDisabled()));
      const suma = await p.locator('.de-kwota').innerText();
      const wezly = await p.locator('#dzien-tresc .pr').count();
      await p.click('#e-graj'); await p.waitForSelector('.mapka.gra', { timeout: 10000 });
      ok('start filmu: mapa, oś i licznik wchodzą w tryb pokazu', await p.locator('.podroz.gra').count() === 1 && await p.locator('.pr-poj').count() === 1 && await p.locator('.tr-poj').count() === 1);
      await czekaj(p, () => document.querySelectorAll('#dzien-tresc .pr.minal').length >= 2);
      const w1 = liczba(await p.locator('.de-kwota').innerText());
      await czekaj(p, () => document.querySelectorAll('#dzien-tresc .pr.minal').length >= 3);
      const w2 = liczba(await p.locator('.de-kwota').innerText());
      ok('w trakcie filmu kwota dnia rośnie od zera', w1 > 0 && w2 > w1 && w2 < liczba(suma) + .01, `${w1} → ${w2} (cel ${suma})`);
      ok('pojazd ma pozycję i kierunek na mapie', /translate\([\d.\-]+ [\d.\-]+\) rotate\(/.test(await p.evaluate(() => document.querySelector('.tr-poj').getAttribute('transform') || '')));
      const mi = await p.locator('#dzien-tresc .pr.minal').count();
      ok('minięte węzły są zaznaczone, reszta przygaszona', mi >= 2 && mi < wezly, `${mi} z ${wezly}`);
      const chip = await p.evaluate(() => { const c = document.querySelector('.mapa-chip'), f = document.querySelector('.mapka'); if (!c || !f) return null; const a = c.getBoundingClientRect(), b = f.getBoundingClientRect(); return { txt: c.textContent.trim(), opa: Number(getComputedStyle(c).opacity), wewn: a.left >= b.left - 1 && a.right <= b.right + 1 && a.top >= b.top - 1 && a.bottom <= b.bottom + 1 }; });
      ok('nigdzie w interfejsie nie ma stawki zł/km ani przeliczników', !/zł\s*\/\s*km|km\s*×/.test(await p.evaluate(() => document.body.innerText)));
      ok('przy pojeździe jest etykieta (dokąd jedzie / gdzie stoi), widoczna i w obrębie mapy', !!chip && chip.txt.length > 3 && chip.opa > .5 && chip.wewn, JSON.stringify(chip));
      await p.screenshot({ path: wyj + '/4_film.png' });
      await p.click('#e-graj'); await p.waitForTimeout(600);
      ok('drugie kliknięcie wstrzymuje film', (await p.locator('#e-graj').getAttribute('aria-label')) === 'Wznów' && await p.locator('#e-graj.gra').count() === 0);
      const stoi1 = await p.locator('.de-kwota').innerText(); await p.waitForTimeout(1500); const stoi2 = await p.locator('.de-kwota').innerText();
      ok('po wstrzymaniu licznik stoi', stoi1 === stoi2, `${stoi1} / ${stoi2}`);
      await p.click('#e-graj'); await czekaj(p, () => /jeszcze raz/.test(document.querySelector('#e-graj').getAttribute('aria-label')), null, 240000);
      ok('na końcu filmu kwota wraca dokładnie do sumy dnia', (await p.locator('.de-kwota').innerText()) === suma, `${await p.locator('.de-kwota').innerText()} = ${suma}`);
      await czekaj(p, () => !document.querySelector('.mapka.gra'), null, 30000);
      ok('po filmie pokaz się wygasza, a kwota zostaje pełna', (await p.locator('.de-kwota').innerText()) === suma);
      /* przewijanie po osi */
      const po = await p.locator('#dzien-tresc .podroz').boundingBox();
      await p.mouse.move(po.x + po.width * .1, po.y + po.height * .3); await p.mouse.move(po.x + po.width * .6, po.y + po.height * .3, { steps: 10 });
      await czekaj(p, () => !!document.querySelector('.mapka.gra') && document.querySelectorAll('#dzien-tresc .pr.minal').length >= 2, null, 30000);
      ok('przesuwanie kursora po osi pokazuje pojazd bez zmiany kwoty', (await p.locator('.de-kwota').innerText()) === suma);
      const czas = await p.locator('.pr-poj b').innerText(); ok('znacznik na osi pokazuje godzinę', /^\d\d:\d\d$/.test(czas), czas);
      await p.screenshot({ path: wyj + '/5_przewijanie.png' });
      await p.mouse.move(po.x + po.width * .2, po.y + po.height * .3); await p.mouse.down(); await p.mouse.move(po.x + po.width * .7, po.y + po.height * .3, { steps: 8 });
      await czekaj(p, s => document.querySelector('.de-kwota').innerText !== s, suma, 30000);
      ok('przeciąganie po osi przewija też licznik kwoty', true);
      await p.mouse.up(); await czekaj(p, () => !document.querySelector('.mapka.gra'), null, 40000);
      ok('po puszczeniu pokaz się wygasza i wraca pełna kwota', (await p.locator('.de-kwota').innerText()) === suma);
      await p.hover('#dzien-tresc .pr >> nth=2'); await p.waitForTimeout(300);
      ok('najechanie na węzeł osi rozjaśnia go na mapie', await p.locator('.tr-pkt.zwrot').count() === 1);
      await p.mouse.move(700, 100); await p.mouse.click(700, 100);
      /* paleta po generowaniu: dzień i motyw */
      const dDzien = Number(await p.locator('#siatka button.dz.trasa').last().getAttribute('data-d'));
      await p.keyboard.press('Control+k'); await p.waitForSelector('.paleta-tlo.otwarta'); await p.keyboard.type(String(dDzien)); await p.waitForTimeout(500);
      const lD = await p.locator('#pal-lista li').first().innerText(); ok('numer dnia podpowiada trasę z tego dnia', new RegExp('Pokaż trasę z dnia ' + dDzien).test(lD), lD.replace(/\n/g, ' | '));
      await p.keyboard.press('Enter'); await czekaj(p, n => new RegExp('\\b' + n + ' ').test(document.querySelector('#e-tyt').textContent), dDzien, 60000);
      ok('polecenie z palety wybiera dzień', true, await p.locator('#e-tyt').innerText());
      await p.keyboard.press('Control+k'); await p.waitForSelector('.paleta-tlo.otwarta'); await p.keyboard.type('motyw'); await p.waitForTimeout(400); await p.keyboard.press('Enter');
      await czekaj(p, () => document.documentElement.dataset.theme === 'light', null, 30000); ok('polecenie „motyw” przełącza na Dzień', true);
      await p.waitForTimeout(3500);
      ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 4)));
    }
    await t.zamknij();
  }

  /* ---------- wycieczka po pierwszym uruchomieniu ---------- */
  if (chce('wycieczka')) {
    const t2 = await otworz({ w: 1440, h: 900, wycieczka: true }); const q = t2.p;
    await q.goto(t2.adres + '/index.html'); await profil(q);
    await q.waitForSelector('.wyc.otwarta', { timeout: 60000 });
    const licz = () => q.evaluate(() => document.querySelector('.wyc-licz').textContent);
    await czekaj(q, () => /^1 z \d+$/.test(document.querySelector('.wyc-licz').textContent), null, 60000); await q.waitForTimeout(1200);
    const N = Number((await licz()).split(' z ')[1]);
    ok('po zapisaniu danych rusza wycieczka po aplikacji (kroki, w tym o motywie, uwagach i telefonie)', /^1 z \d+$/.test(await licz()) && N >= 9, await licz());
    const sw = await q.evaluate(() => { const s = document.querySelector('.wyc-swiatlo').style; return { x: parseFloat(s.left), y: parseFloat(s.top), w: parseFloat(s.width), h: parseFloat(s.height) }; }), kafel = await q.locator('#kA .b-lewa').boundingBox();
    ok('reflektor otacza opisywany element', sw.x < kafel.x && sw.y < kafel.y && sw.x + sw.w > kafel.x + kafel.width && sw.y + sw.h > kafel.y + kafel.height, JSON.stringify(sw));
    await q.screenshot({ path: wyj + '/6_wycieczka1.png' });
    await q.keyboard.press('ArrowRight'); await czekaj(q, n => document.querySelector('.wyc-licz').textContent === '2 z ' + n, N, 30000); await q.waitForTimeout(1200);
    ok('strzałka w prawo przechodzi do kroku 2', true);
    await q.screenshot({ path: wyj + '/7_wycieczka2.png' });
    await q.click('[data-w="wstecz"]'); await czekaj(q, () => document.querySelector('.wyc-licz').textContent.startsWith('1 z '), null, 30000);
    ok('przycisk Wstecz wraca do kroku 1', true);
    await q.keyboard.press('Escape'); await czekaj(q, () => document.querySelector('.wyc').hidden, null, 15000);
    ok('Esc kończy wycieczkę i zapamiętuje to na urządzeniu', await q.evaluate(() => localStorage.getItem('pmt-ui-wycieczka') === '1'));
    ok('po wycieczce aplikacja jest znów aktywna', await q.evaluate(() => document.querySelector('#aplikacja').inert === false));
    await q.keyboard.press('Control+k'); await q.waitForSelector('.paleta-tlo.otwarta'); await q.keyboard.type('wycieczk'); await q.waitForTimeout(400); await q.keyboard.press('Enter');
    await q.waitForSelector('.wyc.otwarta', { timeout: 20000 }); ok('z palety można wywołać wycieczkę ponownie', true);
    await czekaj(q, () => document.querySelector('.wyc-licz').textContent.startsWith('1 z '), null, 30000);
    const tytuly = [await q.locator('#wyc-tyt').innerText()];
    for (let i = 2; i <= N; i++) { await q.keyboard.press('ArrowRight'); await czekaj(q, a => document.querySelector('.wyc-licz').textContent === a[0] + ' z ' + a[1], [i, N], 30000); tytuly.push(await q.locator('#wyc-tyt').innerText()); }
    ok('samouczek mówi o zmianie wyglądu, powiadomieniach, uwagach i telefonie', ['Noc czy Dzień', 'Ważne informacje', 'Uwagi, telefon i wygląd'].every(x => tytuly.includes(x)), tytuly.join(' / '));
    await q.keyboard.press('ArrowRight'); await czekaj(q, () => document.querySelector('.wyc').hidden, null, 15000); ok('ostatni krok kończy wycieczkę', true);
    ok('wycieczka bez błędów w konsoli', t2.bledy.length === 0, JSON.stringify(t2.bledy.slice(0, 4)));
    await t2.zamknij();
  }

  /* ---------- telefon: przesuwanie zakładek, nagłówek, wyszukiwanie w menu konta ---------- */
  if (chce('telefon')) {
    const t3 = await otworz({ w: 390, h: 844, mobile: true, dsf: 2 }); const m = t3.p;
    await m.goto(t3.adres + '/index.html'); await profil(m, true); await m.waitForTimeout(5000);
    ok('telefon: nagłówek mieści się w ekranie', await m.evaluate(() => document.querySelector('.prawa').getBoundingClientRect().right <= innerWidth + .5), String(await m.evaluate(() => Math.round(document.querySelector('.prawa').getBoundingClientRect().right))));
    ok('telefon: lupa w nagłówku jest ukryta, a wyszukiwanie jest w menu konta', !(await m.locator('#szukaj').isVisible()));
    await m.tap('#konto'); await czekaj(m, () => document.querySelector('#konto-menu').classList.contains('otwarty'), null, 20000); await m.waitForTimeout(700);
    ok('telefon: w menu konta jest „Szukaj poleceń”', await m.locator('#szukaj-menu').isVisible());
    await m.tap('#szukaj-menu'); await m.waitForSelector('.paleta-tlo.otwarta', { timeout: 10000 }); ok('telefon: wyszukiwanie z menu konta otwiera paletę', true);
    await m.keyboard.press('Escape'); await czekaj(m, () => document.querySelector('.paleta-tlo').hidden, null, 15000);
    const cdp = await m.context().newCDPSession(m);
    const swipe = async (x0, x1, y = 640) => {
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x0, y }] });
      for (let i = 1; i <= 8; i++) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x0 + (x1 - x0) * i / 8, y: y + i }] });
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    };
    const tab = () => m.evaluate(() => document.querySelector('#aplikacja').dataset.tab);
    const naTab = async (nazwa) => { await czekaj(m, n => document.querySelector('#aplikacja').dataset.tab === n, nazwa, 40000).catch(() => {}); await m.waitForTimeout(1500); return tab(); };
    ok('telefon: start na zakładce Dziś', (await tab()) === 'dzis');
    await swipe(320, 80); ok('telefon: przesunięcie palcem w lewo przechodzi do Miesiąca', (await naTab('miesiac')) === 'miesiac', await tab());
    await swipe(320, 80); ok('telefon: kolejne przesunięcie w lewo — Dokumenty', (await naTab('dokumenty')) === 'dokumenty', await tab());
    await swipe(320, 80); await m.waitForTimeout(2500); ok('telefon: na ostatniej zakładce przesunięcie nic nie psuje', (await tab()) === 'dokumenty');
    await swipe(80, 320); ok('telefon: przesunięcie w prawo wraca do Miesiąca', (await naTab('miesiac')) === 'miesiac', await tab());
    await swipe(80, 130); await m.waitForTimeout(2500); ok('telefon: krótki ruch nie zmienia zakładki', (await tab()) === 'miesiac');
    await m.screenshot({ path: wyj + '/8_telefon.png' });
    ok('telefon: bez błędów w konsoli', t3.bledy.length === 0, JSON.stringify(t3.bledy.slice(0, 4)));
    await t3.zamknij();
  }
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
