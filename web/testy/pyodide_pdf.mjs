import { loadPyodide } from '../vendor/pyodide/pyodide.mjs';
import fs from 'node:fs';
const W = new URL('..', import.meta.url).pathname;
const py = await loadPyodide({ indexURL: W + 'vendor/pyodide/' });
await py.loadPackage(W + 'vendor/paczki/pillow-11.3.0-cp313-cp313-pyodide_2025_0_wasm32.whl');
for (const w of ['fonttools-4.56.0-py3-none-any.whl', 'defusedxml-0.7.1-py2.py3-none-any.whl', 'fpdf2-2.8.9-py3-none-any.whl']) {
  py.unpackArchive(new Uint8Array(fs.readFileSync(W + 'vendor/paczki/' + w)), 'zip', { extractDir: '/lib/python3.13/site-packages' });
}
py.FS.mkdirTree('/usr/share/fonts/truetype/liberation');
for (const f of ['LiberationSans-Regular.ttf', 'LiberationSans-Bold.ttf'])
  py.FS.writeFile('/usr/share/fonts/truetype/liberation/' + f, fs.readFileSync(W + 'silnik/fonty/' + f));
py.runPython(`
import http.client as _hc, urllib.request as _u
if not hasattr(_hc, 'HTTPSConnection'):
    _hc.HTTPSConnection = _hc.HTTPConnection
if not hasattr(_u, 'HTTPSHandler'):
    _u.HTTPSHandler = _u.HTTPHandler   # fpdf2 importuje tę nazwę; Pyodide bez ssl jej nie ma (obrazów z sieci nie pobieramy)
`);
py.FS.writeFile('/pmt_silnik.py', fs.readFileSync(W + 'silnik/pmt_silnik.py', 'utf8'));
const src = "SILNIK='/'\nOUT='/pdf_out'\n" + fs.readFileSync(W + 'testy/pdf_proba.py', 'utf8');
const t0 = Date.now();
let r;
try {
  r = await py.runPythonAsync(`
import io, sys
b = io.StringIO(); o = sys.stdout; sys.stdout = b
try:
    exec(compile(${JSON.stringify(src)}, 'p', 'exec'), {})
finally:
    sys.stdout = o
b.getvalue()`);
} catch (e) { console.log('BLAD:', String(e.message).slice(-900)); process.exit(1); }
console.log(r.trim());
fs.mkdirSync('/tmp/pdf_py', { recursive: true });
for (const n of py.FS.readdir('/pdf_out').filter(x => x.endsWith('.pdf'))) fs.writeFileSync('/tmp/pdf_py/' + n, py.FS.readFile('/pdf_out/' + n));
console.log('czas ms', Date.now() - t0);
