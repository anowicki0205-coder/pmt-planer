// PMT Planer (web) — magazyn danych na urządzeniu: profil i miesiące (localStorage), pliki PDF (IndexedDB).
// Nic nie opuszcza urządzenia: PESEL i dokumenty są tylko tutaj (zasada: PESEL wyłącznie po stronie klienta).
// WSZYSTKO jest tu ZASZYFROWANE kluczem danych konta (AES-256 + podpis HMAC, zob. js/sejf.js): w localStorage leży „enc1:…”, w IndexedDB koperta „PMT1…”.
// Klucz pojawia się dopiero po zalogowaniu (odblokuj); bez niego magazyn jest pusty i NIE zapisuje niczego jawnie. Dane sprzed szyfrowania (jawny JSON, surowe PDF-y)
// są odczytywane raz, po odblokowaniu, i od razu zapisywane już zaszyfrowane (migruj).
import * as S from './sejf.js';
// Dane są rozdzielone na konta: każdy zalogowany (5-cyfrowy login) ma własną przestrzeń na tym urządzeniu — nowe konto nie widzi
// PESEL-u, adresów, planu ani dokumentów poprzedniego. Przed ustawKonto() magazyn jest pusty i nic nie zapisuje.
let KLUCZ = null, NAZWA_BAZY = null, KOD = null, KL = null;
const bezpiecznie = (f, domyslnie) => { try { return f(); } catch (e) { return domyslnie; } };
export function ustawKonto(kod) { KOD = kod || null; KLUCZ = kod ? `pmt-web-v1:${kod}` : null; NAZWA_BAZY = kod ? `pmt-web-pliki:${kod}` : null; bazaObietnica = null; KL = null; pamRaw = null; pamJson = null; }
/** Odblokowanie magazynu kluczem danych konta (32 bajty z sejfu). Zmiana konta (ustawKonto) blokuje go z powrotem. */
export function odblokuj(dek) { KL = dek ? S.klucze(dek) : null; pamRaw = null; pamJson = null; }
export const odblokowany = () => !!KL;

/* Odczyt magazynu konta: jawny tekst JSON albo null, gdy nie da się go odczytać (brak klucza, zły klucz, uszkodzone dane). Odszyfrowany tekst jest pamiętany dla tego samego szyfrogramu —
   odczyty są częste (każdy wiersz listy), a odszyfrowanie całego magazynu przy każdym z nich byłoby marnotrawstwem. Zwracamy zawsze NOWY obiekt (JSON.parse), jak dawniej. */
let pamRaw = null, pamJson = null;
const surowe = () => KLUCZ ? bezpiecznie(() => localStorage.getItem(KLUCZ), null) : null;
function jawnyTekst() {
  const raw = surowe(); if (raw === null) return '{}';
  if (S.czyTekstZaszyfrowany(raw)) { if (!KL) return null; if (raw === pamRaw) return pamJson; const t = S.odszyfrujTekst(KL, raw); if (t !== null) { pamRaw = raw; pamJson = t; } return t; }
  return KL ? raw : null;      // dane sprzed szyfrowania (jawny JSON): czytelne dopiero po odblokowaniu — wtedy migruj() zapisze je zaszyfrowane
}
function czytaj() { const t = KLUCZ ? jawnyTekst() : null; return t === null ? {} : bezpiecznie(() => JSON.parse(t) || {}, {}); }
/** Zapis: zawsze zaszyfrowany. Bez klucza — nic (nigdy jawnie). Nie nadpisuje danych, których nie umiemy odczytać (np. po błędnym kluczu): lepiej odmówić niż je skasować. */
function zapisz(d) {
  if (!KLUCZ || !KL) return;
  if (surowe() !== null && jawnyTekst() === null) return;
  bezpiecznie(() => { const json = JSON.stringify(d), raw = S.szyfrujTekst(KL, json); localStorage.setItem(KLUCZ, raw); pamRaw = raw; pamJson = json; });
}
/** Czy magazyn konta jest zaszyfrowany i da się go odczytać bieżącym kluczem (albo jest pusty). */
export const czytelny = () => !!KL && (surowe() === null || jawnyTekst() !== null);
/** Kasuje sam magazyn konta w localStorage (profil, miesiące, plan) — gdy jest uszkodzony i nie da się go odczytać. Pliki PDF i sejf zostają. */
export function wyczyscMagazyn() { if (KLUCZ) bezpiecznie(() => localStorage.removeItem(KLUCZ)); pamRaw = null; pamJson = null; }
/** Po odblokowaniu: dane zapisane dawniej jawnie (localStorage i pliki PDF) zapisuje ponownie, już zaszyfrowane. Zwraca, ile elementów przepisano. */
export async function migruj() {
  if (!KL || !KLUCZ) return 0; let n = 0;
  const raw = surowe(); if (raw !== null && !S.czyTekstZaszyfrowany(raw)) { const d = bezpiecznie(() => JSON.parse(raw), null); if (d && typeof d === 'object') { zapisz(d); n++; } }
  try {
    const b = await baza();
    n += await new Promise((ok, err) => {
      let ile = 0; const t = b.transaction('pliki', 'readwrite'), st = t.objectStore('pliki'), q = st.openCursor();
      q.onsuccess = () => { const c = q.result; if (!c) return; const v = c.value; if (v && !S.jestZaszyfrowane(v)) { try { c.update(S.szyfruj(KL, v instanceof Uint8Array ? v : new Uint8Array(v))); ile++; } catch (e) { /* ten plik zostaje jawny do następnej próby */ } } c.continue(); };
      t.oncomplete = () => ok(ile); t.onerror = () => err(t.error);
    });
  } catch (e) { /* brak IndexedDB: nie ma plików do przepisania */ }
  return n;
}

