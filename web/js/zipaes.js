// PMT Planer (web) — archiwum ZIP zahasłowane szyfrem AES-256 (odmiana „WinZip AES”, AE-2), do wysyłki podpisanych dokumentów pocztą.
// W dokumentach jest PESEL, więc paczka nie może iść jawnie. Otwiera ją 7-Zip, WinRAR i Keka; zwykły Eksplorator Windows często nie umie otworzyć AES-256.
// Format (dla każdego pliku osobno): sól 16 B | weryfikator hasła 2 B | dane zaszyfrowane AES-256-CTR (licznik little-endian od 1) | kod uwierzytelniający HMAC-SHA1 (10 B).
// Klucze: PBKDF2-HMAC-SHA1 (1000 iteracji, tak wymaga format) z hasła i soli → 32 B klucz AES | 32 B klucz HMAC | 2 B weryfikator.
// Własne SHA-1/HMAC/PBKDF2, bo WebCrypto nie istnieje na stronie otwartej przez zwykłe http, a 1000 iteracji liczy się błyskawicznie.
// Bez kompresji (PDF-y są już skompresowane). Czyste funkcje — bez dostępu do interfejsu.
import { rozwinKlucz, ctrLE, losowe } from './sejf.js';

function sha1(m) {
  const l = m.length, n = Math.ceil((l + 9) / 64) * 64, p = new Uint8Array(n); p.set(m); p[l] = 0x80;
  const dv = new DataView(p.buffer); dv.setUint32(n - 8, Math.floor(l / 0x20000000)); dv.setUint32(n - 4, (l * 8) >>> 0);
  const h = Uint32Array.of(0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0), w = new Uint32Array(80);
  for (let o = 0; o < n; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getUint32(o + i * 4);
    for (let i = 16; i < 80; i++) { const x = w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]; w[i] = (x << 1) | (x >>> 31); }
    let a = h[0], b = h[1], c = h[2], d = h[3], e = h[4];
    for (let i = 0; i < 80; i++) {
      const f = i < 20 ? (b & c) | (~b & d) : i < 40 ? b ^ c ^ d : i < 60 ? (b & c) | (b & d) | (c & d) : b ^ c ^ d, k = i < 20 ? 0x5A827999 : i < 40 ? 0x6ED9EBA1 : i < 60 ? 0x8F1BBCDC : 0xCA62C1D6;
      const t = ((((a << 5) | (a >>> 27)) + f + e + k + w[i]) >>> 0); e = d; d = c; c = ((b << 30) | (b >>> 2)) >>> 0; b = a; a = t;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e;
  }
  const out = new Uint8Array(20), ov = new DataView(out.buffer); for (let i = 0; i < 5; i++) ov.setUint32(i * 4, h[i]); return out;
}
const scal = (a, b) => { const o = new Uint8Array(a.length + b.length); o.set(a); o.set(b, a.length); return o; };
export function hmacSha1(klucz, m) {
  let k = klucz; if (k.length > 64) k = sha1(k);
  const ip = new Uint8Array(64).fill(0x36), op = new Uint8Array(64).fill(0x5c); for (let i = 0; i < k.length; i++) { ip[i] ^= k[i]; op[i] ^= k[i]; }
  return sha1(scal(op, sha1(scal(ip, m))));
}
export function pbkdf2Sha1(haslo, sol, iter, dlugosc) {
  const wyn = new Uint8Array(Math.ceil(dlugosc / 20) * 20);
  for (let b = 1, o = 0; o < dlugosc; b++, o += 20) {
    let u = hmacSha1(haslo, scal(sol, Uint8Array.of(b >>> 24, (b >>> 16) & 255, (b >>> 8) & 255, b & 255))); const t = u.slice();
    for (let i = 1; i < iter; i++) { u = hmacSha1(haslo, u); for (let j = 0; j < 20; j++) t[j] ^= u[j]; }
    wyn.set(t, o);
  }
  return wyn.subarray(0, dlugosc);
}

/** Dane jednego pliku → [sól 16 B | weryfikator 2 B | szyfrogram | kod 10 B]. */
export function zaszyfrujPlikAes(haslo, bajty, sol = losowe(16)) {
  const kl = pbkdf2Sha1(new TextEncoder().encode(haslo), sol, 1000, 66), szyfr = ctrLE(rozwinKlucz(kl.slice(0, 32)), bajty), kod = hmacSha1(kl.slice(32, 64), szyfr).subarray(0, 10);
  const o = new Uint8Array(16 + 2 + szyfr.length + 10); o.set(sol); o.set(kl.subarray(64, 66), 16); o.set(szyfr, 18); o.set(kod, 18 + szyfr.length); return o;
}

/** pliki: [{ nazwa, bajty: Uint8Array }], haslo: tekst (co najmniej 1 znak) → Blob z zahasłowanym archiwum ZIP (nazwy w UTF-8). */
export function zipujAes(pliki, haslo) {
  if (!haslo) throw new Error('brak hasła do paczki');
  const kod = new TextEncoder(), czesci = [], centralne = [], d = new Date();
  const czas = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1), data = ((Math.max(d.getFullYear(), 1980) - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  const dodatek = Uint8Array.of(0x01, 0x99, 0x07, 0x00, 0x02, 0x00, 0x41, 0x45, 0x03, 0x00, 0x00);      // pole AES: wersja AE-2, „AE”, siła 256 bitów, metoda właściwa 0 (bez kompresji)
  let przes = 0;
  for (const p of pliki) {
    const nazwa = kod.encode(p.nazwa), dane = zaszyfrujPlikAes(haslo, p.bajty);
    const lok = new DataView(new ArrayBuffer(30));
    lok.setUint32(0, 0x04034b50, true); lok.setUint16(4, 51, true); lok.setUint16(6, 0x0801, true); lok.setUint16(8, 99, true); lok.setUint16(10, czas, true); lok.setUint16(12, data, true);
    lok.setUint32(14, 0, true); lok.setUint32(18, dane.length, true); lok.setUint32(22, p.bajty.length, true); lok.setUint16(26, nazwa.length, true); lok.setUint16(28, dodatek.length, true);
    czesci.push(new Uint8Array(lok.buffer), nazwa, dodatek, dane);
    const cen = new DataView(new ArrayBuffer(46));
    cen.setUint32(0, 0x02014b50, true); cen.setUint16(4, 51, true); cen.setUint16(6, 51, true); cen.setUint16(8, 0x0801, true); cen.setUint16(10, 99, true); cen.setUint16(12, czas, true); cen.setUint16(14, data, true);
    cen.setUint32(16, 0, true); cen.setUint32(20, dane.length, true); cen.setUint32(24, p.bajty.length, true); cen.setUint16(28, nazwa.length, true); cen.setUint16(30, dodatek.length, true); cen.setUint32(42, przes, true);
    centralne.push(new Uint8Array(cen.buffer), nazwa, dodatek);
    przes += 30 + nazwa.length + dodatek.length + dane.length;
  }
  const rozm = centralne.reduce((s, x) => s + x.length, 0), kon = new DataView(new ArrayBuffer(22));
  kon.setUint32(0, 0x06054b50, true); kon.setUint16(8, pliki.length, true); kon.setUint16(10, pliki.length, true); kon.setUint32(12, rozm, true); kon.setUint32(16, przes, true);
  return new Blob([...czesci, ...centralne, new Uint8Array(kon.buffer)], { type: 'application/zip' });
}
