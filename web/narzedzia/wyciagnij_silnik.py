#!/usr/bin/env python3
"""Wyciąga z PMT_Delegacje.py część SILNIKOWĄ (bez Qt) — dosłownie, bez przepisywania.

Do pliku wynikowego trafia dokładnie ten tekst funkcji, klas i stałych, który stoi w programie
na komputerze: wybieramy węzły najwyższego poziomu (AST) potrzebne rootom, nic nie zmieniamy w treści.
Węzły odwołujące się do PyQt6 są pomijane (a ich zależności też, o ile nikt inny ich nie potrzebuje).

użycie: python wyciagnij_silnik.py [--zrodlo ../PMT_Delegacje.py] [--wynik silnik/pmt_silnik.py] [--pokaz]
"""
import ast, sys, os, argparse, hashlib

ROOTY = [
    # rachunek i limity
    "szacuj_delegacje", "ile_dokumentow", "rozdziel_rowno", "pojemnosc_dnia_km", "pojemnosc_dnia_zl", "maks_kwota_miesiaca",
    "kwota_typowego_dnia", "ustaw_tryb_pracy", "ustawienia_planowania",
    # kalendarz roboczy
    "pobierz_dni_robocze", "swieta_w_roku", "dni_zablokowane_miesiaca", "czy_niedziela_handlowa",
    # generowanie tras i dokumentów
    "generuj_trasy", "generuj_pdfy", "generuj_mape_html", "dni_delegacji_z_planu", "slad_dnia", "PrzerwanoGenerowanie",
    "pobierz_coords", "nazwa_do_pliku", "tekst_stawki", "kilometry_dokumentu", "opis_przejazdow", "uprzatnij_poprzedni_komplet",
    # planer wizyt
    "planuj_wizyty", "planuj_cyklicznie", "przeplanuj_zalegle", "zalegle_wizyty", "cykl_dla_punktu", "generuj_mape_planu_html",
    # walidacje
    "waliduj_pesel", "waliduj_adres", "waliduj_miesiac", "waliduj_kwote", "rozpoznaj_wojewodztwo",
    # dane i klasy
    "Miasto", "RawEtap", "Etap", "DzienTrasy", "DanePracownika", "PunktWizyty", "DzienPlanu", "MIESIACE_PL",
    "oblicz_dystans", "dystans_drogowy", "coords_z_miasta", "zaladuj_baze",
    # import listy sklepów i planer: odpowiedniki PlanerWizytThread / _wczytaj_pozycje_z_pliku
    "_dopasuj_kolumny", "_wiersz_na_adres", "NAGLOWKI_KOLUMN", "_klucz_geo", "_geo_cache", "_norm_miasto", "_zbuduj_indeks_miast",
    "zapisz_geo_cache", "_czas_przejazdu_min", "_dyst_prosty", "PLAN_CZAS_WIZYTY_MIN", "PLAN_SREDNIA_PREDKOSC_KMH", "GODZINA_STARTU_WIECZOR",
    "STAWKA_ZA_KM", "MAX_KWOTA_DOKUMENTU", "MAX_KWOTA_DNIA", "MAX_ETAPOW_DOKUMENTU", "MIN_KWOTA",
]

def nazwy_zdefiniowane(n):
    wyn = []
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        wyn.append(n.name)
    elif isinstance(n, ast.Assign):
        for t in n.targets:
            for x in ast.walk(t):
                if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store): wyn.append(x.id)
    elif isinstance(n, (ast.AnnAssign, ast.AugAssign)):
        if isinstance(n.target, ast.Name): wyn.append(n.target.id)
    elif isinstance(n, (ast.Try, ast.If, ast.With, ast.For)):
        for x in ast.walk(n):
            if isinstance(x, (ast.FunctionDef, ast.ClassDef)): wyn.append(x.name)
            elif isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store) and x.id.isupper(): wyn.append(x.id)
            elif isinstance(x, (ast.ImportFrom, ast.Import)):
                for a in x.names: wyn.append((a.asname or a.name).split(".")[0])
    elif isinstance(n, (ast.Import, ast.ImportFrom)):
        for a in n.names: wyn.append((a.asname or a.name).split(".")[0])
    return wyn

