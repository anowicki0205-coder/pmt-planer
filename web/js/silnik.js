// PMT Planer (web) — interfejs silnika dla aplikacji: rozmowa z workerem. Przerwanie = zabicie workera (pliki powstają dopiero na końcu).
export class Silnik {
  constructor() { this._nowy(); }
  _nowy() {
    this.w = new Worker(new URL('./silnik.worker.js', import.meta.url), { type: 'module' });
    this.nr = 0; this.czeka = new Map(); this.gotowy = null;
    this.w.onmessage = ev => {
      const m = ev.data, c = this.czeka.get(m.id); if (!c) return;
      if (m.typ === 'postep') { c.postep && c.postep(m.tekst, m.wartosc); return; }
      this.czeka.delete(m.id); m.ok ? c.ok(m.wynik) : c.err(new Error(m.blad));
    };
    this.w.onerror = e => { for (const c of this.czeka.values()) c.err(new Error(e.message || 'Błąd silnika')); this.czeka.clear(); };
  }
  _wolaj(metoda, arg, postep) {
    return new Promise((ok, err) => { const id = ++this.nr; this.czeka.set(id, { ok, err, postep }); this.w.postMessage({ id, metoda, arg }); });
  }
  start(postep) { return this.gotowy || (this.gotowy = this._wolaj('start', {}, postep)); }
  dni(a) { return this._wolaj('dni', a); }
  stale() { return this._wolaj('stale', {}); }
  maks(a) { return this._wolaj('maks', a); }
  przygotuj(a) { return this._wolaj('przygotuj', a); }
  adres(a) { return this._wolaj('adres', a); }
  czysc() { return this._wolaj('czysc', {}); }
  siec(wlaczona) { return this._wolaj('siec', { wlaczona }); }
  generuj(a, postep) { return this._wolaj('generuj', a, postep); }
  planWczytaj(a) { return this._wolaj('planWczytaj', a); }
  planGeneruj(a, postep) { return this._wolaj('planGeneruj', a, postep); }
  /** Przerywa pracę: zabija workera i przygotowuje nowego (rozgrzeje się przy następnym użyciu). */
  przerwij() {
    this.w.terminate();
    for (const c of this.czeka.values()) c.err(Object.assign(new Error('Przerwano'), { przerwano: true }));
    this.czeka.clear(); this._nowy(); this.gotowy = null;
    this.start(); // rozgrzewka w tle
  }
}
