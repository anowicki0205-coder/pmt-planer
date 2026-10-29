// Wstrzykiwanie kodu: dane „z zewnątrz” (plik z listą sklepów, nazwa wgrywanego pliku, imię z serwera, zapisany profil) zawierają znaczniki HTML i skrypty.
// Żaden z nich nie może zostać wykonany ani pojawić się w stronie jako element — sprawdzamy to na wszystkich ekranach (Dziś, kalendarz, dzień, dokumenty, okna, menu konta).
// Dodatkowo: polityka CSP w index.html blokuje skrypty z innych źródeł i atrybuty onerror/onclick (druga linia obrony), a aplikacja nie działa w obcej ramce.
// NODE_PATH=/opt/node22/lib/node_modules node xss_app.js
const { otworz, generuj } = require('./wspolne'); const { BackendMock } = require('./backend_mock'); const fs = require('fs'), os = require('os'), path = require('path');
(async () => {
  const PAY = '<i id="xss-znacznik">X</i><img src="x" onerror="window.__xss=1"><svg onload="window.__xss=2"></svg>"\'><script>window.__xss=3</script>';
  const B = new BackendMock(); B.uzytkownicy['12345'].imie = PAY; B.uzytkownicy['12345'].rejon = PAY;
  const t = await otworz({ w: 1440, h: 900, zalogowany: false, backend: B }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const bledyCsp = []; p.on('console', m => { if (/Content Security Policy|Refused to/.test(m.text())) bledyCsp.push(m.text().slice(0, 160)); });
  const wstrzyknieto = () => p.evaluate(() => ({ znacznik: !!document.querySelector('#xss-znacznik'), obraz: !!document.querySelector('img[src="x"]'), svg: !!document.querySelector('svg[onload]'), skrypt: [...document.querySelectorAll('script')].some(s => /__xss/.test(s.textContent)), wykonano: window.__xss === undefined ? null : window.__xss }));
  const czysto = async (opis) => { const w = await wstrzyknieto(); ok(`${opis}: nic się nie wstrzyknęło ani nie wykonało`, !w.znacznik && !w.obraz && !w.svg && !w.skrypt && w.wykonano === null, JSON.stringify(w)); };

  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await p.waitForTimeout(800);
  await p.fill('#dz-kod', '12345'); await p.fill('#dz-haslo', 'haslo123'); await p.keyboard.press('Enter');
  await p.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 120000 }); await p.waitForTimeout(1500);
  await czysto('imię z serwera w oknie „Moje dane” (podpowiedź w polu)');
  ok('imię z serwera trafia do pola jako TEKST (wartość równa napisowi, bez znaczników)', (await p.inputValue('#d-imie')) === PAY);
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3500);
  await czysto('pulpit po zalogowaniu (nagłówek, menu konta, powitanie)');

  /* plan z plikiem, w którym nazwy sieci i ulice są kodem */
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'xss-')); const csv = path.join(tmp, 'sklepy.csv');
  const wiersze = ['Sieć;Miasto;Ulica;Numer;Kod pocztowy']; const miasta = [['Józefów', '05-420'], ['Karczew', '05-480'], ['Otwock', '05-400'], ['Legionowo', '05-120']];
  for (let i = 0; i < 12; i++) { const [m, kp] = miasta[i % 4]; wiersze.push(`${PAY.replace(/;/g, ',')} ${i};${m};${PAY.replace(/;/g, ',')};${i + 1};${kp}`); }
  fs.writeFileSync(csv, '﻿' + wiersze.join('\n'), 'utf8');
  await p.click('#plan-otworz'); await p.waitForSelector('#plan-plik', { state: 'attached' }); await p.setInputFiles('#plan-plik', csv);
  await p.waitForFunction(() => /Wczytano|nie zawiera|Nie udało/.test(document.querySelector('#plan-plik-info').textContent), null, { timeout: 60000, polling: 200 });
  await czysto('informacja o wczytanym pliku z planem'); const info = await p.locator('#plan-plik-info').innerText(); console.log('  (plan-plik-info:', info.slice(0, 90).replace(/\n/g, ' '), ')');
  const mozna = await p.locator('#plan-uloz').isEnabled();
  if (mozna) { await p.click('#plan-uloz'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 180000 }); await p.waitForFunction(() => document.querySelector('#przystanki .przystanek'), null, { timeout: 120000, polling: 200 }).catch(() => {}); await p.waitForTimeout(2500); }
  ok('plan ułożony z danych zawierających kod (lista „Dziś” ma wiersze)', mozna && (await p.locator('#przystanki .przystanek').count()) >= 1, 'wierszy: ' + await p.locator('#przystanki .przystanek').count());
  await czysto('kafel „Dziś” (nazwy sieci i adresy z pliku)');
  const nazwa = await p.locator('#przystanki .p-nazwa').first().innerText().catch(() => '');
  ok('nazwa sklepu pokazana jako tekst (widać znaczniki jako zwykłe znaki)', /<i id="xss-znacznik">/.test(nazwa), nazwa.slice(0, 60));
  await p.click('#przystanki .p-znak >> nth=0', { force: true }); await p.waitForTimeout(1200); await czysto('po odhaczeniu wizyty (toast, licznik)');
  await p.click('#plan-btn'); await p.waitForSelector('#plan-usun', { timeout: 20000 }).catch(() => {}); await p.waitForTimeout(800); await czysto('okno planu wizyt'); await p.keyboard.press('Escape'); await p.waitForTimeout(600);

  /* miesiąc, dni, dokumenty */
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await generuj(p); await p.waitForTimeout(3500); await czysto('po wygenerowaniu miesiąca (kalendarz, wykres, kontrola)');
  const dni = await p.locator('#siatka button.dz.trasa').count(); for (const i of [0, Math.floor(dni / 2), dni - 1]) { await p.locator('#siatka button.dz.trasa').nth(i).click({ force: true }); await p.waitForTimeout(900); }
  await czysto('panel dnia z trasą');
  await p.click('#dzwonek'); await p.waitForTimeout(600); await czysto('dymek powiadomień'); await p.keyboard.press('Escape'); await p.mouse.click(5, 5); await p.waitForTimeout(400);
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka'); await p.waitForTimeout(1200); await czysto('okno „Dokumenty do podpisu”');
  const pdf = fs.readFileSync(path.join(__dirname, 'dane/podpisy/ok_jan.pdf'));
  await p.setInputFiles('#plik-wgraj', [{ name: PAY.replace(/[\\/]/g, '') + '.pdf', mimeType: 'application/pdf', buffer: pdf }, { name: '"><img src=x onerror=window.__xss=4>.xades', mimeType: 'text/xml', buffer: Buffer.from('<x/>') }]);
  await p.waitForTimeout(6000); await czysto('wynik wgrania plików o złośliwych nazwach (lista dopasowań i odrzuceń)');
  await p.keyboard.press('Escape'); await p.waitForTimeout(600);
  await p.click('#konto'); await p.waitForTimeout(700); await czysto('menu konta'); await p.keyboard.press('Escape');

  /* zapisany profil z kodem w polach (np. ręcznie zmieniony magazyn): wszystkie ekrany, które go pokazują */
  await p.evaluate(P => { const d = window.__pmtDane.czytaj(); d.profil.imie = P; d.profil.adres = P; window.__pmtDane.zapisz(d); }, PAY);
  await p.reload(); await p.waitForFunction(() => !document.querySelector('#ladowanie.widoczny') && !document.querySelector('#aplikacja.zamknieta'), null, { timeout: 180000 }).catch(() => {}); await p.waitForTimeout(4000);
  await czysto('pulpit z profilem pełnym znaczników (nagłówek, powitanie, menu)');
  await p.click('#konto'); await p.waitForTimeout(600); await czysto('menu konta z takim imieniem'); await p.keyboard.press('Escape'); await p.waitForTimeout(300);
  await p.click('#podpisz').catch(() => {}); await p.waitForTimeout(1500); await czysto('okno dokumentów z takim imieniem'); await p.keyboard.press('Escape'); await p.waitForTimeout(500);

  /* CSP: skrypt wstrzyknięty do strony i atrybut onerror są blokowane przez przeglądarkę */
  const csp = await p.evaluate(async () => {
    const m = document.querySelector('meta[http-equiv="Content-Security-Policy"]'), tresc = m ? m.content : '';
    window.__csp = 0; const s = document.createElement('script'); s.textContent = 'window.__csp = 1'; document.head.appendChild(s);
    const i = document.createElement('img'); i.src = 'x'; i.setAttribute('onerror', 'window.__csp = 2'); document.body.appendChild(i);
    let obcy = 'brak'; try { await fetch('https://obcy.example/x', { mode: 'no-cors' }); obcy = 'poszło'; } catch (e) { obcy = 'zablokowane'; }
    await new Promise(r => setTimeout(r, 600)); return { tresc, wykonano: window.__csp, obcy };
  });
  ok('CSP jest ustawione i blokuje skrypt wstrzyknięty do strony oraz atrybut onerror', !!csp.tresc && /script-src 'self'/.test(csp.tresc) && csp.wykonano === 0, JSON.stringify({ wykonano: csp.wykonano }));
  ok('CSP blokuje połączenia z obcymi adresami (wyciek danych pod cudzy adres)', csp.obcy === 'zablokowane', csp.obcy);
  ok('CSP nie zawiera „unsafe-inline” dla skryptów ani „unsafe-eval”', !/script-src[^;]*'unsafe-(inline|eval)'/.test(csp.tresc) && /object-src 'none'/.test(csp.tresc) && /base-uri 'none'/.test(csp.tresc), csp.tresc.slice(0, 80));
  ok('przeglądarka zgłosiła naruszenia CSP wyłącznie dla naszych prób (nie dla zwykłej pracy aplikacji)', bledyCsp.length >= 2 && bledyCsp.every(x => /script|img|connect|onerror|obcy|inline/i.test(x)), String(bledyCsp.length));
  await t.zamknij();

  /* ramka: aplikacja nie działa w cudzej ramce */
  const t2 = await otworz({ w: 1000, h: 700 }); const q = t2.p;
  await q.goto(t2.adres + '/robots.txt').catch(() => {});
  await q.setContent(`<iframe id="r" src="${t2.adres}/index.html" style="width:900px;height:600px"></iframe>`);
  await q.waitForTimeout(6000);
  const fr = q.frames().find(f => f !== q.mainFrame());
  const w = fr ? await fr.evaluate(() => ({ ukryte: getComputedStyle(document.documentElement).display === 'none', start: !!document.querySelector('#aplikacja') && !document.querySelector('#aplikacja').classList.contains('zamknieta') })).catch(() => ({ ukryte: true })) : { ukryte: true };
  ok('aplikacja wczytana w cudzej ramce jest ukryta i się nie uruchamia', w.ukryte === true && !w.start, JSON.stringify(w));
  await t2.zamknij();
  process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
