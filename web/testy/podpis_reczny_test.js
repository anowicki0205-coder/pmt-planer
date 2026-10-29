// Wykrywanie podpisu odręcznego na skanach (js/podpis_reczny.js) na sztucznych skanach z dane/generuj_skany.py: z podpisem i bez, z przekrzywieniem do ±1,6°, przesunięciem,
// szumem, cieniem i kompresją JPEG, a także „kartka na stole”. Wynik nie może mieć fałszywych alarmów (brak podpisu uznany za podpis) ani przeoczeń na zwykłych skanach.
// Skany powstają przy pierwszym uruchomieniu (python z pillow i numpy: PYTHON_SKANY=/tmp/phvenv/bin/python). NODE_PATH=/opt/node22/lib/node_modules node podpis_reczny_test.js
const { chromium } = require('playwright'); const { serwer } = require('./wspolne'); const fs = require('fs'), path = require('path'), cp = require('child_process');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const kat = path.join(__dirname, 'dane/skany');
  if (!fs.existsSync(path.join(kat, 'lista.json'))) { const r = cp.spawnSync(process.env.PYTHON_SKANY || 'python3', [path.join(__dirname, 'dane/generuj_skany.py')], { encoding: 'utf8' }); if (r.status) { console.log(r.stderr); process.exit(2); } }
  const lista = JSON.parse(fs.readFileSync(path.join(kat, 'lista.json'), 'utf8')), miejsca = JSON.parse(fs.readFileSync(path.join(kat, 'miejsca.json'), 'utf8'));
  const sv = await serwer({}); const b = await chromium.launch(); const p = await b.newPage(); await p.route('**/__p.html', r => r.fulfill({ contentType: 'text/html', body: '<!doctype html>' })); await p.goto(sv.adres + '/__p.html');
  const wyniki = await p.evaluate(async ([lista, miejsca]) => {
    const m = await import('/js/podpis_reczny.js'), sp = m.strefaPodpisu(miejsca), w = [];
    for (const x of lista) { const bytes = new Uint8Array(await (await fetch('/testy/dane/skany/' + x.plik)).arrayBuffer()); const st = await m.stronyZeSkanu(bytes, x.plik); const o = m.szukajPodpisu(st.strony[0], sp.strefa); w.push({ ...x, stan: o.stan, ink: o.ink, rozp: o.rozpietosc, powod: o.powod }); }
    return { w, strefa: m.strefaPodpisu(miejsca) };
  }, [lista, miejsca]);
  // PDF ze skanem (obrazy JPEG osadzone w PDF-ie, jedna strona = jeden obraz)
  if (fs.existsSync(path.join(kat, 'skan2.pdf'))) {
    const pdf = await p.evaluate(async miejsca => {
      const m = await import('/js/podpis_reczny.js'), sp = m.strefaPodpisu(miejsca), by = new Uint8Array(await (await fetch('/testy/dane/skany/skan2.pdf')).arrayBuffer()), st = await m.stronyZeSkanu(by, 'skan2.pdf');
      return { n: st.strony.length, stany: st.strony.map(s => m.szukajPodpisu(s, sp.strefa).stan), powod: st.powod };
    }, miejsca);
    ok('PDF ze skanem: z pliku wyjęte 2 strony, pierwsza z podpisem, druga bez', pdf.n === 2 && pdf.stany[0] === 'jest' && pdf.stany[1] === 'brak', JSON.stringify(pdf));
  }
  const brakPdf = await p.evaluate(async () => { const m = await import('/js/podpis_reczny.js'); const r = await m.stronyZeSkanu(new TextEncoder().encode('%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF'), 'zwykly.pdf'); return r; });
  ok('PDF bez obrazu (nie skan) — jasny powód zamiast błędu', brakPdf.strony.length === 0 && /nie zawiera skanu/.test(brakPdf.powod), brakPdf.powod);
  const zwykle = wyniki.w.filter(x => !x.stol), stol = wyniki.w.filter(x => x.stol);
  const fa = zwykle.filter(x => !x.jest && x.stan === 'jest'), przeoczone = zwykle.filter(x => x.jest && x.stan !== 'jest');
  console.log('  strefa podpisu (mm):', JSON.stringify(wyniki.strefa.strefa));
  ok(`skany z podpisem: wszystkie ${zwykle.filter(x => x.jest).length} rozpoznane`, przeoczone.length === 0, przeoczone.map(x => `${x.plik}:${x.stan}:${(x.ink * 100).toFixed(2)}%`).join(', '));
  ok(`skany bez podpisu: żaden z ${zwykle.filter(x => !x.jest).length} nie uznany za podpisany (brak fałszywych alarmów)`, fa.length === 0, fa.map(x => `${x.plik}:${(x.ink * 100).toFixed(2)}%`).join(', '));
  const inkJest = zwykle.filter(x => x.jest).map(x => x.ink), inkBez = zwykle.filter(x => !x.jest).map(x => x.ink);
  console.log(`  info: udział śladu — z podpisem min ${(Math.min(...inkJest) * 100).toFixed(2)}% / bez podpisu max ${(Math.max(...inkBez) * 100).toFixed(2)}% (próg 0,4%)`);
  const stolFa = stol.filter(x => !x.jest && x.stan === 'jest'), stolPrzeoczone = stol.filter(x => x.jest && x.stan === 'brak');
  ok('kartka na stole: brak fałszywych alarmów i przeoczeń (dozwolone „nie umiem ocenić”)', stolFa.length === 0 && stolPrzeoczone.length === 0, stol.map(x => `${x.jest ? 'z' : 'bez'}:${x.stan}`).join(' '));
  await b.close(); sv.s.close();
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
