// Buduje dane PRZYKŁADOWE pokazywane przy pierwszym uruchomieniu (zamiast pustego programu): przyklad/miesiac.json i przyklad/plan.json.
// Dane powstają z PRAWDZIWEGO silnika (ta sama ścieżka co zwykłe generowanie), dla wymyślonej osoby i listy sklepów z pliku .xlsx/.csv.
// Użycie:  NODE_PATH=/opt/node22/lib/node_modules node narzedzia/zbuduj_przyklad.js [lista_sklepow.csv|xlsx] [kwota]
//   lista sklepów: kolumny jak w „Plan” (sieć, miasto, ulica, numer, kod pocztowy); domyślnie testy/dane/sklepy.xlsx.
//   Z własnego pliku Excel: najpierw python narzedzia/przygotuj_liste_przykladu.py plik.xlsx lista.csv (czyści dane pokazowe), potem ten skrypt z lista.csv.
// Dane pokazowe służą WYŁĄCZNIE do wyświetlenia przykładu — nie wchodzą w żadne liczenie delegacji.
// Po zmianie plików: python narzedzia/zbuduj_sw.py (żeby przykład trafił do pamięci podręcznej offline).
const path = require('path'), fs = require('fs');
const { otworz, generuj } = require('../testy/wspolne');
(async () => {
  const lista = path.resolve(process.argv[2] || path.join(__dirname, '../testy/dane/sklepy.xlsx')), kwota = process.argv[3] || '3684,30';
  const wyj = path.join(__dirname, '../przyklad'); fs.mkdirSync(wyj, { recursive: true });
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p;
  // „dziś” w przeglądarce = 1 września 2026, żeby plan wizyt objął wrzesień (miesiąc przykładu)
  await t.ctx.addInitScript(() => { const R = Date, przes = new R('2026-09-01T07:00:00').getTime() - R.now(); class D extends R { constructor(...a) { a.length ? super(...a) : super(R.now() + przes); } static now() { return R.now() + przes; } } window.Date = D; });
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Anna Przykładowa'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Przykładowa 1, 05-120 Legionowo');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 30000 }); await p.waitForTimeout(3500);
  await p.click('#plan-otworz'); await p.waitForSelector('#plan-plik', { state: 'attached' }); await p.setInputFiles('#plan-plik', lista);
  await p.waitForFunction(() => /Wczytano/.test(document.querySelector('#plan-plik-info').textContent), null, { timeout: 60000, polling: 200 });
  await p.click('#plan-uloz'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 1500000 }); await p.waitForFunction(() => document.querySelector('#przystanki .przystanek'), null, { timeout: 120000, polling: 200 }); await p.waitForTimeout(2000);
  await p.click('#m-dalej'); await p.waitForFunction(() => /Wrzesień/.test(document.querySelector('#m-nazwa').textContent), null, { timeout: 60000, polling: 200 }); await p.waitForTimeout(2500);   // aplikacja startuje na miesiącu, który minął (sierpień) — przechodzimy na wrzesień
  await p.fill('#kwota-in', kwota); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
  await generuj(p); await p.waitForTimeout(3000);
  const dane = await p.evaluate(() => { const klucz = Object.keys(localStorage).find(k => k.startsWith('pmt-web-v1:')); const d = JSON.parse(localStorage.getItem(klucz)); const [k, rec] = Object.entries(d.miesiace)[0]; return { klucz: k, rec, plan: d.plan }; });
  const [rok, mies] = dane.klucz.split('-').map(Number);
  const miesiac = { rok, mies, params: { kwota: dane.rec.params.kwota, tryb: dane.rec.params.tryb, silnik_powyzej_900: dane.rec.params.silnik_powyzej_900, wolne: dane.rec.params.wolne || [] }, wynik: dane.rec.wynik };
  fs.writeFileSync(path.join(wyj, 'miesiac.json'), JSON.stringify(miesiac));
  // do pokazu wystarczą pierwsze dni planu (pełna lista sklepów i dalsze miesiące nie są potrzebne ani nie powinny trafiać do paczki)
  const m0 = dane.plan.miesiace[0], dni = m0.dni.slice(0, 4), sumaKm = dni.reduce((a, d) => a + (d.km || 0), 0), sumaWizyt = dni.reduce((a, d) => a + d.wizyty.length, 0);
  const planPokazowy = { miesiace: [{ ...m0, dni, suma_km: Math.round(sumaKm * 10) / 10, suma_wizyt: sumaWizyt }], suma_km: Math.round(sumaKm * 10) / 10, suma_wizyt: sumaWizyt, bez_pozycji: [], nierozplanowane: [], baza: dane.plan.baza, cykliczny: false, tryb: dane.plan.tryb, pozycje: [] };
  fs.writeFileSync(path.join(wyj, 'plan.json'), JSON.stringify(planPokazowy));
  dane.plan = planPokazowy;
  console.log(`przyklad/miesiac.json: ${rok}-${mies}, kwota ${miesiac.params.kwota}, ${miesiac.wynik.dni.length} dni z trasą, ${miesiac.wynik.dokumenty.length} poleceń`);
  console.log(`przyklad/plan.json: ${dane.plan.miesiace.reduce((s, m) => s + m.dni.length, 0)} dni, ${dane.plan.suma_wizyt} wizyt`);
  console.log('błędy konsoli:', JSON.stringify(t.bledy.slice(0, 4)));
  await t.zamknij();
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