export const profil = {
  wczytaj() { return czytaj().profil || null; },
  zapisz(p) { const d = czytaj(); d.profil = p; zapisz(d); },
  usun() { const d = czytaj(); delete d.profil; zapisz(d); },
};
export const miesiace = {
  klucz: (rok, mies) => `${rok}-${String(mies).padStart(2, '0')}`,
  wszystkie() { return czytaj().miesiace || {}; },
  daj(rok, mies) { return (czytaj().miesiace || {})[this.klucz(rok, mies)] || null; },
  ile() { return Object.keys(czytaj().miesiace || {}).length; },
  zapisz(rok, mies, rekord) { const d = czytaj(); d.miesiace = d.miesiace || {}; d.miesiace[this.klucz(rok, mies)] = rekord; zapisz(d); },
  usun(rok, mies) { const d = czytaj(); if (d.miesiace) delete d.miesiace[this.klucz(rok, mies)]; zapisz(d); },
};
export const ustawienia = {
  daj(k, dom) { const u = czytaj().ustawienia || {}; return k in u ? u[k] : dom; },
  ustaw(k, w) { const d = czytaj(); d.ustawienia = d.ustawienia || {}; d.ustawienia[k] = w; zapisz(d); },
};

/* ---- pliki PDF w IndexedDB ---- */
let bazaObietnica = null;
function baza() {
  return bazaObietnica || (bazaObietnica = new Promise((ok, err) => {
    if (!NAZWA_BAZY) { err(new Error('brak konta')); return; }
    const q = indexedDB.open(NAZWA_BAZY, 1);
    q.onupgradeneeded = () => q.result.createObjectStore('pliki');
    q.onsuccess = () => { const db = q.result; db.onversionchange = () => { db.close(); bazaObietnica = null; }; ok(db); };      // inna karta usuwa bazę (Usuń dane, zmiana konta): zamykamy połączenie, inaczej jej usuwanie wisiałoby w nieskończoność
    q.onerror = () => err(q.error);
  }));
}
const tx = async (tryb, f) => { const b = await baza(); return new Promise((ok, err) => { const t = b.transaction('pliki', tryb); const r = f(t.objectStore('pliki')); t.oncomplete = () => ok(r && r.result); t.onerror = () => err(t.error); }); };
export const pliki = {
  async zapisz(klucz, bajty) {
    if (!KL) throw new Error('Magazyn jest zablokowany (zaloguj się ponownie)');
    const koperta = S.szyfruj(KL, bajty instanceof Uint8Array ? bajty : new Uint8Array(bajty));
    await tx('readwrite', s => s.put(koperta, klucz));
  },
  /** Odszyfrowany plik albo null (brak pliku, zły klucz, uszkodzony). Plik sprzed szyfrowania (surowy) jest zwracany tak jak leży — migruj() zaraz go zaszyfruje. */
  async daj(klucz) { const v = await tx('readonly', s => s.get(klucz)); if (!v || !KL) return null; return S.jestZaszyfrowane(v) ? S.odszyfruj(KL, v) : v; },
  async usun(klucz) { await tx('readwrite', s => s.delete(klucz)); },
  async usunMiesiac(prefiks) {
    const b = await baza();
    return new Promise((ok, err) => { const t = b.transaction('pliki', 'readwrite'), s = t.objectStore('pliki'); const q = s.openKeyCursor();
      q.onsuccess = () => { const c = q.result; if (!c) return; if (String(c.key).startsWith(prefiks)) s.delete(c.key); c.continue(); };
      t.oncomplete = () => ok(); t.onerror = () => err(t.error); });
  },
};
export const nazwaKlucza = (rok, mies, nazwa) => `${miesiace.klucz(rok, mies)}/${nazwa}`;

/** Usuwa z urządzenia WSZYSTKO, co należy do bieżącego konta: profil z PESEL-em, miesiące, plan, ustawienia (localStorage) i pliki PDF (IndexedDB). */
export async function usunKonto() {
  if (!KLUCZ) return;
  bezpiecznie(() => localStorage.removeItem(KLUCZ)); S.usunSejf(KOD); S.zapomnijKlucz(); KL = null; pamRaw = null; pamJson = null;
  const nazwa = NAZWA_BAZY;
  try { const b = await (bazaObietnica || Promise.resolve(null)).catch(() => null); if (b) b.close(); } catch (e) { /* otwarte połączenie zamknie przeładowanie strony */ }
  bazaObietnica = null;
  await new Promise(ok => { try { const q = indexedDB.deleteDatabase(nazwa); q.onsuccess = q.onerror = q.onblocked = () => ok(); } catch (e) { ok(); } });
}

/* ---- plan wizyt i odhaczone wizyty ---- */
export const plan = {
  wczytaj() { return czytaj().plan || null; },
  zapisz(p) { const d = czytaj(); d.plan = p; zapisz(d); },
  usun() { const d = czytaj(); delete d.plan; zapisz(d); },
};
export const wizyty = {
  klucz: (data, adres) => `${data}|${adres}`,
  daj(data, adres) { return ((czytaj().wizyty || {})[`${data}|${adres}`]) || null; },
  ustaw(data, adres, ok, godz) { const d = czytaj(); d.wizyty = d.wizyty || {}; const k = `${data}|${adres}`; if (ok) d.wizyty[k] = { ok: true, godz: godz || '' }; else delete d.wizyty[k]; zapisz(d); },
};

/* Tylko dla testów (strona z ustawionym window.__testy): odczyt i zapis jawnego obiektu konta, żeby testy mogły sprawdzać i przygotowywać dane mimo szyfrowania. */
if (globalThis.__testy) globalThis.__pmtDane = { czytaj, zapisz, surowe };
