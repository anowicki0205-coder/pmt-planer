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
  const dane = P => ({ z: 'program', wersja_programu: '3.25.1', data: '2026-10-29', profil: { imie: 'Jan Testowy', pesel: '90010112349', adres: 'ul. Testowa 1, 00-001 Warszawa', stanowisko: 'KR', silnik_powyzej_900: false },
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
  const toast = await p.waitForFunction(() => { const e = document.querySelector('#toast-tekst'); return e && /gotowa/.test(e.textContent) ? e.textContent : false; }, null, { timeout: 20000, polling: 100 }).then(h => h.jsonValue()).catch(() => '');
  await p.waitForTimeout(2500);
  const po = await p.evaluate(() => { const d = window.__pmtDane.czytaj(); return { profil: d.profil, sk: d.ustawienia && d.ustawienia['sklepy-z-programu'] }; });
  ok('po „Zapisz” profil zapisany z danymi z programu (PESEL, KR, silnik do 900 cm³)', po.profil && po.profil.pesel === '90010112349' && po.profil.imie === 'Jan Testowy' && po.profil.stanowisko === 'KR' && po.profil.silnik_powyzej_900 === false, JSON.stringify(po.profil));
  ok('lista 3 sklepów z programu czeka w ustawieniach konta', po.sk && po.sk.pozycje.length === 3 && po.sk.pozycje[2].adres === 'Dębowa Wola 12, Jedlińsk');
  ok('komunikat po zapisie mówi, że lista sklepów jest gotowa i co zrobić (ułożyć z niej plan)', /Lista 3 sklepów z programu jest gotowa.*ułóż z niej plan/.test(toast), toast);

  /* ---- okno Plan: lista z programu gotowa do ułożenia (otwiera się samo, bo plik nie miał gotowego planu) ---- */
  await p.waitForSelector('#plan-plik', { state: 'attached', timeout: 15000 });
  ok('plik bez planu: okno „Plan wizyt” otwiera się samo, żeby od razu ułożyć plan z przeniesionej listy', (await p.locator('#arkusz-tlo.otwarty').count()) === 1);
  const planInfo = await p.locator('#plan-plik-info').innerText();
  ok('okno „Plan wizyt” pokazuje listę przeniesioną z programu i pozwala od razu ułożyć plan', /przeniesiona z programu: 3 adresów/.test(planInfo) && !(await p.locator('#plan-uloz').isDisabled()) && /Ułóż plan$/.test((await p.locator('#plan-uloz').innerText()).trim()), planInfo + ' | ' + await p.locator('#plan-uloz').innerText());
  await p.screenshot({ path: '/tmp/przen_3_plan.png' });
  await p.keyboard.press('Escape'); await p.waitForTimeout(500);

  const bledy = t.bledy.filter(b => !/favicon|ERR_|net::|Failed to load/.test(b));
  ok('bez błędów w konsoli', bledy.length === 0, bledy.join(' | ').slice(0, 300));
  await t.zamknij();

  /* ---- plik z gotowym planem i odhaczeniami: kafel Dziś nie jest goły ---- */
  const lokalnie = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const dzis = new Date(), jutro = new Date(dzis.getTime() + 86400000), dawno = new Date(dzis.getTime() - 60 * 86400000);
  const D = lokalnie(dzis), J = lokalnie(jutro), S = lokalnie(dawno);
  const W = (nazwa, adres, siec, miasto, lat, lng) => ({ nazwa, adres, siec, miasto, lat, lng });
  const miesiac = dni => ({ dni });
  const zPlanem = zrob('z_planem.pmtdane', { ...dane(), plan: { cykliczny: false, cykl_domyslny: 4, miesiace: [miesiac([
      { data: S, km: 10, minuty: 60, wizyty: [W('Stary', 'Dawna 1, Miasto', 'Żabka', 'Miasto', 52.1, 21.0)] },
      { data: D, km: 41.2, minuty: 95, wizyty: [W('Żabka', 'Główna 1, Grodzisk Mazowiecki', 'Żabka', 'Grodzisk Mazowiecki', 52.1034, 20.6312), W('Biedronka', 'Piękna 2, Żyrardów', 'Biedronka', 'Żyrardów', 52.05, 20.44), W('Zła <img src=x onerror="window.__xss=1">', 'Dębowa Wola 12, Jedlińsk', '<img src=x onerror="window.__xss=1">', 'Jedlińsk', 51.6, 21.1)] },
      { data: J, km: 20, minuty: 70, wizyty: [W('Żabka', 'Główna 1, Grodzisk Mazowiecki', 'Żabka', 'Grodzisk Mazowiecki', 52.1034, 20.6312)] }])] },
    odhaczenia: { [`${D}|główna 1, grodzisk mazowiecki`]: { czas: `${D.slice(8)}.${D.slice(5, 7)}.${D.slice(0, 4)} 08:15`, notatka: '' }, [`${S}|dawna 1, miasto`]: { czas: '01.01.2026 09:00' } } }, '12345', 'haslo123');
  const t2 = await otworz({ w: 1440, h: 900, opcjeSerwera: { odbiorca: 'kierownik@example.com' } }); const q = t2.p;
  const info2 = () => q.locator('#przenos-info').innerText();
  await q.goto(t2.adres + '/index.html'); await q.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await q.setInputFiles('#plik-program', zPlanem); await q.waitForFunction(() => /Wczytano/.test(document.querySelector('#przenos-info').textContent), null, { timeout: 60000, polling: 150 });
  ok('komunikat po wczytaniu mówi o planie wizyt (3 dni) i że pojawi się w kaflu Dziś', /Wczytano:.*3 sklepów.*plan wizyt \(3 dni\).*Plan pojawi się w kaflu Dziś/s.test(await info2()), (await info2()).slice(0, 220));
  const przed = await q.evaluate(() => { const d = window.__pmtDane.czytaj(); return !!d.plan; });
  ok('przed „Zapisz” plan nie jest zapisany', !przed);
  await q.click('#zapisz-dane'); await q.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 });
  await q.waitForFunction(() => document.querySelector('#d-pier-t') && /^1\/3$/.test(document.querySelector('#d-pier-t').textContent.trim()), null, { timeout: 60000, polling: 200 });
  ok('kafel Dziś ma 3 wizyty z planu z programu (nie jest „goły”)', (await q.locator('#przystanki li.przystanek').count()) === 3 && /^Dziś/.test((await q.locator('#d-tyt').innerText()).trim()), (await q.locator('#d-tyt').innerText()).trim());
  ok('pierwsza wizyta jest odhaczona (z dziennika programu), druga to „następna”', (await q.locator('#przystanki li.przystanek').nth(0).getAttribute('class')).includes('ok') && (await q.locator('#przystanki li.przystanek').nth(1).getAttribute('class')).includes('teraz') && /08:15|^\d\d:\d\d$/.test((await q.locator('#przystanki li.przystanek .p-godz').nth(0).innerText()).trim()));
  const tresc = await q.locator('#przystanki').innerText();
  ok('na liście są sklepy z planu (Żabka Grodzisk, Biedronka Żyrardów), a licznik pokazuje 1/3', /Żabka/.test(tresc) && /Biedronka/.test(tresc) && /Grodzisk/.test(tresc) && (await q.locator('#d-pier-t').innerText()).trim() === '1/3', tresc.replace(/\s+/g, ' ').slice(0, 160));
  ok('tekst z pliku jest tylko tekstem (znaczniki nie wykonują się ani nie rysują obrazków)', (await q.evaluate(() => window.__xss === undefined && !document.querySelector('#przystanki img'))) === true);
  const po2 = await q.evaluate(d => { const x = window.__pmtDane.czytaj(); const dni = x.plan ? x.plan.miesiace.flatMap(m => m.dni.map(z => z.data)) : []; return { dni, z: x.plan && x.plan.zProgramu, poz: x.plan && x.plan.pozycje && x.plan.pozycje.length, wiz: x.wizyty || {}, sk: x.ustawienia && x.ustawienia['sklepy-z-programu'], godzin: x.plan && x.plan.miesiace.flatMap(m => m.dni).find(z => z.data === d).godziny }; }, D);
  ok('plan trafił do magazynu konta (3 dni, oznaczony „z programu”, lista 3 sklepów)', po2.dni.length === 3 && po2.dni.includes(D) && po2.dni.includes(J) && po2.z === true && po2.poz === 3, JSON.stringify(po2.dni));
  ok('silnik dolicza godziny wizyt (każda wizyta dnia ma godzinę)', Array.isArray(po2.godzin) && po2.godzin.length === 3 && po2.godzin.every(g => /^\d\d:\d\d$/.test(g)), JSON.stringify(po2.godzin));
  const kl = `${D}|Główna 1, Grodzisk Mazowiecki`;
  ok('odhaczenie z dziennika programu zapisane z godziną 08:15; wizyta spoza planu (sprzed 60 dni) też tylko jako dzień planu', po2.wiz[kl] && po2.wiz[kl].ok === true && po2.wiz[kl].godz === '08:15', JSON.stringify(po2.wiz));
  ok('lista sklepów „czekająca” została zużyta (plan już jest)', !po2.sk);
  await q.waitForTimeout(2200);
  ok('okno „Plan wizyt” nie otwiera się samo, skoro plan już jest', (await q.locator('#arkusz-tlo.otwarty').count()) === 0 && (await q.locator('#plan-plik').count()) === 0);
  await q.screenshot({ path: '/tmp/przen_4_dzis_z_planem.png' });
  const bledy2 = t2.bledy.filter(b => !/favicon|ERR_|net::|Failed to load/.test(b));
  ok('bez błędów w konsoli (scenariusz z planem)', bledy2.length === 0, bledy2.join(' | ').slice(0, 300));
  await t2.zamknij(); fs.rmSync(tmp, { recursive: true, force: true });
  console.log(kod ? 'KONIEC kod=1' : 'KONIEC kod=0'); process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
