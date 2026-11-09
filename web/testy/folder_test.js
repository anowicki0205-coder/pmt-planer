// Folder „delegacje” (js/folder.js): który folder jest folderem głównym, podfoldery miesięcy, zapis i lista plików — na udawanych uchwytach (bez przeglądarki).
// Uruchom: node folder_test.js
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const F = await import('../js/folder.js');
  /* prosty udawany folder: getDirectoryHandle(nazwa, {create}) i entries(), jak w File System Access API */
  const folder = nazwa => { const dzieci = new Map(); return { kind: 'directory', name: nazwa, dzieci, async getDirectoryHandle(n, o = {}) { if (!dzieci.has(n)) { if (!o.create) throw new DOMException('nie ma', 'NotFoundError'); dzieci.set(n, folder(n)); } return dzieci.get(n); }, async *entries() { yield* dzieci.entries(); } }; };

  ok('nazwa folderu głównego to „delegacje”', F.NAZWA_FOLDERU === 'delegacje');
  const pulpit = folder('PMT'), k1 = await F.korzenDelegacji(pulpit);
  ok('wskazany folder o innej nazwie (np. „PMT”): „delegacje” powstaje w jego środku', k1.name === 'delegacje' && k1 !== pulpit && pulpit.dzieci.has('delegacje'));
  const k2 = await F.korzenDelegacji(pulpit);
  ok('drugi raz ten sam folder „delegacje” (nie powstaje drugi)', k2 === k1 && pulpit.dzieci.size === 1);
  const sam = folder('delegacje'), k3 = await F.korzenDelegacji(sam);
  ok('wskazany folder już nazywa się „delegacje”: używany bezpośrednio, bez zagnieżdżania „delegacje\\delegacje”', k3 === sam && sam.dzieci.size === 0);
  const duze = folder('Delegacje'), k4 = await F.korzenDelegacji(duze);
  ok('wielkość liter w nazwie nie ma znaczenia („Delegacje”)', k4 === duze);
  const m = await F.podfolder(k1, 'wrzesień 2026'), m2 = await F.podfolder(k1, 'wrzesień 2026'), m3 = await F.podfolder(k1, 'październik 2026');
  ok('podfoldery miesięcy powstają w „delegacje” z polską nazwą miesiąca i rokiem; ten sam miesiąc nie tworzy drugiego folderu', m === m2 && m3 !== m && [...k1.dzieci.keys()].join('|') === 'wrzesień 2026|październik 2026');
  ok('odcisk pliku: nazwa|rozmiar|czas zmiany', F.odcisk({ name: 'a.pdf', size: 5, lastModified: 7 }) === 'a.pdf|5|7');
  await t_wypisz();
  async function t_wypisz() {
    const plik = (n, rozm) => ({ kind: 'file', name: n, async getFile() { return { name: n, size: rozm, lastModified: 100 }; } });
    const d = folder('x'); d.dzieci.set('delegacja_01.pdf', plik('delegacja_01.pdf', 10)); d.dzieci.set('podpis.xades', plik('podpis.xades', 5)); d.dzieci.set('~$tymczasowy.pdf', plik('~$tymczasowy.pdf', 1));
    d.dzieci.set('.ukryty.pdf', plik('.ukryty.pdf', 1)); d.dzieci.set('film.mp4', plik('film.mp4', 9)); d.dzieci.set('pobieranie.crdownload', plik('pobieranie.crdownload', 3)); d.dzieci.set('podfolder', folder('podfolder'));
    const l = await F.wypisz(d);
    ok('lista plików: tylko te, które aplikacja umie wczytać (PDF, .xades…); tymczasowe, ukryte, filmy i podfoldery pominięte', l.map(x => x.nazwa).sort().join('|') === 'delegacja_01.pdf|podpis.xades', l.map(x => x.nazwa).join('|'));
  }
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
