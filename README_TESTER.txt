═══════════════════════════════════════════════════════════════════════
  PMT PLANER 3.22.0 — WERSJA TESTOWA
  krótka instrukcja dla testera
═══════════════════════════════════════════════════════════════════════

CO TO ZA WYDANIE
  Robocza paczka przygotowana bezpośrednio dla Ciebie. NIE pochodzi
  z GitHuba, nie ma jej w Releases i nikt inny jej nie dostał.
  Numer wersji: 3.22.0.

URUCHOMIENIE ZE ŹRÓDEŁ (Windows)
  1. Zainstaluj Pythona 3.13 (nie 3.14). W instalatorze zaznacz
     „Add python.exe to PATH".
  2. Rozpakuj CAŁĄ paczkę do jednego, pustego folderu, np. C:\PMT.
  3. Otwórz w tym folderze wiersz poleceń i wpisz:
        py -3.13 -m pip install -r requirements.txt
  4. Uruchom program:
        py -3.13 PMT_Delegacje.py

WŁASNY PLIK WYKONYWALNY
  W tym samym folderze:
        py -3.13 zbuduj.py --folder
  Gotowy program: dist\PMT_Planer\PMT_Planer.exe
  Przenosi się i pakuje CAŁY folder dist\PMT_Planer, nigdy sam plik .exe.

PLIK menedzer.txt — ZRÓB GO PRZED BUDOWANIEM
  Obok zbuduj.py musi leżeć plik menedzer.txt: jedna linia, imię
  i nazwisko przełożonego, nic więcej. Wystarczy Notatnik.
  Bez tego pliku rubryka MENEDŻER na delegacjach wyjdzie pusta.
  W oknie programu nie ma pola na to nazwisko — plik jest jedyną drogą.
  Gdy uruchamiasz ze źródeł, połóż menedzer.txt obok PMT_Delegacje.py.

KONTO TESTOWE
  W arkuszu użytkowników konto, którym się logujesz, musi mieć wypełnioną
  rubrykę „Ważne do" (data). Puste pole program czyta jako konto wygasłe
  i zamyka się z komunikatem o wygasłym dostępie.

POMINIĘCIE ANIMACJI STARTOWEJ
  Raz: kliknij myszą albo naciśnij dowolny klawisz w trakcie animacji.
  Na stałe: połóż pusty plik BEZ_INTRA.txt obok programu albo w swoim
  katalogu użytkownika (C:\Users\TwojeKonto).

GDZIE LĄDUJĄ DOKUMENTY
  Na Pulpicie, w folderze Rozliczenie_Imie_Nazwisko_miesiąc_rok
  (np. Rozliczenie_Jan_Kowalski_czerwiec_2026r). W środku: PDF-y delegacji,
  rozliczenie wydatków i podgląd tras w pliku HTML.

GDY WINDOWS OSTRZEGA PRZED NIEZNANYM PROGRAMEM
  Program nie ma podpisu cyfrowego, więc SmartScreen pokazuje niebieskie
  okno „System Windows ochronił Twój komputer". Kliknij „Więcej informacji",
  potem „Uruchom mimo to".
  Jeśli program znika albo blokada wraca: uruchamiaj ze źródeł (Python jest
  podpisany i nie bywa blokowany) albo poproś dział IT o wyjątek na folder
  programu. Więcej: BEZ_BLOKADY_WINDOWS.txt.

═══════════════════════════════════════════════════════════════════════
  DO SPRAWDZENIA
═══════════════════════════════════════════════════════════════════════
   1. Uruchom program. Oczekiwane: animacja startowa, a po niej okno
      logowania z polami LOGIN i HASŁO.
   2. Wpisz login i hasło, kliknij „Zaloguj". Oczekiwane: okno główne,
      Twoje imię w górnym pasku, po lewej menu z pozycją „Nowa Wyprawa".
   3. Kliknij „Nowa Wyprawa" i wypełnij: imię i nazwisko, PESEL (11 cyfr),
      adres zamieszkania, stanowisko, kwotę docelową, miesiąc rozliczenia
      w formacie MM.RRRR, pojemność silnika. Oczekiwane: program przyjmuje
      wpisy.
   4. Zostaw celowo puste jedno pole i kliknij „Generuj PDF". Oczekiwane:
      okno „Uzupełnij dane" z nazwą brakującego pola, pole na czerwono,
      nic się nie generuje. Uzupełnij je.
   5. Kliknij „Generuj PDF" z kompletem danych. Oczekiwane: oś etapów
      przesuwa się do końca, mapa tras otwiera się w przeglądarce,
      a folder z dokumentami sam otwiera się na Pulpicie.
   6. Otwórz jedną delegację z tego folderu. Oczekiwane: Twoje dane,
      rozpisana trasa, wypełniona rubryka MENEDŻER, jedna strona.
   7. Zsumuj kwoty ze wszystkich delegacji. Oczekiwane: suma równa kwocie
      docelowej co do grosza.
   8. Obejrzyj mapę, która otworzyła się w przeglądarce (plik
      Trasy_Mapa.html z tego folderu). Oczekiwane: pierwszy i ostatni
      punkt każdego dnia to Twój adres.
   9. Kliknij „Motyw" w górnym pasku. Oczekiwane: cały program zmienia
      barwy; żadne okno ani przycisk nie zostaje w poprzednich.
  10. Wejdź w „Plan Wizyt", kliknij „Excel" i wczytaj plik z punktami,
      potem „Zaplanuj wizyty". Oczekiwane: wizyty rozłożone na kalendarzu.
  11. Kliknij „Tryb Trasy", a potem „DOJECHAŁEM — ODHACZ WIZYTĘ".
      Oczekiwane: wizyta oznaczona, program przechodzi do następnej.
  12. Kliknij „Delegacja z planu". Oczekiwane: na Pulpicie powstaje osobny
      folder Rozliczenie_z_planu_... z dokumentami z zaplanowanych wizyt.
  13. Wejdź w „Kopia zapasowa", kliknij „Eksportuj kopię zapasową", a potem
      „Przywróć z kopii" tym samym plikiem. Oczekiwane: plan i punkty
      wracają w komplecie.
  14. Wejdź w „Twoja praca". Oczekiwane: liczby wizyt i delegacji zgodne
      z tym, co przed chwilą zrobiłeś.
  15. Kliknij gwiazdkę w górnym pasku. Oczekiwane: otwiera się karta
      testera z listą rzeczy do sprawdzenia i licznikiem punktów.
  16. Kliknij „Hasło" w górnym pasku i ustaw nowe. Oczekiwane: potwierdzenie
      zmiany; nowe hasło działa przy następnym logowaniu.
  17. Kliknij „Zgłoś błąd". Oczekiwane: otwiera się program pocztowy
      z wpisanym adresem.
  18. Kliknij „Wyloguj", zaloguj się ponownie. Oczekiwane: wracają Twoje
      dane, plan i adres — nie cudze i nie puste.
  19. Zamknij program, połóż pusty plik BEZ_INTRA.txt obok niego i uruchom
      ponownie. Oczekiwane: okno logowania od razu, bez animacji.
  20. Wejdź w „O programie". Oczekiwane: numer wersji 3.22.0.

  Co zgłaszać: numer punktu, co kliknąłeś, co się stało, a czego
  oczekiwałeś. Jeśli program się zamknął, dołącz plik
  PMT_diagnostyka_animacji.txt ze swojego katalogu użytkownika.
