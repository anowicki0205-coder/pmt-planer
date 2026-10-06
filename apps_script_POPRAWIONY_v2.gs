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
//         stracą wtedy puls, sesję i reset hasła.
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
var AKCJE_PODPISANE = ['logowanie', 'puls', 'sesja', 'zmien_haslo', 'reset_hasla'];

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
    var wazneDo = new Date(teraz.getTime() + DOMYSLNE_DNI_NOWEGO * 864e5);
    sh.appendRow([kod, "", "", wazneDo, teraz,
                  dane.wersja || "", dane.system || "", 0, 0, 0,
                  "NOWY — uzupelnij dane"]);
    nr = sh.getLastRow();
    _log(ss, kod, "nowy_kod", "Pierwszy kontakt");
  }

  // Statystyki: program przysyła PRZYROSTY od ostatniej udanej
  // synchronizacji (delta), więc offline nic nie ginie — dolicza się
  // przy najbliższym połączeniu.
  var w = sh.getRange(nr, 1, 1, 11).getValues()[0];
  var uruchomien = (Number(w[7]) || 0) + (Number(dane.uruchomienia) || 0);
  var dokumentow = (Number(w[8]) || 0) + (Number(dane.dokumenty)    || 0);
  var minut      = (Number(w[9]) || 0) + (Number(dane.minuty)       || 0);

  sh.getRange(nr, 5, 1, 6).setValues([[teraz,
      dane.wersja || w[5], dane.system || w[6],
      uruchomien, dokumentow, minut]]);

  // Status sesji
  var wazne = w[3] instanceof Date ? w[3] : (w[3] ? new Date(w[3]) : null);
  var dzis = new Date(); dzis.setHours(0, 0, 0, 0);
  var aktywna = !!(wazne && wazne >= dzis);

  return {
    status: aktywna ? "ok" : "wygasla",
    imie: String(w[1] || ""),
    rejon: String(w[2] || ""),
    wazne_do: wazne ? Utilities.formatDate(wazne, "Europe/Warsaw", "yyyy-MM-dd") : "",
    nieobecnosci: _nieobecnosci(ss, kod)
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

function _log(ss, kod, zdarzenie, szczegoly) {
  try {
    _zakladka(ss, ZAKLADKA_LOG, []).appendRow([new Date(), kod, zdarzenie, szczegoly || ""]);
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
  blokada.tryLock(20000);
  try {
    var dane = JSON.parse(e.postData.contents || "{}");

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
             + String(dane.akcja) + " — sekret w paczce rozni sie od SEKRETY_PMT");
      }
    }
    // Kontrola wersji (WYMAGANA_WERSJA, domyślnie wyłączona).
    if (AKCJE_PODPISANE.indexOf(String(dane.akcja)) >= 0
        && wersjaZaStara(dane.wersja)) {
      return _json({ status: "blad",
        opis: "Ta wersja programu nie jest juz obslugiwana. Pobierz nowa wersje." });
    }

    // Aplikacja na telefon zostala wycofana (3.24.0) — backend obsluguje
    // wylacznie program na komputerze: piec akcji, wszystkie podpisane.
    switch (dane.akcja) {
      case "logowanie":   return _json(logowanie(dane));
      case "puls":        return _json(obsluzPuls(dane));
      case "sesja":       return _json(zapiszSesje(dane));
      case "zmien_haslo": return _json(zmienHaslo(dane));
      case "reset_hasla": return _json(resetHasla(dane));
      default: return _json({ status: "blad", opis: "Nieznana akcja" });
    }
  } catch (err) {
    return _json({ status: "blad", opis: String(err) });
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
         "za stara wersja " + wersjaKlienta);
    return { status: "blad",
             opis: "Ta wersja programu (" + wersjaKlienta + ") nie jest juz obslugiwana. " +
                   "Pobierz aktualna wersje ze strony wydania." };
  }
  var haslo = String(dane.haslo || dane.telefon || "").trim();
  if (!haslo) return { status: "blad", opis: "Podaj haslo albo numer telefonu" };
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
      if (!hashBaza && !telBaza)
        return { status: "blad",
                 opis: "To konto nie ma telefonu w bazie — administrator musi go uzupelnic" };
      if (hashBaza && telBaza && tel.length >= 9 &&
          telBaza.slice(-9) === tel.slice(-9))
        return { status: "blad",
                 opis: "To konto ma ustawione haslo — zaloguj sie haslem. " +
                       "Numer telefonu sluzy tylko do zmiany lub resetu hasla." };
      return { status: "blad",
               opis: hashBaza ? "Nieprawidlowe haslo" : "Nieprawidlowy numer telefonu" };
    }
    var zrodlo = String(dane.zrodlo || "www");
    _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "logowanie_" + zrodlo,
         "OK" + (haslem ? " (haslo)" : " (telefon)"));
    return { status: "ok", imie: String(w[i][1] || "") };
  }
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
  if (!stare)          return { status: "blad", opis: "Podaj dotychczasowe haslo albo telefon" };
  if (nowe.length < 6) return { status: "blad", opis: "Nowe haslo: min. 6 znakow" };
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
      var powod = hashBaza ? (telPasuje ? "telefon zamiast hasla" : "zle haslo")
                           : "zly telefon";
      _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "zmiana_hasla",
           "ODRZUCONA (" + powod + ")");
      return { status: "blad", opis: hashBaza
               ? (telPasuje
                  ? "To konto ma ustawione haslo — podaj dotychczasowe haslo " +
                    "albo uzyj „Nie pamietam hasla” w oknie logowania"
                  : "Dotychczasowe haslo nie pasuje")
               : "Numer telefonu nie zgadza sie z kartoteka" };
    }
    sh.getRange(i + 2, 14).setValue(_hash(kod, nowe));
    _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "zmiana_hasla",
         "OK (" + (haslem ? "haslem" : "telefonem") + ")");
    return { status: "ok" };
  }
  return { status: "blad", opis: "Nie znaleziono takiego kodu" };
}


