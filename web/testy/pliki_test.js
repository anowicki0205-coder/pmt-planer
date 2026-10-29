// Jednostkowy test js/pliki.js: ZIP („Pobierz wszystkie”), scalanie PDF-ów do wydruku i dopasowanie wgranych plików do dokumentów.
// Wymaga: Node 22, poppler (pdfinfo, pdftotext), unzip. Uruchom: node pliki_test.js
const fs = require('fs'), path = require('path'), os = require('os'), cp = require('child_process');
(async () => {
  const { zipuj, scalPdf, dopasujPliki, normalizujNazwe, zawieraOryginal, crc32, rozpakujZip } = await import('../js/pliki.js');
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const kat = path.join(__dirname, 'dane/pdf'), nazwy = ['polecenie_1.pdf', 'polecenie_2.pdf', 'rozliczenie.pdf'];
  const bajty = nazwy.map(n => new Uint8Array(fs.readFileSync(path.join(kat, n))));
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'pliki-'));
  const uruchom = (cmd, args) => cp.spawnSync(cmd, args, { encoding: 'utf8' });

  // ---- ZIP ----
  ok('crc32 zgodne ze znaną wartością', crc32(new TextEncoder().encode('123456789')) === 0xCBF43926);
  const zip = zipuj([{ nazwa: 'Polecenie_1_Łódź.pdf', bajty: bajty[0] }, { nazwa: 'Rozliczenie.pdf', bajty: bajty[2] }]);
  const zp = path.join(tmp, 'a.zip'); fs.writeFileSync(zp, Buffer.from(await zip.arrayBuffer()));
  const t = uruchom('unzip', ['-t', zp]); ok('unzip -t: archiwum poprawne', t.status === 0 && /No errors detected/.test(t.stdout), (t.stdout + t.stderr).trim().split('\n').slice(-2).join(' | '));
  const roz = path.join(tmp, 'rozpakowane'); uruchom('unzip', ['-o', '-d', roz, zp]);
  ok('po rozpakowaniu pliki są bajt w bajt takie same', fs.readFileSync(path.join(roz, 'Rozliczenie.pdf')).equals(Buffer.from(bajty[2])));
  const py = uruchom('python3', ['-c', 'import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); print(z.namelist())', zp]); ok('nazwy z polskimi znakami w UTF-8', /Łódź/.test(py.stdout), py.stdout.trim());


  // ---- odczyt ZIP-a (np. paczka podpisanych plików z gov.pl) ----
  const wlasny = new Uint8Array(await zip.arrayBuffer()), rozp = await rozpakujZip(wlasny);
  ok('rozpakujZip: własny ZIP (bez kompresji) wraca bajt w bajt', rozp.length === 2 && rozp[0].nazwa === 'Polecenie_1_Łódź.pdf' && Buffer.from(rozp[0].bajty).equals(Buffer.from(bajty[0])) && Buffer.from(rozp[1].bajty).equals(Buffer.from(bajty[2])), rozp.map(x => x.nazwa).join(', '));
  const zd = path.join(tmp, 'deflate.zip');
  uruchom('python3', ['-c', 'import zipfile,sys; z=zipfile.ZipFile(sys.argv[1],"w",zipfile.ZIP_DEFLATED); [z.write(f, "podpisane/"+f.split("/")[-1]) for f in sys.argv[2:]]; z.writestr("__MACOSX/._x","x"); z.writestr(".ukryty","x"); z.writestr("katalog/","")', zd, path.join(kat, nazwy[0]), path.join(kat, nazwy[1])]);
  const rd = await rozpakujZip(new Uint8Array(fs.readFileSync(zd)));
  ok('rozpakujZip: ZIP z kompresją deflate (jak z innych programów), podkatalogi spłaszczone, śmieci pominięte', rd.length === 2 && rd[0].nazwa === 'polecenie_1.pdf' && Buffer.from(rd[1].bajty).equals(Buffer.from(bajty[1])), rd.map(x => x.nazwa).join(', '));
  let bladZip = ''; try { await rozpakujZip(new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])); } catch (e) { bladZip = e.message; }
  ok('rozpakujZip: plik, który nie jest ZIP-em, daje czytelny błąd', /nie jest archiwum ZIP/.test(bladZip), bladZip);

  // ---- scalanie PDF ----
  const scalony = scalPdf(bajty), sp = path.join(tmp, 'scalony.pdf'); fs.writeFileSync(sp, Buffer.from(scalony));
  const info = uruchom('pdfinfo', [sp]);
  ok('pdfinfo: 5 stron (2 + 2 + 1), bez błędów składni', /Pages:\s+5/.test(info.stdout) && !/Syntax Error|Error/.test(info.stderr), (info.stderr || '').trim().slice(0, 160));
  ok('pdfinfo: format A4 zachowany (MediaBox dziedziczony z drzewa stron)', /Page size:\s+595\.\d+ x 841\.\d+/.test(info.stdout), (info.stdout.match(/Page size:.*/) || [''])[0]);
  const tekst = uruchom('pdftotext', ['-layout', sp, '-']).stdout;
  ok('pdftotext: tytuły wszystkich trzech dokumentów w kolejności', (() => { const a = tekst.indexOf('Polecenie 1'), b = tekst.indexOf('Polecenie 2'), c = tekst.indexOf('Rozliczenie'); return a >= 0 && b > a && c > b; })());
  ok('pdftotext: polskie znaki i napisy ze wszystkich stron', /Łódź, Żyrardów/.test(tekst) && /strona 2 z 2/.test(tekst) && /3 684,30 zł/.test(tekst));
  const scalPonownie = scalPdf([scalony, bajty[2]]), sp2 = path.join(tmp, 'scalony2.pdf'); fs.writeFileSync(sp2, Buffer.from(scalPonownie));
  ok('scalony plik można scalić dalej (6 stron)', /Pages:\s+6/.test(uruchom('pdfinfo', [sp2]).stdout));
  let blad = null; try { scalPdf([new Uint8Array([1, 2, 3])]); } catch (e) { blad = e; } ok('śmieci zamiast PDF → czytelny wyjątek', !!blad, blad && blad.message);

  // ---- dopasowanie ----
  ok('normalizacja nazw: ogonki, dopiski i rozszerzenia znikają', normalizujNazwe('Polecenie_1_Łukasz_Żółć_podpisany.pdf') === 'polecenie 1 lukasz zolc' && normalizujNazwe('x.pdf.xades') === 'x', normalizujNazwe('Polecenie_1_Łukasz_Żółć_podpisany.pdf'));
  // „podpisany” PDF = oryginał + dopisany blok (tak robi podpis PAdES)
  const podpisany = i => { const d = new Uint8Array(bajty[i].length + 300); d.set(bajty[i]); d.set(new TextEncoder().encode('\n%podpis\n/ByteRange [0 1 2 3]\n'), bajty[i].length); return d; };
  ok('zawieraOryginal: podpisany PDF tak, cudzy PDF nie', zawieraOryginal(podpisany(0), bajty[0]) && !zawieraOryginal(podpisany(1), bajty[0]) && !zawieraOryginal(bajty[0].subarray(0, 100), bajty[0]));
  const dok = [{ i: 0, nazwa: 'Polecenie_1_Jan_wrzesien_2026.pdf', tytul: 'Polecenie 1', wolny: true, bajty: async () => bajty[0] }, { i: 1, nazwa: 'Polecenie_2_Jan_wrzesien_2026.pdf', tytul: 'Polecenie 2', wolny: true, bajty: async () => bajty[1] },
    { i: 2, nazwa: 'Rozliczenie_Jan_wrzesien_2026.pdf', tytul: 'Rozliczenie', wolny: true, bajty: async () => bajty[2] }];
  const F = (name, b) => ({ name, _b: b });
  const odczyt = async f => f._b;
  // a) po zawartości — nazwy bez żadnego związku z dokumentami
  let w = await dopasujPliki([F('losowa_nazwa_1.pdf', podpisany(2)), F('inna.pdf', podpisany(0))], dok, odczyt);
  ok('po zawartości: pliki o przypadkowych nazwach trafiają do właściwych dokumentów', w[0].i === 2 && w[0].jak === 'tresc' && w[1].i === 0 && w[1].jak === 'tresc', JSON.stringify(w.map(x => [x.plik.name, x.i, x.jak])));
  // b) po nazwie — skany (JPG) nie mają oryginału w środku
  w = await dopasujPliki([F('IMG_Polecenie 2.jpg', new Uint8Array(10)), F('Rozliczenie.jpg', new Uint8Array(10)), F('skan 1.png', new Uint8Array(10))], dok, odczyt);
  ok('po nazwie: „Polecenie 2”, „Rozliczenie”, „skan 1”', w[0].i === 1 && w[1].i === 2 && w[2].i === 0 && w.every(x => x.jak === 'nazwa'), JSON.stringify(w.map(x => [x.plik.name, x.i, x.jak])));
  w = await dopasujPliki([F('delegacja_02_Jan_Testowy_wrzesien_2026r_podpisany.pdf', new Uint8Array(10)), F('rozliczenie_wydatków_Jan_Testowy.jpg', new Uint8Array(10))], dok, odczyt);
  ok('po nazwie z silnika: „delegacja_02…” → Polecenie 2, „rozliczenie_wydatków…” → Rozliczenie', w[0].i === 1 && w[1].i === 2, JSON.stringify(w.map(x => [x.i, x.jak])));
  // c) według kolejności — nazwy z aparatu
  w = await dopasujPliki([F('IMG_0003.jpg', new Uint8Array(10)), F('IMG_0001.jpg', new Uint8Array(10)), F('IMG_0002.jpg', new Uint8Array(10))], dok, odczyt);
  ok('według kolejności: zdjęcia z aparatu sortowane naturalnie → dokumenty po kolei', w.find(x => x.plik.name === 'IMG_0001.jpg').i === 0 && w.find(x => x.plik.name === 'IMG_0002.jpg').i === 1 && w.find(x => x.plik.name === 'IMG_0003.jpg').i === 2 && w.every(x => x.jak === 'kolejnosc'));
  // d) już podpisane dokumenty nie są zajmowane przez dopasowanie według kolejności; nadmiar plików zostaje bez dokumentu
  const dok2 = dok.map(d => ({ ...d, wolny: d.i !== 0 }));
  w = await dopasujPliki([F('a.jpg', new Uint8Array(10)), F('b.jpg', new Uint8Array(10)), F('c.jpg', new Uint8Array(10))], dok2, odczyt);
  ok('kolejność omija dokumenty już podpisane, a nadmiar plików czeka na ręczny wybór', w[0].i === 1 && w[1].i === 2 && w[2].i === null, JSON.stringify(w.map(x => x.i)));
  // e) dwa pliki do jednego dokumentu (podpisany PDF i jego .xades)
  w = await dopasujPliki([F('Polecenie_1_Jan_wrzesien_2026_podpisany.pdf', podpisany(0)), F('Polecenie_1_Jan_wrzesien_2026.pdf.xades', new Uint8Array(10))], dok, odczyt);
  ok('podpisany PDF i jego .xades trafiają do TEGO SAMEGO dokumentu', w[0].i === 0 && w[1].i === 0, JSON.stringify(w.map(x => [x.i, x.jak])));
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
