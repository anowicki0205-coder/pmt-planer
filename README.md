# PMT — komplet systemu (program v3.24.0)

> **Wydanie i wdrożenie krok po kroku: `WYDANIE.txt`.** Mapa plików: `START_TUTAJ.txt`.
> Budowanie: `INSTRUKCJA_BUDOWY.txt` · Backend: `BACKEND_APPS_SCRIPT.txt`
> Blokowanie przez Windows: `BEZ_BLOKADY_WINDOWS.txt`
> Testy przed wydaniem: `python testy_pmt.py`

## Co zmieniła wersja 3.24.0 (względem 3.22.0)

| Obszar | Zmiana |
|---|---|
| Wygląd | nowy ekran programu (`nowy_wyglad.py` na widżetach z `prototyp/`), stare okno App zostaje pod spodem tylko jako pojemnik na panele (przełącznik `--stary` zniknął) |
| Start | program staje na miesiącu, który minął (w październiku — wrzesień), z pojemnością „powyżej 900 cm³”; ręczna zmiana pojemności obowiązuje do końca sesji |
| Kompas | jedno kliknięcie uruchamia generowanie (w paczce testowej to samo kliknięcie od razu je przerywało); klik w trakcie pracy przerywa |
| Logowanie | nowe okno logowania (`okno_logowania.py`); dokumenty, podpis i wysyłka w `pmt_dokumenty.py`, `pmt_podpis.py`, `pmt_wysylka.py` |
| Mapa | mapa w skali regionu, kadr trasy dnia, podziałka mierząca prawdę |
| Silnik | sufit rozciągania odcinków, nieprzekraczalna podłoga linii prostej, ostrzeżenie liczbą przy zbyt niskiej kwocie |
| Budowanie | `build.yml` uruchamia `python zbuduj.py --folder` — jedno źródło prawdy dla CI i komputera; zbuduj.py sprawdza po budowie zawartość paczki i uzgadnia `wersja_exe.txt` ze źródłem |
| Backend | `apps_script_POPRAWIONY_v2.gs`: numer telefonu ustawia hasło tylko na koncie bez hasła, limit prób resetu z dziennikiem, puls oddaje tylko własne nieobecności; podpis obejmuje wszystkie akcje, z okresem przejściowym (`PODPIS_OBOWIAZKOWY`) i wpisem `podpis_zly` przy rozjeździe sekretu |
| Aplikacja na telefon | wycofana: z repozytorium zniknęły `pmt_wizyty.html`, `sw.js`, `manifest.webmanifest`, ikony PWA, `planogramy.json` i `produkty/`; z backendu — analiza zdjęć na klucz Anthropic, zgłoszenia i zdjęcia na Dysku, planogramy, wizyty i pulpit (1114 → 620 linii) |
| Sekret aplikacji | klucz HMAC podpisu zapytań poza kodem — plik `sekret.txt` obok programu (sekret `PMT_SEKRET` przy budowaniu), jak `menedzer.txt`; bez niego, po włączeniu `PODPIS_OBOWIAZKOWY`, program się nie zaloguje; ujawniony sekret wymienić — OBRÓT SEKRETU w `BACKEND_APPS_SCRIPT.txt` |
| Testy | `testy_pmt.py` — pełny zestaw i `--szybko` (wcześniej wisiał na modalnym zaproszeniu testera) |
| Wydanie | jedna instrukcja `WYDANIE.txt`; budowanie testowe (Actions → „Buduj wydanie” → Run workflow) daje paczkę do sprawdzenia bez wydania; paczka z tagu nie przejdzie z etykietą testową; macOS i Linux dostają nazwisko przełożonego |
| Odporność | wersja.txt podmieniony przez stronę firmowego proxy nie oferuje fałszywej aktualizacji ani nie zdejmuje blokady; podniesienie progu `min=` daje zawsze 14 dni okresu przejściowego |
| CI | testy bez internetu i z budżetem klatki liczonym do szybkości maszyny; nieudane sprawdzenie wypisuje się przy czerwonym znaczku |

## Co zmieniła wersja 3.21.0

