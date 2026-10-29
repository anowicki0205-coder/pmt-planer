// Wiele wywołań silnika NARAZ (dni miesiąca, sprawdzanie adresu, maksimum kwoty) nie może mieszać argumentów:
// dawniej wspólna zmienna w workerze dawała sporadyczny „KeyError: 'rok'” i miesiąc bez dni roboczych.
// NODE_PATH=/opt/node22/lib/node_modules node wspolbieznosc_app.js
const { otworz } = require('./wspolne');
(async () => {
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 }); await p.waitForTimeout(3000);
  const w = await p.evaluate(async () => {
    const { Silnik } = await import('/js/silnik.js'); const s = new Silnik(); await s.start();
    const zadania = [];
    for (let i = 0; i < 24; i++) {
      const mies = 1 + (i % 12);
      zadania.push(s.dni({ rok: 2026, miesiac: mies, tryb: i % 2 ? 'wieczory' : 'tydzien', wolne: [] }).then(r => ({ rodzaj: 'dni', mies, n: r.dni.length, ok: r.dni.length > 15 && r.dni.every(d => Number(d.slice(5, 7)) === mies) })));
      zadania.push(s.adres({ adres: 'ul. Testowa ' + (1 + i) + ', 00-001 Warszawa' }).then(r => ({ rodzaj: 'adres', ok: r.ok === true && /Warszawa/.test(r.adres_caly) })));
      zadania.push(s.maks({ rok: 2026, miesiac: mies, tryb: 'tydzien', silnik_powyzej_900: true, kwota: 1500, wolne: [] }).then(r => ({ rodzaj: 'maks', ok: r.maks > 1000 && r.dni > 15 })));
    }
    const wyniki = await Promise.allSettled(zadania);
    return wyniki.map(x => x.status === 'fulfilled' ? x.value : { rodzaj: 'blad', ok: false, blad: String(x.reason && x.reason.message || x.reason) });
  });
  const zle = w.filter(x => !x.ok);
  ok(`72 wywołania naraz (dni, adres, maks): wszystkie dostają własne argumenty i poprawne wyniki`, w.length === 72 && zle.length === 0, zle.length ? JSON.stringify(zle.slice(0, 3)) : `${w.length} poprawnych`);
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 4))); if (t.bledy.length) kod = 1;
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
