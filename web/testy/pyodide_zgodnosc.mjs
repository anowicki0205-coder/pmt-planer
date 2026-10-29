// Ten sam test zgodności co zgodnosc_silnika.py, ale w Pyodide (Python w przeglądarce / Node).
import { loadPyodide } from '../vendor/node_modules/pyodide/pyodide.mjs';
import fs from 'node:fs';
const py = await loadPyodide();
const kod = fs.readFileSync(new URL('../silnik/pmt_silnik.py', import.meta.url), 'utf8');
py.FS.writeFile('/pmt_silnik.py', kod);
const test = fs.readFileSync(new URL('./zgodnosc_silnika.py', import.meta.url), 'utf8')
  .replace(/^RAZEM = .*$/m, 'RAZEM = "/"')
  .replace('sys.path.insert(0, os.path.join(RAZEM, "web", "silnik")); S = importlib.import_module("pmt_silnik")', 'sys.path.insert(0, "/"); S = importlib.import_module("pmt_silnik")');
py.globals.set('ARGV', ['x', 'wyciag']);
const t0 = Date.now();
const wyj = await py.runPythonAsync(`
import sys, io
sys.argv = list(ARGV)
_buf = io.StringIO(); _old = sys.stdout; sys.stdout = _buf
try:
    exec(compile(${JSON.stringify(test)}, "zgodnosc", "exec"), {"__name__": "__main__", "__file__": "/testy/zgodnosc_silnika.py"})
finally:
    sys.stdout = _old
_buf.getvalue()
`);
fs.writeFileSync('/tmp/zg_pyodide.json', wyj);
console.error('czas ms:', Date.now() - t0);
