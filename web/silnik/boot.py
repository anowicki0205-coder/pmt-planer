# -*- coding: utf-8 -*-
"""PMT Planer (web) — warstwa „host": sztuczki środowiska Pyodide. TO NIE JEST SILNIK — silnik to pmt_silnik.py
(wyciągnięty dosłownie z programu). Tu tylko to, czego przeglądarka nie daje wprost:

  1. HTTPSConnection / HTTPSHandler: Pyodide bez modułu ssl nie ma tych nazw, a fpdf2 je importuje;
  2. urllib.request.urlopen → synchroniczny XMLHttpRequest (wolno w Web Workerze), dzięki czemu silnik
     bez żadnej zmiany pyta o drogi (OSRM) i współrzędne (Nominatim) tą samą ścieżką co w programie.
"""
import sys, io
import http.client as _hc
import urllib.request as _u
import urllib.error as _ue

if not hasattr(_hc, "HTTPSConnection"):
    _hc.HTTPSConnection = _hc.HTTPConnection
if not hasattr(_u, "HTTPSHandler"):
    _u.HTTPSHandler = _u.HTTPHandler

SIEC_WLACZONA = True          # JS może wyłączyć (tryb samolotowy); wtedy silnik używa swoich zapasowych szacunków


class _Odpowiedz:
    def __init__(self, url, status, tresc):
        self.url, self.status, self.code, self._tresc = url, status, status, tresc
        self.headers = {}
    def read(self, n=-1):
        return self._tresc if n is None or n < 0 else self._tresc[:n]
    def getcode(self): return self.status
    def geturl(self): return self.url
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def close(self): pass


def _urlopen(req, data=None, timeout=None, **_ignored):
    """Zamiennik urllib.request.urlopen (tylko GET): synchroniczny XHR z workera."""
    if not SIEC_WLACZONA:
        raise _ue.URLError("sieć wyłączona")
    adres = req.full_url if hasattr(req, "full_url") else str(req)
    from js import XMLHttpRequest
    xhr = XMLHttpRequest.new()
    try:
        xhr.open("GET", adres, False)
        xhr.responseType = "arraybuffer"
        if timeout:
            xhr.timeout = int(float(timeout) * 1000)
        xhr.send()
    except Exception as e:                       # brak sieci, CORS, przekroczony czas
        raise _ue.URLError(str(e))
    status = int(xhr.status)
    if status == 0:
        raise _ue.URLError("brak odpowiedzi serwera")
    if status >= 400:
        raise _ue.HTTPError(adres, status, "HTTP %d" % status, {}, io.BytesIO(b""))
    return _Odpowiedz(adres, status, bytes(xhr.response.to_py()))


_u.urlopen = _urlopen


def ustaw_siec(wlaczona):
    global SIEC_WLACZONA
    SIEC_WLACZONA = bool(wlaczona)
