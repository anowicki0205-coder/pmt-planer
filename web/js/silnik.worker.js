// PMT Planer (web) — Web Worker z silnikiem delegacji (Pyodide + oryginalny kod Pythona).
// Protokół: {id, metoda, arg} → {id, ok, wynik|blad}; w trakcie pracy {id, typ:'postep', tekst, wartosc}.
import { loadPyodide } from '../vendor/pyodide/pyodide.mjs';

const KORZEN = new URL('../', import.meta.url);
const adres = s => new URL(s, KORZEN).href;
let py = null, start = null;

async function pobierz(s, opcjonalnie = false) {
  const r = await fetch(adres(s), { cache: 'force-cache' });
  if (!r.ok) { if (opcjonalnie) return null; throw new Error('Nie można pobrać ' + s + ' (' + r.status + ')'); }
  return new Uint8Array(await r.arrayBuffer());
}
/* menedzer.txt (nazwisko przełożonego) leży obok index.html. Czytamy go ZAWSZE ze świeżego żądania (bez pamięci podręcznej przeglądarki, w której mógł zostać stary „404”)
   i ponawiamy przy każdym użyciu, gdy go jeszcze nie ma — dzięki temu plik dołożony po uruchomieniu aplikacji też zadziała, bez odświeżania strony. */
const SC_MENEDZERA = '/home/pyodide/menedzer.txt', stanMenedzera = { url: '', status: 0, blad: '', sugestia: '' };
/** Notatnik potrafi zapisać plik jako UTF-8 z BOM, UTF-16 albo ANSI (Windows-1250): rozpoznajemy kodowanie i oddajemy pierwszą niepustą linię jako czysty tekst. */
function tekstZPliku(b) {
  let t;
  if (b.length >= 2 && b[0] === 0xFF && b[1] === 0xFE) t = new TextDecoder('utf-16le').decode(b.subarray(2));
  else if (b.length >= 2 && b[0] === 0xFE && b[1] === 0xFF) t = new TextDecoder('utf-16be').decode(b.subarray(2));
  else {
    try { t = new TextDecoder('utf-8', { fatal: true }).decode(b); } catch (e) { t = new TextDecoder('windows-1250').decode(b); }
    if (t.charCodeAt(0) === 0xFEFF) t = t.slice(1);
  }
  return (t.split(/\r?\n/).map(x => x.trim()).find(x => x) || '');
}
async function wczytajMenedzera(wymus) {
  try { if (!wymus && py.FS.analyzePath(SC_MENEDZERA).exists) return true; } catch (e) { /* sprawdzimy pobraniem */ }
  stanMenedzera.url = adres('menedzer.txt'); stanMenedzera.status = 0; stanMenedzera.blad = ''; stanMenedzera.sugestia = '';
  try {
    const r = await fetch(stanMenedzera.url, { cache: 'no-store' }); stanMenedzera.status = r.status;
    if (r.ok) {
      const tekst = tekstZPliku(new Uint8Array(await r.arrayBuffer()));
      if (tekst) { py.FS.mkdirTree('/home/pyodide'); py.FS.writeFile(SC_MENEDZERA, tekst + '\n'); return true; }      // zawsze czysty UTF-8 (silnik czyta go jak w programie)
      stanMenedzera.blad = 'plik jest pusty'; return false;
    }
    const r2 = await fetch(adres('menedzer.txt.txt'), { cache: 'no-store' }).catch(() => null);      // typowa pomyłka: Windows ukrywa rozszerzenie i powstaje „menedzer.txt.txt”
    if (r2 && r2.ok) stanMenedzera.sugestia = 'podwojone-txt';
  } catch (e) { stanMenedzera.blad = String(e && e.message || e); }
  return false;
}
const syncfs = (z) => new Promise((ok, err) => py.FS.syncfs(z, e => e ? err(e) : ok()));

async function uruchom(meldunek) {
  meldunek('Uruchamianie silnika…', 0.05);
  py = await loadPyodide({ indexURL: adres('vendor/pyodide/') });
  meldunek('Ładowanie bibliotek dokumentów…', 0.30);
  await py.loadPackage(adres('vendor/paczki/pillow-11.3.0-cp313-cp313-pyodide_2025_0_wasm32.whl'));
  for (const w of ['fonttools-4.56.0-py3-none-any.whl', 'defusedxml-0.7.1-py2.py3-none-any.whl', 'fpdf2-2.8.9-py3-none-any.whl', 'et_xmlfile-2.0.0-py3-none-any.whl', 'openpyxl-3.1.5-py2.py3-none-any.whl'])
    py.unpackArchive(await pobierz('vendor/paczki/' + w), 'zip', { extractDir: '/lib/python3.13/site-packages' });
  meldunek('Czcionki dokumentów…', 0.55);
  py.FS.mkdirTree('/usr/share/fonts/truetype/liberation');
  for (const f of ['LiberationSans-Regular.ttf', 'LiberationSans-Bold.ttf'])
    py.FS.writeFile('/usr/share/fonts/truetype/liberation/' + f, await pobierz('silnik/fonty/' + f));
  // pamięć podręczna silnika (drogi, współrzędne) przeżywa odświeżenie strony
  py.FS.mkdirTree('/home/pyodide');
  try { py.FS.mount(py.FS.filesystems.IDBFS, {}, '/home/pyodide'); await syncfs(true); } catch (e) { /* bez trwałego dysku też działa */ }
  // opcjonalne pliki obok aplikacji (jak obok programu na komputerze); brak pliku = brak wpisu (ponowna próba przy generowaniu)
  await wczytajMenedzera(true);
  meldunek('Silnik delegacji…', 0.75);
  py.FS.mkdirTree('/app');
  for (const f of ['pmt_silnik.py', 'boot.py', 'most.py']) py.FS.writeFile('/app/' + f, await pobierz('silnik/' + f));
  try { py.FS.writeFile('/app/sieci_cel.txt', await pobierz('silnik/sieci_cel.txt')); } catch (e) { /* bez listy sieci zostaje dotychczasowa lista programu */ }
  py.FS.mkdirTree('/dokumenty');
  await py.runPythonAsync("import sys\nsys.path.insert(0, '/app')\nimport warnings\nwarnings.filterwarnings('ignore')\nimport boot\nimport most");
  meldunek('Gotowe', 1);
}

