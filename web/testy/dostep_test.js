// Dostęp (js/dostep.js) w Node, z atrapą backendu (testy/backend_mock.js — te same reguły co .gs): jeden puls naraz (bez podwójnych przyrostów w arkuszu),
// sekret nie zapamiętuje pustego wyniku, odebrany dostęp przeżywa wylogowanie (logowanie bez sieci odmawia), hasło liczone w postaci jak na serwerze
// (przycięte, telefon jako 9 cyfr) dla skrótu sesji i sejfu, a sejf założony dawniej surowym tekstem nadal się otwiera; przestawiony zegar urządzenia nie psuje podpisów.
// Uruchom: node testy/dostep_test.js
const nc = require('crypto');
const { BackendMock } = require('./backend_mock.js');
const pamiec = () => { const m = new Map(); return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => { m.set(k, String(v)); }, removeItem: k => { m.delete(k); }, clear: () => m.clear() }; };
globalThis.localStorage = pamiec(); globalThis.sessionStorage = pamiec();
const B = new BackendMock({ uzytkownicy: {
  '12345': { imie: 'Jan Testowy', telefon: '600100200', hash: nc.createHash('sha256').update('PMT|12345|haslo123').digest('hex'), wazne_do: '2099-12-31' },
  '22222': { imie: 'Anna Nowa', telefon: '501502503', hash: '', wazne_do: '2099-12-31' },
  '44444': { imie: 'Ola Blokowana', telefon: '700800901', hash: nc.createHash('sha256').update('PMT|44444|haslo444').digest('hex'), wazne_do: '2099-12-31' },
} });
let sekretPada = false, wyslanePulsy = 0, zegarUrzadzenia = 0, ostatnieZapytanie = null;
const prawdziwyCzas = Date.now; Date.now = () => prawdziwyCzas() + zegarUrzadzenia;      // zegar urządzenia (aplikacji) da się przestawić; atrapa serwera liczy czas prawdziwy
const naSerwerze = f => { const z = Date.now; Date.now = prawdziwyCzas; try { return f(); } finally { Date.now = z; } };
globalThis.fetch = async (url, o = {}) => {
  const u = String(url);
  if (u === 'sekret.txt') { if (sekretPada) throw new TypeError('Failed to fetch'); return { ok: true, text: async () => 'SEKRET-TESTOWY\n' }; }
  if (B.martwy) throw new TypeError('Failed to fetch');
  if (!o.body) return { ok: true, text: async () => '' };
  ostatnieZapytanie = JSON.parse(o.body); if (ostatnieZapytanie.akcja === 'puls') wyslanePulsy++;
  await new Promise(r => setTimeout(r, 5));
  const odp = naSerwerze(() => JSON.stringify(B.obsluz(o.body))); return { ok: true, text: async () => odp };
};
(async () => {
  const D = await import('../js/dostep.js'), S = await import('../js/sejf.js'); let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const sha = t => nc.createHash('sha256').update(t).digest('hex');
  const offline = async f => { B.martwy = true; try { return await f(); } finally { B.martwy = false; } };

  /* sekret: pusty wynik (brak sieci) nie zostaje na zawsze */
  sekretPada = true; const s1 = await D.sekret(); sekretPada = false; const s2 = await D.sekret();
  ok('sekret bez sieci = pusty, ale następne zapytanie pobiera go ponownie', s1 === '' && s2 === 'SEKRET-TESTOWY', JSON.stringify([s1, s2]));
  ok('udany sekret jest zapamiętany (to samo żądanie)', D.sekret() === D.sekret());

  /* hasło z odstępem: skrót sesji = skrót serwera, sejf w postaci przyciętej */
  let w = await D.zaloguj('12345', 'haslo123 ');
  ok('logowanie hasłem z końcową spacją przechodzi', w.ok, w.komunikat);
  ok('skrót sesji liczony z hasła przyciętego (jak „Haslo hash” na serwerze)', D.skrotAktywny() === sha('PMT|12345|haslo123'));
  ok('wynik logowania podaje postać hasła do sejfu i tekst z pola', w.haslo === 'haslo123' && w.wpisane === 'haslo123 ' && !w.telefon, JSON.stringify(w));
  let sj = await D.przygotujSejf('12345', w.haslo, w.wpisane);
  ok('pierwsze logowanie zakłada sejf', sj.stan === 'ok' && sj.nowy);
  ok('sejf otwiera hasło bez spacji', !!(await S.otworzSejf('12345', 'haslo123')));
  const pelneOk = (await D.puls() || {}).pelne === true;
  ok('puls z podpisem hasłem przechodzi (pelne)', pelneOk);
  D.wyloguj();
  w = await D.zaloguj('12345', 'haslo123');
  sj = await D.przygotujSejf('12345', w.haslo, w.wpisane);
  ok('następne logowanie bez spacji otwiera ten sam sejf (nie „obcy”)', sj.stan === 'ok' && !sj.nowy, sj.stan);
  ok('autologowanie rozpoznaje hasło także z odstępem', await D.czyHasloZnane('12345', ' haslo123 ') && !(await D.czyHasloZnane('12345', 'haslo12')));

  /* sejf założony przed poprawką surowym tekstem („haslo123 ”): otwiera się i przechodzi na postać przyciętą */
  const dek0 = await S.utworzSejf('12345', 'haslo123 ');
  sj = await D.przygotujSejf('12345', 'haslo123', 'haslo123 ');
  ok('dawny sejf (surowy tekst) otwiera się i oddaje ten sam klucz', sj.stan === 'ok' && Buffer.from(sj.dek).equals(Buffer.from(dek0)));
  ok('…i jest od razu przepisany na hasło przycięte', !!(await S.otworzSejf('12345', 'haslo123')) && !(await S.otworzSejf('12345', 'haslo123 ')));

  /* jeden puls naraz */
  D.policzDokumenty(7); const przed = B.pulsy.length, wyslPrzed = wyslanePulsy;
  const [p1, p2] = await Promise.all([D.puls(), D.puls()]);
  const nowe = B.pulsy.slice(przed);
  ok('dwa równoczesne pulsy wysyłają kolejkę raz (serwer nie liczy dokumentów podwójnie)', wyslanePulsy - wyslPrzed === 1 && nowe.length === 1 && nowe[0].dokumenty === 7 && p1 === p2, JSON.stringify(nowe.map(p => p.dokumenty)));
  await D.puls();
  ok('po zakończeniu następny puls idzie normalnie, z pustą kolejką', B.pulsy.length === przed + 2 && B.pulsy[B.pulsy.length - 1].dokumenty === 0);
  D.wyloguj();

  /* telefon: różne zapisy numeru to ten sam sejf, także bez sieci */
  w = await D.zaloguj('22222', '501 502 503');
  ok('logowanie telefonem: serwer mówi „telefon”, sejf dostaje 9 cyfr', w.ok && w.telefon && w.haslo === '501502503', JSON.stringify(w));
  sj = await D.przygotujSejf('22222', w.haslo, w.wpisane);
  D.wyloguj();
  w = await D.zaloguj('22222', '501502503'); sj = await D.przygotujSejf('22222', w.haslo, w.wpisane);
  ok('kolejne logowanie innym zapisem numeru otwiera ten sam sejf', w.ok && sj.stan === 'ok' && !sj.nowy, sj.stan);
  D.wyloguj();
  w = await offline(() => D.zaloguj('22222', '+48 501-502-503'));
  ok('bez sieci numer w innym zapisie też otwiera sejf', w.ok && w.offline && !!w.dek, w.komunikat);
  D.wyloguj();

  /* odebrany dostęp (pusta data „Ważne do”) przeżywa wylogowanie */
  w = await D.zaloguj('44444', 'haslo444'); await D.przygotujSejf('44444', w.haslo, w.wpisane);
  ok('konto z ważnym dostępem loguje się', w.ok && D.ocenaSesji().wazna);
  B.uzytkownicy['44444'].wazne_do = '';
  const o = await D.puls();
  ok('puls zwraca „wygasla”, ocena sesji nieważna', o && o.status === 'wygasla' && !D.ocenaSesji().wazna);
  D.wyloguj();
  w = await offline(() => D.zaloguj('44444', 'haslo444'));
  ok('po wylogowaniu logowanie bez sieci odmawia (dostęp wygasł)', !w.ok && /wygas/.test(w.komunikat || ''), w.komunikat);
  B.uzytkownicy['44444'].wazne_do = '2099-12-31';
  w = await D.zaloguj('44444', 'haslo444');
  ok('po przedłużeniu logowanie online zdejmuje blokadę', w.ok && D.ocenaSesji().wazna, JSON.stringify(D.ocenaSesji()));
  D.wyloguj();
  w = await offline(() => D.zaloguj('44444', 'haslo444'));
  ok('…a potem znów działa logowanie bez sieci', w.ok && w.offline, w.komunikat);

  D.wyloguj();

  /* zegar urządzenia przestawiony o 15 min: podpis dostaje czas serwera, logowanie (przy obowiązkowym podpisie) i hasło paczki przechodzą */
  zegarUrzadzenia = 15 * 60000; B.podpisObowiazkowy = true; B.paczka = { haslo: 'Tajne-Haslo-1', wazne_do: '2099-12-31', adres: 'kierownik@firma.pl' };
  w = await D.zaloguj('12345', 'haslo123');
  ok('zegar +15 min: logowanie przy obowiązkowym podpisie przechodzi (druga próba z czasem serwera)', w.ok, w.komunikat);
  const hp = await D.pobierzHasloPaczki();
  ok('zegar +15 min: hasło paczki przychodzi (podpis hasłem w oknie serwera)', hp.ok && hp.haslo === 'Tajne-Haslo-1', JSON.stringify(hp));
  zegarUrzadzenia = 0; B.podpisObowiazkowy = false; D.wyloguj();

  /* numer, który aplikacja web zgłasza w arkuszu („web 3.25.1”), ma być numerem najnowszego programu: panel administracji nie może pokazywać użytkowników web jako starszych */
  { const fs = require('fs'), path = require('path'), pyf = path.join(__dirname, '..', '..', 'PMT_Delegacje.py');
    if (fs.existsSync(pyf)) { const m = /^WERSJA_PROGRAMU\s*=\s*"([0-9.]+)"/m.exec(fs.readFileSync(pyf, 'utf8')); ok('web zgłasza w arkuszu ten sam numer co najnowszy program (WERSJA_PROGRAMU w PMT_Delegacje.py) — przy nowym wydaniu programu trzeba podbić też WERSJA w js/dostep.js', !!m && D.WERSJA === m[1], `web ${D.WERSJA}, program ${m && m[1]}`); }
    else ok('plik programu niedostępny w tym układzie katalogów — porównanie numerów pominięte', true); }
  /* oznaczenie klienta: backend nie stosuje do aplikacji web bramki wersji programu (WYMAGANA_WERSJA) */
  w = await D.zaloguj('12345', 'haslo123'); const zLogowania = ostatnieZapytanie; await D.puls();
  ok('każde zapytanie aplikacji niesie klient: "web" (logowanie, puls)', w.ok && zLogowania.klient === 'web' && ostatnieZapytanie.akcja === 'puls' && ostatnieZapytanie.klient === 'web', JSON.stringify([zLogowania && zLogowania.klient, ostatnieZapytanie && ostatnieZapytanie.klient]));
  D.wyloguj();

  /* hasło zmienione na innym urządzeniu: pierwszy puls bez „pelne” — dalej karta nie podpisuje starym skrótem (nie zużywa limitu złych podpisów konta) */
  B.paczka = { haslo: 'Tajne-Haslo-1', wazne_do: '2099-12-31', adres: 'kierownik@firma.pl' };
  w = await D.zaloguj('12345', 'haslo123'); const hashPrzed = B.uzytkownicy['12345'].hash;
  B.uzytkownicy['12345'].hash = sha('PMT|12345|inneHaslo9');
  await D.puls(); const pierwszy = ostatnieZapytanie; await D.puls(); const drugi = ostatnieZapytanie;
  const zapPrzed = ostatnieZapytanie, hp2 = await D.pobierzHasloPaczki();
  ok('stare hasło: pierwszy puls podpisany, po „pelne: false” kolejne już bez podpisu hasłem', !!pierwszy.podpis_hasla && !drugi.podpis_hasla, JSON.stringify([!!pierwszy.podpis_hasla, !!drugi.podpis_hasla]));
  ok('…a hasło paczki od razu prosi o ponowne logowanie, bez pytania serwera', hp2.powod === 'logowanie' && ostatnieZapytanie === zapPrzed, JSON.stringify(hp2));
  D.wyloguj(); B.uzytkownicy['12345'].hash = hashPrzed;
  w = await D.zaloguj('12345', 'haslo123'); await D.puls();
  ok('ponowne logowanie przywraca podpis hasłem', w.ok && !!ostatnieZapytanie.podpis_hasla);
  /* serwer zajęty (kolejka) to nie odmowa konta */
  const obsluz = B.obsluz.bind(B); B.obsluz = t => (JSON.parse(t).akcja === 'haslo_paczki' ? { status: 'blad', opis: 'Serwer zajety — sprobuj ponownie za chwile' } : obsluz(t));
  const hp3 = await D.pobierzHasloPaczki(); B.obsluz = obsluz;
  ok('„Serwer zajety” przy haśle paczki: komunikat „spróbuj ponownie”, nie „wyloguj się”', hp3.powod === 'siec' && /Serwer zajety/.test(hp3.komunikat) && !/Wyloguj/.test(hp3.komunikat), JSON.stringify(hp3));
  const hp4 = await D.pobierzHasloPaczki();
  ok('…i nie oznacza skrótu jako nieaktualnego (następna próba idzie normalnie)', hp4.ok, JSON.stringify(hp4));
  /* hasło paczki z polską literą: Eksplorator Windows zamienia wpisane hasło na bajty wg strony kodowej systemu, przeglądarka wg UTF-8 — paczka by się nie otworzyła, więc wysyłka ma odmówić z wyjaśnieniem */
  const paczkaPrzed = B.paczka; B.paczka = { haslo: 'Zażółć-hasło-1234', wazne_do: '2099-12-31', adres: 'kierownik@firma.pl' };
  const hp5 = await D.pobierzHasloPaczki();
  ok('hasło paczki z polskimi znakami: odmowa (powód „odpowiedz”) z komunikatem o znakach spoza ASCII, bez hasła w wyniku', !hp5.ok && hp5.powod === 'odpowiedz' && /ASCII/.test(hp5.komunikat) && !hp5.haslo && !/Zażółć/.test(hp5.komunikat), JSON.stringify(hp5));
  B.paczka = { haslo: 'Dobre-Haslo_#7!x', wazne_do: '2099-12-31', adres: 'kierownik@firma.pl' };
  const hp6 = await D.pobierzHasloPaczki();
  ok('hasło ze znakami specjalnymi, ale w ASCII, przechodzi', hp6.ok && hp6.haslo === 'Dobre-Haslo_#7!x', JSON.stringify(hp6));
  B.paczka = paczkaPrzed;
  D.wyloguj();

  console.log(kod ? 'BŁĘDY' : 'WSZYSTKO OK'); process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
