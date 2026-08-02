/**********************************************************************
 *  PMT Planer — backend w Google Apps Script
 *
 *  CO TO ROBI: odbiera "pulsy" od programu (kto, jaka wersja, ile
 *  dokumentów itd.), zapisuje je w arkuszu i odsyła programowi jego
 *  status: do kiedy ważna sesja + lista nieobecności (urlopy/L4/
 *  zastępstwa) do uwzględnienia w planowaniu tras.
 *
 *  JAK URUCHOMIĆ (raz, ~5 minut):
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
 *********************************************************************/

var ZAKLADKA_UZYTKOWNICY  = "Uzytkownicy";
var ZAKLADKA_NIEOBECNOSCI = "Nieobecnosci";
var ZAKLADKA_LOG          = "Log";

// Ile dni sesji dostaje NOWY kod przy pierwszym kontakcie, zanim
// zdążysz ręcznie ustawić datę (0 = nowy kod od razu zablokowany).
var DOMYSLNE_DNI_NOWEGO = 30;

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
function doPost(e) {
  var blokada = LockService.getScriptLock();
  blokada.tryLock(20000);   // pulsy z wielu komputerów naraz — po kolei
  try {
    var dane = JSON.parse(e.postData.contents || "{}");
    if (dane.akcja === "puls") return _json(obsluzPuls(dane));
    return _json({ status: "blad", opis: "Nieznana akcja" });
  } catch (err) {
    return _json({ status: "blad", opis: String(err) });
  } finally {
    blokada.releaseLock();
  }
}

// GET zostawiamy jako prosty test "czy żyje" — otwarcie adresu /exec
// w przeglądarce ma pokazać znak życia, nic więcej.
function doGet(e) {
  return _json({ status: "ok", opis: "PMT backend dziala" });
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
    nieobecnosci: _nieobecnosci(ss)
  };
}