/* ====== REJESTR SESJI: kto, kiedy i jak dlugo pracowal ================= */
function zapiszSesje(dane) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var kod = String(dane.kod || "").trim();
  var imie = "";
  var shU = ss.getSheetByName(ZAKLADKA_UZYTKOWNICY);
  if (shU && shU.getLastRow() > 1) {
    var w = shU.getRange(2, 1, shU.getLastRow() - 1, 2).getValues();
    for (var i = 0; i < w.length; i++) {
      if (String(w[i][0]).trim() === kod) { imie = String(w[i][1] || ""); break; }
    }
  }
  var nazwy = { logowanie: "zalogowanie", wylogowanie: "wylogowanie",
                zamkniecie: "zamkniecie programu" };
  _zakladka(ss, ZAKLADKA_SESJE,
    ["Kiedy", "Kod", "Imie i nazwisko", "Zdarzenie", "Czas sesji (min)",
     "Dokumenty w sesji", "Plany wizyt", "Wersja programu"])
    .appendRow([new Date(), kod, imie,
                nazwy[String(dane.rodzaj)] || String(dane.rodzaj || "?"),
                Number(dane.minuty) || "",
                Number(dane.dokumenty) || "", Number(dane.plany) || "",
                String(dane.wersja || "")]);
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
var RESET_PROB_NA_KOD_NA_GODZINE     = 5;
var RESET_PROB_LACZNIE_NA_GODZINE    = 30;
var RESET_OKNO_SEKUND                = 3600;

/* Zlicza probe pod kluczem i mowi, czy limit juz przekroczony. Licznik zyje
   RESET_OKNO_SEKUND od OSTATNIEJ proby (kazda proba odnawia okno), wiec
   ponawianie w kolko nie skraca blokady. doPost trzyma ScriptLock, wiec
   odczyt-zapis licznika nie sciga sie z innym wywolaniem. */
function _zaDuzoProb(klucz, limit) {
  var pam = CacheService.getScriptCache();
  var ile = (Number(pam.get(klucz)) || 0) + 1;
  pam.put(klucz, String(ile), RESET_OKNO_SEKUND);
  return ile > limit;
}

function resetHasla(dane) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var kod = String(dane.kod || "").trim();
  var tel = String(dane.telefon || "").replace(/\D/g, "");
  var kluczKodu = "reset:" + kod.replace(/[^0-9A-Za-z]/g, "").slice(0, 32);
  if (_zaDuzoProb("reset:wszyscy", RESET_PROB_LACZNIE_NA_GODZINE) ||
      _zaDuzoProb(kluczKodu, RESET_PROB_NA_KOD_NA_GODZINE)) {
    _log(ss, kod, "reset_hasla", "ODRZUCONA (za duzo prob)");
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
    var telBaza = String(w[i][12] || "").replace(/\D/g, "");
    if (!telBaza) {
      _log(ss, kod, "reset_hasla", "ODRZUCONA (konto bez telefonu)");
      return { status: "blad", opis: "Konto nie ma telefonu w kartotece — zglos sie do administratora" };
    }
    if (tel.length < 9 || telBaza.slice(-9) !== tel.slice(-9)) {
      _log(ss, kod, "reset_hasla", "ODRZUCONA (zly telefon)");
      return { status: "blad", opis: "Numer telefonu nie zgadza sie z kartoteka" };
    }
    sh.getRange(i + 2, 14).setValue("");     // kasujemy hash hasla
    _log(ss, kod, "reset_hasla", "OK");
    return { status: "ok",
             opis: "Haslo skasowane. Zaloguj sie numerem telefonu i ustaw nowe haslo." };
  }
  _log(ss, kod, "reset_hasla", "ODRZUCONA (nieznany kod)");
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
