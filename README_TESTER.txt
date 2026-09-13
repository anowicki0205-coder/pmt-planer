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

NOWY WYGLĄD — URUCHOMIENIE
  Ze źródeł:     py -3.13 PMT_Delegacje.py
  Z pliku .exe:  PMT_Planer.exe
  Nowy wygląd jest jedynym ekranem programu — otwiera się sam, po
  zalogowaniu i animacji startowej.

NOWY WYGLĄD — CO W NIM DZIAŁA
  Dane pracownika   imię, PESEL, adres, stanowisko, pojemność silnika;
                    zapis do profilu (C:\Users\TwojeKonto\.pmt_uzytkownicy.json)
  Miesiąc           boczne zakładki paska górnego, PgUp i PgDn;
                    także przez granicę roku
  Dni bez pracy     kliknięcie kafla na taśmie; osobno dla każdego miesiąca
  Kwota, tryb pracy, limit dnia — wracają po zamknięciu okna
  Generowanie       kompas; ten sam silnik i te same PDF-y co stary ekran
  Przerwanie        kliknięcie kompasu w trakcie pracy albo Esc;
                    po przerwaniu w folderze nie ma żadnego pliku
  Postęp            łuk kompasu i plakietki: dane, trasy, PDF, mapa
  Kilometry         kafel REALNE DROGI / DROGI Z PAMIĘCI / SZACUNEK
  Taca              pliki z folderu wyniku, kwota co do grosza, liczba
                    delegacji, ścieżka folderu; kliknięcie kartki dnia
                    otwiera PDF jej polecenia wyjazdu
  Podpis i wysyłka  przyciski na tacy; te same okna co stary ekran
  Pieczęć „podpisana" na dniach dokumentów, które wróciły podpisane

NOWY WYGLĄD — CZEGO W NIM NIE MA
  Logowanie i kod dostępu. Pracownik pochodzi z profilu albo z pól
  wypełnionych na ekranie.
  Napis „Konto ważne do 31.12.2026" w pasku górnym — stały tekst,
  nie data Twojego konta.
  Plan wizyt, statystyki, kalendarz, aktualizacje, panel administratora.
  Szyna ikon po lewej nic nie przełącza.
  Przycisk otwierający mapę tras. Plik Trasy_Mapa.html leży w folderze
  wyniku, pod przyciskiem „Otwórz folder".
  Liczby pokazane przed naciśnięciem kompasu to szacunek.

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


  ── NOWY WYGLĄD ───────────────────────────────────────────────────────
  21. Uruchom program zwyczajnie. Oczekiwane: logowanie, animacja
      startowa, a po niej nowy ekran; w pasku górnym Twoje inicjały
      i data ważności konta.
  22. Uzupełnij PESEL, adres i stanowisko, ustaw pojemność silnika
      (imię jest z konta). Zamknij program i uruchom go ponownie.
      Oczekiwane: wszystkie pola i pojemność na swoim miejscu.
  23. Kliknij lewą, a potem prawą zakładkę paska górnego. To samo
      klawiszami PgUp i PgDn. Oczekiwane: zmienia się miesiąc na pasku
      i dni na taśmie; grudzień cofa się do listopada, styczeń do grudnia
      poprzedniego roku.
  24. Kliknij kilka kafli taśmy. Oczekiwane: oznaczone jako dni bez pracy;
      po przejściu na inny miesiąc i powrocie — te same dni.
  25. Wpisz kwotę i kliknij kompas. Oczekiwane: łuk idzie do końca,
      plakietki dane → trasy → PDF → mapa, a po zakończeniu wysuwa się
      taca z plikami, kwotą i folderem.
  26. Kliknij kompas jeszcze raz w trakcie pracy (albo naciśnij Esc).
      Oczekiwane: ekran wraca do stanu sprzed kliknięcia, w folderze
      wyniku nie ma żadnego nowego pliku.
  27. Na tacy kliknij kartkę jednego dnia, potem „Otwórz folder",
      potem „Podpisz" i „Wyślij". Oczekiwane: PDF tego dnia, folder
      z dokumentami, okno podpisu i okno wysyłki.
  28. Porównaj kwotę na tacy z sumą delegacji z punktu 7. Oczekiwane:
      ta sama liczba co do grosza.
  29. Kliknij po kolei ikony szyny po lewej — od góry: pinezka, kalendarz,
      słupki, strzałka, tarcza, warstwy; na dole domek i „i". Oczekiwane:
      Nowa wyprawa, Plan wizyt, Bilans miesiąca, Twoja praca, Kopia
      zapasowa, Ustawienia, powrót na ekran główny, O programie.
  30. W pasku górnym kliknij dzwonek, „Zgłoś błąd" i swoje inicjały.
      Oczekiwane: lista komunikatów, nowa wiadomość do zgłoszeń oraz menu
      z pozycjami: hasło, karta testera, animacja startowa, wylogowanie.

  Co zgłaszać: numer punktu, co kliknąłeś, co się stało, a czego
  oczekiwałeś. Jeśli program się zamknął, dołącz plik
  PMT_diagnostyka_animacji.txt ze swojego katalogu użytkownika.