/* ------------------------------------------------------------------ */
/*  Nieobecności: urlopy / L4 / zastępstwa                            */
/*  Zwracamy tylko bieżące i przyszłe — historia programu nie obchodzi */
/* ------------------------------------------------------------------ */
function _nieobecnosci(ss) {
  var sh = ss.getSheetByName(ZAKLADKA_NIEOBECNOSCI);
  if (!sh || sh.getLastRow() < 2) return [];
  var dzis = new Date(); dzis.setHours(0, 0, 0, 0);
  var wynik = [];
  var dane = sh.getRange(2, 1, sh.getLastRow() - 1, 6).getValues();
  for (var i = 0; i < dane.length; i++) {
    var od = dane[i][1], doD = dane[i][2];
    if (!(od instanceof Date) || !(doD instanceof Date)) continue;
    if (doD < dzis) continue;                       // już minęła
    wynik.push({
      kod: String(dane[i][0]).trim(),
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


/* ================================================================== */
/*  v2 — ROZSZERZENIA: planogramy, wizyty, analiza AI                 */
/*                                                                    */
/*  KLUCZ API (do analizy zdjęć przez Claude):                        */
/*  Edytor Apps Script → Ustawienia projektu (koło zębate) →          */
/*  Właściwości skryptu → Dodaj: nazwa ANTHROPIC_KLUCZ, wartość =     */
/*  klucz z console.anthropic.com. Klucz zostaje na serwerze Google — */
/*  telefony go nigdy nie widzą.                                      */
/*  PO WKLEJENIU TEJ WERSJI: uruchom raz "inicjalizuj" i zrób nowe    */
/*  wdrożenie (Wdróż → Zarządzaj → Wersja: Nowa).                     */
/* ================================================================== */

var ZAKLADKA_PLANOGRAMY = "Planogramy";
var ZAKLADKA_WIZYTY     = "Wizyty";
var ZAKLADKA_REJONIZACJA = "Rejonizacja";
var ZAKLADKA_PRODUKTY = "Produkty";
var ZAKLADKA_ZGLOSZENIA = "Zgloszenia";

function inicjalizuj_v2() {
  // kolumna N (Haslo hash) w Uzytkownicy — dopisz naglowek, jesli go nie ma
  var ssU = SpreadsheetApp.getActiveSpreadsheet();
  var shU = ssU.getSheetByName(ZAKLADKA_UZYTKOWNICY);
  if (shU && !String(shU.getRange(1, 14).getValue())) shU.getRange(1, 14).setValue("Haslo hash");
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  inicjalizuj();
  _zakladka(ss, ZAKLADKA_PLANOGRAMY,
    ["Id", "Nazwa", "Siec/Sklep", "Obowiazuje od", "Pozycje JSON"]);
  _zakladka(ss, ZAKLADKA_WIZYTY,
    ["Kiedy", "Kod", "Sklep", "Planogram", "Dostepnosc przed %",
     "Dostepnosc po %", "Braki przed", "Braki po", "Poprawki czlowieka", "Uwagi"]);
  _zakladka(ss, ZAKLADKA_REJONIZACJA,
    ["Siec", "Miasto", "Ulica", "Kod", "Zadan"]);
  _zakladka(ss, ZAKLADKA_PRODUKTY,
    ["Kod", "Nazwa", "EAN", "Foto URL"]);
  _zakladka(ss, ZAKLADKA_ZGLOSZENIA,
    ["Kiedy", "Kod", "Sklep", "Opis", "Foto URL"]);
}

/* --- rozszerzony rozdzielacz akcji (podmienia doPost z v1) --------- */
function doPost(e) {
  var blokada = LockService.getScriptLock();
  blokada.tryLock(20000);
  try {
    var dane = JSON.parse(e.postData.contents || "{}");
    switch (dane.akcja) {
      case "puls":               return _json(obsluzPuls(dane));
      case "pobierz_planogramy": return _json(pobierzPlanogramy());
      case "zapisz_planogram":   return _json(zapiszPlanogram(dane));
      case "analiza_polki":      return _json(analizaPolki(dane));
      case "zapisz_wizyte":      return _json(zapiszWizyte(dane));
      case "moje_sklepy":        return _json(mojeSklepy(dane));
      case "logowanie":          return _json(logowanie(dane));
      case "produkty":           return _json(produkty());
      case "zapisz_produkt":      return _json(zapiszProdukt(dane));
      case "ostatnia_wizyta":     return _json(ostatniaWizyta(dane));
      case "zgloszenie":          return _json(zgloszenie(dane));
      case "zmien_haslo":         return _json(zmienHaslo(dane));
      default: return _json({ status: "blad", opis: "Nieznana akcja" });
    }
  } catch (err) {
    return _json({ status: "blad", opis: String(err) });
  } finally {
    blokada.releaseLock();
  }
}

/* --- planogramy: raz sfotografowane i zatwierdzone = dane ---------- */
function pobierzPlanogramy() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ZAKLADKA_PLANOGRAMY);
  if (!sh || sh.getLastRow() < 2) return { status: "ok", planogramy: [] };
  var w = sh.getRange(2, 1, sh.getLastRow() - 1, 5).getValues();
  var lista = [];
  for (var i = 0; i < w.length; i++) {
    if (!w[i][0]) continue;
    var pozycje = [];
    try { pozycje = JSON.parse(w[i][4] || "[]"); } catch (e) {}
    lista.push({ id: String(w[i][0]), nazwa: String(w[i][1]),
                 sklep: String(w[i][2]), pozycje: pozycje });
  }
  return { status: "ok", planogramy: lista };
}

function zapiszPlanogram(dane) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = _zakladka(ss, ZAKLADKA_PLANOGRAMY, []);
  var id = "PG" + new Date().getTime();
  sh.appendRow([id, String(dane.nazwa || "Bez nazwy"),
                String(dane.sklep || ""), new Date(),
                JSON.stringify(dane.pozycje || [])]);
  _log(ss, dane.kod || "?", "nowy_planogram", id + " " + (dane.nazwa || ""));
  return { status: "ok", id: id };
}

/* --- analiza zdjęcia przez Claude (klucz zostaje na serwerze) ------ */
function analizaPolki(dane) {
  var klucz = PropertiesService.getScriptProperties().getProperty("ANTHROPIC_KLUCZ");
  if (!klucz) return { status: "blad", opis: "Brak klucza: ustaw ANTHROPIC_KLUCZ we Wlasciwosciach skryptu" };

  // tryb "planogram": czytamy planogram do listy pozycji
  // tryb "polka": porownujemy zdjecie polki z przekazana lista pozycji
  var tryb = dane.tryb === "planogram" ? "planogram" : (dane.tryb === "ean" ? "ean" : "polka");
  var polecenie;
  if (tryb === "ean") {
    polecenie = "Na zdjeciu jest kod kreskowy produktu. Odczytaj CYFRY kodu EAN " +
      "(13 lub 8 cyfr, zwykle wydrukowane pod kreskami). " +
      "Odpowiedz WYLACZNIE poprawnym JSON: {\"ean\":\"same cyfry\",\"pewnosc\":0.0-1.0}";
  } else if (tryb === "planogram") {
    polecenie = "Na zdjeciu jest planogram polki (schemat ulozenia produktow). " +
      "Odczytaj WSZYSTKIE pozycje rzad po rzedzie, od gornego, kazdy rzad od lewej. " +
      "Odpowiedz WYLACZNIE poprawnym JSON, bez zadnego innego tekstu, w formacie: " +
      '{"pozycje":[{"rzad":1,"nr":1,"produkt":"nazwa i wariant","kod":"kod indeksu jesli widoczny","ean":"kod EAN jesli widoczny, inaczej pusty","pewnosc":0.0-1.0}]}';
  } else {
    polecenie = "OBRAZ 1 to zdjecie realnej polki sklepowej." +
      ((dane.strony_b64 || []).length ? " KOLEJNE OBRAZY to strony planogramu (wzorzec ulozenia) — uzyj ich do dopasowania." : "") +
      " Planogram jako lista (pola rzad = rzad od gory, nr = pozycja od lewej): " +
      JSON.stringify(dane.pozycje || []) + ". " +
      "METODA (system kontroli brakow OOS): " +
      "KROK A: znajdz na OBRAZIE 1 WSZYSTKIE puste miejsca: biala karta popychacza POS, wolna szczelina, przerwa, brak paczki w prowadnicy. " +
      "KROK B: kazde puste miejsce zlokalizuj: ktory rzad od gory, ktora pozycja od lewej, jakie marki stoja obok. " +
      "KROK C: dopasuj puste miejsca do planogramu (rzad+nr oraz sasiedzi) i wskaz KODY produktow, ktorych brakuje. " +
      "ZASADY: 'brak' dostaja WYLACZNIE pozycje dopasowane do pustych miejsc z kroku A. " +
      "Gdy dopasowanie kodu niepewne — wybierz najbardziej prawdopodobny, obniz pewnosc, " +
      "a w 'uwaga' podaj lokalizacje (np. 'rzad 2, poz 5, obok Camel'). " +
      "Pozycji obecnych ('jest') NIE wypisuj — beda domyslne. " +
      "DODATKOWO: (a) opisz siatke ZDJECIA polki: ile rzedow widac i ile pozycji w kazdym rzedzie; " +
      "(b) dla kazdego braku podaj rzad_foto (od gory, na ZDJECIU) i poz_foto (od lewej); " +
      "(c) jako 'rada' napisz JEDNO zdanie trenera merchandisingu po polsku o stanie tej polki " +
      "(np. obrocone etykiety, krzywe facingi, dobra robota gdy porzadek). " +
      "Odpowiedz WYLACZNIE poprawnym JSON: " +
      '{"pozycje":[{"kod":"...","status":"brak","pewnosc":0.0-1.0,"uwaga":"max 8 slow","rzad_foto":1,"poz_foto":1}],' +
      '"siatka":{"rzedy":1,"pozycje_w_rzedach":[1]},"rada":"..."}';
  }

  var tresci = [{ type: "image", source: { type: "base64",
      media_type: dane.typ_obrazu || "image/jpeg", data: dane.obraz_b64 } }];
  (dane.strony_b64 || []).slice(0, 2).forEach(function (s) {
    tresci.push({ type: "image", source: { type: "base64",
        media_type: "image/jpeg", data: s } });
  });
  tresci.push({ type: "text", text: polecenie });
  var zapytanie = {
    model: "claude-sonnet-4-6",
    max_tokens: 16000,
    messages: [{ role: "user", content: tresci }]
  };

  var odp = UrlFetchApp.fetch("https://api.anthropic.com/v1/messages", {
    method: "post",
    contentType: "application/json",
    headers: { "x-api-key": klucz, "anthropic-version": "2023-06-01" },
    payload: JSON.stringify(zapytanie),
    muteHttpExceptions: true
  });
  if (odp.getResponseCode() !== 200) {
    return { status: "blad", opis: "API " + odp.getResponseCode() + ": " +
             odp.getContentText().slice(0, 300) };
  }
  var tresc = JSON.parse(odp.getContentText());
  var tekst = "";
  (tresc.content || []).forEach(function (b) { if (b.type === "text") tekst += b.text; });
  tekst = tekst.replace(/```json|```/g, "").trim();
  var wynik = _sparsujJson(tekst);
  if (wynik && tryb === "ean") return { status: "ok", tryb: tryb,
      ean: String(wynik.ean || "").replace(/\D/g, ""), pewnosc: wynik.pewnosc };
  if (wynik) return { status: "ok", tryb: tryb, pozycje: wynik.pozycje || [],
                      siatka: wynik.siatka || null, rada: wynik.rada || "" };
  return { status: "blad", opis: "Model nie zwrocil JSON", surowe: tekst.slice(0, 500) };
}

/* Parser odporny na drobne smieci i UCIETA odpowiedz: bierze fragment od
   pierwszego "{", a gdy JSON.parse pada — docina do ostatniego kompletnego
   obiektu w tablicy pozycje i domyka nawiasy. */
function _sparsujJson(t) {
  var od = t.indexOf("{");
  if (od < 0) return null;
  t = t.slice(od);
  try { return JSON.parse(t); } catch (e) {}
  var doKon = t.lastIndexOf("}");
  if (doKon > 0) { try { return JSON.parse(t.slice(0, doKon + 1)); } catch (e) {} }
  var ost = t.lastIndexOf("},");
  if (ost > 0) { try { return JSON.parse(t.slice(0, ost + 1) + "]}"); } catch (e) {} }
  return null;
}

/* --- raport wizyty: przed / po / delta ----------------------------- */
function zapiszWizyte(d) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = _zakladka(ss, ZAKLADKA_WIZYTY, []);
  sh.appendRow([new Date(), String(d.kod || ""), String(d.sklep || ""),
                String(d.planogram || ""),
                Number(d.dostepnosc_przed) || 0, Number(d.dostepnosc_po) || 0,
                (d.braki_przed || []).join(", "), (d.braki_po || []).join(", "),
                Number(d.poprawki) || 0, String(d.uwagi || "")]);
  _log(ss, d.kod || "?", "wizyta", (d.sklep || "") + " " +
       (Number(d.dostepnosc_przed) || 0) + "%->" + (Number(d.dostepnosc_po) || 0) + "%");
  return { status: "ok" };
}