| Obszar | Zmiana |
|---|---|
| Przełożony | nazwisko poza kodem — wyłącznie plik `menedzer.txt` obok programu (sekret `PMT_MENEDZER` przy budowaniu); w programie nie ma pola, nie trafia do repozytorium |
| Dane osobowe | plan wizyt, lista sklepów, dziennik, notatki dni i adres bazy należą do KONTA, nie do komputera; wylogowanie czyści imię, rejon, ważność sesji i listę nieobecności |
| Obowiązkowa aktualizacja | wiersze `min=` i `blokada=` w `wersja.txt`; okres przejściowy zamiast natychmiastowego odcięcia przy błędnej dacie; blokadę da się zdjąć zdalnie; automat wydania już jej nie kasuje |
| Windows | koniec z uruchamianiem PowerShella i z automatycznym kasowaniem plików z pulpitu/Pobranych/Dokumentów; wydania z CI budowane z metadanymi i bez UPX |
| Silnik | pełne rozpisanie zamówionej kwoty, dokument do 986,34 zł i 30 etapów |
| Testy | `testy_pmt.py` — 101 kontroli, w tym 12 scenariuszy generowania tras |

## Z czego składa się system

| Część | Pliki | Gdzie działa |
|---|---|---|
| Program na komputerze | `PMT_Delegacje.py` + moduły (`nowy_wyglad.py`, `okno_logowania.py`, `pmt_*.py`, `prototyp/`) | paczka z GitHub Releases u każdego użytkownika |
| Aktualizacje | `wersja.txt` (numer, `min=`, `blokada=`), `updater*.bat/.sh` | program czyta je z gałęzi main |
| Backend | `apps_script_POPRAWIONY_v2.gs` | Arkusz Google → Rozszerzenia → Apps Script |
| Budowanie | `zbuduj.py`, `.github/workflows/build.yml`, `requirements.txt` | GitHub Actions (tag `vX.Y.Z`) albo komputer |
| Testy | `testy_pmt.py`, `.github/workflows/testy.yml` | GitHub Actions przy każdej zmianie |

Backend obsługuje pięć akcji programu: `logowanie`, `puls`, `sesja`,
`zmien_haslo`, `reset_hasla`. Wdrożenie i wydanie: `WYDANIE.txt`.

---

## WAŻNE zasady, które kosztowały nas czas

- **W wydaniu (Release) mogą być TYLKO trzy pliki**: `PMT_Planer_Windows.zip`,
  `PMT_Planer_macOS.zip`, `PMT_Planer_Linux.zip`. Każdy dodatkowy `.zip`
  potrafił zmylić aktualizator starszych wersji (program pobierał złe archiwum
  i zgłaszał brak pliku `.exe`). Wersja 3.13.2 jest już na to odporna —
  szuka archiwum z "windows" w nazwie — ale zasada zostaje.
- **„Failed to load Python DLL … \\Temp\\…zip…\\python313.dll”** u użytkownika =
  uruchomił program W ŚRODKU archiwum ZIP otwartego w Eksploratorze (wypakował
  się sam `.exe`, bez `_internal`). Nie paczka, nie antywirus. Instrukcja dla
  użytkownika: BEZ_BLOKADY_WINDOWS.txt. Paczka od 3.21.2 zawiera podpowiedź
  `0_NAJPIERW_ROZPAKUJ_CALY_FOLDER.txt`, a `URUCHOM_PMT.bat` rozpoznaje tę sytuację.
- **„DLL load failed while importing iup: Zasady kontroli aplikacji zablokowały ten plik”** =
  Windows zablokował niepodpisany `.pyd` z fontTools (3.21.3). Od 3.21.4 fontTools jest
  instalowany czysto pythonowo (`--no-binary fonttools` w requirements.txt), CI tego pilnuje,
  a program bez biblioteki PDF startuje i mówi, co zrobić. Szczegóły: BEZ_BLOKADY_WINDOWS.txt.
- **Moduły obok programu są obowiązkowe** — pełna lista to `WYMAGANE` w `zbuduj.py`:
  `karta_testera.py`, `wyglad_3d.py`, `nowy_wyglad.py`,
  `okno_logowania.py`, `pmt_dokumenty.py`, `pmt_podpis.py`, `pmt_wysylka.py`,
  `logo_retro.py` i katalog `prototyp/` z widżetami `proto_*.py`. Bez nich program
  nie wystartuje albo traci kartę testera i głębię —
  tak wyglądała paczka 3.22.0 z GitHuba (bez nowego wyglądu). Animacja startowa
  (`intro_zywa_mapa.py`) zniknęła z programu w 3.23.0 — start idzie prosto do okna.
  Od 3.23.0 zbuduj.py zatrzymuje budowanie, gdy któregoś modułu nie ma w paczce.
- **Buildy na Pythonie 3.13**, nie 3.14 (błąd `python314.dll` u użytkowników).
- **Po każdej zmianie skryptu w arkuszu** trzeba wydać **nową wersję wdrożenia**,
  inaczej pod adresem `/exec` działa stary kod.
- **Dane osobowe** (kody, telefony, nazwisko przełożonego, sekret) nie trafiają do repozytorium.

---
