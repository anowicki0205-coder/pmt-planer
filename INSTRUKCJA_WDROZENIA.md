# PMT — instrukcja wdrożenia wersji 3.13.4

Stan sprawdzony na serwerze przed napisaniem tej instrukcji:
- `.github/workflows/build.yml` — **już poprawny** (nowa kolejność: Windows pierwszy) ✔
- `wersja.txt` i `PMT_Delegacje.py` w repo — **stare (3.13.2)**, do podmiany
- wydania v3.13.3 i v3.12.3 — **bez plików** (skasowane)

Zostały więc dwa kroki: wgrać pliki i wydać release.

---

## KROK 1 — pliki do katalogu GŁÓWNEGO repozytorium (13 plików)

Pobierz `DO_REPO_katalog_glowny.zip`, rozpakuj na pulpicie — dostaniesz 13 luźnych
plików. Potem:

1. Wejdź na `github.com/anowicki0205-coder/pmt-planer`
2. **Add file → Upload files**
3. Zaznacz w rozpakowanym folderze **wszystkie 13 plików naraz** (Ctrl+A) i przeciągnij
4. Na dole: **Commit changes**

Pliki w paczce (nadpiszą stare — tak ma być):

| Plik | Rola |
|---|---|
| `PMT_Delegacje.py` | program desktop, **wersja 3.13.4** |
| `wersja.txt` | numer wersji, który program czyta przy starcie |
| `wersja_info.txt` | dane wersji wkompilowane w plik .exe |
| `updater.bat`, `updater.sh` | skrypty podmiany pliku programu |
| `pmt_logo.ico`, `pmt_logo.icns`, `pmt_logo.png` | ikony do budowania |
| `pmt_wizyty.html` | aplikacja mobilna |
| `manifest.webmanifest`, `sw.js`, `pwa_192.png`, `pwa_512.png` | oprawa PWA (instalacja, offline, powiadomienia) |

---

## KROK 2 — usuń z katalogu głównego dwa zbędne pliki

W repo kliknij plik → ikona kosza (Delete file) → Commit:

- `build.yml` (kopia w złym miejscu; właściwy jest w `.github/workflows/`)
- `PMT_komplet.zip` (paczka archiwalna — w repo tylko przeszkadza)

---

## KROK 3 — wydaj wersję v3.13.4

1. Repo → **Releases** → **Draft a new release**
2. **Choose a tag** → wpisz `v3.13.4` → **Create new tag on publish**
3. Tytuł: `PMT Planer v3.13.4`
4. **Publish release**
5. Zakładka **Actions** — zadanie „Buduj wydanie": najpierw kończy się **windows**,
   potem **pozostale** (macOS, Linux). Łącznie ok. 10–15 minut.

Po zakończeniu w wydaniu powinny być **dokładnie trzy pliki, w tej kolejności**:

```
PMT_Planer.Windows.zip     <- Windows (pierwszy na liście — to kluczowe)
PMT_Planer_Linux.zip
PMT_Planer_macOS.zip
```

Nazwa Windows ma kropkę zamiast podkreślenia **celowo**: kropka sortuje się przed
podkreśleniem, więc archiwum Windows zawsze trafia na początek listy. Stare wersje
programu (3.12.x) pobierają pierwszy plik z wydania bez sprawdzania systemu — dzięki
tej nazwie dostaną właściwy.

---

## KROK 4 — sprawdzenie, że działa

Uruchom starą wersję programu (3.12.2) na dowolnym komputerze:
- pojawia się okno „NOWA WERSJA JEST GOTOWA v3.12.2 → v3.13.4"
- klikasz aktualizuj → pasek postępu → program restartuje się sam
- po restarcie: ustawienia → wiersz „Wersja" pokazuje **3.13.4**

Znaki, że nowa wersja faktycznie działa:
- okno logowania jest **granatowe, w stylu programu** (nie systemowe okienko Windows)
- w widoku miesiąca dni, które minęły **bez ani jednej wizyty**, są **krwistoczerwone**

---

## KROK 5 — backend w arkuszu (jeśli jeszcze nie zrobione)

1. Arkusz → Rozszerzenia → Apps Script
2. Ctrl+A → wklej całą treść `apps_script.gs` → zapisz
3. Uruchom funkcję `inicjalizuj_v2` (utworzy brakujące zakładki, poprosi o zgody)
4. **Wdróż → Zarządzaj wdrożeniami → ołówek → Wersja: Nowa → Wdróż**

Bez punktu 4 pod adresem `/exec` nadal działa stary kod — to najczęściej pomijany krok.

---

## Czego NIE robić

- Nie wgrywaj `build.yml` do katalogu głównego — GitHub czyta go tylko z `.github/workflows/`
- Nie dołączaj żadnych dodatkowych plików `.zip` do wydania (np. paczki kompletu) —
  stare wersje programu pobierają pierwszy `.zip` z listy i mogą trafić na zły plik
- Nie zmieniaj nazw archiwów w `build.yml` bez zmiany funkcji `znajdz_plik_wydania()`
  w programie — one są ze sobą sparowane