/* --- rejonizacja: sklepy przypisane do kodu (dla aplikacji wizyt) --- */
function mojeSklepy(dane) {
  var kod = String(dane.kod || "").trim();
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ZAKLADKA_REJONIZACJA);
  if (!sh || sh.getLastRow() < 2) return { status: "ok", sklepy: [] };
  var w = sh.getRange(2, 1, sh.getLastRow() - 1, 5).getValues();
  var lista = [];
  for (var i = 0; i < w.length; i++) {
    if (String(w[i][3]).trim() !== kod) continue;
    lista.push({ siec: String(w[i][0]).trim(), miasto: String(w[i][1]).trim(),
                 ulica: String(w[i][2]).trim(), zadan: Number(w[i][4]) || 1 });
  }
  return { status: "ok", sklepy: lista };
}


/* --- logowanie: kod (login) + telefon (haslo testowe) --------------- */
/*  Telefon porownujemy po samych cyfrach (spacje/kreski bez znaczenia).*/
/*  UWAGA: konto musi miec wypelniona kolumne "Telefon" (M) w zakladce  */
/*  Uzytkownicy — konta bez telefonu nie zaloguja sie do aplikacji.     */
function logowanie(dane) {
  var kod = String(dane.kod || "").trim();
  var tel = String(dane.telefon || "").replace(/\D/g, "");
  if (!/^\d{5}$/.test(kod)) return { status: "blad", opis: "Kod musi miec 5 cyfr" };
  if (tel.length < 9)        return { status: "blad", opis: "Podaj 9-cyfrowy numer telefonu" };
  var haslo = String(dane.haslo || dane.telefon || "");
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ZAKLADKA_UZYTKOWNICY);
  if (!sh || sh.getLastRow() < 2) return { status: "blad", opis: "Brak bazy uzytkownikow" };
  var w = sh.getRange(2, 1, sh.getLastRow() - 1, 14).getValues();
  for (var i = 0; i < w.length; i++) {
    if (String(w[i][0]).trim() !== kod) continue;
    var hashBaza = String(w[i][13] || "").trim();     // kolumna N: Haslo hash
    if (hashBaza) {                                    // konto z ustawionym haslem
      if (_hash(kod, haslo) !== hashBaza)
        return { status: "blad", opis: "Nieprawidlowe haslo" };
    } else {                                           // przejsciowo: telefon
      var telBaza = String(w[i][12] || "").replace(/\D/g, "");
      if (!telBaza) return { status: "blad", opis: "To konto nie ma telefonu w bazie — administrator musi go uzupelnic" };
      if (telBaza.slice(-9) !== tel.slice(-9))
        return { status: "blad", opis: "Nieprawidlowy numer telefonu" };
    }
    _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "logowanie_www", "OK");
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

