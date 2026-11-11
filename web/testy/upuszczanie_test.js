// Jednostkowy test js/upuszczanie.js: odczyt upuszczonych plików i FOLDERÓW (wpisy FileSystemEntry udawane obiektami) — przechodzenie w głąb, partie readEntries, odsiew nieobsługiwanych plików z wnętrza folderu,
// plik upuszczony wprost przechodzi zawsze, limit i głębokość. Uruchom: node upuszczanie_test.js
(async () => {
  const { przejdzWpisy, wpisyZUpuszczenia, obslugiwanyPlik } = await import('../js/upuszczanie.js');
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const plik = (nazwa, tresc = 'x') => new File([tresc], nazwa);
  const wpisPliku = nazwa => ({ isFile: true, isDirectory: false, name: nazwa, file: ok => ok(plik(nazwa)) });
  const wpisFolderu = (nazwa, dzieci, naPartie = 2) => ({ isFile: false, isDirectory: true, name: nazwa, createReader: () => { let i = 0; return { readEntries: (ok) => { const p = dzieci.slice(i, i + naPartie); i += naPartie; ok(p); } }; } });
  const nazwy = r => r.pliki.map(x => x.plik.name + (x.zFolderu ? '*' : ''));

  ok('rozszerzenia: PDF, .xades, ZIP, skany i zdjęcia są obsługiwane; .docx, .exe i .txt nie', ['a.pdf', 'A.PDF', 'b.xades', 'c.zip', 'd.jpg', 'e.HEIC', 'f.png'].every(obslugiwanyPlik) && !['g.docx', 'h.exe', 'i.txt', 'pdf'].some(obslugiwanyPlik));

  let r = await przejdzWpisy([wpisPliku('a.pdf'), wpisPliku('notatki.txt')]);
  ok('plik upuszczony wprost przechodzi zawsze (także nieobsługiwany — dostanie powód w zwykłym wgrywaniu)', JSON.stringify(nazwy(r)) === '["a.pdf","notatki.txt"]', JSON.stringify(nazwy(r)));

  r = await przejdzWpisy([wpisFolderu('Pobrane', [wpisPliku('a.pdf'), wpisPliku('b.docx'), wpisPliku('c.jpg'), wpisPliku('.ukryty.pdf'), wpisPliku('d.xades')])]);
  ok('z wnętrza upuszczonego folderu biorę tylko obsługiwane pliki, bez ukrytych (a.pdf, c.jpg, d.xades), i oznaczam je jako „z folderu” — czytanie partiami po 2 nie gubi plików', JSON.stringify(nazwy(r)) === '["a.pdf*","c.jpg*","d.xades*"]', JSON.stringify(nazwy(r)));

  r = await przejdzWpisy([wpisFolderu('A', [wpisFolderu('B', [wpisFolderu('C', [wpisFolderu('D', [wpisFolderu('E', [wpisPliku('za_gleboko.pdf')]), wpisPliku('d.pdf')]), wpisPliku('c.pdf')]), wpisPliku('b.pdf')]), wpisPliku('a.pdf')])]);
  ok('foldery w folderach: przechodzę do 4 poziomów w głąb (głębsze pomijam)', JSON.stringify(nazwy(r).sort()) === '["a.pdf*","b.pdf*","c.pdf*","d.pdf*"]', JSON.stringify(nazwy(r)));

  r = await przejdzWpisy([wpisFolderu('Duzy', Array.from({ length: 50 }, (_, i) => wpisPliku(`p${i}.pdf`)))], { limit: 20 });
  ok('limit plików: po przekroczeniu zatrzymuję się i zgłaszam, że było więcej', r.pliki.length === 20 && r.obciete === true, `${r.pliki.length} ${r.obciete}`);

  const zepsuty = { isFile: true, isDirectory: false, name: 'zniknal.pdf', file: (ok, blad) => blad(new Error('NotFound')) };
  r = await przejdzWpisy([wpisFolderu('F', [zepsuty, wpisPliku('dobry.pdf')]), { isFile: false, isDirectory: true, name: 'Bez dostepu', createReader: () => ({ readEntries: (ok, blad) => blad(new Error('Security')) }) }]);
  ok('plik, który zniknął w trakcie odczytu, i folder bez dostępu nie przerywają reszty', JSON.stringify(nazwy(r)) === '["dobry.pdf*"]', JSON.stringify(nazwy(r)));

  const wpis = wpisPliku('z_wpisu.pdf'), zwykly = plik('zwykly.pdf');
  const dt1 = { items: [{ kind: 'file', webkitGetAsEntry: () => wpis, getAsFile: () => zwykly }, { kind: 'string' }] };
  const dt2 = { items: [{ kind: 'file', webkitGetAsEntry: () => null, getAsFile: () => zwykly }] };
  const dt3 = { files: [plik('a.pdf'), plik('b.pdf')] };
  ok('z zdarzenia drop: wpis (gdy jest), inaczej zwykły plik, inaczej lista files — i pozycje inne niż pliki są pomijane', wpisyZUpuszczenia(dt1)[0] === wpis && wpisyZUpuszczenia(dt1).length === 1 && wpisyZUpuszczenia(dt2)[0] === zwykly && wpisyZUpuszczenia(dt3).length === 2 && wpisyZUpuszczenia(null).length === 0);
  r = await przejdzWpisy(wpisyZUpuszczenia(dt3));
  ok('zdarzenie z samą listą files (starsza przeglądarka, test) też się przechodzi', JSON.stringify(nazwy(r)) === '["a.pdf","b.pdf"]');
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
