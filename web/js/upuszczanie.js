// PMT Planer (web) — pliki i FOLDERY upuszczone na okno podpisu (przeciągnięte z Eksploratora albo z paska pobierania przeglądarki).
// Przeglądarki podają upuszczony folder jako „wpis” (FileSystemEntry): jego zawartość trzeba odczytać partiami (readEntries zwraca naraz najwyżej ~100 pozycji).
// Wpisy trzeba pobrać SYNCHRONICZNIE w obsłudze zdarzenia drop (po pierwszym await przeglądarka je unieważnia) — dlatego wpisyZUpuszczenia() jest zwykłą funkcją, a przejdzWpisy() można czekać dowolnie długo.

/** Rozszerzenia, które aplikacja w ogóle umie przyjąć (PDF z podpisem, plik .xades, ZIP z gov.pl, podpisy w osobnych plikach, skany i zdjęcia). */
export const ROZSZERZENIA_PODPISANYCH = /\.(pdf|xades|xml|zip|sig|p7s|p7m|png|jpe?g|heic|heif|webp|tiff?|gif|bmp)$/i;
export const obslugiwanyPlik = nazwa => ROZSZERZENIA_PODPISANYCH.test(String(nazwa));

const jestPlikiem = w => !!w && typeof w.arrayBuffer === 'function' && typeof w.name === 'string' && w.isFile === undefined && w.isDirectory === undefined;
const plikZWpisu = w => new Promise((ok, blad) => w.file(ok, blad));
async function wszystkieWpisy(czytnik) {
  const wyn = [];
  for (let n = 0; n < 50; n++) {      // zabezpieczenie przed czytnikiem, który nigdy nie zwraca pustej partii
    const partia = await new Promise((ok, blad) => czytnik.readEntries(ok, blad));
    if (!partia.length) break; wyn.push(...partia);
  }
  return wyn;
}

/**
 * Z zdarzenia drop: lista „źródeł” do przejścia — wpisy (pliki i foldery) albo zwykłe pliki, gdy przeglądarka wpisów nie umie (starsze przeglądarki, zdarzenia syntetyczne).
 * Wołać synchronicznie w obsłudze zdarzenia.
 */
export function wpisyZUpuszczenia(dt) {
  if (!dt) return [];
  const zr = [];
  const pozycje = dt.items ? [...dt.items].filter(i => i && i.kind === 'file') : [];
  if (pozycje.length) {
    for (const i of pozycje) {
      const wpis = typeof i.webkitGetAsEntry === 'function' ? i.webkitGetAsEntry() : null;
      const plik = typeof i.getAsFile === 'function' ? i.getAsFile() : null;
      if (wpis) zr.push(wpis); else if (plik) zr.push(plik);
    }
    if (zr.length) return zr;
  }
  return dt.files ? [...dt.files] : [];
}

/**
 * Przechodzi źródła i zwraca pliki: [{ plik, zFolderu }]. Plik upuszczony wprost (zFolderu: false) idzie dalej zawsze, a plik z wnętrza upuszczonego folderu (zFolderu: true) tylko wtedy, gdy ma
 * rozszerzenie, które aplikacja umie przyjąć (reszty folderu — zdjęć wakacyjnych, dokumentów Worda — nie czytamy). Ograniczenia: głębokość 4 poziomów, najwyżej `limit` plików (obciete: true, gdy było więcej).
 */
export async function przejdzWpisy(zrodla, { glebokosc = 4, limit = 600 } = {}) {
  const pliki = []; let obciete = false;
  async function wejdz(w, gl, zFolderu) {
    if (pliki.length >= limit) { obciete = true; return; }
    if (jestPlikiem(w)) { pliki.push({ plik: w, zFolderu }); return; }
    if (w && w.isFile) {
      if (zFolderu && (w.name.startsWith('.') || !obslugiwanyPlik(w.name))) return;
      try { pliki.push({ plik: await plikZWpisu(w), zFolderu }); } catch (e) { /* plik zniknął w trakcie odczytu — pomijam */ }
    } else if (w && w.isDirectory && gl > 0) {
      let dzieci = []; try { dzieci = await wszystkieWpisy(w.createReader()); } catch (e) { /* folder bez dostępu — pomijam */ }
      for (const d of dzieci) await wejdz(d, gl - 1, true);
    }
  }
  for (const w of zrodla) await wejdz(w, glebokosc, false);
  return { pliki, obciete };
}
