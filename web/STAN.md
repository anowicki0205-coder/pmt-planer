# PMT Planer — aplikacja webowa (budowa wersji finalnej)

Zasady od właściciela: silnik liczenia delegacji przenosimy W CAŁOŚCI z programu (nic nie zmieniamy);
NIE wypuszczamy na GitHub do czasu testów i zielonego światła (nie commitować, nie pushować, nie tworzyć PR);
bez płatnych rozwiązań; nr rejestracyjnych nie wprowadzamy; bez zbędnych informacji; jeden ekran bez przewijania;
przełożony = „Kierownik regionu" (nazwisko tylko z menedzer.txt/PMT_MENEDZER, nigdy w kodzie); PESEL tylko po stronie klienta;
sekretów (sekret.txt, pmt_kod.txt, PMT_SEKRET) nigdy do plików ani do repo.
Wygląd: makieta w ../scratchpad .../proto/i/final (Ciekłe szkło: bento + zorza; motywy Noc/Dzień) — wzorzec wyglądu.

## Architektura (zdecydowana)
- Silnik = ORYGINALNY kod Pythona z PMT_Delegacje.py, wyciągnięty DOSŁOWNIE narzędziem narzedzia/wyciagnij_silnik.py
  do silnik/pmt_silnik.py (AST: tylko węzły bez PyQt6, plus wywołania inicjalizujące moduł). Nie edytować ręcznie.
- Uruchamiany w przeglądarce przez Pyodide (Python 3.13 w WebAssembly) w Web Workerze; PDF-y: fpdf2 + Pillow + fonttools
  (paczki w vendor/paczki, czcionki Liberation Sans w silnik/fonty — metrycznie jak Arial; silnik szuka ich w tych samych ścieżkach co na Linuksie).
- Warstwa „host" (nie silnik): silnik/boot.py — sztuczki środowiskowe (HTTPSConnection, urlopen przez synchroniczny XHR w workerze,
  trwały dysk IDBFS dla cache'ów ~/.pmt_*.json) + silnik/most.py — odpowiednik GeneratorThread.run / _dane_do_generacji (klej, nie rachunek).
- Zgodność: testy/zgodnosc_silnika.py (oryginał kontra wyciąg: bajt w bajt), testy/pyodide_zgodnosc.mjs (niezmienniki w Pyodide).
  UWAGA ZNANA: wynik silnika zależy od ostatniego bitu funkcji matematycznych (glibc/musl/MSVC) — te same dane dają na różnych
  platformach INNY dobór miejscowości, ale ZAWSZE tę samą kwotę co do grosza, liczbę dni i limity. Nie do uniknięcia także między Windows a Linux.

## Stan (aktualizacja po pierwszej kompletnej wersji testowej)
- [x] wyciąg silnika (241 węzłów) identyczny z oryginałem na 3 scenariuszach (testy/zgodnosc_silnika.py)
- [x] silnik w Pyodide: generuj_trasy + generuj_pdfy; most.py/boot.py/worker/API; testy/silnik_przegladarka.js
- [x] interfejs z makiety „Ciekłe szkło" na prawdziwych danych: przed generowaniem (kwota, tryb, silnik, dni wolne w kalendarzu), generowanie
      z przerwaniem, miesiąc (kalendarz, kurtyna, dzień z trasą, dokumenty, kontrola, termin), Moje dane, nawigacja miesięcy, od nowa
- [x] podpis: pobierz → podpisz na gov.pl → wgraj (PDF z /ByteRange albo .xades/.xml/.sig/.p7s/.p7m); wysyłka: udostępnianie plików (telefon)
      albo pobranie + mailto (komputer); stan wysłane z cofnięciem
- [x] PWA: manifest, ikony, service worker (python narzedzia/zbuduj_sw.py po każdej zmianie plików); praca bez internetu sprawdzona
- [x] testy: silnik_przegladarka, przeplyw_app, uklad_app (8 rozdzielczości × 2 motywy), telefon_app, podpis_offline_app, przerwanie_i_od_nowa
- [x] PLAN WIZYT / „Dziś": import listy sklepów (.xlsx/.csv, kolumny rozpoznawane jak w programie), układanie planu silnikiem
      (planuj_wizyty / planuj_cyklicznie), kafel „Dziś" z listą wizyt, godzinami szacunkowymi, odhaczaniem (trwałe) i przyciskiem „Nawiguj"
      (Mapy Google, bez klucza); testy/plan_app.js (komputer i telefon: W=390 H=844 MOB=1)
- [x] LOGOWANIE i backend (Apps Script): js/dostep.js — ten sam backend i te same reguły co program (logowanie kod+hasło albo telefon,
      puls, rejestr sesji, zmiana i reset hasła; podpis HMAC sekretem z pliku sekret.txt; skrót hasła SHA-256 „PMT|kod|hasło”;
      bez sieci wchodzi tylko znane konto, do 45 dni od ostatniego kontaktu z serwerem). Dane rozdzielone na konta (każdy login ma
      własny profil, plan, dokumenty). Testy: testy/logowanie_app.js + testy/backend_mock.js (zamiennik reguł Apps Script).
      NIE SPRAWDZONE na prawdziwym Google (sandbox nie ma do niego dostępu) — pierwszy test na żywo patrz CZYTAJ_TO.txt.
- [x] widok Rok: klik w nazwę miesiąca → 12 miesięcy roku ze stanem (do wygenerowania / do podpisu / do wysłania / wysłane) i kwotą
- [x] wdrożenie na GitHub Pages: .github/workflows/web-pages.yml (tylko ręczny start — Actions → Run workflow, po scaleniu do głównej gałęzi; sekrety PMT_SEKRET i PMT_MENEDZER z sekretów repo)
- [x] JEDNA PEŁNA WERSJA wizualna (decyzja właściciela: bez wyboru trybów animacji; ruch zawsze włączony; zorza dwuprzebiegowa z wygładzaniem bikubicznym — bez pikselozy)
- [x] ŻYWY INTERFEJS (js/zywe.js, sygnały „pmt:*” z aplikacji): suwak kwoty, podgląd cieczy w dniach, lupa i fala w kalendarzu, malowanie dni wolnych,
      teatr trasy (▶, pojazd, przewijanie osi), duchy w pustych stanach, bąbelki w probówkach, podpowiedzi w Kontroli, paleta poleceń (Ctrl+K),
      wycieczka po aplikacji, przesuwanie zakładek na telefonie, akcenty kolorystyczne kafli. Test: testy/zywe_app.js