/* zmiana hasla: weryfikacja starym sposobem (haslo lub telefon), zapis hasha */
function zmienHaslo(dane) {
  var kod = String(dane.kod || "").trim();
  var stare = String(dane.stare_haslo || "");
  var nowe = String(dane.nowe_haslo || "");
  if (nowe.length < 6) return { status: "blad", opis: "Nowe haslo: min. 6 znakow" };
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ZAKLADKA_UZYTKOWNICY);
  var w = sh.getRange(2, 1, sh.getLastRow() - 1, 14).getValues();
  for (var i = 0; i < w.length; i++) {
    if (String(w[i][0]).trim() !== kod) continue;
    var hashBaza = String(w[i][13] || "").trim();
    var telBaza = String(w[i][12] || "").replace(/\D/g, "");
    var ok = hashBaza ? (_hash(kod, stare) === hashBaza)
                      : (telBaza && telBaza.slice(-9) === stare.replace(/\D/g, "").slice(-9));
    if (!ok) return { status: "blad", opis: "Weryfikacja nie powiodla sie" };
    sh.getRange(i + 2, 14).setValue(_hash(kod, nowe));
    _log(SpreadsheetApp.getActiveSpreadsheet(), kod, "zmiana_hasla", "OK");
    return { status: "ok" };
  }
  return { status: "blad", opis: "Nie znaleziono takiego kodu" };
}


