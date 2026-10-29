// Przeniesienie danych z programu na komputerze: plik z programu (pmt_przeniesienie.py) → „Moje dane” w aplikacji web (formularz wypełnia się sam, nic nie zapisuje się bez „Zapisz”),
// lista sklepów czeka w oknie „Plan wizyt”; błędne pliki (inne konto, inne hasło, zmieniony, nie z PMT) są odrzucane z czytelnym komunikatem.
// NODE_PATH=/opt/node22/lib/node_modules node przeniesienie_app.js
const { otworz } = require('./wspolne'); const { execFileSync } = require('child_process'), path = require('path'), fs = require('fs'), os = require('os');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const korzen = path.resolve(__dirname, '..', '..'), tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'przen-app-'));
  const zrob = (nazwa, dane, kodKonta, haslo) => {
    const wyj = execFileSync('python3', ['-I', '-c', `
import sys, json; sys.path.insert(0, sys.argv[1]); import pmt_przeniesienie as P
print(P.zaszyfruj(json.loads(sys.stdin.read()), sys.argv[2], P.hash_hasla(sys.argv[2], sys.argv[3])))`, korzen, kodKonta, haslo], { encoding: 'utf8', input: JSON.stringify(dane) }).trim();
    const f = path.join(tmp, nazwa); fs.writeFileSync(f, wyj); return f;
  };
  const dane = P => ({ z: 'program', wersja_programu: '3.25.0', data: '2026-10-29', profil: { imie: 'Jan Testowy', pesel: '90010112349', adres: 'ul. Testowa 1, 00-001 Warszawa', stanowisko: 'KR', silnik_powyzej_900: false },
    sklepy: [{ adres: 'Główna 1, Grodzisk Mazowiecki', siec: 'Żabka', miasto: 'Grodzisk Mazowiecki' }, { adres: 'Piękna 2, Żyrardów', siec: 'Biedronka', miasto: 'Żyrardów' }, { adres: 'Dębowa Wola 12, Jedlińsk', siec: '', miasto: 'Jedlińsk' }] });
  const dobry = zrob('dobry.pmtdane', dane(), '12345', 'haslo123');
  const innyKod = zrob('inne_konto.pmtdane', dane(), '54321', 'haslo123');
  const innyHaslo = zrob('inne_haslo.pmtdane', dane(), '12345', 'cos-innego');
  const smiec = path.join(tmp, 'smiec.pmtdane'); fs.writeFileSync(smiec, 'to nie jest plik programu');
  const zmieniony = path.join(tmp, 'zmieniony.pmtdane'); { const k = JSON.parse(fs.readFileSync(dobry, 'utf8')); k.dane = (k.dane[0] === 'A' ? 'B' : 'A') + k.dane.slice(1); fs.writeFileSync(zmieniony, JSON.stringify(k)); }
  const bezDanych = zrob('pusty.pmtdane', { z: 'program', profil: null, sklepy: [] }, '12345', 'haslo123');

  const t = await otworz({ w: 1440, h: 900, opcjeSerwera: { odbiorca: 'kierownik@example.com' } }); const p = t.p;
  const info = () => p.locator('#przenos-info').innerText();
  const czekajInfo = re => p.waitForFunction(r => new RegExp(r).test(document.querySelector('#przenos-info').textContent), re.source, { timeout: 60000, polling: 150 });
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  ok('pierwsze uruchomienie („Zacznijmy od Twoich danych”) ma przycisk wczytania danych z programu', (await p.locator('#plik-program').count()) === 1 && /Wczytaj dane z programu/.test(await p.locator('#przenos-etykieta').innerText()));
  await p.screenshot({ path: '/tmp/przen_1_pusty.png' });

  /* ---- odrzucenia ---- */
  for (const [plik, re, opis] of [[smiec, /nie jest plik z danymi z programu/, 'plik nie z PMT'], [innyKod, /z konta 54321.*zalogowany jako 12345/, 'plik innego konta (kod)'], [innyHaslo, /inne konto albo inne hasło/, 'plik zrobiony innym hasłem'], [zmieniony, /inne konto albo inne hasło|zmieniony/, 'plik zmieniony po zapisaniu'], [bezDanych, /niczego do wczytania/, 'plik bez danych']]) {
    await p.setInputFiles('#plik-program', plik); await czekajInfo(re);
    ok(`odrzucony: ${opis}`, re.test(await info()) && (await p.locator('#przenos-info.zle').count()) === 1, (await info()).slice(0, 120));
  }
  ok('po odrzuceniach formularz jest nietknięty (puste PESEL i adres)', (await p.inputValue('#d-pesel')) === '' && (await p.inputValue('#d-adres')) === '');

  /* ---- dobry plik ---- */
  await p.setInputFiles('#plik-program', dobry); await czekajInfo(/Wczytano/);
  ok('dobry plik: komunikat „Wczytano” z liczbą sklepów i prośbą o sprawdzenie', /Wczytano:.*3 sklepów.*Zapisz/s.test(await info()) && (await p.locator('#przenos-info.ok').count()) === 1, (await info()).slice(0, 160));
  ok('formularz wypełniony: imię, PESEL, adres, stanowisko KR', (await p.inputValue('#d-imie')) === 'Jan Testowy' && (await p.inputValue('#d-pesel')) === '90010112349' && (await p.inputValue('#d-adres')) === 'ul. Testowa 1, 00-001 Warszawa' && (await p.inputValue('#d-stan')) === 'KR');
  const przedZapisem = await p.evaluate(() => { const d = window.__pmtDane.czytaj(); return { profil: !!d.profil, sklepy: !!(d.ustawienia && d.ustawienia['sklepy-z-programu']) }; });
  ok('przed „Zapisz” nic nie jest zapisane (ani profil, ani lista sklepów)', !przedZapisem.profil && !przedZapisem.sklepy, JSON.stringify(przedZapisem));
  await p.screenshot({ path: '/tmp/przen_2_wczytano.png' });
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 });
  const toast = await p.waitForFunction(() => { const e = document.querySelector('#toast-tekst'); return e && /czeka/.test(e.textContent) ? e.textContent : false; }, null, { timeout: 20000, polling: 100 }).then(h => h.jsonValue()).catch(() => '');
  await p.waitForTimeout(2500);
  const po = await p.evaluate(() => { const d = window.__pmtDane.czytaj(); return { profil: d.profil, sk: d.ustawienia && d.ustawienia['sklepy-z-programu'] }; });
  ok('po „Zapisz” profil zapisany z danymi z programu (PESEL, KR, silnik do 900 cm³)', po.profil && po.profil.pesel === '90010112349' && po.profil.imie === 'Jan Testowy' && po.profil.stanowisko === 'KR' && po.profil.silnik_powyzej_900 === false, JSON.stringify(po.profil));
  ok('lista 3 sklepów z programu czeka w ustawieniach konta', po.sk && po.sk.pozycje.length === 3 && po.sk.pozycje[2].adres === 'Dębowa Wola 12, Jedlińsk');
  ok('komunikat po zapisie mówi, gdzie jest lista sklepów i co zrobić', /Lista 3 sklepów z programu czeka.*„Plan”/.test(toast), toast);

  /* ---- okno Plan: lista z programu gotowa do ułożenia ---- */
  await p.click('#plan-otworz'); await p.waitForSelector('#plan-plik', { state: 'attached' });
  const planInfo = await p.locator('#plan-plik-info').innerText();
  ok('okno „Plan wizyt” pokazuje listę przeniesioną z programu i pozwala od razu ułożyć plan', /przeniesiona z programu: 3 adresów/.test(planInfo) && !(await p.locator('#plan-uloz').isDisabled()) && /Ułóż plan$/.test((await p.locator('#plan-uloz').innerText()).trim()), planInfo + ' | ' + await p.locator('#plan-uloz').innerText());
  await p.screenshot({ path: '/tmp/przen_3_plan.png' });
  await p.keyboard.press('Escape'); await p.waitForTimeout(500);

  const bledy = t.bledy.filter(b => !/favicon|ERR_|net::|Failed to load/.test(b));
  ok('bez błędów w konsoli', bledy.length === 0, bledy.join(' | ').slice(0, 300));
  await t.zamknij(); fs.rmSync(tmp, { recursive: true, force: true });
  console.log(kod ? 'KONIEC kod=1' : 'KONIEC kod=0'); process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