- [x] service worker: kod aplikacji (strona, skrypty, style) zawsze z sieci, gdy jest internet (kopia z pamięci tylko offline) — koniec ze starą wersją po aktualizacji
- [x] kwota wpisywana (suwak wyłączony stałą SUWAK_KWOTY) + arkusz „Sprawdź, zanim wygeneruję” przed generowaniem; testy używają pomocnika generuj() z testy/wspolne.js
- [x] adres bez ulicy: przełącznik rodzaju adresu w „Moich danych”, pytanie przy niejednoznacznej nazwie (jak w programie), profil.typ_adresu → wymus_typ w silniku (silnik/most.py niesie to_wies i nazwa_do_pytania); test testy/adres_app.js
- [x] jakość i płynność (decyzja właściciela: ta sama najwyższa jakość dla każdego, bez wpływu użytkownika i bez automatycznych obniżek): usunięta adaptacja poziomów; tło w natywnej rozdzielczości ekranu
      (do 8,4 mln px), pole zorzy 0,3 px CSS (pomiar błędu względem pełnej rozdzielczości w CZYTAJ_TO), paralaksa co klatkę przeglądarki, wykrycie grafiki programowej + jednorazowa instrukcja;
      ?diag pokazuje klatki/s, kartę, wersję i rozdzielczość tła. Test: testy/jakosc_app.js (jakość nie zmienia się przy małej liczbie klatek)
- [x] bez stawek i przeliczników w interfejsie (arkusz potwierdzenia, hero, kafel dnia, paleta) — to sprawa programu; limity (dnia, polecenia) zostają
- [x] BENTO (inspiracja: bento grid): każdy kafel w swoim kolorze (szkło zalane kolorem, pastelowe w motywie jasnym), ciaśniejsze odstępy i większe zaokrąglenia, ognisty kafel „Dziś” z wielką datą w tle
      i zapowiedzią listy w pustym stanie, pływająca etykieta przy pojeździe w teatrze trasy
- [x] WYDAJNOŚĆ (uwaga „muli i przycina”): pomiar wykazał, że głównym kosztem był backdrop-filter pod szkłem (każda klatka tła = ponowne rozmycie całej sceny pod szkłem). Usunięty z kafli, pigułek i okien
      (szkło barwione, przezroczyste; ?szklo=blur przywraca stare do porównań). Regulator tła (RUCH w js/aplikacja.js): wspólna bramka 30/s dla zorzy i kurtyny, wstrzymanie na czas pisania,
      rzadziej pod oknem i po 60 s bezczynności, schodzenie do 20/15/10 klatek/s tylko gdy strona realnie nie nadąża; jakość klatki stała. Skończone liczby iteracji animacji CSS.
      UWAGA: pomiary w SwiftShader (grafika programowa) — proporcje, nie liczby bezwzględne; prawdziwa karta/Edge niezmierzone.
- [x] Tydzień = pierwszy i domyślny tryb pracy (trybDom: „Wieczory” tylko po świadomym wyborze, także dla starych profili)
- [x] menedzer.txt: odczyt w chwili użycia (cache: no-store), ponowna próba bez odświeżania, wykrycie „.txt.txt”, arkusz z adresem i statusem odpowiedzi; test testy/menedzer_app.js
- [x] kolory kafli wyraziste (bento v2, oba motywy; reguły jasnego motywu w podwójnej postaci: data-theme + prefers-color-scheme)
- [x] zmiana motywu: fala + pierścień światła z iskrami (View Transitions: koło odsłaniające nowy wygląd; bez VT: niebo nowego motywu w kole); test testy/motyw_app.js
      (ścieżka VT niesprawdzalna w SwiftShader — Chromium przerywa przejście przez timeout; sprawdzona logicznie i w ścieżce ręcznej)
- [x] samouczek rozszerzony (Dziś w terenie, Noc czy Dzień, Ważne informacje, Uwagi/telefon/wygląd)
- [x] Trasa dnia 2.0: siatka, poziomice, radar, opisy z obwódką bez nakładania, kamera zbliżająca się do pojazdu z miękkimi brzegami kadru, etykieta celu, ślad pojazdu
- [x] odhaczanie wizyt: wiersze nie wyciekają poza kafel (w przejściu View Transitions nazwane są tylko w pełni widoczne wiersze), fanfary po 100% dnia (konfetti na jednym canvasie, napis, poświata)
- [x] instalacja na telefonie (js/pomoc.js): przycisk w menu konta i palecie, kroki dla Androida/iOS/komputera, kod QR (vendor/qr, MIT), ikony maskable, manifest, meta Apple; „Napisz uwagę” z danymi technicznymi
- [x] iOS/Safari: test w prawdziwym WebKit (testy/webkit_app.py, xvfb + webkit2gtk-driver) — komputer i 390×844; naprawiony błąd w sprawdzAdres. NIE sprawdzone: fizyczny iPhone (pamięć iOS dla Pyodide,
      instalacja jako aplikacja, pobieranie PDF, czyszczenie danych po 7 dniach bez instalacji). Minimum praktyczne: iOS 16.4+.
- [x] okno „Sprawdź, zanim wygeneruję”: pełny adres startu i mety + PESEL (do sprawdzenia przed generowaniem)
- [x] okna (arkusze, menu, paleta, wycieczka, komunikaty) w kolorze panelu (fiolet–granat–turkus; w Dniu pastele) zamiast czerni
- [x] dokumenty do podpisu (js/podpis.js, js/pliki.js): siatka kart, „Pobierz wszystkie” = jeden ZIP, bez „Wgraj podpisany” na etapie przed podpisem; podpis elektroniczny (wgranie wszystkich podpisanych plików naraz,
      dopasowanie po zawartości/nazwie/kolejności) i wydruk + podpis odręczny (jeden PDF do druku — własne scalanie PDF, skany naraz); wysyłka na adres z odbiorca.txt (Web Share na telefonie, ZIP + mailto na komputerze).
      NIE zrobione (świadomie): wysyłka bez poczty użytkownika przez Apps Script — wymaga Twojej zgody (dokumenty z PESEL przeszłyby przez Twoje konto Google).
- [x] „cel wyjazdu” na PDF = Biedronka + Żabka + 3–4 sieci losowane z silnik/sieci_cel.txt (lista właściciela), alfabetycznie po polsku, osobno na każdym poleceniu, losowanie powtarzalne
      (silnik/most.py — podklasa PDFReport; silnik bez zmian). Test testy/cel_app.js na prawdziwych PDF-ach. Wcześniejsza wersja „odwiedzone sklepy z planu” została usunięta (zła interpretacja).
