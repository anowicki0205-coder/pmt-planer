// Service worker (narzedzia/sw.szablon.js → sw.js) na kopii strony w katalogu tymczasowym: aktualizacja pobiera tylko zmienione pliki (niezmienione kopiuje
// ze starej pamięci, bez ponownych 15 MB Pyodide), zerwane pobieranie przerywa instalację i zostawia poprzednią wersję z kompletem plików,
// a kod aplikacji idzie z pamięci bieżącej wersji (bez mieszania modułów z dwóch wydań).
// NODE_PATH=/opt/node22/lib/node_modules node sw_instalacja_app.js
const fs = require('fs'), path = require('path'), os = require('os'), { execFileSync } = require('child_process');
const ZRODLO = path.resolve(__dirname, '..'), KOPIA = fs.mkdtempSync(path.join(os.tmpdir(), 'pmt-sw-'));
for (const n of fs.readdirSync(ZRODLO)) if (n !== 'testy') fs.cpSync(path.join(ZRODLO, n), path.join(KOPIA, n), { recursive: true });      // pełna kopia (z vendor/, ok. 16 MB): zbuduj_sw.py nie wchodzi w dowiązania
const zbuduj = () => execFileSync('python3', [path.join(KOPIA, 'narzedzia', 'zbuduj_sw.py')]).toString().trim();
const dopisz = (plik, tekst) => fs.appendFileSync(path.join(KOPIA, plik), '\n// ' + tekst + '\n');
zbuduj();
process.env.PMT_KORZEN = KOPIA;
const { otworz } = require('./wspolne');
(async () => {
  const dziennik = [], zepsute = [];
  const t = await otworz({ w: 1200, h: 800, opcjeSerwera: { dziennik, zepsute } }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const wersjaSw = () => /const WERSJA = '([0-9a-f]+)'/.exec(fs.readFileSync(path.join(KOPIA, 'sw.js'), 'utf8'))[1];
  const pamieci = () => p.evaluate(async () => (await caches.keys()).filter(k => k.startsWith('pmt-web-')).sort());
  const aktywna = () => p.evaluate(async () => { const r = await navigator.serviceWorker.getRegistration(); return r && r.active ? r.active.state : ''; });
  /** wymusza sprawdzenie aktualizacji i czeka, aż instalacja się skończy (aktywacja albo odrzucenie) */
  const aktualizuj = () => p.evaluate(async () => {
    const r = await navigator.serviceWorker.getRegistration(); await r.update().catch(() => {});
    const w = r.installing || r.waiting; if (!w) return 'bez-zmian';
    return new Promise(ok => { const f = () => { if (w.state === 'activated' || w.state === 'redundant') ok(w.state); }; w.addEventListener('statechange', f); f(); setTimeout(() => ok('czas:' + w.state), 120000); });
  });
  await p.goto(t.adres + '/__pusta');      // lekka strona (404) z tego samego źródła: sam service worker, bez uruchamiania aplikacji i silnika
  await p.evaluate(() => navigator.serviceWorker.register('sw.js'));
  await p.waitForFunction(() => navigator.serviceWorker && navigator.serviceWorker.controller, null, { timeout: 120000 });
  await p.waitForFunction(async () => { const r = await navigator.serviceWorker.getRegistration(); return r && r.active && r.active.state === 'activated'; }, null, { timeout: 120000, polling: 300 });
  const v1 = wersjaSw();
  ok('pierwsza instalacja: pamięć wersji 1 z mapą skrótów', (await pamieci()).includes('pmt-web-' + v1) && await p.evaluate(async v => !!(await (await caches.open('pmt-web-' + v)).match('./__skroty.json')), v1));

  /* 1. nowe wydanie zmienia jeden moduł: pobierany jest tylko on (i sw.js), Pyodide i reszta są kopiowane */
  dopisz('js/pomoc.js', 'wydanie-2'); zbuduj(); const v2 = wersjaSw(); dziennik.length = 0;
  const s2 = await aktualizuj();
  const pobrane = [...new Set(dziennik)];
  ok('aktualizacja się zainstalowała i aktywowała', s2 === 'activated' && (await pamieci()).join() === 'pmt-web-' + v2, s2 + ' ' + JSON.stringify(await pamieci()));
  ok('pobrany został zmieniony plik, a niezmienione (Pyodide, czcionki, inne moduły) nie', pobrane.includes('/js/pomoc.js') && !pobrane.some(u => /vendor\/|\/js\/aplikacja\.js|\/css\//.test(u)), JSON.stringify(pobrane));
  ok('nowa pamięć ma komplet plików (także skopiowany pyodide.asm.wasm)', await p.evaluate(async v => { const c = await caches.open('pmt-web-' + v); return !!(await c.match('./vendor/pyodide/pyodide.asm.wasm')) && /wydanie-2/.test(await (await c.match('./js/pomoc.js')).text()); }, v2));

  /* 2. kod z pamięci bieżącej wersji: plik zmieniony na serwerze bez nowego wydania nie trafia do strony */
  dopisz('js/pomoc.js', 'zmiana-bez-wydania');
  const tresc = await p.evaluate(async () => (await fetch('js/pomoc.js')).text());
  ok('moduł idzie z pamięci tej wersji, nie z sieci (bez mieszania wydań)', /wydanie-2/.test(tresc) && !/zmiana-bez-wydania/.test(tresc));

  /* 3. zerwane pobieranie zmienionego pliku: instalacja przerwana, poprzednia wersja zostaje cała */
  dopisz('js/zipaes.js', 'wydanie-3'); zbuduj(); const v3 = wersjaSw(); zepsute.push('/js/zipaes.js');
  const s3 = await aktualizuj();
  ok('instalacja z brakującym plikiem nie przechodzi', s3 === 'redundant', s3);
  ok('poprzednia wersja dalej działa i ma komplet plików', await aktywna() === 'activated' && (await pamieci()).includes('pmt-web-' + v2) && await p.evaluate(async v => { const c = await caches.open('pmt-web-' + v); return !!(await c.match('./vendor/pyodide/pyodide.asm.wasm')) && !!(await c.match('./js/zipaes.js')); }, v2), JSON.stringify(await pamieci()));
  ok('przerwana instalacja nie zostawiła działającej wersji 3', !(await p.evaluate(async v => !!(await (await caches.open('pmt-web-' + v)).match('./__skroty.json')), v3)));
  zepsute.length = 0;
  const s4 = await aktualizuj();
  ok('gdy plik jest znowu dostępny, wydanie 3 instaluje się normalnie', s4 === 'activated' && (await pamieci()).join() === 'pmt-web-' + v3, s4 + ' ' + JSON.stringify(await pamieci()));
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.filter(b => !/Failed to load resource|net::ERR/.test(b)).slice(0, 4)));
  await t.zamknij(); fs.rmSync(KOPIA, { recursive: true, force: true });
  process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); try { fs.rmSync(KOPIA, { recursive: true, force: true }); } catch (x) {} process.exit(2); });