/* --- baza produktow: kod -> nazwa / EAN / zdjecie (wklej eksport z SAP) --- */
function produkty() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ZAKLADKA_PRODUKTY);
  if (!sh || sh.getLastRow() < 2) return { status: "ok", produkty: [] };
  var w = sh.getRange(2, 1, sh.getLastRow() - 1, 4).getValues();
  var lista = [];
  for (var i = 0; i < w.length; i++) {
    if (!w[i][0]) continue;
    lista.push({ kod: String(w[i][0]).trim(), nazwa: String(w[i][1] || "").trim(),
                 ean: String(w[i][2] || "").trim(), foto: String(w[i][3] || "").trim() });
  }
  return { status: "ok", produkty: lista };
}


/* --- uzupelnienie produktu z terenu: EAN + zdjecie opakowania ---------- */
/*  Zdjecie laduje na Twoj Dysk Google (folder "PMT Produkty"), a wiersz   */
/*  w zakladce Produkty jest tworzony/aktualizowany po kodzie.             */
/*  UWAGA: pierwsze uzycie poprosi o nowa zgode (dostep do Dysku) —        */
/*  po wklejeniu skryptu uruchom raz "inicjalizuj_v2" i zaakceptuj.        */
function zapiszProdukt(dane) {
  var kod = String(dane.kod || "").trim();
  if (!kod) return { status: "blad", opis: "Brak kodu produktu" };
  var fotoUrl = "";
  if (dane.foto_b64) {
    var folder;
    var it = DriveApp.getFoldersByName("PMT Produkty");
    folder = it.hasNext() ? it.next() : DriveApp.createFolder("PMT Produkty");
    var blob = Utilities.newBlob(Utilities.base64Decode(dane.foto_b64),
                                 "image/jpeg", "produkt_" + kod + ".jpg");
    var plik = folder.createFile(blob);
    plik.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    fotoUrl = "https://drive.google.com/uc?export=view&id=" + plik.getId();
  }
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = _zakladka(ss, ZAKLADKA_PRODUKTY, ["Kod", "Nazwa", "EAN", "Foto URL"]);
  var w = sh.getDataRange().getValues();
  var nr = -1;
  for (var i = 1; i < w.length; i++) {
    if (String(w[i][0]).trim() === kod) { nr = i + 1; break; }
  }
  if (nr === -1) {
    sh.appendRow([kod, String(dane.nazwa || ""), String(dane.ean || ""), fotoUrl]);
  } else {
    if (dane.nazwa) sh.getRange(nr, 2).setValue(String(dane.nazwa));
    if (dane.ean)   sh.getRange(nr, 3).setValue(String(dane.ean));
    if (fotoUrl)    sh.getRange(nr, 4).setValue(fotoUrl);
  }
  _log(ss, dane.kod_uzytkownika || "?", "produkt", kod + " EAN:" + (dane.ean || "-") +
       (fotoUrl ? " +foto" : ""));
  return { status: "ok", foto: fotoUrl };
}


