// Okno „Dokumenty do podpisu”: opcjonalny widok 3D — pierścień kart z atrapą dokumentu zbudowaną z wygenerowanych danych (dostępny od razu po generowaniu, stan „czeka”), powiększenie po kliknięciu.
// Domyślnie zostaje lista kart; wybór widoku jest pamiętany. Sprawdza: dane na kartach (prawdziwe, PESEL zasłonięty), kolory stanów, obrót (strzałki, kropki, klik w kartę z boku), powiększony podgląd (pełne dane, Esc, ‹ ›),
// ruch „na żywo” (pętla animacji), układ w kilku rozmiarach okna i brak błędów w konsoli.
// NODE_PATH=/opt/node22/lib/node_modules node karty3d_app.js
const { otworz, generuj } = require('./wspolne');
(async () => {
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const liczba = s => Number(String(s).replace(/[^\d,.-]/g, '').replace(',', '.'));
  const przod = () => p.evaluate(() => { const k = document.querySelector('.karta3d.przod'); return k ? Number(k.dataset.i) : -1; });
  const nazwaPrzodu = () => p.locator('#k3-nazwa').innerText();
  const czekajPrzod = async i => { await p.waitForFunction(i => { const k = document.querySelector('.karta3d.przod'); return k && Number(k.dataset.i) === i; }, i, { timeout: 8000, polling: 100 }).catch(() => {}); await p.waitForTimeout(200); return przod(); };      // przy włączonym „życiu” (ZYCIE=tak) obrót dojeżdża płynnie, a grafika programowa jest wolna
  const wynik = () => p.evaluate(() => Object.values(window.__pmtDane.czytaj().miesiace)[0].wynik);
  const otworzOkno = async () => { await p.click('#podpisz'); await p.waitForSelector('#dok-siatka'); await p.waitForTimeout(500); };
  const zamknijOkno = async () => { await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); await p.waitForTimeout(300); };

  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await generuj(p); await p.waitForTimeout(3000);
  const W = await wynik(); const nDok = W.dokumenty.length;
  ok('wygenerowano 6 poleceń wyjazdu (+ rozliczenie); silnik oddaje też przełożonego do podglądu', nDok === 6 && W.przelozony === 'Kierownik Testowy', `poleceń w wyniku: ${nDok}, przełożony: ${W.przelozony}`);

  /* ---- probówka na pulpicie prowadzi do swojego dokumentu ---- */
  await p.click('#fiolki .fiolka[data-dok="2"]'); await p.waitForSelector('.dok-k[data-i="2"]'); await p.waitForTimeout(300);
  const probowka = await p.evaluate(() => { const c = document.querySelector('.dok-k[data-i="2"]'), r = c.getBoundingClientRect(); return { blysk: c.classList.contains('blysk'), wOknie: r.top >= 0 && r.bottom <= innerHeight, listy: document.querySelectorAll('.dok-k').length }; });
  ok('klik w probówkę 3 (widok listy): okno dokumentów otwiera się od razu na tym dokumencie — karta mignęła i jest w widoku', probowka.blysk && probowka.wOknie && probowka.listy === 7, JSON.stringify(probowka));
  await zamknijOkno();

  /* ---- domyślnie lista kart, przełącznik widoku ---- */
  await otworzOkno();
  ok('domyślnie: lista kart (7), bez pierścienia 3D; przełącznik „Karty | Widok 3D” jest, „Karty” wciśnięte', (await p.locator('.dok-k').count()) === 7 && (await p.locator('#k3-scena').count()) === 0 && (await p.locator('.k3-przel [data-w="lista"][aria-pressed="true"]').count()) === 1 && (await p.locator('.k3-przel [data-w="3d"][aria-pressed="false"]').count()) === 1);

  /* ---- widok 3D tuż po generowaniu (wszystkie dokumenty „czekają na podpis”) ---- */
  await p.click('[data-akcja="widok"][data-w="3d"]'); await p.waitForSelector('#k3-scena'); await p.waitForTimeout(400);
  ok('widok 3D: 7 kart na pierścieniu, jedna z przodu, 7 kropek stanu, lista kart zniknęła', (await p.locator('.karta3d').count()) === 7 && (await p.locator('.karta3d.przod').count()) === 1 && (await p.locator('.k3-kropka').count()) === 7 && (await p.locator('.dok-k').count()) === 0);
  ok('wszystkie karty mają stan „czeka” (indygo) już po generowaniu, kropki tak samo; „Widok 3D” wciśnięty; wybór zapamiętany na urządzeniu', (await p.locator('.karta3d.k3-czeka').count()) === 7 && (await p.locator('.k3-kropka.k3-czeka').count()) === 7 && (await p.locator('.k3-przel [data-w="3d"][aria-pressed="true"]').count()) === 1 && (await p.evaluate(() => localStorage.getItem('pmt-ui-karty'))) === '3d');
  const kol = await p.evaluate(() => { const k = document.querySelector('.karta3d'); const s = getComputedStyle(k); return { c1: s.getPropertyValue('--c1').trim(), tlo: s.backgroundImage }; });
  ok('kolory stanów zachowane: „czeka” = indygo/fiolet (nie zielony), tło jest gradientem', kol.c1.toLowerCase() === '#5b6dff' && /gradient/.test(kol.tlo), JSON.stringify(kol));
  await p.waitForFunction(() => { const r = document.querySelector('.karta3d.przod').getBoundingClientRect(); return r.bottom <= innerHeight && r.top >= 0; }, null, { timeout: 8000, polling: 100 }).catch(() => {});      // okno przewija się do karuzeli płynnie (przy „życiu”)
  ok('karta jest wyśrodkowana na pierścieniu i widoczna w oknie (przednia w całości, w granicach okna przeglądarki)', await p.evaluate(() => { const r = document.querySelector('.karta3d.przod').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight && r.width > 150; }));

  /* ---- prawdziwe dane na atrapie ---- */
  const dane = await p.evaluate(() => [...document.querySelectorAll('.karta3d')].map(k => ({ i: Number(k.dataset.i), html: k.innerHTML, tekst: k.innerText, suma: ((k.querySelector('.da-koszty .r.b') || {}).textContent) || '', opis: (k.querySelector('.k3-st span') || {}).textContent || '' })));
  ok('atrapa na każdej karcie: imię i nazwisko, adres, przełożony, firma — z wygenerowanych danych', dane.every(d => /Jan Testowy/.test(d.tekst) && (/Testowa 1/.test(d.tekst) || /Rozliczenie wydatków/.test(d.tekst)) && /PMT (SERVICES|HR) SP\. Z O\.O\. SP\. K\./.test(d.tekst)));
  ok('PESEL na karcie jest zasłonięty (pełnego numeru nie ma w kodzie karty, widać tylko końcówkę)', dane.every(d => !d.html.includes('90010112349')) && dane.some(d => /•+349/.test(d.tekst)));
  const polecenia = dane.filter(d => d.suma);
  ok('kwota na atrapie = kwota dokumentu z wyniku silnika (każde polecenie)', polecenia.length >= 6 && polecenia.every(d => { const dok = W.dokumenty.find(x => x.nr === d.i + 1); return dok && Math.abs(liczba(d.suma) - dok.kw) < 0.005 && Math.abs(liczba(d.opis.split('·').pop()) - dok.kw) < 0.005; }), polecenia.map(d => d.suma).join(' '));
  ok('rozliczenie: atrapa „Rozliczenie wydatków za miesiąc” z listą poleceń', dane.some(d => /Rozliczenie wydatków za miesiąc/.test(d.tekst) && /delegacja 01 Jan Testowy/.test(d.tekst)));

  /* ---- obrót: strzałki, przycisk ›, kropka, klik w kartę z boku ---- */
  const p0 = await przod(); const n0 = await nazwaPrzodu();
  await p.locator('#k3-scena').focus(); await p.keyboard.press('ArrowRight'); const p1 = await czekajPrzod((p0 + 1) % 7);
  ok('strzałka w prawo obraca pierścień: z przodu inna karta, podpis pod karuzelą się zmienia', p1 !== p0 && (await nazwaPrzodu()) !== n0, `${p0} → ${p1}, „${await nazwaPrzodu()}”`);
  await p.keyboard.press('ArrowLeft'); await czekajPrzod(p0);
  ok('strzałka w lewo wraca do poprzedniej karty', (await przod()) === p0);
  await p.click('[data-akcja="k3-prawo"]'); const p2 = await czekajPrzod((p0 + 1) % 7);
  await p.click('[data-akcja="k3-lewo"]'); await czekajPrzod(p0);
  ok('przyciski ‹ › obracają o jedną kartę', p2 !== p0 && (await przod()) === p0);
  await p.click('.k3-kropka[data-i="4"]'); await czekajPrzod(4);
  ok('kropka stanu obraca pierścień do wskazanego dokumentu (kropka aktywna = karta z przodu)', (await przod()) === 4 && (await p.locator('.k3-kropka.akt').getAttribute('data-i')) === '4');
  const bok = await p.evaluate(() => { const o = document.querySelector('.karta3d.przod'); const i = Number(o.dataset.i), n = document.querySelectorAll('.karta3d').length; return (i + 1) % n; });
  const punkt = await p.evaluate(b => { const k = document.querySelector(`.karta3d[data-i="${b}"]`), r = k.getBoundingClientRect(); for (let y = r.top + 8; y < r.bottom - 8; y += 10) for (let x = r.left + 8; x < r.right - 8; x += 10) { const e = document.elementFromPoint(x, y); if (e && k.contains(e) && !e.closest('button')) return { x, y }; } return null; }, bok);
  if (punkt) await p.mouse.click(punkt.x, punkt.y); await czekajPrzod(bok);
  ok('kliknięcie karty z boku wysuwa ją na przód (nie otwiera podglądu)', (await przod()) === bok && (await p.locator('.k3-podglad').count()) === 0, `przód: ${await przod()}`);

  /* ---- przeciąganie myszą i kółko myszy ---- */
  const sc = await p.locator('#k3-scena').boundingBox(), p3 = await przod();
  await p.mouse.move(sc.x + sc.width * 0.5, sc.y + 30); await p.mouse.down(); await p.mouse.move(sc.x + sc.width * 0.5 - 60, sc.y + 30, { steps: 4 }); await p.mouse.move(sc.x + sc.width * 0.5 - 200, sc.y + 30, { steps: 6 }); await p.mouse.up();
  const p4 = await czekajPrzod((p3 + 1) % 7);
  ok('przeciągnięcie pierścienia myszą w lewo obraca go o kartę do przodu i zatrzaskuje się na karcie; nie otwiera podglądu', p4 !== p3 && (await p.locator('.k3-podglad').count()) === 0 && (await p.locator('.k3-scena.chwyt').count()) === 0, `${p3} → ${p4}`);
  await p.mouse.move(sc.x + sc.width / 2, sc.y + sc.height / 2); await p.mouse.wheel(0, 120); const p5 = await czekajPrzod((p4 + 1) % 7);
  ok('kółko myszy obraca pierścień (przewinięcie w dół = następna karta)', p5 === (p4 + 1) % 7, `${p4} → ${p5}`);

  /* ---- powiększenie po kliknięciu w kartę z przodu ---- */
  await p.click('.k3-kropka[data-i="0"]'); await czekajPrzod(0);
  await p.locator('.karta3d.przod .da-papier').click({ force: true }); await p.waitForSelector('.k3-podglad'); await p.waitForTimeout(300);
  const wiersze = await p.evaluate(() => { const c = [...document.querySelectorAll('.k3-pg-kartka .da-tab > span:not(.h)')]; return c.length / 8; });
  const etapy = W.dni.filter(d => Number(d.dokument) === 1).reduce((s, d) => s + (d.etapy || []).length, 0);
  ok('powiększony podgląd polecenia 1: WSZYSTKIE odcinki trasy z danych silnika (nie skrócone jak na miniaturze)', etapy > 6 && wiersze === etapy, `${wiersze} z ${etapy}`);
  const pg = await p.locator('.k3-pg-kartka').innerText();
  ok('podgląd: pełny PESEL i adres do sprawdzenia przed podpisem, przełożony, cel wyjazdu, kwota, trzy pola podpisów', /90010112349/.test(pg) && /Testowa 1, 00-001 Warszawa/.test(pg) && /Kierownik Testowy/.test(pg) && /projekt: /.test(pg) && Math.abs(liczba(await p.locator('.k3-pg-kartka .da-koszty .r.b').innerText()) - W.dokumenty.find(x => x.nr === 1).kw) < 0.005 && /podpis Księgowej/.test(pg) && /podpis Dyrektora/.test(pg) && /podpis pracownika/.test(pg));
  ok('podgląd: panel stanu („czeka na podpis”) i przycisk „Otwórz plik PDF”; okno dokumentów nie zniknęło', /czeka na podpis/.test(await p.locator('.k3-pg-panel').innerText()) && (await p.locator('.k3-pg-panel [data-akcja="otworz"]').count()) === 1 && (await p.locator('#arkusz-tlo.otwarty').count()) === 1);
  await p.click('[data-akcja="k3-nast"]'); await p.waitForTimeout(200);
  ok('podgląd: › przechodzi do następnego dokumentu (polecenie 2)', /Polecenie 2/.test(await p.locator('.k3-pg-gora b').innerText()));
  await p.click('[data-akcja="k3-poprz"]'); await p.click('[data-akcja="k3-poprz"]'); await p.waitForTimeout(200);
  ok('podgląd: ‹ z pierwszego przechodzi do ostatniego (rozliczenie) — cyklicznie', /Rozliczenie/.test(await p.locator('.k3-pg-gora b').innerText()));
  await p.keyboard.press('Escape'); await p.waitForSelector('#k3-scena', { timeout: 5000 });
  ok('Esc w podglądzie wraca do karuzeli i NIE zamyka okna dokumentów; z przodu ostatnio oglądany dokument', (await p.locator('.k3-podglad').count()) === 0 && (await p.locator('#arkusz-tlo.otwarty').count()) === 1 && (await przod()) === 6);
  await p.locator('#k3-scena').focus(); await p.keyboard.press('Enter'); await p.waitForSelector('.k3-podglad');
  ok('Enter na karuzeli otwiera podgląd karty z przodu', (await p.locator('.k3-podglad').count()) === 1);
  await p.click('[data-akcja="k3-wroc"]'); await p.waitForSelector('#k3-scena');
  await p.click('.karta3d.przod [data-akcja="powieksz"]'); await p.waitForSelector('.k3-podglad');
  ok('przycisk „Powiększ” na karcie z przodu otwiera podgląd', (await p.locator('.k3-podglad').count()) === 1);
  await p.keyboard.press('Escape'); await p.waitForSelector('#k3-scena');
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 });
  ok('drugi Esc (na karuzeli) zamyka okno dokumentów', (await p.locator('#arkusz-tlo.otwarty').count()) === 0);

  /* ---- wybór widoku pamiętany; powrót do listy ---- */
  await otworzOkno();
  ok('po ponownym otwarciu okna nadal widok 3D (wybór zapamiętany)', (await p.locator('#k3-scena').count()) === 1 && (await p.locator('.dok-k').count()) === 0);
  await p.click('[data-akcja="widok"][data-w="lista"]'); await p.waitForTimeout(300);
  ok('„Karty” przywraca listę 7 kart (stan „czeka”) i zapamiętuje wybór', (await p.locator('.dok-k').count()) === 7 && (await p.locator('.dok-k.st-czeka').count()) === 7 && (await p.locator('#k3-scena').count()) === 0 && (await p.evaluate(() => localStorage.getItem('pmt-ui-karty'))) === 'lista');
  await p.click('[data-akcja="widok"][data-w="3d"]'); await p.waitForSelector('#k3-scena');

  /* ---- układ w różnych rozmiarach okna ---- */
  for (const [w, h] of [[1440, 900], [1280, 650], [1024, 768], [820, 1000], [390, 844]]) {
    await p.setViewportSize({ width: w, height: h });
    await p.waitForFunction(() => { const z = Math.max(.4, Math.min(1, document.querySelector('#k3-scena').clientHeight / 500)); return Math.abs(parseFloat(document.querySelector('#k3-pier').style.transform.slice(6)) - z) < .011; }, null, { timeout: 15000, polling: 100 });      // pierścień dopasowuje się do sceny po kilku klatkach (grafika programowa jest wolna)
    await p.waitForTimeout(300);
    await p.evaluate(() => document.querySelector('#k3-scena').scrollIntoView({ block: 'center' })); await p.waitForTimeout(250);
    const u = await p.evaluate(() => {
      const ark = document.querySelector('#arkusz'), s = document.querySelector('#k3-scena').getBoundingClientRect(), k = document.querySelector('.karta3d.przod').getBoundingClientRect(), b = document.querySelector('.karta3d.przod [data-akcja="powieksz"]');
      const br = b.getBoundingClientRect(), x = br.left + br.width / 2, y = br.top + br.height / 2, el = document.elementFromPoint(x, y);
      return { pier: document.querySelector('#k3-pier').style.transform, ch: document.querySelector('#k3-scena').clientHeight, poziomo: ark.scrollWidth - ark.clientWidth, k: [Math.round(k.left), Math.round(k.right), Math.round(k.width)], wew: k.left >= 0 && k.right <= innerWidth, scena: s.height, przyciskTrafiony: !!(el && el.closest('[data-akcja="powieksz"]')), granice: (() => { const t = [...document.querySelectorAll('.karta3d')].map(q => q.getBoundingClientRect()); return [Math.round(Math.min(...t.map(r => r.top)) - s.top), Math.round(s.bottom - Math.max(...t.map(r => r.bottom)))]; })(), wszystkieWScenie: [...document.querySelectorAll('.karta3d')].every(q => { const r = q.getBoundingClientRect(); return r.top >= s.top - 4 && r.bottom <= s.bottom + 4; }), kropkiNadKartami: document.querySelector('#k3-pasek').getBoundingClientRect().bottom <= Math.min(...[...document.querySelectorAll('.karta3d')].map(q => q.getBoundingClientRect().top)) + 2, przyciskWidoczny: br.top >= 0 && br.bottom <= innerHeight };
    });
    ok(`układ ${w}×${h}: bez przewijania poziomego, przednia karta w całości w oknie, przycisk „Powiększ” klikalny, żadna karta nie wystaje ze sceny ani nie zasłania kropek`, u.poziomo <= 1 && u.wew && u.przyciskTrafiony && u.wszystkieWScenie && u.kropkiNadKartami, JSON.stringify(u));
  }
  await p.setViewportSize({ width: 1440, height: 900 }); await p.waitForTimeout(400);
  await zamknijOkno();

  await p.click('#fiolki .fiolka[data-dok="4"]'); await p.waitForSelector('#k3-scena');
  ok('klik w probówkę 5 (widok 3D): karuzela od razu ma z przodu ten dokument', (await czekajPrzod(4)) === 4, `przód: ${await przod()}`);
  await zamknijOkno(); await p.click('#fiolki .fiolka.rozl'); await p.waitForSelector('#k3-scena');
  ok('klik w probówkę rozliczenia: z przodu rozliczenie (7. karta)', (await czekajPrzod(6)) === 6, `przód: ${await przod()}`);
  await zamknijOkno();

  ok('brak błędów w konsoli i wyjątków strony', t.bledy.length === 0, t.bledy.slice(0, 3).join(' | '));
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('BŁĄD TESTU', e); process.exit(2); });