let licznikWolan = 0;
function wolaj(metoda, arg, postep) {
  /* osobne zmienne na KAŻDE wywołanie: dwa wywołania naraz (np. sprawdzenie adresu i dni miesiąca) nie mogą nadpisać sobie argumentów
     (dawniej wspólna zmienna _ARG dawała sporadyczny błąd „KeyError: 'rok'” i miesiąc bez dni roboczych) */
  const n = ++licznikWolan, a = '_ARG' + n, pp = '_POSTEP' + n;
  py.globals.set(a, JSON.stringify(arg ?? {}));
  py.globals.set(pp, postep || null);
  const dopisek = (metoda === 'generuj' || metoda === 'plan_generuj') ? `, ${pp}` : '';
  return py.runPythonAsync(`import json, most\njson.dumps(most.${metoda}(json.loads(${a})${dopisek}), ensure_ascii=False)`).then(JSON.parse)
    .finally(() => { try { py.globals.delete(a); py.globals.delete(pp); } catch (e) { /* zmienna już zniknęła */ } });
}

const METODY = {
  async dni(a) { return wolaj('api_dni', a); },
  async stale(a) { return wolaj('api_stale', a); },
  async maks(a) { return wolaj('api_maks', a); },
  async przygotuj(a) {
    await wczytajMenedzera(false);
    const w = await wolaj('przygotuj', a);
    if (w && w.powod === 'brak menedzer.txt') w.szczegoly = { ...stanMenedzera };
    return w;
  },
  async adres(a) { return wolaj('api_adres', a); },
  /** Kasuje pliki pamięci silnika zapisane na urządzeniu (trasy i współrzędne, liczniki, kopia menedzer.txt): są wspólne dla wszystkich kont tej przeglądarki, więc czyścimy je przy zmianie konta, wylogowaniu i „Usuń dane”. */
  async czysc() {
    await py.runPythonAsync(`
import os, glob, sys
_d = os.path.expanduser("~")
for _f in glob.glob(os.path.join(_d, ".pmt_*")) + [os.path.join(_d, "menedzer.txt")]:
    try: os.remove(_f)
    except OSError: pass
_m = sys.modules.get("pmt_silnik")
if _m is not None and hasattr(_m, "_road_cache"): _m._road_cache.clear()
`);
    try { await syncfs(false); } catch (e) { /* bez trwałego dysku nie ma czego kasować */ }
    return {};
  },
  async siec(a) { py.globals.set('_S', !!a.wlaczona); await py.runPythonAsync('boot.ustaw_siec(_S)'); return {}; },
  async planWczytaj(a) {
    const rozsz = (a.nazwa.toLowerCase().match(/\.(csv|xlsx)$/) || ['', 'xlsx'])[1];
    const sc = '/plan_import.' + rozsz; py.FS.writeFile(sc, a.bajty);
    return wolaj('plan_wczytaj', { sciezka: sc });
  },
  async planGeneruj(a, postep) {
    a.siec = a.siec !== false;
    await wczytajMenedzera(false);
    const w = await wolaj('plan_generuj', a, postep);
    try { await syncfs(false); } catch (e) { /* cache nie zapisany */ }
    return w;
  },
  async generuj(a, postep) {
    await wczytajMenedzera(false);
    const w = await wolaj('generuj', a, postep);
    try { await syncfs(false); } catch (e) { /* cache nie zapisany — trudno */ }
    const pdf = w.pliki.map(n => ({ nazwa: n, bajty: py.FS.readFile(w.folder + '/' + n) }));
    return { wynik: w, pdf };
  },
};

self.onmessage = async ev => {
  const { id, metoda, arg } = ev.data;
  const meld = (t, v) => self.postMessage({ id, typ: 'postep', tekst: t, wartosc: v });
  try {
    if (metoda === 'start') { start = start || uruchom(meld); await start; self.postMessage({ id, ok: true, wynik: {} }); return; }
    await start;
    const wynik = await METODY[metoda](arg, meld);
    const przenies = wynik && wynik.pdf ? wynik.pdf.map(p => p.bajty.buffer) : [];
    self.postMessage({ id, ok: true, wynik }, przenies);
  } catch (e) {
    self.postMessage({ id, ok: false, blad: String(e && e.message || e).split('\n').filter(Boolean).pop() });
  }
};
