// Asystent podpisu na TELEFONIE (390x844, ekran dotykowy: pointer:coarse): ten sam asystent co na komputerze, ale zamiast przeciągania — przycisk „Wybierz podpisane pliki” (dotknięcie otwiera wybór plików
// telefonu); wszystko mieści się na szerokości ekranu. Pobieranie dokumentów przez asystenta, ścieżka odręczna z przyciskiem wyboru skanów, brak pola przeciągania.
// NODE_PATH=/opt/node22/lib/node_modules node asystent_telefon_app.js
const { wpiszAdres, otworz, generuj, wieczory } = require('./wspolne'); const fs = require('fs');
(async () => {
  const wyj = process.env.PMT_ZRZUTY || ''; if (wyj) fs.mkdirSync(wyj, { recursive: true });
  const W = Number(process.argv[2]) || 390;      // szerokość telefonu w pikselach CSS (np. 360, 390, 412)
  const t = await otworz({ w: W, h: 844, dsf: 2, mobile: true, widokPodpisu: null }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const tekst = s => p.locator(s).innerText();
  const zrzut = async n => { if (wyj) await p.screenshot({ path: `${wyj}/telefon_${n}.png` }); };
  const pobrane = []; p.on('download', d => pobrane.push(d));
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await wpiszAdres(p, 'ul. Testowa 1, 00-001 Warszawa');
  await p.tap('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3500);
  await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await wieczory(p, { tap: true });
  await p.tap('.zakladka[data-tab="miesiac"]'); await p.waitForTimeout(2500);
  for (const d of [21, 22, 23, 24, 25, 26]) { await p.tap(`#siatka button.dz[data-d="${d}"]`); await p.waitForTimeout(250); }
  await p.tap('.zakladka[data-tab="dzis"]'); await p.waitForTimeout(2000);
  await generuj(p, { tap: true }); await p.waitForTimeout(4000);
  await p.tap('.zakladka[data-tab="dokumenty"]'); await p.waitForTimeout(1000); await p.tap('#podpisz'); await p.waitForSelector('#asystent', { timeout: 20000 }); await p.waitForTimeout(1500);

  const bezPrzewijaniaWbok = async () => p.evaluate(() => { const a = document.querySelector('#arkusz'); return a.scrollWidth <= a.clientWidth + 1 && document.documentElement.scrollWidth <= window.innerWidth + 1; });
  ok('na telefonie okno podpisu to asystent z pytaniem o sposób podpisu (dwie karty), a nie cztery kroki naraz', (await p.locator('.kroki4').count()) === 0 && /Jak chcesz podpisać dokumenty/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent .as-wybor').count()) === 2);
  ok('wszystko mieści się na szerokości telefonu (bez przewijania w bok)', await bezPrzewijaniaWbok());
  ok('podpowiedź o przeglądarce nie męczy telefonu (jest dla komputerów)', (await p.locator('#as-rada-przegl').count()) === 0);
  await zrzut('1_wybor');
  await p.tap('#asystent [data-sposob="gov"]');
  ok('gov.pl na telefonie: „Pobierz dokumenty do podpisu” z jednym dużym przyciskiem', /Pobierz dokumenty do podpisu/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent [data-akcja="pobierz-do-podpisu"]').count()) === 1);
  ok('telefon: bez podpowiedzi o folderze pobierania na pulpicie (to rada dla komputerów)', (await p.locator('#asystent details.as-folder-pobierania').count()) === 0);
  await p.tap('#asystent [data-akcja="pobierz-do-podpisu"]'); await p.waitForSelector('#asystent a#otworz-gov', { timeout: 30000 });
  const n = Number(((await tekst('#asystent .as-status')).match(/0 z (\d+)/) || [])[1] || 0) + 1;      // polecenia do podpisu + rozliczenie wydatków (podpisu nie wymaga, ale też się pobiera)
  for (let i = 0; i < 100 && pobrane.length < n; i++) await p.waitForTimeout(150);      // zdarzenia pobrań dochodzą z opóźnieniem
  ok('po dotknięciu pobierają się wszystkie polecenia (delegacja_NN) i rozliczenie wydatków', n > 1 && pobrane.length === n && pobrane.filter(d => /^delegacja_\d\d_.*\.pdf$/.test(d.suggestedFilename())).length === n - 1 && pobrane.filter(d => /^rozliczenie.*\.pdf$/i.test(d.suggestedFilename())).length === 1, `${n}: ` + pobrane.map(d => d.suggestedFilename()).join(', '));
  ok('w kroku podpisu: zamiast pola przeciągania jest przycisk „Wybierz podpisane pliki” (telefon nie przeciąga), brak folderu „Pobrane” jako odnośnika do wskazania na siłę — przycisk wyboru jest widoczny i klikalny', (await p.locator('#asystent .as-wybierz').isVisible()) && !(await p.locator('#asystent .as-strefa-duza').count()) && /Wybierz podpisane pliki/.test(await tekst('#asystent .as-wybierz')));
  ok('i nadal wszystko mieści się na szerokości telefonu', await bezPrzewijaniaWbok());
  await zrzut('2_podpisz');
  const wysokosc = await p.locator('#asystent .as-wybierz').evaluate(e => e.getBoundingClientRect().height);
  ok('przyciski są dość duże do dotykania (co najmniej 44 px wysokości)', wysokosc >= 44, String(Math.round(wysokosc)));
  await p.tap('#asystent .as-przelacz');
  ok('odręcznie na telefonie: „Podpisz odręcznie”, zeskanowanie aplikacją w telefonie i przycisk „Wybierz podpisane pliki”', /Podpisz odręcznie/.test(await tekst('#asystent .as-tytul')) && /w telefonie/.test(await tekst('#asystent .as-lista')) && (await p.locator('#asystent .as-wybierz').isVisible()));
  await zrzut('3_odrecznie');
  /* widok klasyczny (cztery kroki naraz) pod przełącznikiem: na wąskim ekranie też nie może się ucinać po prawej (zrzut z telefonu: „Pobierz PDF” i opisy były ucięte) */
  await p.tap('#asystent details.asyst-inne > summary, details.asyst-inne > summary'); await p.tap('details.asyst-inne [data-akcja="widok-podpisu"][data-w="klasyczny"]'); await p.waitForSelector('.kroki4', { timeout: 10000 }); await p.waitForTimeout(800);
  await zrzut('4_klasyczny');
  const ciete = await p.evaluate(() => { const a = document.querySelector('#arkusz-tresc') || document.querySelector('#arkusz'), r = a.getBoundingClientRect(); return [...a.querySelectorAll('.kroki4 *')].filter(e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.right > r.right + 1; }).map(e => e.className || e.tagName).slice(0, 5); });
  ok('widok klasyczny na telefonie: żaden element nie wychodzi poza prawą krawędź okna', ciete.length === 0 && await bezPrzewijaniaWbok(), JSON.stringify(ciete));
  /* telefon z powiększoną czcionką (Ustawienia → Wyświetlanie → Rozmiar czcionki): rem rośnie, a nic nie może wychodzić poza okno — ani w asystencie, ani w widoku klasycznym */
  for (const [nazwa, pokaz] of [['klasyczny', null], ['asystent', async () => { await p.tap('[data-akcja="widok-podpisu"][data-w="asystent"]'); await p.waitForSelector('#asystent', { timeout: 10000 }); }]]) {
    if (pokaz) await pokaz();
    await p.evaluate(() => { document.documentElement.style.fontSize = '135%'; }); await p.waitForTimeout(500);
    const wyjscie = await p.evaluate(() => { const a = document.querySelector('#arkusz-tresc') || document.querySelector('#arkusz'), r = a.getBoundingClientRect(), sel = document.querySelector('.kroki4') ? '.kroki4 *' : '#asystent *'; return [...a.querySelectorAll(sel)].filter(e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.right > r.right + 1; }).map(e => (e.className && String(e.className).slice(0, 30)) || e.tagName).slice(0, 6); });
    await zrzut('5_czcionka_' + nazwa);
    ok(`powiększona czcionka (135%), widok „${nazwa}”: nic nie wychodzi poza prawą krawędź okna`, wyjscie.length === 0 && await bezPrzewijaniaWbok(), JSON.stringify(wyjscie));
    await p.evaluate(() => { document.documentElement.style.fontSize = ''; });
  }
  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
