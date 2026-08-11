#!/bin/bash
# ============================================================
#  PMT Planer - skrypt aktualizacji (macOS / Linux)
#
#  WAZNE: ten plik jest pobierany SWIEZO z GitHuba przy kazdej
#  aktualizacji, NIE jest zaszyty w programie. Jesli kiedys
#  znajdzie sie tu blad, wystarczy poprawic TEN plik w repo -
#  dziala to natychmiast u WSZYSTKICH uzytkownikow.
#
#  ZABEZPIECZENIE: przed podmiana robimy kopie STAREJ wersji.
#  Po uruchomieniu nowej wersji sprawdzamy znacznik pmt_zyje.flag
#  zapisywany przez sam program zaraz po starcie - istnienie
#  procesu nic nie dowodzi, znacznik tak. Brak znacznika =
#  automatyczny powrot do poprzedniej, dzialajacej wersji.
#
#  Argumenty: $1=nowy plik  $2=plik docelowy  $3=PID starego programu
# ============================================================
NOWY="$1"
CEL="$2"
PID="$3"
TMPDIR_="${TMPDIR:-/tmp}"
LOG="$TMPDIR_/pmt_aktualizacja.log"
FLAGA="$TMPDIR_/pmt_zyje.flag"
KOPIA="$CEL.poprzednia"

echo "==============================" >  "$LOG"
echo "Start: $(date)"                 >> "$LOG"
echo "Nowy plik: $NOWY"               >> "$LOG"
echo "Plik docelowy: $CEL"            >> "$LOG"
echo "PID starego programu: $PID"     >> "$LOG"

[ -f "$NOWY" ] || { echo "[BLAD] Brak pobranego pliku: $NOWY" >> "$LOG"; exit 1; }

# 1) czekaj, az stary proces sie zamknie (do ~2 min)
echo "[1] Czekam na zamkniecie programu (PID $PID)..." >> "$LOG"
for i in $(seq 1 60); do
    kill -0 "$PID" 2>/dev/null || break
    sleep 2
done
echo "[1] OK." >> "$LOG"

# 2) kopia zapasowa starej, dzialajacej wersji
echo "[2] Zapisuje kopie poprzedniej wersji..." >> "$LOG"
[ -f "$CEL" ] && cp -f "$CEL" "$KOPIA" 2>>"$LOG"

# 3) podmiana pliku (z ponawianiem - bywa chwile zablokowany)
echo "[3] Podmieniam plik..." >> "$LOG"
OK=0
for i in $(seq 1 15); do
    if cp -f "$NOWY" "$CEL" 2>>"$LOG"; then OK=1; break; fi
    sleep 1
done
if [ "$OK" != "1" ]; then
    echo "[3] BLAD: nie udalo sie podmienic pliku (uprawnienia?). Stara wersja nienaruszona." >> "$LOG"
    exit 1
fi
chmod +x "$CEL" 2>>"$LOG"
rm -f "$NOWY" 2>/dev/null

# 4) usun stary znacznik "program zyje" i uruchom nowa wersje
rm -f "$FLAGA" 2>/dev/null
# 25 sekund: tyle zwykle trwa sprawdzanie swiezo zapisanego pliku przez system
# (Gatekeeper na macOS, skanery na Linuksie). Start wczesniej konczyl sie bledem.
sleep 25

# 4a) TEST DOSTEPNOSCI PLIKU - ta sama poprawka co w wersji Windows.
#     Swiezo skopiowany plik potrafi byc jeszcze "trzymany" przez system
#     (indeksowanie, ochrona antywirusowa, wolny dysk sieciowy), a proba
#     uruchomienia w tym momencie konczy sie bledem wczytywania bibliotek.
PROBNY="${TMPDIR:-/tmp}/pmt_test_dostepu.tmp"
i=1
while [ "$i" -le 10 ]; do
    if cp "$CEL" "$PROBNY" 2>/dev/null; then
        rm -f "$PROBNY" 2>/dev/null
        echo "[4] Plik gotowy do uruchomienia (proba $i)." >> "$LOG"
        break
    fi
    echo "[4] Plik jeszcze zajety - czekam (proba $i)..." >> "$LOG"
    sleep 3
    i=$((i+1))
done

# 4b) sprzatanie porzuconych katalogow _MEI po poprzednich uruchomieniach
rm -rf "${TMPDIR:-/tmp}"/_MEI* 2>/dev/null

# macOS: plik pobrany z sieci ma znacznik kwarantanny i system odmawia
# uruchomienia go ze skryptu, czesto BEZ zadnego komunikatu.
if command -v xattr >/dev/null 2>&1; then
    xattr -d com.apple.quarantine "$CEL" 2>/dev/null && \
        echo "[4] Zdjeto kwarantanne macOS." >> "$LOG"
fi
# czekamy tez, az stary proces naprawde zniknie z pamieci
NAZWA=$(basename "$CEL")
for i in $(seq 1 15); do
    if ! pgrep -f "$NAZWA" >/dev/null 2>&1; then
        echo "[4] Stary proces zamkniety - proba $i." >> "$LOG"
        break
    fi
    echo "[4] Stary proces jeszcze dziala - czekam - proba $i..." >> "$LOG"
    sleep 3
done

echo "[4] Uruchamiam nowa wersje..." >> "$LOG"
nohup "$CEL" >/dev/null 2>&1 &

# 5) weryfikacja przez znacznik - jak w wersji Windows
WYSTARTOWALA=0
PROBA2=0
for i in $(seq 1 20); do
    sleep 3
    if [ -f "$FLAGA" ]; then WYSTARTOWALA=1; break; fi
    if [ "$PROBA2" = "0" ] && [ "$i" -ge 10 ]; then
        echo "[4] Znacznik sie nie pojawil - drugie podejscie..." >> "$LOG"
        nohup "$CEL" >/dev/null 2>&1 &
        PROBA2=1
    fi
done

if [ "$WYSTARTOWALA" = "1" ]; then
    echo "[OK] Nowa wersja dziala. $(date)" >> "$LOG"
    rm -f "$KOPIA" 2>/dev/null
    rm -f "$0" 2>/dev/null
    exit 0
fi

# 6) rollback - przywroc poprzednia, dzialajaca wersje
echo "[4] BLAD: nowa wersja sie nie uruchomila. Przywracam poprzednia..." >> "$LOG"
if [ -f "$KOPIA" ]; then
    cp -f "$KOPIA" "$CEL" 2>>"$LOG"
    chmod +x "$CEL" 2>>"$LOG"
    rm -f "$KOPIA" 2>/dev/null
    nohup "$CEL" >/dev/null 2>&1 &
    echo "[OK] Przywrocono poprzednia wersje." >> "$LOG"
else
    echo "[BLAD] Brak kopii do przywrocenia." >> "$LOG"
fi
exit 1
