# PMT — komplet systemu (stan: sierpień 2026, program v3.13.2)

Kopia zapasowa wszystkich elementów systemu. Rozpakuj na komputerze źródłowym
i trzymaj jako punkt odniesienia — każdy plik opisany jest niżej razem z tym,
DOKĄD go wgrać.

---

## Co gdzie trafia

| Katalog | Plik | Miejsce docelowe |
|---|---|---|
| `1_program_desktop` | `PMT_Delegacje.py`, `wersja.txt`, `wersja_info.txt` | repozytorium GitHub (katalog główny) |
| `1_program_desktop` | `updater.bat`, `updater.sh` | repozytorium GitHub (katalog główny) |
| `2_ikony` | `pmt_logo.ico`, `.icns`, `.png` | repozytorium GitHub (katalog główny) |
| `3_budowanie_github` | `build.yml` | repozytorium → `.github/workflows/build.yml` |
| `4_backend_arkusz` | `apps_script.gs` | Arkusz Google → Rozszerzenia → Apps Script |
| `5_program_desktop_online` | `pmt_online.py` | źródło modułu online (jest już wklejony w programie) |
| `6_aplikacja_wizyty` | `pmt_wizyty.html`, `manifest.webmanifest`, `sw.js`, `pwa_192.png`, `pwa_512.png` | repozytorium GitHub (katalog główny) |
| `7_dane_do_arkusza` | pliki `.csv` | import do Arkusza Google — **NIGDY do repozytorium** (dane osobowe) |
| — | `PMT_plan_wdrozenia.pdf` | checklista wdrożeniowa do wydruku |

---

## Kolejność wdrożenia (gdyby trzeba było odtworzyć wszystko od zera)

1. **Arkusz**: wklej `apps_script.gs` → zapisz → uruchom `inicjalizuj_v2`
   (utworzy zakładki i poprosi o zgody) → **Wdróż → Zarządzaj wdrożeniami →
   ołówek → Wersja: Nowa → Wdróż**. Adres `/exec` jest już wklejony w plikach
   klienckich — zmieniaj go tylko, jeśli tworzysz nowe wdrożenie od podstaw.
2. **Klucz AI**: Ustawienia projektu → Właściwości skryptu → `ANTHROPIC_KLUCZ`.
3. **Dane**: zakładki Uzytkownicy (+ telefony!), Rejonizacja, Produkty —
   import plików z `7_dane_do_arkusza` z **włączoną** opcją "Konwertuj tekst
   na liczby, daty i formuły" (chroni zera wiodące w kodach).
4. **Repozytorium**: wgraj pliki z `1_`, `2_`, `6_` do katalogu głównego,
   `build.yml` do `.github/workflows/`.
5. **Strona aplikacji**: Settings → Pages → Deploy from a branch → main → /(root).
   Adres: `https://<login>.github.io/<repo>/pmt_wizyty.html`
6. **Wydanie programu**: Releases → Draft a new release → tag `v3.13.2` →
   Publish. GitHub zbuduje Windows/macOS/Linux i dołączy trzy pliki .zip.

---

## WAŻNE zasady, które kosztowały nas czas

- **W wydaniu (Release) mogą być TYLKO trzy pliki**: `PMT_Planer_Windows.zip`,
  `PMT_Planer_macOS.zip`, `PMT_Planer_Linux.zip`. Każdy dodatkowy `.zip`
  potrafił zmylić aktualizator starszych wersji (program pobierał złe archiwum
  i zgłaszał brak pliku `.exe`). Wersja 3.13.2 jest już na to odporna —
  szuka archiwum z "windows" w nazwie — ale zasada zostaje.
- **Buildy na Pythonie 3.13**, nie 3.14 (błąd `python314.dll` u użytkowników).
- **Po każdej zmianie skryptu w arkuszu** trzeba wydać **nową wersję wdrożenia**,
  inaczej pod adresem `/exec` działa stary kod.
- **Dane osobowe** (kody, telefony, rejonizacja) nie trafiają do repozytorium.

---

## Stan systemu w tej wersji

**Program desktop (v3.13.2)**: logowanie 5-cyfrowym kodem w oknie w stylu
programu, sesje zarządzane zdalnie przez arkusz, statystyki pracy
(uruchomienia / dokumenty / minuty) z kolejką offline, dni niezrealizowane
w kalendarzu na krwistą czerwień, synchronizacja natychmiastowa po
wygenerowaniu PDF + pętla co 15 minut, odporny aktualizator.

**Backend (Apps Script)**: logowanie (hasło z hashem SHA-256, przejściowo
telefon), rejonizacja i "moje sklepy", planogramy, analiza półek AI
(strategia "puste miejsca najpierw" + strony planogramu jako wzorzec, siatka
współrzędnych, rada trenera), baza Produkty (EAN + zdjęcia na Dysku),
historia wizyt, zgłoszenia z terenu, zmiana hasła, pulpit administratora
(menu PMT → Odśwież pulpit: statystyki per osoba + alerty poniżej 70%).

**Aplikacja mobilna (PWA)**: instalowana z ikoną PMT, działa offline,
powiadomienia przez service workera, przepływ wizyty (planogram wielostronicowy
→ skan półki → lista ✓/✗ → dokładanie z drzewkiem przyczyn → skan kontrolny →
delta + weryfikacja deklaracji), plan dnia z nawigacją, skaner EAN na żywo,
dyktafon uwag, autozapis i wznowienie wizyty, strefy braków na zdjęciu,
protokół PDF dla kierownika, moduł wykrywania nowości.