- [x] pierwsze uruchomienie: przykładowy, pełny miesiąc zamiast pustego programu (przyklad/*.json z prawdziwego silnika; lista „Dziś” z lok_test.xlsx przez narzedzia/przygotuj_liste_przykladu.py + zbuduj_przyklad.js);
      dane pokazowe nie wchodzą w liczenie delegacji (guard w generuj()), po pierwszym wygenerowaniu przykład znika z menu i palety; testy/przyklad_app.js
- [x] kwota: da się ją wpisać od pierwszego ekranu (klik w dużą kwotę w przykładzie → własny miesiąc z kursorem w polu) i zmienić po wygenerowaniu (klik w kwotę → „Zmienić kwotę?” → usunięcie dokumentów)
- [x] DOKUMENTY DO PODPISU: ścieżka pobierz → podpisz (gov.pl lub odręcznie) → wgraj → SPRAWDZENIE → wyślij (js/podpis.js), kolorowe kroki i karty ze stanem (zamiast płaskich list); wycofane partie po 5 plików
      i zapis do folderu (po uwadze właściciela, że niewiele dają); gov.pl: 5 plików po 25 MB — okno tylko podpowiada liczbę tur. Automatyczna wysyłka na gov.pl NIE jest możliwa (zabezpieczenia przeglądarki).
- [x] sprawdzanie podpisów elektronicznych w przeglądarce (js/weryfikacja.js): PAdES (CMS/PKCS#7: skrót zakresu, podpis RSA/RSA-PSS/ECDSA, pokrycie całości, tożsamość dokumentu), XAdES (skrót pliku,
      własna kanonizacja XML sprawdzona względem lxml), imię i nazwisko + PESEL z certyfikatu; bez weryfikacji łańcucha zaufania. Testy na PDF-ach podpisanych pyHankiem i kontrola poppler (pdfsig).
- [x] podpis odręczny na skanie (js/podpis_reczny.js): silnik zapisuje współrzędne miejsca „podpis pracownika” (silnik/most.py), przeglądarka wycina ten fragment i szuka śladu pisma (pomija proste
      kreski); 40/40 sztucznych skanów z podpisem i 40/40 bez (0 fałszywych alarmów), PDF ze skanem wielostronicowym rozdzielany na dokumenty; ręczne potwierdzenie jako zabezpieczenie.
- [x] pulpit: kafel „Na telefon” z kodem QR (pomoc.js + index.html + css), komputer ≥1100×520 (do v3.25.1: ≥1180×780, przez co kafel znikał w zwykłym oknie laptopa), obok „Kontroli”.
- [ ] panel koordynatora (wymaga rozszerzenia backendu)
- [x] nazwisko przełożonego: decyzja właściciela — menedzer.txt z sekretu repozytorium, jak w programie (na stronie będzie publicznie czytelny)
- [ ] test na prawdziwym telefonie (Android i iPhone), w Edge z kartą graficzną i w Firefoksie (tu Chromium z grafiką programową i WebKit na Linuksie); wdrożenie na GitHub Pages dopiero po zielonym świetle

- [x] NAZWY PLIKÓW Z PODPISEM (js/podpis.js: docelowe/zapiszPliki): plik wracający pod dowolną nazwą jest rozpoznawany (PDF po zawartości, .xades po skrócie dokumentu, skan po nazwie/kolejności) i zapisywany
      pod nazwą z generowania (PDF, PDF.xades, skan = nazwa + .jpg / _str01.jpg); pierwotne nazwy w rekordzie miesiąca (pierwotneNazwy); kontrola „nazwa” w szczegółach; załączniki pod tymi nazwami; stare zapisy przemianowane przy otwarciu okna.
- [x] http: własna kryptografia do sprawdzania podpisów (js/krypto_js.js) gdy brak Web Crypto; krypto_js_test (30 sprawdzeń vs Web Crypto), weryfikacja_test z BEZ_WEBCRYPTO=1, cały obieg podpisów na http://pmt.example;
      WDROZENIE.txt (instrukcja); szablon Pages uzupełniony o przyklad/, vendor/qr, odbiorca.txt, uwagi.txt (+ opcjonalny sekret PMT_ODBIORCA), sprawdzony symulacją kroku „Przygotuj paczkę strony”.

- [x] KALENDARZ v4 i WYKRES DNI v4 (po uwadze „kalendarz mi się nie podoba, słupki przypominają fiolki”): kolorowe karty dni (skala n1…n5 = kwota dnia wobec limitu), płaskie białe słupki w pomarańczowym
      panelu obok niebieskiego pola kwoty, wybrany dzień niebieski; wykres WebGL (kurtyna) usunięty — DOM; podgląd kwoty w dniach roboczych to płaskie wypełnienie. Test: testy/wykres_kalendarz_app.js
      (komputer Noc/Dzień, telefon). Na telefonie wykres dni dalej jest ukryty (jak dotąd).
- [x] KOLORY v3 (wzór bento grid): nasycone, kryjące kafle, białe pastylki, kolorowe kroki podpisów — patrz CZYTAJ_TO.txt, sekcja KOLORY.

- [x] MOZAIKA PULPITU (po uwadze „na wzorze pola były w pionie i w poziomie”): siatka 12×6 na komputerach ≥1100×520 (do v3.25.1: ≥1180×700 — w oknie przeglądarki laptopa wracał stary układ poziomych rzędów; test web/testy/mozaika_app.js) — „Dziś” pionowo z lewej (4 wiersze), kwota z wykresem poziomo (7 kolumn × 3 wiersze), Dokumenty pionowo
      z prawej (2 kolumny × 3 wiersze), Kalendarz i Dzień na dole, Kontrola i „Na telefon” (pionowy) pod „Dziś”; barwy sąsiadów rozdzielone (kalendarz turkusowy, Dziś czerwono-pomarańczowe, Kontrola złota);
      dopasowania wnętrz w wąskich kaflach (container queries). Mniejsze okna i telefon bez zmian.

## Po pierwszym teście właściciela (Firefox)
- [x] „brak życia”: najprawdopodobniejsza przyczyna — system zgłasza „ogranicz animacje” (Windows: Ustawienia → Ułatwienia dostępu → Efekty wizualne → Efekty animacji; zdalny pulpit też to wymusza), a aplikacja to szanuje i wyłącza cały ruch.
      Dodane: menu konta → Animacje (System / Pełne / Oszczędne), jednorazowa podpowiedź, klasa html.spokoj zamiast media query.
- [x] przejścia bez View Transitions (Firefox, starsze Safari): przejscieReczne() na Web Animations — zmiana dnia (klon wyjścia + przesunięcie pierścienia), miesiąc/generowanie (kafle wchodzą po kolei),
      rozwinięcie kafla (odsłonięcie), zakładki na telefonie, lista Dziś, motyw (tło przygasa, kolory płyną).
- [x] reakcje na dotyk: fala przy kliknięciu, iskry przy odhaczeniu wizyty, wejście/wyjście okien, potrząśnięcie przy błędzie, powitanie, podpowiedzi przy ikonach.
- [x] nakładanie tekstu: pismo (html font-size) maleje w niskich i wąskich oknach (wcześniej twarda dolna granica 12,5 px powodowała zachodzenie); układ kart (jak na telefonie) już od szerokości < 900 px;
      poprawki: legenda kalendarza, „Wygeneruj od nowa” na telefonie, termin w nagłówku, liczba sklepów przy Plan, lista Kontroli. Test: testy/nakladanie_app.js (STRES=1 symuluje szersze pismo Firefoksa).
- [x] kolejne uwagi właściciela: autologowanie po wpisaniu hasła (jak w programie), usunięte „Silnik auta” i „Tryb pracy” z Moich danych (zmienne co miesiąc), „do 900 cm³” zamiast „poniżej”,
      usunięta linia „N dni roboczych · stawka · maks.” (zostają tylko komunikaty o błędach), zmiana motywu trwa ok. 3 s,
      wydajność: tryby ruchu (Auto/Pełne/Lekkie/Brak) z automatycznym przejściem na lekki; połysk krawędzi aktualizuje tylko kafle w zasięgu kursora (wcześniej przemalowywał wszystkie przy każdym ruchu myszy);
      zorza w trybie lekkim: niższa rozdzielczość, mniej kroków, odstęp klatek dopasowany do możliwości.
- [x] tryb lekki: zorza CSS zamiast shadera WebGL (po uwadze o „pikselozie”), światło kursora jednym elementem, unoszenie kafli, pulsy tylko na transformie; test w testy/ruch_app.js
- [x] jakość „Płynne” = zorza wypieczona z prawdziwego shadera (pieczona: 6 klatek, przenikanie + dryf, rozmiar klatki dobierany do szybkości komputera), nie CSS-owy zamiennik; CSS-owa zorza zostaje tylko jako zapas
      do czasu wypieczenia i przy braku WebGL. Nazwy trybów: Auto / Maksymalne / Płynne / Spokojne. Drabinka w trybie auto (Maksymalne → Płynne → Płynne bez rozmycia tła) z próbnikiem płynności.
      Nowe efekty: pył gwiezdny za kursorem, magnetyczne przyciski, rozbłysk zorzy przy przejściach i akcjach, filmowe wejście okna logowania, powolne „wschodzenie” sceny.
- [x] decyzja właściciela: użytkownik NIE wybiera trybu animacji. Usunięty przełącznik (logowanie, menu konta); do testów zostaje ukryty adres ?ruch=pelny|lekki|brak|auto oraz ?diag (nakładka z trybem i klatkami/s).
- [x] DECYZJA WŁAŚCICIELA (ostateczna na czas testów): JEDNA PEŁNA WERSJA — usunięte tryby (Auto/Maksymalne/Płynne/Spokojne), wypieczona i CSS-owa zorza, drabinka jakości, próbnik płynności,
      automatyczne obniżanie szkła (strazKlatek) i respektowanie „ogranicz animacje”. Zostaje: ?diag (klatki/s + nazwa grafiki). Kopie sprzed usunięcia: /tmp nie jest trwałe — w razie powrotu do trybów odtworzyć z historii rozmowy.
      Zostają nowe efekty: pył gwiezdny, magnes, rozbłysk zorzy przy przejściach, filmowe wejście logowania, przejścia bez View Transitions, połysk krawędzi tylko w kaflach w zasięgu kursora (ten sam wygląd, mniej przemalowań).

## Po kolejnym teście właściciela (Firefox, Edge)
- [x] logowanie przy KAŻDYM uruchomieniu (znacznik sesji karty w sessionStorage; F5 nie pyta, nowa karta pyta) — Edge nie „pamięta” już poprzednio zalogowanego bez pytania; podpowiada tylko login.
- [x] ważność dostępu sprawdzana od razu po poprawnym haśle (wczesny puls, limit 12 s); konto z pustym/przeszłym „Ważne do” jest odrzucane w oknie logowania z czytelnym komunikatem (dawniej: wejście, prośba o zmianę hasła i po chwili powrót do logowania).
      NIEZWERYFIKOWANE na prawdziwym backendzie (brak dostępu do arkusza) — przyczyna dobrana z kodu Apps Script (puls: wygasla przy pustej/przeszłej dacie) i zachowania programu na komputerze.
- [x] kod QR na kaflu „Na telefon” od razu: serwer_lokalny.py podaje adres komputera w sieci (/__adres.json), aplikacja rysuje QR bez pytania (test qr_kafel_app.js).
- [x] odhaczanie wizyt: klucz wizyty adres#n — powtórzony adres w planie nie odhacza wszystkich naraz; baner „Gratulacje! Dzień zrobiony” także w trybie spokojnym (test plan_app.js).
- [x] pulpit pod otwartym oknem blaknie i rozmywa się (html.okno; test okno_tlo_app.js).
- [x] kod QR „Na telefon” niezależny od komputera: prowadzi pod stały adres publiczny z adres_aplikacji.txt (szablon wdrożenia GitHub Pages wpisuje go sam; opcjonalnie sekret PMT_ADRES = własna domena).
      Bez tego adresu (przed wdrożeniem) zostaje adres strony / adres komputera w sieci (wymaga włączonego komputera). Test: qr_kafel_app.js z odczytem kodu dekoderem OpenCV.
      NIEZWERYFIKOWANE: sam workflow (krok zapisujący adres) sprawdziłem tylko składniowo i fragment powłoki osobno — nie był uruchomiony na GitHubie.

## Audyt bezpieczeństwa danych (zob. BEZPIECZENSTWO.txt)
- [x] BACKEND (apps_script_POPRAWIONY_v2.gs): formuły z danych klienta w arkuszu (=IMPORTXML… = wyciek arkusza) — naprawione; limity zgadywania haseł (8/15 min, 25/6 h na login); puls z nieznanego kodu nie zakłada
      kont; rejestr sesji i dzienniki z limitami; walidacja kodu; ogólny komunikat błędu; opcja PULS_DANE_TYLKO_PO_LOGOWANIU (domyślnie wyłączona). Test na prawdziwym pliku .gs: testy/backend_gs_test.js.
- [x] STRONA: CSP + referrer + ochrona przed ramką; test wstrzykiwania kodu na wszystkich ekranach (xss_app.js) — ucieczka była poprawna, dodano apostrof; brak inline onclick.
- [x] URZĄDZENIE: pamięć silnika czyszczona przy zmianie konta i wylogowaniu; „Usuń dane z urządzenia” w „Moje dane”; service worker nie trzyma starych plików ustawień.
- [x] NARZĘDZIA: serwer_lokalny.py bez listy katalogów i z trybem „lokalnie”; zbuduj_zip.py wyklucza kopie plików poufnych i przerywa przy napisie w kształcie sekretu.
- [ ] DECYZJE WŁAŚCICIELA: wymiana sekretu z historii repozytorium (stary sekret jest w publicznej historii), wdrożenie za logowaniem, jeśli menedzer.txt nie może być publiczny.
      (Tokeny sesji i szyfrowanie na urządzeniu — zrobione w wersji web; program na komputerze zostaje bez szyfrowania, bo ma być zastąpiony wersją web.)
- NIEZWERYFIKOWANE: prawdziwy backend (brak dostępu do script.google.com z tego środowiska) — zachowanie apostrofu w komórce i CacheService sprawdzić po wdrożeniu; program na komputerze nie testowany.
- [x] PULS I SESJA WYMAGAJĄ HASŁA (podpis kluczem pochodnym od hasła: HMAC, klucz = skrót hasła z kolumny „Haslo hash”): backend (WYMAGAJ_HASLA_W_PULSIE), aplikacja web (js/dostep.js),
      program na komputerze (PMT_Delegacje.py: _podpisz_zadanie, online_synchronizuj z polem „pelne”); testy: backend_gs_test.js, logowanie_app.js, testy_pmt.py (903/903).
- [x] SZYFROWANIE DANYCH NA URZĄDZENIU: js/sejf.js (AES-256-CTR + HMAC-SHA256, PBKDF2 600 000, klucz danych w sejfie chronionym hasłem), js/magazyn.js (localStorage i IndexedDB zaszyfrowane,
      migracja danych sprzed szyfrowania), js/dostep.js (skrót hasła tylko w sessionStorage, sejf otwiera logowanie offline i autologowanie), okno odzyskiwania po zmianie hasła, wykrywanie
      uszkodzonych danych. Testy: sejf_test.js, szyfrowanie_app.js. Zapomniane hasło = utrata danych lokalnych (świadomie, bez tylnych drzwi).
- [x] PRZEJŚCIE UŻYTKOWNIKÓW Z PROGRAMU NA KOMPUTERZE NA WEB (przygotowane, NIE wdrożone, nic nie wypchnięte): program 3.25.0 (ostatnia wersja na komputer) czyta z wersja.txt wiersze web= (adres; jest włącznikiem)
      i wygaszenie= (data) i pokazuje przed logowaniem okno z informacją (raz dziennie do terminu, od terminu przy każdym starcie i zamknięcie); build.yml zachowuje te wiersze przy podbiciu wersji;
      przygotuj_przejscie.py robi z adresu i daty gotowe wiersze i wiadomości; PRZEJSCIE_NA_WEB.txt = procedura (kolejność, kontrola, hamulec). Testy: sekcja 3b w testy_pmt.py (964/964 w trybie --szybko).
      NIEZWERYFIKOWANE: wygląd okna na prawdziwym Windows; budowanie na GitHubie z nowym kodem build.yml (sprawdzony tylko fragment w bashu); rzeczywiste dotarcie wiadomości do ludzi.
      Dane z programu przenosi plik (patrz niżej: PRZENIESIENIE DANYCH); historia miesięcy i wygenerowane wcześniej trasy nie przenoszą się.
- [x] OKNO „DOKUMENTY DO PODPISU” (uwaga właściciela): pole przeciągania leży między krokiem 3 a 4; dodany krok 5 „Wyślij” — szary i nieaktywny, dopóki wszystkie dokumenty nie są wgrane i sprawdzone (potem się zapala; przycisk
      z data-akcja="wyslij" jest tylko w aktywnym kroku, stopka ma samo „Zamknij”). podpis.js, aplikacja.css; testy: podpis_offline_app.js (pięć kroków, zapalenie kroku 5), ustawienia_po_generowaniu_app.js.
- [x] TRYB PRACY I SILNIK PO WYGENEROWANIU (uwaga właściciela: „to może się zmieniać”): znaczek „auto … ✎” i krok „Ustaw ✎” otwierają arkusz „Tryb pracy i auto” (wybór → „Zmień i usuń dokumenty”, z potwierdzeniem jak przy
      zmianie kwoty); wybór idzie do profilu jako domyślny na kolejne miesiące. Test: testy/ustawienia_po_generowaniu_app.js. NIE sprawdzone na prawdziwym telefonie (znaczek schowany na wąskich ekranach, krok „Ustaw” działa).
- [~] PROGRAM NA KOMPUTERZE: szyfrowania danych lokalnych (PESEL, plan, skrót hasła) NIE robię — decyzja właściciela: program zostaje zastąpiony wersją web. Zbudowana i przetestowana w części próba
      (sejf stdlib: PBKDF2 + HMAC-CTR, dane per konto, odzyskiwanie po zmianie hasła, kopia zapasowa) została odłożona poza repozytorium. Zostaje tylko podpis pulsu hasłem (zgodność z backendem).
- [x] FIREFOX vs EDGE (uwaga właściciela: „mozilla pokazuje inny wygląd niż explorer”): zrzuty i obliczone style wszystkich elementów porównane w Firefoksie 159 (Xvfb + WebGL) i Chromium; poprawione: pierścień postępu
      (calc bez jednostki w stroke-dasharray), znikająca nazwa na mapie (obrys wliczany do prostokąta tekstu SVG), zamazane polskie litery na mapie (osobny napis-obrys zamiast paint-order), próg
      procent/kwot pod wykresem dni (58 → 60 rem). NIEZWERYFIKOWANE: prawdziwy Firefox na Windows (inne czcionki systemowe, DPI), Safari; „ciekłe szkło” celowo tylko w Chromium.
- [x] ŻYCIE KALENDARZA I FIOLEK (uwaga właściciela: „dni mogłyby pulsować, fiolki kołysać cieczą — nadaj życia”): tylko te dwa kafle mają ciągły ruch mimo trybu spokojnego (animacje „zycie-…” w css/aplikacja.css,
      klasa html.zyje, przełącznik `const zycie` w js/aplikacja.js, wyłączane przez „Ogranicz ruch”); przy okazji naprawione bąbelki w fiolkach (nigdy się nie tworzyły przy pierwszym rysowaniu).
      Test: testy/zycie_app.js (17 sprawdzeń); spokoj_app.js i reszta testów działają z wyłączonym „życiem”. NIE zmierzone: płynność na prawdziwym komputerze.
- [x] PRZENIESIENIE DANYCH PROGRAM → WEB (decyzja właściciela: „robimy przenoszenie danych”, wczytywanie z Excela zostaje dla nowych użytkowników): program 3.25.0, w oknie informacji o przejściu, ma przycisk „Przenieś dane” —
      zapisuje plik .pmtdane (Moje dane + lista sklepów) zaszyfrowany kodem i hasłem konta (PBKDF2-HMAC-SHA256 100 tys. iteracji z skrótu hasła, strumień HMAC-SHA256, podpis HMAC; moduł pmt_przeniesienie.py, tylko stdlib).
      Aplikacja web (js/przeniesienie.js, okno „Moje dane” → „Wczytaj dane z programu na komputerze”) odczytuje plik, wypełnia formularz (nic nie zapisuje się bez „Zapisz”), a listę sklepów odkłada na okno „Plan”.
      Przenosi się: imię, PESEL, adres, stanowisko, pojemność silnika, lista sklepów, plan wizyt i odhaczenia (od 31 dni wstecz; v3.25.1). NIE przenosi się: notatki, historia miesięcy i wygenerowane trasy (dokumenty zostają na dysku).
      Testy: testy_pmt.py sekcja 3d (1001/1001 w trybie --szybko), web/testy/przeniesienie_test.js (zgodność Python↔JS, odrzucenia, oczyszczanie), web/testy/przeniesienie_app.js (przepływ w przeglądarce).
      NIEZWERYFIKOWANE: wygląd okna i wybór pliku na prawdziwym Windows; użytkownicy bez zapamiętanego skrótu hasła (program wtedy pyta o hasło — pomyłka = plik, którego aplikacja nie odczyta, z czytelnym komunikatem);
      szyfrowanie opiera się na skrócie hasła, który zna też backend (administrator arkusza + plik mógłby go odczytać) — dla danych leżących na komputerze użytkownika to akceptowalne, ale to nie jest tajemnica wobec administratora.
- [x] POPRAWKI PO TEŚCIE WŁAŚCICIELA (program 3.25.1; 5 uwag z zrzutów): (1) okno przejścia ucinało „Otwórz aplikację” — przyciski mają minimalną szerokość z napisu, a okno rośnie, gdy trzeba;
      „Przenieś dane” jest osobnym, zielonym przyciskiem akcji (QPushButton#akcja). (2) PRYWATNOŚĆ: okno „Przenieś dane” nie pokazuje już listy kont z kodami (każdy mógł pobrać cudze dane) — pyta o WŁASNY
      kod i hasło i sprawdza je ze skrótem zapisanym na komputerze (trzy próby, komunikaty bez ujawniania, czy konto istnieje); zbierane są dane tego jednego konta. (3) „Otwórz aplikację” otwiera przeglądarkę
      i zamyka program (wcześniej okno zostawało nad stroną). (4) po wczytaniu pliku aplikacja nie jest goła: plik niesie plan wizyt i odhaczenia (od dziś−31 dni), silnik (plan_z_programu w most.py) dolicza
      sumy i godziny, a po „Zapisz” kafel Dziś ma wizyty; plik bez planu → okno „Plan” otwiera się samo z gotową listą. Wygenerowane wcześniej trasy i historia miesięcy NIE przenoszą się (zostają na dysku). (5) kod QR: kafel „Na telefon” znikał w zainstalowanej aplikacji na komputerze (okno standalone) — teraz chowa się tylko na telefonie/iOS (przyczyna to hipoteza, do potwierdzenia
      przez właściciela). Testy: testy_pmt.py sekcja 3d, przeniesienie_test.js, przeniesienie_app.js (dwa scenariusze), qr_kafel_app.js.
      NIEZWERYFIKOWANE: wygląd okna na prawdziwym Windows; przejście na produkcyjną stronę github.io; 3.25.0 już rozesłane zawiera lukę z listą kont — dlatego wymagana jest 3.25.1 (min=3.25.1 w wersja.txt, na wyraźne polecenie).
- [x] WYSYŁKA ZAHASŁOWANĄ PACZKĄ (po uwagach właściciela: zahasłować dokumenty z PESEL-em, zapanować nad spamem; wszystko ustawia administrator w arkuszu; jeden moduł w oknie dokumentów, bez opcji
      dodatkowych; status automatyczny): krok 5 „Wyślij” w oknie „Dokumenty do podpisu” pobiera ze skryptu (akcja haslo_paczki; zakładka „Ustawienia”: haslo_paczki, haslo_paczki_wazne_do, adres_odbiorcy; po
      terminie skrypt hasła nie wydaje; bez któregoś z trzech wysyłka wyłączona), robi jedną paczkę ZIP z AES-256 (js/zipaes.js) i plik wiadomości .eml z adresatem, tematem „[PMT] Delegacje — …”, krótką treścią
      i załącznikiem (js/poczta.js, nagłówek X-Unsent: 1); na telefonie systemowe udostępnianie. Samo kliknięcie „Wyślij” ustawia status „Wysłane” (kafel pulpitu + „chmurki” dokumentów: „Wysłano” z datą zamiast
      „Otwórz”; „Cofnij wysłanie” przywraca) — aplikacja nie widzi, czy wiadomość wyszła z poczty. Adres odbiorcy już NIE leży na stronie (odbiorca.txt usunięty z wdrożenia i sekretu PMT_ODBIORCA).
      Spam: stały początek tematu → reguła w poczcie odbiorcy. Testy: paczka_test.js (pyzipper + prawdziwy 7-Zip + parser poczty), backend_gs_test.js (sekcja 7), podpis_offline_app.js. NIEZWERYFIKOWANE:
      otwieranie .eml w prawdziwym Outlooku/Thunderbirdzie/Poczcie Windows (poczta w przeglądarce go nie otworzy — kto nie może, wysyła pliki sam); backend na prawdziwym Apps Script (wymaga wklejenia nowej
      wersji skryptu i „Wdróż → Nowa wersja”); Eksplorator Windows często nie otwiera AES-256 (potrzebny 7-Zip/WinRAR). NIE zrobione (świadomie): kolejka na serwerze z wysyłką o stałej godzinie.
- [x] WIDOK 3D DOKUMENTÓW (uwaga właściciela: „efekt wow”, atrapa dokumentu z danymi, powiększanie): opcja w oknie „Dokumenty do podpisu” (przełącznik „Karty | Widok 3D”, domyślnie lista, wybór pamiętany) —
      karty na obracanym pierścieniu, na każdej atrapa dokumentu z danych wyniku silnika (silnik oddaje teraz też „przelozony”), dostępna zaraz po generowaniu (stan „czeka”, indygo; zielony/bursztynowy/czerwony
      jak na liście), powiększony podgląd po kliknięciu (cały dokument, pełny PESEL, panel stanu), pieczęć „Wysłano”. Kafel „Dokumenty” (probówki) bez zmian. Pliki: js/karuzela.js, js/dokument_atrapa.js,
      podpis.js, aplikacja.css (.k3-*, .da-*); testy: atrapa_test.js, karty3d_app.js (także z ZYCIE=tak), podpis_offline_app.js (stany i „Wysłano” w 3D). Atrapa jest repliką układu, nie zdjęciem pliku.
- [x] WIDOWISKO GENEROWANIA + „ŻYCIE” PODPISÓW (uwaga właściciela: punkty 1 i 2 z propozycji ożywienia): panel z postępem silnika (GPS → trasa → stos kartek) i wachlarzem prawdziwych dokumentów z kwotami po
      wyniku; podpis „rysuje się”, zły dokument drży, pieczęć „Wysłano” opada; klik w probówkę prowadzi do jej dokumentu. Ruch dla wszystkich (html.zyje, animacje „zycie-…” z !important przebijają tryb spokojny),
      wyjątek: „Ogranicz ruch” w systemie. Pliki: js/widowisko.js, podpis.js, dokument_atrapa.js, aplikacja.css; testy: widowisko_app.js (+ karty3d_app, podpis_offline_app także z ZYCIE=tak).
      Odrzucone przez właściciela: miesiąc jako pierścień dni (nie robimy).

## Pełny przegląd (listopad 2026): błędy, bezpieczeństwo, dane osobowe
Przegląd w obszarach (aplikacja web, podpisy, dostęp i sejf, backend, silnik, CI, program, bezpieczeństwo), każde zgłoszenie sprawdzone przez osobnego weryfikatora
(ok. 110 zgłoszeń, większość potwierdzona), poprawki w pakietach z recenzją diffu. Część web — zrobiona:
- [x] APLIKACJA: zmiana miesiąca w trakcie generowania nie przenosi dokumentów (miesiąc zapamiętany przed pierwszym await, strzałki wyłączone); komunikaty widoczne w trybie spokojnym;
      okna trzymają fokus (pulpit pod spodem inert); tryb i auto wybrane przed „Moimi danymi” zostają; „Wieczory” bez profilu liczą soboty; dni wolne, tryb i auto miesiąca bez rekordu
      pamiętane na urządzeniu jak kwota ('wolne-RRRR-MM', 'ust-RRRR-MM'; „od nowa” i zmiana trybu po wygenerowaniu nie wracają do profilu po wizycie w innym miesiącu); w trakcie
      generowania tryb, auto i dni wolne zablokowane; „Dziś” po północy; błąd zapisu (pełna pamięć) nie zostawia „generowania” ani połowy plików; nazwy miejscowości jako tekst;
      szybkie strzałki liczą od wczytywanego miesiąca; okno odzyskiwania sejfu pyta przed usunięciem (bezpieczny przycisk w miejscu tego, który otwiera ostrzeżenie).
- [x] PODPISY: zmiany zapisane w PDF-ie PRZED podpisem (strona zamalowana, adnotacja, podmieniony strumień, też w /ObjStm) → odrzucone; atrybuty strony porównywane z dziedziczeniem
      (iText/OpenPDF wpisują odziedziczony MediaBox i „/Rotate 0” — to nie zmiana); certyfikat samopodpisany → „uwaga”; ponowny skan zastępuje pliki tylko dokumentu jednostronicowego;
      wznowienie przerwanego sprawdzania; Android bez udostępniania ZIP-ów: pobranie + odnośnik „Otwórz wiadomość”.
- [x] DOSTĘP I SEJF: klucz danych i skrót hasła tylko w pamięci strony; do sessionStorage trafiają wyłącznie przy ZAMIERZONYM odświeżeniu (F5, Ctrl+R, przeładowanie przez aplikację),
      nie przy zamknięciu karty (sessionStorage leży na dysku); pamięć silnika (współrzędne domu, trasy) w zaszyfrowanym magazynie konta zamiast jawnej bazy IDBFS (kasowanej);
      blokada konta przeżywa wylogowanie; normalizacja hasła (spacje, telefon); czas serwera koryguje zegar urządzenia; autologowanie bez PBKDF2 po pauzie i najwyżej jedna automatyczna
      próba nieznanego hasła (limit prób na serwerze); niepodzielna instalacja service workera; „Usuń dane” kasuje też login ze statusu; wymuszone wylogowanie czyści silnik.
- Testy: naprawy_aplikacja_app.js (nowy), weryfikacja_test.js (+ nowe pliki w dane/podpisy), karuzela_test.js, dostep_test.js, sw_instalacja_app.js, szyfrowanie_app.js, logowanie_app.js,
  dane_na_urzadzeniu_app.js, podpis_offline_app.js, przeplyw_app.js, xss_app.js, widowisko_app.js, zywe_app.js — wszystkie przechodzą. Testy odświeżające stronę bez gotowej sesji udają F5.
Część backend / silnik / program / CI — zrobiona (każdy pakiet z recenzją i poprawkami po niej):
- [x] BACKEND (apps_script_POPRAWIONY_v2.gs, WYMAGA WDROŻENIA NOWEJ WERSJI SKRYPTU): złe podpisy hasłem (puls, sesja, hasło paczki) 150 / 6 h na kod — koniec wyroczni do zgadywania
      hasła; ochrona przed formułami także przy wartościach zapisywanych z powrotem; reset hasła w stałym oknie + odblokujKonta() z edytora; dzienniki z osobnymi przydziałami
      (zdarzenia po uwierzytelnieniu, odmowy na istniejące konta) i najwyżej 20 wpisów odmów bez hasła na zdarzenie na godzinę; nieistniejące kody bez kluczy w CacheService;
      logowanie i zmiana hasła nie zdradzają, czy telefon pasuje do kodu; „Serwer zajety” zamiast pracy bez blokady; daty tekstowe DD.MM.RRRR / RRRR-MM-DD; hasło paczki tylko
      z tekstu/liczby całkowitej; aplikacja web (pole klient: "web") zwolniona z bramki wersji programu. Web: po „pelne: false” karta nie podpisuje odrzuconym skrótem.
- [x] SILNIK (PMT_Delegacje.py → ponowny wyciąg web/silnik/pmt_silnik.py; zgodność program ↔ web potwierdzona): plan wizyt — miejscowości spoza bazy offline do „bez lokalizacji”
      (nie Warszawa), każdy dzień od domu; jedna awaria sieci nie wyłącza OSRM/geokodowania do końca życia workera; baza bez sieci = miejscowość lub poczta zgodna z województwem
      (nie stolica; web bez żadnej pozycji odmawia generowania); CSV z polskiego Excela (cp1250, UTF-16); grudzień od 2025 — trzy niedziele handlowe; województwa dla kodów
      z pogranicza; adres: „Bielsko-Biała”, „Jana Pawła II”, „Nakło nad Notecią”; PESEL — także data urodzenia; wieczory — powrót najpóźniej o 22:00.
      Do decyzji (pominięte): „maks.” kwoty miesiąca zawyżony względem tego, co silnik rozpisze; kwoty < ok. 300 zł czasem niedobite (zgłaszane).
- [x] PROGRAM (do niewydanej 3.25.1): „Tylko podpisane” nie dołącza niepodpisanego oryginału (tylko Podpisane + kontrola sumy); kopia zapasowa tylko z danymi tego konta, bez wspólnej
      pamięci adresów, odtworzenie nie kasuje innych kont; skrót hasła tylko w pamięci (na dysku weryfikator PBKDF2); log_error bez abortu; updater_folder.bat — sukces tylko po fladze,
      wiszący proces zamykany przed przywróceniem kopii, „!” w ścieżce; updater.sh — paczki folderowe macOS/Linux; „Przenieś dane” po zmianie hasła w webie (serwer potwierdza
      bieżące hasło; w webie pole „Hasło z programu na komputerze” dla pliku ze starszym hasłem); „Wskaż plik” odrzuca niepodpisaną kopię i pyta o dokument.
      Do decyzji (pominięte): sprzątanie PESEL-i z ~/.pmt_uzytkownicy.json po przeniesieniu; panel „Ustawienia” widoczny dla każdego zalogowanego; „&” w ścieżce programu.
      UWAGA: poprawione updater_folder.bat / updater.sh programy pobierają z gałęzi main — działają dopiero po scaleniu do main.
- [x] CI: domyślnie contents: read, zapis tylko w jobach wydania bez pip; bez zewnętrznej akcji z tokenem (gh release); wydanie z tagu dopiero po zielonych testach (testy.yml
      przez workflow_call); wersja.txt zachowuje min=/blokada=/web=/wygaszenie=, nie rusza po anulowaniu, ponowne uruchomienie nie odkręca hamulca, podbicie tylko dla wydania
      „Latest”; filtr ścieżek testów obejmuje wszystkie moduły paczki. Do zrobienia przez właściciela: przypięcie akcji do SHA (+ ewentualnie dependabot), opcjonalnie
      Settings → Actions → „Read repository contents” jako domyślne uprawnienie.
- [x] UWAGI WŁAŚCICIELA PO TEŚCIE (4.11): (1) NA DOKUMENCIE (delegacja, rozliczenie, raport tras HTML) nie ma już dopisku o źródle odległości („Odległości: szacunek / realne drogi / drogi z pamięci”) —
      program i aplikacja nadal wiedzą, skąd są kilometry (okno programu, komunikat po generowaniu w aplikacji „Kilometry z szacunku…”), ale dokument milczy; układ strony bez zmian (ta sama wysokość nagłówka).
      Tacka programu dla miesiąca z dysku pokazuje wtedy zwykłe „KILOMETRY” (dawne PDF-y z dopiskiem nadal się czytają). Atrapa dokumentu w aplikacji też bez dopisku. wyciagnij_silnik.py ma teraz w korzeniach
      stan_zrodla_odleglosci i zeruj_zrodlo_odleglosci (most.py ich używa, a PDF już ich nie wciąga). (2) FIOLKI SIĘ NIE KOŁYSZĄ: zniknęło bujanie probówki, chlupot powierzchni cieczy i chlupot za kursorem;
      zamiast tego ciecz napełnia się od dołu do swojego poziomu (animacja „zycie-napelnij”, każda fiolka po kolei, przy każdym narysowaniu fiolek) i idzie więcej, wyraźniejszych bąbelków (8 na fiolkę).
      Przy okazji naprawiony błąd: rejestracja `@property --sw` (liczba, dla chlupotu) zerowała szerokość łączników na osi podróży (.pr-odc, .pr-km) i wyłączała poświatę fali przy zmianie motywu —
      `--sw` ma w pliku trzy znaczenia, więc nie wolno go rejestrować (komentarz w CSS). Testy: zycie_app.js (napełnianie sprawdzane na wybranych klatkach animacji), zywe_app.js, atrapa_test.js, testy_pmt.py.
- [x] PODPIS ZAUFANY Z GOV.PL — fałszywy „błąd podpisu” (zgłoszone po teście właściciela, 4.11; sprawdzone na prawdziwym pliku z gov.pl): (1) KRYPTOGRAFIA: pieczęć podpisu zaufanego
      zapisuje RSA PKCS#1 v1.5 z DigestInfo BEZ pola NULL po identyfikatorze skrótu. Podpis jest poprawny (po odszyfrowaniu kluczem z certyfikatu wychodzi SHA-256 podpisanych atrybutów,
      a messageDigest = SHA-256 zakresów pliku), ale OpenSSL, NSS/Poppler i Web Crypto są ścisłe i go odrzucają — urzędowy walidator (Java) przyjmuje. weryfikacja.js: gdy ścisłe
      sprawdzenie mówi „nie”, sprawdza jeszcze własna kryptografia (krypto_js.js), która porównuje CAŁY blok 00 01 FF…FF 00 DigestInfo skrót w obu zapisach (z NULL i bez);
      blok z dopisanymi bajtami albo zmieniony podpis nadal odpada. (2) OSOBA: certyfikatem jest PIECZĘĆ Ministra („Minister do spraw informatyzacji — pieczęć podpisu zaufanego”,
      Ministerstwo Cyfryzacji, VATPL-5252955037), a osoba jest tylko w słowniku podpisu: /Name i /Reason „…w imieniu: IMIĘ NAZWISKO, PESEL: …” (leży w podpisanym zakresie).
      Dla takiej pieczęci (nie samopodpisanej) imię i PESEL do kontroli „czy to ta osoba” bierzemy ze słownika; /Name musi zgadzać się z imieniem w powodzie; bez wskazania osoby
      stan „uwaga”, nie „podpisała inna osoba: Minister”. Komunikat: „Podpis zaufany w imieniu: …”. UWAGA: łańcucha zaufania nadal nie sprawdzamy (robi to urzędowy walidator) —
      aplikacja ufa nazwie certyfikatu pieczęci, więc to wygodna kontrola, nie podpis prawny. (3) CZAS: pieczęć nie niesie atrybutu czasu — czas z pola /M słownika podpisu.
      Testy: weryfikacja_test.js (+9 plików testowych z podpisem „jak z gov.pl”: pieczec_ministra*.pdf, rsa_bez_null*.pdf; generuj_podpisy.py / podpisy_lib.py), krypto_js_test.js
      (DigestInfo bez NULL dla SHA-1/256/384/512 + blok z dopisanymi bajtami), oba także w trybie BEZ_WEBCRYPTO. Prawdziwego pliku z gov.pl NIE ma w repozytorium (zawiera PESEL).
- [x] WYSYŁKA DOKUMENTÓW — SPOSOBY (uwagi właściciela 4–5.11): na komputerze cztery sposoby przełączane przyciskiem „Zmień sposób” (wybór pamiętany; domyślny pierwszy dostępny): szkic w Outlooku (Microsoft Graph, uśpiony do wpisania
      identyfikatora aplikacji — WDROZENIE.txt p. 7), zapis na pulpicie (showSaveFilePicker ze startIn: 'desktop', tylko Chrome/Edge: okno „Zapisz jako” na Pulpicie, ikona .eml z załącznikiem w środku), otwarcie poczty (mailto: —
      adres, temat, treść; paczka ZIP w Pobranych do dołączenia, bo mailto: nie umie dołączać plików) i zwykłe pobranie .eml. Telefon bez zmian (udostępnianie). Załącznik w wersji roboczej wchodzi tylko przez szkic w Outlooku albo plik .eml.
      Testy: outlook_test.js, podpis_offline_app.js (okno logowania Microsoft i atrapa Graph, mailto:, przełączanie sposobów, duża paczka przez sesję wysyłania, atrapa showSaveFilePicker). Natywnego okna zapisu w teście
      nie da się obsłużyć — wspolne.js je wyłącza, a scenariusz podstawia atrapę; zachowanie prawdziwego okna i Outlooka z plikiem .eml sprawdza dopiero właściciel.
- [x] WYSYŁKA — PLIK .eml DOMYŚLNY (decyzja właściciela 5.11: „tylko plik .eml”, bez rejestracji w Microsoft i bez IT): kolejka sposobów na komputerze: szkic w Outlooku (tylko z identyfikatorem) → plik .eml → pulpit → mailto:.
      Po pierwszym pobraniu .eml jednorazowa wskazówka w kroku 5 (3 kroki + makieta menu): prawy przycisk na pliku w okienku pobierania → „Zawsze otwieraj pliki tego typu” (Firefox: „…podobne pliki”);
      od tej pory „Wyślij” od razu pokazuje okno poczty z gotową wiadomością. „Zrobione” chowa ją na stałe (localStorage pmt-ui-eml-auto), potem w komunikacie przycisk „Jak sprawić, żeby otwierała się sama?”.
      Plik .eml zbudowany jak wiadomość zapisana przez Outlook: multipart/mixed → multipart/alternative (tekst + HTML) + ZIP, nagłówki Date i Message-ID (zgłoszenia: nowy Outlook dla Windows gubi treść/załącznik
      przy samym zwykłym tekście albo bez Message-ID — NIE sprawdzone na prawdziwym nowym Outlooku). Testy: paczka_test.js (budowa MIME, HTML, Date, Message-ID), podpis_offline_app.js (kolejność, wskazówka).
