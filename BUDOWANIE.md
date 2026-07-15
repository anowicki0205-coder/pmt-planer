# PMT Planer — budowanie na Windows, macOS i Linux

## Zasada ogólna

PyInstaller **nie robi cross-kompilacji** — plik dla danego systemu trzeba
zbudować NA tym systemie (Windows → na Windows, macOS → na Macu, Linux → na
Linuksie). Kod źródłowy jest jeden i ten sam.

Zalecany Python: **3.12 lub 3.13** (nie 3.14 — patrz problem z python314.dll).

## Windows (jak dotychczas)

```
py -3.13 -m venv venv
venv\Scripts\activate
pip install pyinstaller pyqt6 fpdf2 openpyxl
pyinstaller --onefile --windowed --icon pmt_logo.ico ^
    --add-data "pmt_logo.ico;." --name PMT_Planer PMT_Delegacje.py
```

Wydanie na GitHub: `PMT_Planer.zip` (jak dotychczas — nazwa **bez** słów
"linux"/"mac", żeby wykrywanie platformy w programie działało poprawnie).

## Linux

```
python3 -m venv venv
source venv/bin/activate
pip install pyinstaller pyqt6 fpdf2 openpyxl
pyinstaller --onefile --windowed --icon pmt_logo.png \
    --add-data "pmt_logo.png:." --name PMT_Planer PMT_Delegacje.py
```

Wynik: pojedyncza binarka `dist/PMT_Planer`. Spakuj do
**`PMT_Planer-linux.zip`** i dołącz do tego samego wydania na GitHubie —
program na Linuksie sam znajdzie plik z "linux" w nazwie.

Uwaga: binarkę buduj na możliwie STARYM Linuksie (np. Ubuntu 20.04/22.04) —
zadziała wtedy też na nowszych. Odwrotnie nie.

Czcionki do PDF: program szuka Arial → Liberation Sans → DejaVu Sans.
Na typowych dystrybucjach Liberation/DejaVu są zainstalowane fabrycznie.

## macOS

```
python3 -m venv venv
source venv/bin/activate
pip install pyinstaller pyqt6 fpdf2 openpyxl
pyinstaller --onefile --windowed --icon pmt_logo.icns \
    --add-data "pmt_logo.icns:." --name PMT_Planer PMT_Delegacje.py
```

Wynik: `dist/PMT_Planer` (binarka) oraz `dist/PMT_Planer.app` (aplikacja).
Do wydania spakuj **binarkę** (nie .app) jako **`PMT_Planer-macos.zip`** —
auto-aktualizacja podmienia pojedynczy plik.

Uwaga Gatekeeper: niepodpisany program pobrany z internetu macOS zablokuje
przy pierwszym uruchomieniu — użytkownik musi kliknąć prawym → Otwórz, albo
`xattr -d com.apple.quarantine PMT_Planer`. Podpisywanie (Apple Developer,
99 USD/rok) rozwiązuje to na stałe, ale przy jednym użytkowniku szkoda pieniędzy.

Ważne: buduj na Macu z takim samym lub starszym typem procesora, jakiego
używa odbiorca (Apple Silicon vs Intel) — binarka z M1/M2 nie ruszy na
starym Intelu bez Rosetty w drugą stronę.

## Wydanie na GitHubie — komplet plików

W repo (gałąź main):
- `wersja.txt` — numer + opis zmiany (jak dotychczas)
- `updater.bat` — skrypt podmiany dla Windows (jak dotychczas)
- `updater.sh` — NOWY: skrypt podmiany dla macOS/Linux

W assets wydania (Release):
- `PMT_Planer.zip` — Windows (bez "linux"/"mac" w nazwie!)
- `PMT_Planer-linux.zip` — Linux (opcjonalnie)
- `PMT_Planer-macos.zip` — macOS (opcjonalnie)

Jeśli dla jakiegoś systemu nie ma pliku, program na nim NIE spróbuje
zainstalować złego pliku — pokaże komunikat i przycisk do strony pobierania.

## Co zostało zmienione w kodzie (żeby działał na 3 systemach)

1. `otworz_w_systemie()` — otwieranie folderów: os.startfile (Windows),
   `open` (macOS), `xdg-open` (Linux).
2. `sciezka_pulpitu()` — Pulpit przez Qt/XDG (na polskim Linuksie katalog
   nazywa się "Pulpit", nie "Desktop"); gdy brak — katalog domowy.
3. `znajdz_plik_wydania()` — wybiera plik wydania pasujący do systemu
   (Windows: .zip/.exe; Linux: *linux*.zip/AppImage; macOS: *mac*.zip).
4. `zbuduj_skrypt_podmiany_sh()` + `updater.sh` — pełna auto-aktualizacja
   z kopią zapasową, weryfikacją znacznika pmt_zyje.flag i rollbackiem,
   1:1 z logiką windowsową. Przetestowane (podmiana + rollback).
5. Uruchamianie updatera: `cmd /c` na Windows, `bash` + start_new_session
   na uniksach.
6. Czcionki PDF: Arial (Win/mac) → Liberation Sans → DejaVu Sans (Linux),
   z poprawną nazwą pliku LiberationSans-Regular.ttf (wcześniej literówka
   powodowała, że ta ścieżka nigdy nie działała).
7. Ikony: pmt_logo.ico (Windows), pmt_logo.icns (macOS), pmt_logo.png (Linux)
   — wszystkie wygenerowane z tego samego zaokrąglonego logo.

Dane użytkownika (`~/.pmt_*.json`) są w tym samym miejscu na każdym systemie
— przeniesienie plików między komputerami przenosi całą historię.