def uzywane_nazwy(n):
    return {x.id for x in ast.walk(n) if isinstance(x, ast.Name)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zrodlo", default=os.path.join(os.path.dirname(__file__), "..", "..", "PMT_Delegacje.py"))
    ap.add_argument("--wynik", default=os.path.join(os.path.dirname(__file__), "..", "silnik", "pmt_silnik.py"))
    ap.add_argument("--pokaz", action="store_true", help="tylko wypisz, co wchodzi i czego brakuje")
    a = ap.parse_args()
    tekst = open(a.zrodlo, encoding="utf-8").read()
    linie = tekst.split("\n")
    drzewo = ast.parse(tekst)
    qt = set()
    for n in drzewo.body:
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("PyQt6"):
            for al in n.names: qt.add(al.asname or al.name)
    zmiana = True
    while zmiana:                       # klasy dziedziczące po Qt też są „Qt”
        zmiana = False
        for n in drzewo.body:
            if isinstance(n, ast.ClassDef) and n.name not in qt and (uzywane_nazwy(ast.Module(body=[ast.Expr(b) for b in n.bases], type_ignores=[])) & qt):
                qt.add(n.name); zmiana = True
    wezly = list(enumerate(drzewo.body))
    zdef = {}
    for i, n in wezly:
        for nm in nazwy_zdefiniowane(n): zdef.setdefault(nm, []).append(i)
    # węzły dotykające Qt (bezpośrednio) — nie do silnika
    qt_wezly = {i for i, n in wezly if not isinstance(n, (ast.Import, ast.ImportFrom)) and (uzywane_nazwy(n) & qt)}
    # stałe i funkcje, które tylko „mówią” z interfejsem, ale nie mają Qt, mogą wejść — liczymy domknięcie
    wchodzi, kolejka, brak = set(), [], set()
    # wywołania wykonywane przy ładowaniu modułu (scalenie bazy miast, wczytanie cache): to też silnik —
    # bez nich ruszyłby w innym stanie niż program. Bierzemy te, które nie dotykają Qt i używają tylko znanych nazw.
    import builtins
    for i, n in wezly:
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and i not in qt_wezly:
            potrzebne = uzywane_nazwy(n)
            if potrzebne and all(x in zdef or hasattr(builtins, x) for x in potrzebne):
                kolejka.append(i)
    for r in ROOTY:
        if r not in zdef: brak.add(r); continue
        kolejka += zdef[r]
    while kolejka:
        i = kolejka.pop()
        if i in wchodzi: continue
        if i in qt_wezly:
            brak.add("QT:" + ",".join(nazwy_zdefiniowane(wezly[i][1])[:1])); continue
        wchodzi.add(i)
        for nm in uzywane_nazwy(wezly[i][1]):
            for j in zdef.get(nm, []):
                if j not in wchodzi: kolejka.append(j)
    # importy bezQt: wszystkie niezwiązane z PyQt6
    importy = [i for i, n in wezly if isinstance(n, (ast.Import, ast.ImportFrom)) and not (isinstance(n, ast.ImportFrom) and (n.module or "").startswith("PyQt6"))]
    # try/fpdf-import i inne bloki: jeśli zdefiniowały coś potrzebnego, są już w „wchodzi”
    ostateczne = sorted(set(importy) | wchodzi)
    if a.pokaz:
        print("węzłów w silniku:", len(wchodzi), "z", len(wezly))
        print("pominięte (Qt) lub brakujące:", sorted(brak))
        nz = [nazwy_zdefiniowane(wezly[i][1])[:1] for i in sorted(wchodzi)]
        print("rodzaje węzłów top-level wchodzących:", {type(wezly[i][1]).__name__ for i in wchodzi})
        return 0
    wyjscie = ['"""PMT — silnik delegacji WYCIĄGNIĘTY dosłownie z PMT_Delegacje.py przez narzedzia/wyciagnij_silnik.py.',
               'NIE EDYTUJ RĘCZNIE: każda zmiana silnika dzieje się w programie na komputerze i trafia tu ponownym wyciągnięciem."""']
    wyjscie.append("# źródło: PMT_Delegacje.py sha256:" + hashlib.sha256(tekst.encode("utf-8")).hexdigest()[:16])
    for i in ostateczne:
        n = wezly[i][1]
        start = (min([d.lineno for d in getattr(n, "decorator_list", [])] + [n.lineno])) - 1
        wyjscie.append("\n".join(linie[start:n.end_lineno]))
    os.makedirs(os.path.dirname(a.wynik), exist_ok=True)
    open(a.wynik, "w", encoding="utf-8").write("\n\n".join(wyjscie) + "\n")
    print("zapisano", a.wynik, "—", len(ostateczne), "węzłów; pominięte/brak:", sorted(brak))
    return 0

sys.exit(main())
