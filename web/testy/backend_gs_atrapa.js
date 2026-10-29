// Uruchamia PRAWDZIWY plik apps_script_POPRAWIONY_v2.gs w Node na atrapach usług Google (arkusz, cache, blokada, narzędzia) — żeby sprawdzać backend
// tym samym kodem, który wklejasz do Apps Script, a nie jego przepisaną kopią. Atrapa zapisuje komórki jak arkusz: tekst zaczynający się od = + - @
// zostałby w prawdziwym arkuszu formułą, więc atrapa zgłasza takie komórki (metoda formuly()).
const fs = require('fs'), path = require('path'), vm = require('vm'), crypto = require('crypto');
const SCIEZKA = path.resolve(__dirname, '../../apps_script_POPRAWIONY_v2.gs');
const czyFormula = v => typeof v === 'string' && /^[=+\-@]/.test(v);

class Zakladka {
  constructor(nazwa) { this.nazwa = nazwa; this.w = []; }
  getLastRow() { return this.w.length; }
  appendRow(r) { this.w.push(r.slice()); }
  setFrozenRows() {}
  getDataRange() { const t = this; return { getValues: () => t.w.map(r => r.slice()) }; }
  getRange(r, c, nr = 1, nc = 1) {
    const t = this;
    return {
      getValues: () => { const o = []; for (let i = 0; i < nr; i++) { const x = []; for (let j = 0; j < nc; j++) x.push((t.w[r - 1 + i] || [])[c - 1 + j] ?? ''); o.push(x); } return o; },
      getValue: () => (t.w[r - 1] || [])[c - 1] ?? '',
      setValues: v => { v.forEach((rz, i) => rz.forEach((x, j) => { t.w[r - 1 + i] = t.w[r - 1 + i] || []; t.w[r - 1 + i][c - 1 + j] = x; })); },
      setValue: x => { t.w[r - 1] = t.w[r - 1] || []; t.w[r - 1][c - 1] = x; },
      setFontWeight() {},
    };
  }
}
const sha256hex = s => crypto.createHash('sha256').update(s, 'utf8').digest('hex');
const naBajty = buf => [...buf].map(b => (b > 127 ? b - 256 : b));      // Apps Script oddaje bajty ze znakiem

function zaladuj(opcje = {}) {
  const zak = new Map(), pamiec = new Map(), wlasciwosci = new Map();
  let zegar = opcje.start || Date.now();
  const arkusz = {
    getSheetByName: n => zak.get(n) || null,
    insertSheet: n => { const z = new Zakladka(n); zak.set(n, z); return z; },
  };
  const ctx = {
    console, Date: class extends Date { constructor(...a) { if (a.length) super(...a); else super(zegar); } static now() { return zegar; } },
    SpreadsheetApp: { getActiveSpreadsheet: () => arkusz },
    ContentService: { MimeType: { JSON: 'json' }, createTextOutput: s => ({ tresc: s, setMimeType() { return this; } }) },
    LockService: { getScriptLock: () => ({ tryLock: () => true, releaseLock() {} }) },
    CacheService: { getScriptCache: () => ({
      get: k => { const e = pamiec.get(k); if (!e) return null; if (e.do < zegar) { pamiec.delete(k); return null; } return e.v; },
      put: (k, v, ttl = 600) => { pamiec.set(k, { v: String(v), do: zegar + ttl * 1000 }); },
      remove: k => { pamiec.delete(k); },
    }) },
    PropertiesService: { getScriptProperties: () => ({ getProperty: k => wlasciwosci.has(k) ? wlasciwosci.get(k) : null, setProperty: (k, v) => wlasciwosci.set(k, String(v)) }) },
    Utilities: {
      DigestAlgorithm: { SHA_256: 'SHA_256' }, Charset: { UTF_8: 'UTF_8' },
      computeDigest: (alg, tekst) => naBajty(crypto.createHash('sha256').update(tekst, 'utf8').digest()),
      computeHmacSha256Signature: (tekst, klucz) => naBajty(crypto.createHmac('sha256', klucz).update(tekst, 'utf8').digest()),
      formatDate: (d, tz, wz) => { const x = new Date(d.getTime() + 2 * 3600000), p = n => String(n).padStart(2, '0'); return wz.replace('yyyy', x.getUTCFullYear()).replace('MM', p(x.getUTCMonth() + 1)).replace('dd', p(x.getUTCDate())); },
      getUuid: () => crypto.randomUUID(),
    },
  };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(SCIEZKA, 'utf8'), ctx, { filename: 'apps_script_POPRAWIONY_v2.gs' });
  const sekret = opcje.sekret || 'SEKRET-TESTOWY';
  vm.runInContext(`SEKRETY_PMT = [${JSON.stringify(sekret)}]; ` + (opcje.podpisObowiazkowy ? 'PODPIS_OBOWIAZKOWY = true;' : ''), ctx);
  if (opcje.ustaw) vm.runInContext(opcje.ustaw, ctx);
  vm.runInContext('inicjalizuj()', ctx);
  const uz = zak.get('Uzytkownicy');
  const dodajUzytkownika = (kod, imie, rejon, wazneDo, telefon, haslo) => {
    const w = new Array(14).fill(''); w[0] = kod; w[1] = imie; w[2] = rejon; w[3] = wazneDo ? new ctx.Date(wazneDo) : ''; w[12] = telefon || ''; w[13] = haslo ? sha256hex(`PMT|${kod}|${haslo}`) : '';
    uz.appendRow(w);
  };
  // haslo: klient podpisuje puls/sesję kluczem pochodnym od hasła (HMAC, klucz = skrót „PMT|kod|hasło”) — jak aplikacja web i program na komputerze
  const podpisz = (d, haslo, hashKlucza) => { const cz = Math.floor(zegar / 1000); const o = { ...d, klucz_czas: cz, wersja: d.wersja || '3.24.0' }; const baza = `${o.kod || ''}|${o.akcja || ''}|${cz}`; o.podpis = crypto.createHmac('sha256', sekret).update(baza, 'utf8').digest('hex');
    const klucz = hashKlucza || (haslo ? sha256hex(`PMT|${o.kod}|${haslo}`) : ''); if (klucz) o.podpis_hasla = crypto.createHmac('sha256', klucz).update(baza, 'utf8').digest('hex'); return o; };
  const post = (d, { bezPodpisu = false, haslo = '', hashKlucza = '' } = {}) => { const o = vm.runInContext('doPost', ctx)({ postData: { contents: typeof d === 'string' ? d : JSON.stringify(bezPodpisu ? d : podpisz(d, haslo, hashKlucza)) } }); return JSON.parse(o.tresc); };
  const formuly = () => { const wynik = []; zak.forEach((z, n) => z.w.forEach((r, i) => r.forEach((v, j) => { if (czyFormula(v)) wynik.push(`${n}!R${i + 1}C${j + 1}=${String(v).slice(0, 60)}`); }))); return wynik; };
  return { ctx, zak, arkusz, post, formuly, dodajUzytkownika, dalej: ms => { zegar += ms; }, hash: (kod, haslo) => sha256hex(`PMT|${kod}|${haslo}`), uz, wywolaj: kod => vm.runInContext(kod, ctx), get: n => zak.get(n) };
}
module.exports = { zaladuj, SCIEZKA, czyFormula, istnieje: () => fs.existsSync(SCIEZKA) };
