// Przeniesienie danych z programu na komputerze do aplikacji web: plik robi Python (pmt_przeniesienie.py, ten sam kod co w programie), czyta go JavaScript (js/przeniesienie.js) —
// dwa niezależne zapisy tego samego szyfru i podpisu muszą się zgadzać. Złe konto/hasło, zmieniony plik i śmieci na wejściu nie dają danych; dane z pliku są oczyszczane.
// Uruchom: node testy/przeniesienie_test.js
const { execFileSync } = require('child_process'), path = require('path'), fs = require('fs'), os = require('os');
(async () => {
  const P = await import('../js/przeniesienie.js'); let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const korzen = path.resolve(__dirname, '..', '..'), tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'przen-'));
  const py = (skrypt, wejscie = '', ...arg) => execFileSync('python3', ['-I', '-c', skrypt, korzen, ...arg], { encoding: 'utf8', input: wejscie, maxBuffer: 1 << 28 }).trim();
  const wytworz = (dane, kodKonta, haslo) => py(`
import sys, json; sys.path.insert(0, sys.argv[1]); import pmt_przeniesienie as P
dane = json.loads(sys.stdin.read()); print(P.zaszyfruj(dane, sys.argv[2], P.hash_hasla(sys.argv[2], sys.argv[3])))`, JSON.stringify(dane), kodKonta, haslo);
  const skrot = (k, h) => require('crypto').createHash('sha256').update(`PMT|${k}|${h}`).digest('hex');

  const dane = { z: 'program', wersja_programu: '3.25.0', data: '2026-10-29', profil: { imie: 'Jan Żółć-Łódzki', pesel: '90010112349', adres: 'ul. Polna 5, 00-001 Warszawa', stanowisko: 'KR', silnik_powyzej_900: false },
    sklepy: [{ adres: 'Główna 1, Grodzisk Mazowiecki', siec: 'Żabka', miasto: 'Grodzisk Mazowiecki' }, { adres: 'Dębowa Wola 12, Jedlińsk', siec: '', miasto: 'Jedlińsk' }] };
  const plik = wytworz(dane, '12345', 'haslo123');
  ok('plik z programu nie zawiera PESEL-u ani nazwiska jawnym tekstem', !plik.includes('90010112349') && !/Żółć|Polna|Żabka/.test(plik) && P.kodZPliku(plik) === '12345', plik.slice(0, 90) + '…');
  const r = await P.odczytaj(plik, skrot('12345', 'haslo123'));
  ok('aplikacja odczytuje plik zrobiony przez program (to samo konto i hasło)', r.ok && r.kod === '12345');
  ok('dane zgadzają się co do znaku (polskie litery, PESEL, adres, stanowisko, silnik)', r.ok && JSON.stringify(r.dane.profil) === JSON.stringify(dane.profil), r.ok ? JSON.stringify(r.dane.profil) : r.komunikat);
  ok('lista sklepów przechodzi w całości i w tej samej kolejności', r.ok && JSON.stringify(r.dane.sklepy) === JSON.stringify(dane.sklepy));
  const zle = await P.odczytaj(plik, skrot('12345', 'inne-haslo'));
  ok('inne hasło: odmowa z czytelnym komunikatem, bez danych', !zle.ok && zle.powod === 'klucz' && /konto|hasło/.test(zle.komunikat) && !zle.dane);
  const bezHasla = await P.odczytaj(plik, '');
  ok('brak skrótu hasła (niezalogowany): prośba o ponowne logowanie', !bezHasla.ok && /Zaloguj/.test(bezHasla.komunikat));
  const k = JSON.parse(plik); const zmien = (pole, f) => JSON.stringify({ ...k, [pole]: f(k[pole]) });
  const zmienione = [['dane', s => (s[0] === 'A' ? 'B' : 'A') + s.slice(1)], ['kod', () => '54321'], ['iv', s => (s[0] === '0' ? '1' : '0') + s.slice(1)], ['sol', s => (s[0] === '0' ? '1' : '0') + s.slice(1)], ['mac', s => (s[0] === '0' ? '1' : '0') + s.slice(1)]];
  let wszystkieOdrzucone = true, ktore = '';
  for (const [p, f] of zmienione) { const w = await P.odczytaj(zmien(p, f), skrot('12345', 'haslo123')); if (w.ok) { wszystkieOdrzucone = false; ktore += p + ' '; } }
  ok('zmiana jakiegokolwiek pola pliku (dane, kod, iv, sol, mac) jest wykrywana', wszystkieOdrzucone, ktore && 'przeszło: ' + ktore);
  const smieci = ['', 'nie json', '{}', '{"pmt":"przeniesienie"}', '{"pmt":"przeniesienie","v":2}', JSON.stringify({ ...k, sol: 'zz' }), JSON.stringify({ ...k, dane: '%%%' })];
  let ok2 = true; for (const s of smieci) { const w = await P.odczytaj(s, skrot('12345', 'haslo123')); if (w.ok || w.powod !== 'format') ok2 = false; }
  ok('śmieci i obce formaty: „to nie jest plik z danymi z programu”, bez wyjątków', ok2);
  ok('kodZPliku nie rzuca na śmieciach', P.kodZPliku('x') === null && P.kodZPliku('{"pmt":"przeniesienie","kod":"12"}') === null);

  /* duży ładunek (wiele bloków strumienia) i granice długości */
  const duzo = { z: 'program', profil: null, sklepy: Array.from({ length: 1500 }, (_, i) => ({ adres: `Ulica ${i} ${'x'.repeat(i % 40)}, Miasto ${i % 90}`, siec: i % 3 ? 'Żabka' : 'Biedronka', miasto: `Miasto ${i % 90}` })) };
  const r2 = await P.odczytaj(wytworz(duzo, '77777', 'Ęś#12'), skrot('77777', 'Ęś#12'));
  ok('1500 sklepów (kilkaset bloków strumienia) odczytane bez uszczerbku', r2.ok && r2.dane.sklepy.length === 1500 && r2.dane.sklepy[1499].adres === duzo.sklepy[1499].adres && r2.dane.profil === null);

  /* oczyszczanie: obce pola, długie teksty, zły PESEL-owy śmieć, nie-listy */
  const brudne = P.oczyscDane({ profil: { imie: '  Ala   Ma  Kota  ', pesel: '9001-0112 349abc', adres: 'a'.repeat(500), stanowisko: 'admin', silnik_powyzej_900: 0, haker: '<img src=x onerror=1>' }, sklepy: [{ adres: ' A  1 ', siec: 5, miasto: null, x: 1 }, { adres: '' }, null, 'tekst', { adres: 'B 2' }], obce: { a: 1 } });
  ok('oczyszczanie: spacje scalone, PESEL tylko cyfry (≤11), pola ≤200 znaków, stanowisko tylko KR/merchandiser, obce klucze znikają',
    brudne.profil.imie === 'Ala Ma Kota' && brudne.profil.pesel === '90010112349' && brudne.profil.adres.length === 200 && brudne.profil.stanowisko === 'merchandiser' && !('haker' in brudne.profil) && !('obce' in brudne), JSON.stringify(brudne.profil).slice(0, 160));
  ok('oczyszczanie: puste adresy i nie-obiekty odpadają, liczby w polach stają się tekstem', brudne.sklepy.length === 2 && brudne.sklepy[0].adres === 'A 1' && brudne.sklepy[0].siec === '5' && brudne.sklepy[0].miasto === '');
  ok('oczyszczanie: brak profilu i brak listy nie psują nic', (() => { const x = P.oczyscDane({}); return x.profil === null && Array.isArray(x.sklepy) && x.sklepy.length === 0; })());
  /* Python odrzuca to samo, co JavaScript (symetria) */
  const symetria = py(`
import sys, json; sys.path.insert(0, sys.argv[1]); import pmt_przeniesienie as P
t = P.zaszyfruj({"a": 1}, "12345", "s"); 
try: P.odszyfruj(t, "inny"); print("PRZESZLO")
except ValueError as e: print("odrzucone")`);
  ok('Python też odrzuca zły klucz (symetria)', symetria === 'odrzucone', symetria);
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log(kod ? 'KONIEC kod=1' : 'KONIEC kod=0'); process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