/* --- kontekst historyczny: ostatnia wizyta w danym sklepie -------------- */
function ostatniaWizyta(dane) {
  var sklep = String(dane.sklep || "").trim().toLowerCase();
  if (!sklep) return { status: "ok", wizyta: null };
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ZAKLADKA_WIZYTY);
  if (!sh || sh.getLastRow() < 2) return { status: "ok", wizyta: null };
  var w = sh.getRange(2, 1, sh.getLastRow() - 1, 10).getValues();
  for (var i = w.length - 1; i >= 0; i--) {          // od najnowszej
    if (String(w[i][2]).trim().toLowerCase() !== sklep) continue;
    return { status: "ok", wizyta: {
      kiedy: (w[i][0] instanceof Date)
             ? Utilities.formatDate(w[i][0], "Europe/Warsaw", "dd.MM.yyyy") : String(w[i][0]),
      przed: Number(w[i][4]) || 0, po: Number(w[i][5]) || 0,
      braki_po: String(w[i][7] || ""), uwagi: String(w[i][9] || "") } };
  }
  return { status: "ok", wizyta: null };
}

/* --- szybkie zgloszenie z terenu (konkurencja / nowosc / problem) ------- */
function zgloszenie(dane) {
  var fotoUrl = "";
  if (dane.foto_b64) {
    var it = DriveApp.getFoldersByName("PMT Zgloszenia");
    var folder = it.hasNext() ? it.next() : DriveApp.createFolder("PMT Zgloszenia");
    var plik = folder.createFile(Utilities.newBlob(Utilities.base64Decode(dane.foto_b64),
                                 "image/jpeg", "zgloszenie_" + new Date().getTime() + ".jpg"));
    plik.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
    fotoUrl = "https://drive.google.com/uc?export=view&id=" + plik.getId();
  }
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  _zakladka(ss, ZAKLADKA_ZGLOSZENIA, ["Kiedy", "Kod", "Sklep", "Opis", "Foto URL"])
    .appendRow([new Date(), String(dane.kod || ""), String(dane.sklep || ""),
                String(dane.opis || ""), fotoUrl]);
  _log(ss, dane.kod || "?", "zgloszenie", (dane.sklep || "") + " " + (dane.opis || "").slice(0, 60));
  return { status: "ok" };
}


