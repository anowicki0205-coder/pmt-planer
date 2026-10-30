// Zahasłowana paczka z dokumentami (ZIP z AES-256) i gotowa wiadomość (.eml): paczkę i plik robi JavaScript (js/zipaes.js, js/poczta.js), a czyta je NIEZALEŻNA biblioteka Pythona
// (pyzipper — własna implementacja formatu WinZip AES) i standardowy parser poczty (email). Zgodność dwóch osobnych implementacji jest dowodem, że 7-Zip/WinRAR też to otworzą.
// Wymaga pyzipper: python3 -m venv /tmp/pzvenv && /tmp/pzvenv/bin/pip install pyzipper   (albo PYZ_PYTHON=<python z pyzipper>)
// Uruchom: node testy/paczka_test.js
const { execFileSync } = require('child_process'), path = require('path'), fs = require('fs'), os = require('os');
(async () => {
  const Z = await import('../js/zipaes.js'), E = await import('../js/poczta.js'); let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'paczka-')); const hex = b => Buffer.from(b).toString('hex'); const enc = t => new TextEncoder().encode(t);
  const PY = process.env.PYZ_PYTHON || ['/tmp/pzvenv/bin/python', 'python3'].find(p => { try { execFileSync(p, ['-c', 'import pyzipper'], { stdio: 'ignore' }); return true; } catch (e) { return false; } });
  if (!PY) { console.log('  BŁĄD brak pyzipper — zainstaluj: python3 -m venv /tmp/pzvenv && /tmp/pzvenv/bin/pip install pyzipper'); process.exit(1); }
  const py = (skrypt, ...arg) => execFileSync(PY, ['-I', '-c', skrypt, ...arg], { encoding: 'utf8', maxBuffer: 1 << 28 }).trim();

  /* ---- wektory testowe (RFC 3174, RFC 2202, RFC 6070) ---- */
  ok('SHA-1 (przez HMAC) zgadza się z wzorcem Node dla wiadomości o długościach wokół granic dopełnienia (0, 3, 55, 56, 63, 64, 65, 119, 120, 1000, 100000 bajtów)', (() => {
    for (const n of [0, 3, 55, 56, 63, 64, 65, 119, 120, 1000, 100000]) { const m = Buffer.alloc(n, 0x61 + (n % 7)), k = Buffer.from('klucz-' + n); if (hex(Z.hmacSha1(new Uint8Array(k), new Uint8Array(m))) !== require('crypto').createHmac('sha1', k).update(m).digest('hex')) return false; }
    return true; })());
  ok('HMAC-SHA1 z RFC 2202 (przypadek 1: klucz 20×0x0b, „Hi There”)', hex(Z.hmacSha1(new Uint8Array(20).fill(0x0b), enc('Hi There'))) === 'b617318655057264e28bc0b6fb378c8ef146be00');
  ok('HMAC-SHA1 z kluczem dłuższym niż blok (RFC 2202, przypadek 6)', hex(Z.hmacSha1(new Uint8Array(80).fill(0xaa), enc('Test Using Larger Than Block-Size Key - Hash Key First'))) === largeKey());
  function largeKey() { return require('crypto').createHmac('sha1', Buffer.alloc(80, 0xaa)).update('Test Using Larger Than Block-Size Key - Hash Key First').digest('hex'); }
  ok('PBKDF2-HMAC-SHA1 z RFC 6070 (1, 2 i 4096 iteracji)', hex(Z.pbkdf2Sha1(enc('password'), enc('salt'), 1, 20)) === '0c60c80f961f0e71f3a9b524af6012062fe037a6' && hex(Z.pbkdf2Sha1(enc('password'), enc('salt'), 2, 20)) === 'ea6c014dc72d6f8ccd1ed92ace1d41f0d8de8957' && hex(Z.pbkdf2Sha1(enc('password'), enc('salt'), 4096, 20)) === '4b007901b765489abead49d926f721d065a429c1');
  ok('PBKDF2: długość wyjścia niebędąca wielokrotnością 20 (66 bajtów) zgadza się z Node', hex(Z.pbkdf2Sha1(enc('Zażółć'), enc('sól-16-bajtow!!!'), 1000, 66)) === require('crypto').pbkdf2Sync('Zażółć', 'sól-16-bajtow!!!', 1000, 66, 'sha1').toString('hex'));

  /* ---- paczka: JavaScript → pyzipper ---- */
  const los = n => { const b = new Uint8Array(n); for (let i = 0; i < n; i += 65536) require('crypto').randomFillSync(b.subarray(i, Math.min(n, i + 65536))); return b; };
  const pliki = [{ nazwa: 'Polecenie wyjazdu 1 — Żółć.pdf', bajty: los(20000) }, { nazwa: 'pusty.txt', bajty: new Uint8Array(0) }, { nazwa: 'jeden.bin', bajty: Uint8Array.of(7) }, { nazwa: 'Rozliczenie_(2).xades', bajty: enc('<xml>ąęć ' + 'x'.repeat(4000) + '</xml>') }, { nazwa: 'Duży.pdf', bajty: los(3 * 1048576 + 5) }];
  const haslo = 'Zażółć-Gęślą#1 jaźń';
  const t0 = Date.now(), blob = Z.zipujAes(pliki, haslo), ms = Date.now() - t0, zip = Buffer.from(await blob.arrayBuffer());
  fs.writeFileSync(path.join(tmp, 'paczka.zip'), zip); pliki.forEach((p, i) => fs.writeFileSync(path.join(tmp, `p${i}.bin`), p.bajty));
  ok(`szyfrowanie 3 MB i czterech mniejszych plików trwa rozsądnie`, ms < 8000, ms + ' ms');
  const wyn = py(`
import sys, json, pyzipper
z = pyzipper.AESZipFile(sys.argv[1]); out = {'nazwy': z.namelist(), 'ok': [], 'info': []}
z.setpassword(sys.argv[2].encode('utf-8'))
for i, n in enumerate(z.namelist()):
    dane = z.read(n); orig = open(sys.argv[3] + '/p%d.bin' % i, 'rb').read(); out['ok'].append(dane == orig)
    inf = z.getinfo(n); out['info'].append([inf.compress_type, inf.flag_bits & 1, inf.file_size, inf.compress_size])
for zle in (b'zle-haslo', b'', 'Zażółć-Gęślą#1 jaźń '.encode()):
    z2 = pyzipper.AESZipFile(sys.argv[1]); z2.setpassword(zle)
    try: z2.read(z2.namelist()[0]); out.setdefault('zle', []).append('PRZESZLO')
    except RuntimeError: out.setdefault('zle', []).append('odmowa')
    except Exception as e: out.setdefault('zle', []).append('odmowa:' + type(e).__name__)
print(json.dumps(out))`, path.join(tmp, 'paczka.zip'), haslo, tmp);
  const w = JSON.parse(wyn);
  ok('pyzipper odczytuje wszystkie 5 plików z prawidłowym hasłem i zawartość zgadza się co do bajta (także pusty i 1-bajtowy)', w.ok.length === 5 && w.ok.every(Boolean), JSON.stringify(w.ok));
  ok('nazwy z polskimi znakami i myślnikiem przechodzą bez zmian', JSON.stringify(w.nazwy) === JSON.stringify(pliki.map(p => p.nazwa)), w.nazwy.join(' | '));
  ok('wpisy są zaszyfrowane (flaga), bez kompresji, a rozmiar = oryginał + 28 bajtów narzutu (sól 16, weryfikator 2, kod 10)', w.info.every(([m, f, rozm, skomp], i) => m === 0 && f === 1 && rozm === pliki[i].bajty.length && skomp === rozm + 28), JSON.stringify(w.info));
  ok('w nagłówku ZIP jest metoda 99 (AES), wersja AE-2, producent „AE”, siła 256 bitów (to rozpoznają 7-Zip i WinRAR)', zip.readUInt16LE(8) === 99 && zip.readUInt16LE(6) === 0x0801 && zip.subarray(30 + Buffer.byteLength(pliki[0].nazwa), 30 + Buffer.byteLength(pliki[0].nazwa) + 11).toString('hex') === '0199070002004145030000');
  ok('złe hasło, puste hasło i hasło ze spacją na końcu są odrzucane', JSON.stringify(w.zle.map(x => x.startsWith('odmowa'))) === '[true,true,true]', w.zle.join(','));
  /* ---- trzecia, niezależna implementacja: prawdziwy 7-Zip (tym otworzy paczkę Kierownik) — gdy jest zainstalowany ---- */
  const sz = ['7z', '7za', '7zz'].find(b => { try { execFileSync(b, ['i'], { stdio: 'ignore' }); return true; } catch (e) { return false; } });
  if (sz) {
    const roz = path.join(tmp, 'rozpakowane'); const wynik = require('child_process').spawnSync(sz, ['x', '-y', '-p' + haslo, '-o' + roz, path.join(tmp, 'paczka.zip')], { encoding: 'utf8' });
    const zgodne = pliki.every(p => { const f = path.join(roz, p.nazwa); return fs.existsSync(f) && Buffer.compare(fs.readFileSync(f), Buffer.from(p.bajty)) === 0; });
    ok('7-Zip rozpakowuje paczkę podanym hasłem: wszystkie pliki zgodne co do bajta (nazwy z polskimi znakami też)', wynik.status === 0 && zgodne, (wynik.stdout.match(/Everything is Ok|ERROR[^\n]*|Wrong password[^\n]*/) || [''])[0]);
    const zle = require('child_process').spawnSync(sz, ['t', '-pzle-haslo', path.join(tmp, 'paczka.zip')], { encoding: 'utf8' });
    ok('7-Zip przy złym haśle odmawia (kod wyjścia ≠ 0)', zle.status !== 0, 'kod ' + zle.status);
  } else console.log('  UWAGA brak 7-Zip w systemie — pominięto sprawdzenie programem 7z (apt-get install p7zip-full)');
  ok('w pliku ZIP nie ma jawnej zawartości (znacznik „<xml>” ani tekst z pliku XAdES)', !zip.includes(Buffer.from('<xml>')) && !zip.includes(Buffer.from('xxxxxxxxxxxxxxxx')));
  ok('te same dane dwa razy dają różne szyfrogramy (losowa sól na plik)', (() => { const a = Z.zaszyfrujPlikAes('h', new Uint8Array(100)), b = Z.zaszyfrujPlikAes('h', new Uint8Array(100)); return hex(a.subarray(0, 16)) !== hex(b.subarray(0, 16)) && hex(a.subarray(18)) !== hex(b.subarray(18)); })());
  const zmieniony = Buffer.from(zip); { const i = zmieniony.indexOf(Buffer.from('Polecenie wyjazdu')) + 80; zmieniony[i] ^= 1; }
  fs.writeFileSync(path.join(tmp, 'zmieniony.zip'), zmieniony);
  ok('zmiana jednego bajtu szyfrogramu jest wykrywana (kod uwierzytelniający), a nie daje śmieci', py(`
import sys, pyzipper
z = pyzipper.AESZipFile(sys.argv[1]); z.setpassword(sys.argv[2].encode())
try: z.read(z.namelist()[0]); print('PRZESZLO')
except Exception as e: print('odmowa')`, path.join(tmp, 'zmieniony.zip'), haslo) === 'odmowa');
  ok('brak hasła → wyjątek (paczka nigdy nie powstaje jawna)', (() => { try { Z.zipujAes(pliki, ''); return false; } catch (e) { return true; } })());

  /* ---- wiadomość .eml ---- */
  const temat = '[PMT] Delegacje — Żaneta Gęśla-Łódzka — Wrzesień 2026 ' + 'x'.repeat(60), tresc = 'Dzień dobry,\n\nw załączeniu zahasłowana paczka (ZIP) z podpisanymi dokumentami za Wrzesień 2026 (5 plików). Hasło zostało uzgodnione osobno.\n\nPozdrawiam\nŻaneta Gęśla-Łódzka';
  const eml = E.zbudujEml({ adres: 'kierownik@example.com', temat, tresc, zalacznik: { nazwa: 'Dokumenty Żaneta_Gęśla Wrzesień 2026 (1).zip', bajty: new Uint8Array(zip), typ: 'application/zip' } });
  fs.writeFileSync(path.join(tmp, 'wiadomosc.eml'), eml);
  const wi = JSON.parse(py(`
import sys, json, email, email.policy, pyzipper, io
raw = open(sys.argv[1], 'rb').read(); m = email.message_from_bytes(raw, policy=email.policy.default)
cz = list(m.iter_attachments()); tr = m.get_body(preferencelist=('plain',))
z = pyzipper.AESZipFile(io.BytesIO(cz[0].get_content())); z.setpassword(sys.argv[2].encode('utf-8'))
print(json.dumps({'x': m['X-Unsent'], 'to': m['To'], 'temat': str(m['Subject']), 'tresc': tr.get_content(), 'zal': len(cz), 'nazwa': cz[0].get_filename(), 'typ': cz[0].get_content_type(),
  'rozmiar': len(cz[0].get_content()), 'plik0': z.read(z.namelist()[1]) == b'' , 'plik4': z.read(z.namelist()[4]) == open(sys.argv[3] + '/p4.bin', 'rb').read(),
  'crlf': raw.count(b'\\r\\n') == raw.count(b'\\n'), 'maxlinia': max(len(l) for l in raw.split(b'\\r\\n')), 'ascii': all(b < 128 for b in raw), 'bcc': m['Bcc']}))`, path.join(tmp, 'wiadomosc.eml'), haslo, tmp));
  ok('parser poczty Pythona widzi nagłówek „X-Unsent: 1” (Outlook otworzy wiadomość jako szkic do wysłania), adresata i jeden załącznik', wi.x === '1' && wi.to === 'kierownik@example.com' && wi.zal === 1 && wi.typ === 'application/zip', JSON.stringify([wi.x, wi.to, wi.zal, wi.typ]));
  ok('temat z polskimi znakami, półpauzą i długi (po zawinięciu) wraca bez zmian', wi.temat === temat, wi.temat);
  ok('treść wraca bez zmian (UTF-8, polskie znaki, akapity)', wi.tresc.replace(/\r\n/g, '\n').trimEnd() === tresc, JSON.stringify(wi.tresc).slice(0, 80));
  ok('nazwa załącznika jest bezpieczna (ASCII, bez spacji i nawiasów), a po otwarciu wiadomości paczka nadal się odszyfrowuje tym samym hasłem', wi.nazwa === 'Dokumenty_Zaneta_Gesla_Wrzesien_2026_1_.zip' && wi.plik0 && wi.plik4, wi.nazwa);
  ok('plik jest czystym ASCII, wiersze ≤ 998 znaków, wszystkie końce wierszy to CRLF', wi.ascii && wi.maxlinia <= 998 && wi.crlf, 'najdłuższy wiersz ' + wi.maxlinia);
  const wstrzykniecie = E.zbudujEml({ adres: 'a@b.pl\r\nBcc: obcy@example.com', temat: 'T\r\nBcc: obcy2@example.com', tresc: 'x', zalacznik: { nazwa: 'a.zip', bajty: Uint8Array.of(1), typ: 'application/zip' } });
  const naglowki = Buffer.from(wstrzykniecie).toString('latin1').split('\r\n\r\n')[0];
  ok('wstrzyknięcie nagłówków (CR/LF w adresie i temacie) nie tworzy dodatkowego nagłówka Bcc', !/^Bcc:/im.test(naglowki), naglowki.split('\r\n').filter(l => /^(To|Subject):/.test(l)).join(' | '));
  ok('naglowekTekst: tekst ASCII zostaje, a każde słowo kodowane mieści się w 76 znakach', E.naglowekTekst('Prosty temat') === 'Prosty temat' && E.naglowekTekst('Żółć '.repeat(30)).split('\r\n').every(l => l.length <= 76));
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(kod ? 'KONIEC kod=1' : 'KONIEC kod=0'); process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
