# -*- coding: utf-8 -*-
"""Przeniesienie danych z programu na komputerze do aplikacji web (PMT Planer).

Moduł towarzyszący (tylko biblioteka standardowa, bez Qt): program zbiera dane konta, szyfruje je
i zapisuje plik .pmtdane; aplikacja web (js/przeniesienie.js) odczytuje go po zalogowaniu tym samym
kodem i hasłem. PESEL nie leży w pliku jawnie.

Format pliku (JSON, jedna linia):
    {"pmt": "przeniesienie", "v": 1, "kod": "12345", "sol": <hex 16 B>, "iv": <hex 16 B>,
     "dane": <base64 szyfrogramu>, "mac": <hex 32 B>}

Klucz:   K  = PBKDF2-HMAC-SHA256(skrót hasła, sol, 100 000 iteracji, 32 B)
         Ks = HMAC-SHA256(K, "pmt-przen-szyfr"),  Kp = HMAC-SHA256(K, "pmt-przen-podpis")
         „skrót hasła" to ten sam SHA-256("PMT|kod|hasło"), który zna backend i aplikacja web po zalogowaniu.
Szyfr:   strumień bloków HMAC-SHA256(Ks, iv || numer bloku, 4 B big-endian) XOR tekst JSON (UTF-8).
Podpis:  HMAC-SHA256(Kp, "PMT-PRZENIESIENIE|1|kod|sol|iv|" + szyfrogram) — sprawdzany PRZED odszyfrowaniem.

Ładunek (JSON w szyfrogramie): profil (Moje dane), sklepy (lista adresów), plan (plan wizyt: miesiące → dni → wizyty z współrzędnymi),
odhaczenia (dziennik odhaczonych wizyt dla dni planu). Czego tu nie ma: historii miesięcy i wygenerowanych dokumentów (zostają na dysku).

Zasada: moduł niczego nie zgaduje i nie zmienia stanu programu; błędny klucz = ValueError, nie śmieci.
"""
import base64
import datetime
import hashlib
import hmac
import json
import os

FORMAT = 1
ROZSZERZENIE = ".pmtdane"
ITERACJE = 100000
MAX_PUNKTOW = 5000
MAX_DLUGOSC_POLA = 200
MAX_MIESIECY = 14          # plan wizyt: miesięcy, dni i wizyt w dniu — ponad to obcinamy (plan z programu ma kilka miesięcy)
MAX_DNI = 400
MAX_WIZYT_W_DNIU = 60
MAX_ODHACZEN = 5000
DNI_WSTECZ = 31            # z planu bierzemy dni od (dziś − 31 dni): starszych aplikacja i tak nie pokaże


def hash_hasla(kod, haslo) -> str:
    """Skrót hasła konta — ten sam wzór co w programie, backendzie i aplikacji web."""
    return hashlib.sha256(("PMT|%s|%s" % (kod, haslo)).encode("utf-8")).hexdigest()


def _hmac(klucz: bytes, dane: bytes) -> bytes:
    return hmac.new(klucz, dane, hashlib.sha256).digest()


def _klucze(skrot: str, sol: bytes):
    k = hashlib.pbkdf2_hmac("sha256", str(skrot).encode("utf-8"), sol, ITERACJE, 32)
    return _hmac(k, b"pmt-przen-szyfr"), _hmac(k, b"pmt-przen-podpis")


def _strumien(klucz: bytes, iv: bytes, dlugosc: int) -> bytes:
    out = bytearray()
    blok = 0
    while len(out) < dlugosc:
        out += _hmac(klucz, iv + blok.to_bytes(4, "big"))
        blok += 1
    return bytes(out[:dlugosc])


def _podpis(kp: bytes, kod: str, sol: bytes, iv: bytes, szyfrogram: bytes) -> bytes:
    return _hmac(kp, ("PMT-PRZENIESIENIE|%d|%s|%s|%s|" % (FORMAT, kod, sol.hex(), iv.hex())).encode("utf-8") + szyfrogram)


