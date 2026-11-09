// PMT Planer (web) — archiwum ZIP z KLASYCZNYM szyfrowaniem (PKWARE „ZipCrypto”) i kompresją deflate, do wysyłki podpisanych dokumentów pocztą.
//
// DLACZEGO NIE AES-256 (js/zipaes.js): odbiorca ma rozpakować załącznik BEZPOŚREDNIO z otrzymanej wiadomości, w Eksploratorze Windows, bez 7-Zip i WinRAR. Eksplorator nie obsługuje AES-256
// (kopiowanie pliku z takiej paczki kończy się błędem 0x80004005 „Nieokreślony błąd”), a klasyczne szyfrowanie ZIP obsługuje: przy rozpakowaniu pyta o hasło. Otwiera je też macOS (Archiwizator) i każdy
// program do ZIP-ów.
//
// CENA — mówimy to wprost: ten szyfr jest znacznie SŁABSZY niż AES. Kto ma w ręku samą paczkę i zna początek któregoś z plików (a PDF zaczyna się od „%PDF-1.”), potrafi odzyskać klucze bez hasła
// (znany atak na tekst jawny, narzędzia dostępne publicznie). Paczka z takim szyfrem chroni więc przed przypadkowym wglądem, skanerami poczty i osobami postronnymi, ale NIE przed celowym atakiem kogoś,
// kto przechwyci wiadomość. Łagodzą to: kompresja deflate przed szyfrowaniem (początek pliku w paczce nie jest już dosłownie „%PDF-1.”), hasło przekazywane inną drogą niż paczka i krótki czas życia hasła.
//
// Hasło może mieć tylko znaki ASCII (litery bez polskich znaków, cyfry, znaki specjalne): Eksplorator zamienia wpisane hasło na bajty wg strony kodowej systemu (u nas CP1250), a przeglądarka wg UTF-8 —
// z polską literą w haśle te bajty by się różniły i paczka by się nie otworzyła. Dlatego aplikacja odmawia wysyłki z takim hasłem (js/dostep.js), a ta funkcja rzuca wyjątek.
// Czyste funkcje — bez dostępu do interfejsu.
import { crc32 } from './pliki.js';
import { losowe } from './sejf.js';

const TABELA = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const krokCrc = (c, b) => ((c >>> 8) ^ TABELA[(c ^ b) & 0xFF]) >>> 0;      // jeden krok CRC-32 bez końcowego odwrócenia (tak liczy je klasyczne szyfrowanie ZIP)

/** Czy hasło nadaje się do paczki otwieranej w Eksploratorze Windows: niepuste, tylko drukowalne znaki ASCII. */
export const hasloZgodneZEksploratorem = h => typeof h === 'string' && /^[\x20-\x7e]+$/.test(h);

/** Szyfr strumieniowy ZIP: trzy 32-bitowe klucze, zainicjowane hasłem; szyfruj(bajt) zwraca bajt szyfrogramu. */
function szyfrZip(haslo) {
  let k0 = 0x12345678, k1 = 0x23456789, k2 = 0x34567890;
  const aktualizuj = b => { k0 = krokCrc(k0, b); k1 = (Math.imul((k1 + (k0 & 0xFF)) >>> 0, 134775813) + 1) >>> 0; k2 = krokCrc(k2, k1 >>> 24); };
  for (let i = 0; i < haslo.length; i++) aktualizuj(haslo.charCodeAt(i));
  return p => { const t = (k2 & 0xFFFF) | 2, c = p ^ (((t * (t ^ 1)) >>> 8) & 0xFF); aktualizuj(p); return c; };
}

/** Kompresja deflate (surowy strumień, bez nagłówka zlib) — wbudowana w przeglądarki i Node; bez niej (stare przeglądarki) → null i plik idzie bez kompresji. */
export async function deflateSurowy(bajty) {
  if (typeof CompressionStream === 'undefined') return null;
  try {
    const cs = new CompressionStream('deflate-raw'), w = cs.writable.getWriter(); w.write(bajty); w.close();
    return new Uint8Array(await new Response(cs.readable).arrayBuffer());
  } catch (e) { return null; }
}

/** pliki: [{ nazwa, bajty: Uint8Array }], haslo: tekst ASCII → Promise<Blob> z archiwum ZIP (nazwy w UTF-8). Każdy plik: [12 B nagłówka szyfrującego | dane (deflate albo bez kompresji, jeśli to nie opłaca się)]. */
export async function zipujKlasycznie(pliki, haslo) {
  if (!haslo) throw new Error('brak hasła do paczki');
  if (!hasloZgodneZEksploratorem(haslo)) throw new Error('hasło do paczki ma znaki spoza ASCII — Eksplorator Windows by jej nie otworzył');
  const kod = new TextEncoder(), czesci = [], centralne = [], d = new Date();
  const czas = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1), data = ((Math.max(d.getFullYear(), 1980) - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  let przes = 0;
  for (const p of pliki) {
    const nazwa = kod.encode(p.nazwa), crc = crc32(p.bajty), skompr = await deflateSurowy(p.bajty), uzyj = !!skompr && skompr.length < p.bajty.length, tresc = uzyj ? skompr : p.bajty, metoda = uzyj ? 8 : 0;
    const szyfruj = szyfrZip(haslo), naglowek = losowe(12); naglowek[11] = crc >>> 24;      // ostatni bajt nagłówka = starszy bajt CRC: po nim program sprawdza, czy hasło jest dobre
    const dane = new Uint8Array(12 + tresc.length);
    for (let i = 0; i < 12; i++) dane[i] = szyfruj(naglowek[i]);
    for (let i = 0; i < tresc.length; i++) dane[12 + i] = szyfruj(tresc[i]);
    const lok = new DataView(new ArrayBuffer(30));
    lok.setUint32(0, 0x04034b50, true); lok.setUint16(4, 20, true); lok.setUint16(6, 0x0801, true); lok.setUint16(8, metoda, true); lok.setUint16(10, czas, true); lok.setUint16(12, data, true);
    lok.setUint32(14, crc, true); lok.setUint32(18, dane.length, true); lok.setUint32(22, p.bajty.length, true); lok.setUint16(26, nazwa.length, true); lok.setUint16(28, 0, true);
    czesci.push(new Uint8Array(lok.buffer), nazwa, dane);
    const cen = new DataView(new ArrayBuffer(46));
    cen.setUint32(0, 0x02014b50, true); cen.setUint16(4, 20, true); cen.setUint16(6, 20, true); cen.setUint16(8, 0x0801, true); cen.setUint16(10, metoda, true); cen.setUint16(12, czas, true); cen.setUint16(14, data, true);
    cen.setUint32(16, crc, true); cen.setUint32(20, dane.length, true); cen.setUint32(24, p.bajty.length, true); cen.setUint16(28, nazwa.length, true); cen.setUint32(42, przes, true);
    centralne.push(new Uint8Array(cen.buffer), nazwa);
    przes += 30 + nazwa.length + dane.length;
  }
  const rozm = centralne.reduce((s, x) => s + x.length, 0), kon = new DataView(new ArrayBuffer(22));
  kon.setUint32(0, 0x06054b50, true); kon.setUint16(8, pliki.length, true); kon.setUint16(10, pliki.length, true); kon.setUint32(12, rozm, true); kon.setUint32(16, przes, true);
  return new Blob([...czesci, ...centralne, new Uint8Array(kon.buffer)], { type: 'application/zip' });
}
