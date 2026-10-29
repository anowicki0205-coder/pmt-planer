import sys, os, json, importlib, tempfile, warnings, glob
warnings.filterwarnings("ignore")
os.environ["HOME"] = tempfile.mkdtemp(prefix="pmt_home_")
sys.path.insert(0, SILNIK)
S = importlib.import_module("pmt_silnik")
def _brak(*a, **k): raise OSError("bez sieci")
S.urllib.request.urlopen = _brak
S.ustaw_tryb_pracy("wieczor")
dni = S.generuj_trasy(3095.26, "Warszawa", 52.2297, 21.0122, "mazowieckie", S.pobierz_dni_robocze(2026, 9), "90010112345", 1.15)
prac = S.DanePracownika(imie="Jan Testowy", pesel="90010112345", adres="ul. Testowa 1, 00-001 Warszawa", stanowisko="Merchandiser",
                        kod_pocztowy="00-001", baza_miasto="Warszawa", baza_lat=52.2297, baza_lng=21.0122, wojewodztwo="mazowieckie")
folder = OUT
S.generuj_pdfy(dni, prac, 9, 2026, folder, 1.15, lambda t, v: None, zrodlo=S.stan_zrodla_odleglosci())
print(json.dumps({"pliki": sorted((os.path.basename(f), os.path.getsize(f)) for f in glob.glob(folder + "/*")), "fpdf_blad": S.FPDF_BLAD}, ensure_ascii=False))