/* ====================== PULPIT ADMINISTRATORA ========================== */
/*  W arkuszu pojawia sie menu "PMT" -> "Odswiez pulpit". Buduje zakladke  */
/*  Pulpit: statystyki per osoba, sklepy-alerty, podsumowanie tygodnia.    */
function onOpen() {
  SpreadsheetApp.getUi().createMenu("PMT")
    .addItem("Odswiez pulpit", "odswiezPulpit")
    .addToUi();
}

function odswiezPulpit() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var shW = ss.getSheetByName(ZAKLADKA_WIZYTY);
  var shU = ss.getSheetByName(ZAKLADKA_UZYTKOWNICY);
  var p = ss.getSheetByName("Pulpit") || ss.insertSheet("Pulpit", 0);
  p.clear();
  var teraz = new Date(), tydzien = new Date(teraz.getTime() - 7 * 864e5);
  var imiona = {};
  if (shU && shU.getLastRow() > 1)
    shU.getRange(2, 1, shU.getLastRow() - 1, 2).getValues()
       .forEach(function (r) { imiona[String(r[0]).trim()] = String(r[1] || ""); });
  var wiersze = (shW && shW.getLastRow() > 1)
    ? shW.getRange(2, 1, shW.getLastRow() - 1, 10).getValues() : [];

  var osoby = {}, sklepy = {};
  wiersze.forEach(function (r) {
    var kiedy = (r[0] instanceof Date) ? r[0] : new Date(r[0]);
    var kod = String(r[1]).trim(), sklep = String(r[2]).trim();
    var po = Number(r[5]) || 0;
    var o = osoby[kod] = osoby[kod] || { razem: 0, tydzien: 0, sumaPo: 0 };
    o.razem++; o.sumaPo += po;
    if (kiedy >= tydzien) o.tydzien++;
    var s = sklepy[sklep] = sklepy[sklep] || [];
    s.push({ kiedy: kiedy, po: po });
  });

  p.getRange(1, 1).setValue("PULPIT PMT — stan na " +
    Utilities.formatDate(teraz, "Europe/Warsaw", "dd.MM.yyyy HH:mm"))
    .setFontWeight("bold").setFontSize(13);

  // --- tabela: osoby ---
  p.getRange(3, 1, 1, 5).setValues([["Kod", "Osoba", "Wizyt (7 dni)", "Wizyt lacznie", "Srednia dostepnosc po"]])
    .setFontWeight("bold").setBackground("#0F172A").setFontColor("#FFFFFF");
  var dane = Object.keys(osoby).sort().map(function (k) {
    var o = osoby[k];
    return [k, imiona[k] || "?", o.tydzien, o.razem,
            o.razem ? Math.round(o.sumaPo / o.razem) + "%" : "-"];
  });
  if (dane.length) p.getRange(4, 1, dane.length, 5).setValues(dane);

  // --- alerty: sklepy ze srednia z 3 ostatnich wizyt < 70% ---
  var w0 = 5 + dane.length + 1;
  p.getRange(w0, 1).setValue("ALERTY — sklepy ponizej 70% (3 ostatnie wizyty)")
    .setFontWeight("bold").setFontColor("#B91C1C");
  var alerty = [];
  Object.keys(sklepy).forEach(function (s) {
    var ost = sklepy[s].sort(function (a, b) { return a.kiedy - b.kiedy; }).slice(-3);
    var sr = ost.reduce(function (x, y) { return x + y.po; }, 0) / ost.length;
    if (ost.length >= 2 && sr < 70) alerty.push([s, Math.round(sr) + "%", ost.length + " wizyt"]);
  });
  if (alerty.length) p.getRange(w0 + 1, 1, alerty.length, 3).setValues(alerty);
  else p.getRange(w0 + 1, 1).setValue("Brak alertow — wszystkie sklepy powyzej progu.");
  p.autoResizeColumns(1, 5);
  p.setFrozenRows(3);
}
