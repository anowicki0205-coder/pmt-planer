// „Cel wyjazdu” na dokumentach: na KAŻDYM poleceniu zawsze Biedronka i Żabka plus 3–4 losowe sieci z listy (silnik/sieci_cel.txt), alfabetycznie po polsku.
// Losowanie jest powtarzalne (PESEL + miesiąc + numer polecenia). Sprawdzamy na prawdziwych PDF-ach. NODE_PATH=/opt/node22/lib/node_modules node cel_app.js
const { otworz, generuj } = require('./wspolne'); const fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
(async () => {
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'cel-'));
  const LISTA = fs.readFileSync(path.join(__dirname, '../silnik/sieci_cel.txt'), 'utf8').split(/\r?\n/).map(x => x.trim()).filter(x => x && !x.startsWith('#'));
  const klucz = (a, b) => a.localeCompare(b, 'pl');
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await generuj(p); await p.waitForTimeout(3000);
  const czytaj = () => p.evaluate(() => { const d = window.__pmtDane.czytaj(); return Object.values(d.miesiace)[0].wynik.dokumenty.map(x => x.sieci); });
  const sieci = await czytaj();
  ok('wygenerowano kilka poleceń', sieci.length >= 3, String(sieci.length));
  ok('na każdym poleceniu zawsze Biedronka i Żabka', sieci.every(s => s.includes('Biedronka') && s.includes('Żabka')));
  ok('oprócz nich 3–4 sieci z listy właściciela (razem 5–6)', sieci.every(s => s.length >= 5 && s.length <= 6 && s.every(n => LISTA.includes(n)) && new Set(s).size === s.length), JSON.stringify(sieci.map(s => s.length)));
  ok('kolejność alfabetyczna po polsku (Ż na końcu)', sieci.every(s => JSON.stringify(s) === JSON.stringify([...s].sort(klucz))), JSON.stringify(sieci[0]));
  ok('polecenia różnią się między sobą (nie ma już tych samych sieci na każdym)', new Set(sieci.map(s => s.join('|'))).size >= 2, sieci.map(s => s.join(', ')).join('  //  '));

  await p.click('#podpisz'); await p.waitForSelector('#pobierz-wsz'); await p.waitForTimeout(600);
  const [dl] = await Promise.all([p.waitForEvent('download'), p.click('#pobierz-wsz')]); const zp = path.join(tmp, 'a.zip'); await dl.saveAs(zp);
  const roz = path.join(tmp, 'roz'); cp.spawnSync('unzip', ['-o', '-q', '-d', roz, zp]);
  const pdfy = fs.readdirSync(roz).filter(f => /^delegacja_\d+_.*\.pdf$/.test(f)).sort();
  ok('w ZIP-ie są wszystkie polecenia', pdfy.length === sieci.length, pdfy.join(', '));
  pdfy.forEach((f, i) => {
    const txt = cp.spawnSync('pdftotext', ['-layout', path.join(roz, f), '-'], { encoding: 'utf8' }).stdout;
    const linia = (txt.split('\n').find(l => /projekt:/.test(l)) || '').trim(), cel = 'projekt: ' + sieci[i].join(', ');
    ok(`Polecenie ${i + 1}: „${cel}”`, linia === cel, `na dokumencie: „${linia}”`);
    ok(`Polecenie ${i + 1}: pod nim nadal stoi „cel wyjazdu - Projekt”, a lista się mieści (bez „i inne”)`, /cel wyjazdu - Projekt/.test(txt) && !/ i inne/.test(linia));
  });
  await p.keyboard.press('Escape'); await p.waitForTimeout(800);

  // powtarzalność: usunięcie dokumentów i ponowne wygenerowanie daje te same sieci
  for (let i = 0; i < 12 && !(await p.locator('#od-nowa-tak').count()); i++) { await p.click('#od-nowa', { force: true }); await p.waitForTimeout(2500); }      // przejścia (View Transitions) przechwytują kliknięcia — klikamy do skutku
  await p.waitForSelector('#od-nowa-tak'); await p.click('#od-nowa-tak');
  await p.waitForFunction(() => /Do wygenerowania/.test(document.querySelector('#status').textContent), null, { timeout: 90000, polling: 250 }); await p.waitForTimeout(2500);
  await generuj(p); await p.waitForTimeout(3000);
  const ponownie = await czytaj();
  ok('ponowne wygenerowanie daje DOKŁADNIE te same sieci na każdym poleceniu', JSON.stringify(ponownie) === JSON.stringify(sieci));
  console.log('  pliki:', tmp); console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 6))); if (t.bledy.length) kod = 1;
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