def zaszyfruj(dane: dict, kod: str, skrot: str, sol: bytes = None, iv: bytes = None) -> str:
    """Zwraca tekst pliku (JSON). sol/iv podajemy tylko w testach (powtarzalny wynik)."""
    kod = str(kod)
    if not (kod.isdigit() and len(kod) == 5):
        raise ValueError("kod konta musi mieć 5 cyfr")
    if not skrot:
        raise ValueError("brak skrótu hasła")
    sol = sol if sol is not None else os.urandom(16)
    iv = iv if iv is not None else os.urandom(16)
    ks, kp = _klucze(skrot, sol)
    tekst = json.dumps(dane, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    szyfrogram = bytes(a ^ b for a, b in zip(tekst, _strumien(ks, iv, len(tekst))))
    return json.dumps({"pmt": "przeniesienie", "v": FORMAT, "kod": kod, "sol": sol.hex(), "iv": iv.hex(),
                       "dane": base64.b64encode(szyfrogram).decode("ascii"),
                       "mac": _podpis(kp, kod, sol, iv, szyfrogram).hex()}, separators=(",", ":"))


def odszyfruj(tekst: str, skrot: str) -> dict:
    """Odwrotność zaszyfruj(); ValueError, gdy plik jest uszkodzony albo klucz (kod/hasło) nie pasuje."""
    try:
        k = json.loads(tekst)
        if k.get("pmt") != "przeniesienie" or k.get("v") != FORMAT:
            raise ValueError("to nie jest plik przeniesienia danych PMT")
        kod = str(k["kod"]); sol = bytes.fromhex(k["sol"]); iv = bytes.fromhex(k["iv"])
        szyfrogram = base64.b64decode(k["dane"], validate=True); mac = bytes.fromhex(k["mac"])
    except ValueError:
        raise
    except Exception:
        raise ValueError("plik przeniesienia jest uszkodzony")
    ks, kp = _klucze(skrot, sol)
    if not hmac.compare_digest(mac, _podpis(kp, kod, sol, iv, szyfrogram)):
        raise ValueError("zły klucz albo plik zmieniony — to nie to konto/hasło")
    return json.loads(bytes(a ^ b for a, b in zip(szyfrogram, _strumien(ks, iv, len(szyfrogram)))).decode("utf-8"))


def _pole(v) -> str:
    return " ".join(str(v if v is not None else "").split())[:MAX_DLUGOSC_POLA]


def _liczba(v, lo, hi, dom=0.0):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return dom
    return dom if x != x or x < lo or x > hi else round(x, 4)


def _wspolrzedna(v, granica):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return round(x, 6) if x == x and -granica <= x <= granica else None


def _plan(plan, dzis):
    """Plan wizyt z programu (.pmt_plan_*.json) → tylko to, co aplikacja web umie odtworzyć: dni od (dziś − 31 dni),
    wizyty z adresem, współrzędne i liczby w rozsądnych granicach. Sumy aplikacja liczy sama. None, gdy nic nie zostaje."""
    if not isinstance(plan, dict):
        return None
    od = dzis - datetime.timedelta(days=DNI_WSTECZ)
    miesiace, ile_dni = [], 0
    for m in (plan.get("miesiace") or [])[:MAX_MIESIECY]:
        if not isinstance(m, dict):
            continue
        dni = []
        for d in (m.get("dni") or []):
            if not isinstance(d, dict) or ile_dni >= MAX_DNI:
                continue
            try:
                data = datetime.date.fromisoformat(str(d.get("data")))
            except ValueError:
                continue
            if data < od:
                continue
            wizyty = []
            for w in (d.get("wizyty") or [])[:MAX_WIZYT_W_DNIU]:
                if isinstance(w, dict) and _pole(w.get("adres")):
                    wizyty.append({"nazwa": _pole(w.get("nazwa")) or _pole(w.get("adres")), "adres": _pole(w.get("adres")),
                                   "siec": _pole(w.get("siec")), "miasto": _pole(w.get("miasto")),
                                   "lat": _wspolrzedna(w.get("lat"), 90), "lng": _wspolrzedna(w.get("lng"), 180)})
            if wizyty:
                dni.append({"data": data.isoformat(), "km": _liczba(d.get("km"), 0, 2000), "minuty": _liczba(d.get("minuty"), 0, 1440), "wizyty": wizyty})
                ile_dni += 1
        if dni:
            pierwszy = datetime.date.fromisoformat(dni[0]["data"])
            miesiace.append({"rok": pierwszy.year, "miesiac": pierwszy.month, "dni": dni})
    if not miesiace:
        return None
    try:
        cykl = max(1, min(52, int(plan.get("cykl_domyslny", 4))))
    except (TypeError, ValueError):
        cykl = 4
    return {"cykliczny": bool(plan.get("cykliczny")), "cykl_domyslny": cykl, "miesiace": miesiace}


def _odhaczenia(dziennik, plan):
    """Odhaczone wizyty z dziennika programu ({"RRRR-MM-DD|adres": {"czas": "dd.mm.RRRR HH:MM"}}) — tylko dla dni, które weszły do planu."""
    if not isinstance(dziennik, dict) or not plan:
        return {}
    dni = {d["data"] for m in plan["miesiace"] for d in m["dni"]}
    wynik = {}
    for klucz, wpis in dziennik.items():
        k = str(klucz)
        if k.split("|", 1)[0] in dni and len(k) <= 300 and len(wynik) < MAX_ODHACZEN:
            wynik[k] = {"czas": _pole(wpis.get("czas")) if isinstance(wpis, dict) else ""}
    return wynik


def zloz_dane(profil, punkty, wersja_programu: str = "", data_iso: str = "", plan=None, dziennik=None) -> dict:
    """Ładunek pliku: wyłącznie to, co aplikacja web umie wczytać (Moje dane, lista sklepów, plan wizyt i odhaczenia)."""
    try:
        dzis = datetime.date.fromisoformat(str(data_iso))
    except ValueError:
        dzis = datetime.date.today()
    p = None
    if isinstance(profil, dict) and (profil.get("imie") or profil.get("pesel")):
        try:
            idx = int(profil.get("silnik_idx", 1))
        except (TypeError, ValueError):
            idx = 1
        stan = _pole(profil.get("stanowisko"))
        p = {"imie": _pole(profil.get("imie")), "pesel": "".join(c for c in str(profil.get("pesel") or "") if c.isdigit())[:11],
             "adres": _pole(profil.get("adres")), "stanowisko": "KR" if stan.upper() == "KR" else "merchandiser",
             "silnik_powyzej_900": idx != 0}
    lista = []
    for x in (punkty or []):
        if isinstance(x, dict) and _pole(x.get("adres")):
            lista.append({"adres": _pole(x.get("adres")), "siec": _pole(x.get("siec")), "miasto": _pole(x.get("miasto"))})
        if len(lista) >= MAX_PUNKTOW:
            break
    pl = _plan(plan, dzis)
    return {"z": "program", "wersja_programu": str(wersja_programu), "data": str(data_iso), "profil": p, "sklepy": lista,
            "plan": pl, "odhaczenia": _odhaczenia(dziennik, pl)}
