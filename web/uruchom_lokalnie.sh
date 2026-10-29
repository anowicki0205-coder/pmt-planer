#!/bin/sh
# PMT Planer (web) — lokalny serwer do testów. Użycie: ./uruchom_lokalnie.sh  (potem http://localhost:8080/index.html)
cd "$(dirname "$0")"
[ -f sekret.txt ] || echo "UWAGA: brak sekret.txt obok tego pliku — zapytania pójdą bez podpisu."
[ -f menedzer.txt ] || echo "UWAGA: brak menedzer.txt obok tego pliku — generowanie dokumentów będzie zablokowane."
exec python3 serwer_lokalny.py 8080
