// PMT Planer (web) — sejf: szyfrowanie danych konta na urządzeniu (PESEL, adres, miesiące, plan, PDF-y).
//
// Jak to działa:
//   • Dla każdego konta powstaje losowy KLUCZ DANYCH (DEK, 32 bajty). Nim szyfrowane są dane konta: AES-256 w trybie CTR + HMAC-SHA256 (szyfrowanie, potem podpis),
//     nowy losowy wektor początkowy przy każdym zapisie. Zmieniony choćby jeden bajt = odczyt odrzucony.
//   • DEK leży na dysku tylko ZASZYFROWANY kluczem wyprowadzonym z hasła użytkownika (PBKDF2-HMAC-SHA256, losowa sól, setki tysięcy iteracji). Samego hasła ani jego
//     skrótu na dysku nie ma — poprawność hasła sprawdza sam sejf (podpis zaszyfrowanego DEK), więc kradzież profilu przeglądarki nie daje szybkiego łamania hasła.
//   • Zmiana hasła przepisuje tylko zaszyfrowany DEK (dane zostają). Zapomniane hasło = dane z tego urządzenia nie do odczytania (dokumenty da się wygenerować od nowa).
//   • Po zalogowaniu DEK jest w pamięci i w sessionStorage karty (ginie z kartą), żeby odświeżenie strony nie pytało o hasło.
// Wszystko jest SYNCHRONICZNE i napisane w czystym JS (działa także na stronie bez https, gdzie nie ma Web Crypto); tylko PBKDF2 korzysta z Web Crypto, gdy jest.
// Poprawność AES, SHA-256, HMAC i PBKDF2 sprawdza testy/sejf_test.js na wektorach z norm i w porównaniu z modułem crypto Node'a.

/* ---------------------------------- SHA-256 (szybka kompresja, bez alokacji w pętli) ---------------------------------- */
const K256 = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]);
const H0_256 = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
const W = new Uint32Array(64);
/** Jedna kompresja SHA-256: stan h (8 słów) + blok 16 słów big-endian w w16. */
function kompresuj(h, w16) {
  const w = W; for (let i = 0; i < 16; i++) w[i] = w16[i];
  for (let i = 16; i < 64; i++) {
    const a = w[i - 15], b = w[i - 2];
    w[i] = (w[i - 16] + (((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3)) + w[i - 7] + (((b >>> 17) | (b << 15)) ^ ((b >>> 19) | (b << 13)) ^ (b >>> 10))) | 0;
  }
  let a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
  for (let i = 0; i < 64; i++) {
    const t1 = (hh + (((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7))) + ((e & f) ^ (~e & g)) + K256[i] + w[i]) | 0;
    const t2 = ((((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10))) + ((a & b) ^ (a & c) ^ (b & c))) | 0;
    hh = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
  }
  h[0] = (h[0] + a) | 0; h[1] = (h[1] + b) | 0; h[2] = (h[2] + c) | 0; h[3] = (h[3] + d) | 0; h[4] = (h[4] + e) | 0; h[5] = (h[5] + f) | 0; h[6] = (h[6] + g) | 0; h[7] = (h[7] + hh) | 0;
}
const blok = new Uint32Array(16);
/** Kontynuacja SHA-256 od stanu h (po `przed` bajtach już przetworzonych, wielokrotność 64) nad bajtami m; zwraca 32 bajty. Modyfikuje h. */
function koncz(h, m, przed) {
  const dl = m.length, calosc = przed + dl, n = (dl + 9 + 63) & ~63, b = new Uint8Array(n); b.set(m); b[dl] = 0x80;
  const dv = new DataView(b.buffer); dv.setUint32(n - 8, Math.floor((calosc * 8) / 4294967296)); dv.setUint32(n - 4, (calosc * 8) >>> 0);
  for (let o = 0; o < n; o += 64) { for (let i = 0; i < 16; i++) blok[i] = dv.getUint32(o + i * 4); kompresuj(h, blok); }
  const out = new Uint8Array(32), ov = new DataView(out.buffer); for (let i = 0; i < 8; i++) ov.setUint32(i * 4, h[i] >>> 0); return out;
}
export function sha256(m) { return koncz(Uint32Array.from(H0_256), m, 0); }
/** Stany SHA-256 po jednym bloku klucza HMAC (ipad/opad) — wspólne dla HMAC i PBKDF2. */
function stanyHmac(klucz) {
  let k = klucz.length > 64 ? sha256(klucz) : klucz; const kb = new Uint8Array(64); kb.set(k);
  const ip = new Uint32Array(8), op = new Uint32Array(8); ip.set(H0_256); op.set(H0_256);
  const dv = new DataView(new ArrayBuffer(64)); const bl = new Uint32Array(16);
  for (let i = 0; i < 64; i++) dv.setUint8(i, kb[i] ^ 0x36); for (let i = 0; i < 16; i++) bl[i] = dv.getUint32(i * 4); kompresuj(ip, bl);
  for (let i = 0; i < 64; i++) dv.setUint8(i, kb[i] ^ 0x5c); for (let i = 0; i < 16; i++) bl[i] = dv.getUint32(i * 4); kompresuj(op, bl);
  return { ip, op };
}
export function hmac(klucz, m) {
  const { ip, op } = stanyHmac(klucz), wew = koncz(Uint32Array.from(ip), m, 64); return koncz(Uint32Array.from(op), wew, 64);
}
const rowne = (a, b) => { if (a.length !== b.length) return false; let r = 0; for (let i = 0; i < a.length; i++) r |= a[i] ^ b[i]; return r === 0; };   // porównanie w stałym czasie

/* ---------------------------------- PBKDF2-HMAC-SHA256 ---------------------------------- */
/** Czysty JS: dwie kompresje na iterację (stany ipad/opad liczone raz). */
export function pbkdf2Js(haslo, sol, iter) {
  const { ip, op } = stanyHmac(haslo), ms = new Uint8Array(sol.length + 4); ms.set(sol); ms[ms.length - 1] = 1;
  let u = koncz(Uint32Array.from(op), koncz(Uint32Array.from(ip), ms, 64), 64);
  const uw = new Uint32Array(8), udv = new DataView(u.buffer, u.byteOffset, 32); for (let i = 0; i < 8; i++) uw[i] = udv.getUint32(i * 4);      // bajty → słowa big-endian
  const t = Uint32Array.from(uw), bw = new Uint32Array(16), hi = new Uint32Array(8), ho = new Uint32Array(8);
  for (let j = 1; j < iter; j++) {
    for (let i = 0; i < 8; i++) bw[i] = uw[i]; bw[8] = 0x80000000; for (let i = 9; i < 15; i++) bw[i] = 0; bw[15] = (64 + 32) * 8;
    hi.set(ip); kompresuj(hi, bw);
    for (let i = 0; i < 8; i++) bw[i] = hi[i]; bw[8] = 0x80000000; for (let i = 9; i < 15; i++) bw[i] = 0; bw[15] = (64 + 32) * 8;
    ho.set(op); kompresuj(ho, bw);
    for (let i = 0; i < 8; i++) { uw[i] = ho[i]; t[i] ^= ho[i]; }
  }
  const out = new Uint8Array(32), ov = new DataView(out.buffer); for (let i = 0; i < 8; i++) ov.setUint32(i * 4, t[i] >>> 0); return out;
}
const enc = new TextEncoder(), dec = new TextDecoder();
const subtle = () => (globalThis.crypto && crypto.subtle) || null;
/** PBKDF2 z hasła (tekst) i soli: Web Crypto, gdy jest (szybko, bez blokowania strony), inaczej czysty JS. Zwraca 32 bajty. */
export async function pbkdf2(haslo, sol, iter) {
  const s = subtle(), hb = enc.encode(haslo);
  if (s) { try { const k = await s.importKey('raw', hb, 'PBKDF2', false, ['deriveBits']); return new Uint8Array(await s.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: sol, iterations: iter }, k, 256)); } catch (e) { /* poniżej: czysty JS */ } }
  await new Promise(r => setTimeout(r, 0));      // pozwól odświeżyć ekran przed dłuższym liczeniem
  return pbkdf2Js(hb, sol, iter);
}

/* ---------------------------------- AES-256 (szyfrowanie bloku) + tryb CTR ---------------------------------- */
const SBOX = new Uint8Array(256), TE0 = new Uint32Array(256), TE1 = new Uint32Array(256), TE2 = new Uint32Array(256), TE3 = new Uint32Array(256);
(() => {
  let p = 1, q = 1; const rotl = (x, n) => ((x << n) | (x >> (8 - n))) & 0xff;
  do {
    p = (p ^ (p << 1) ^ (p & 0x80 ? 0x1b : 0)) & 0xff;                  // p *= 3
    q = (q ^ (q << 1)) & 0xff; q = (q ^ (q << 2)) & 0xff; q = (q ^ (q << 4)) & 0xff; if (q & 0x80) q ^= 0x09;      // q /= 3
    SBOX[p] = (q ^ rotl(q, 1) ^ rotl(q, 2) ^ rotl(q, 3) ^ rotl(q, 4) ^ 0x63) & 0xff;
  } while (p !== 1);
  SBOX[0] = 0x63;
  for (let x = 0; x < 256; x++) {
    const s = SBOX[x], s2 = ((s << 1) ^ (s & 0x80 ? 0x1b : 0)) & 0xff, s3 = s2 ^ s;
    const t = ((s2 << 24) | (s << 16) | (s << 8) | s3) >>> 0;
    TE0[x] = t; TE1[x] = ((t >>> 8) | (t << 24)) >>> 0; TE2[x] = ((t >>> 16) | (t << 16)) >>> 0; TE3[x] = ((t >>> 24) | (t << 8)) >>> 0;
  }
})();
const RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40];
/** Harmonogram kluczy AES-256: 60 słów. */
function rozwinKlucz(k) {
  if (k.length !== 32) throw new Error('klucz AES-256 ma 32 bajty');
  const w = new Uint32Array(60), dv = new DataView(k.buffer, k.byteOffset, 32); for (let i = 0; i < 8; i++) w[i] = dv.getUint32(i * 4);
  const sub = x => ((SBOX[x >>> 24] << 24) | (SBOX[(x >>> 16) & 255] << 16) | (SBOX[(x >>> 8) & 255] << 8) | SBOX[x & 255]) >>> 0;
  for (let i = 8; i < 60; i++) {
    let t = w[i - 1];
    if (i % 8 === 0) t = (sub(((t << 8) | (t >>> 24)) >>> 0) ^ (RCON[i / 8 - 1] << 24)) >>> 0; else if (i % 8 === 4) t = sub(t);
    w[i] = (w[i - 8] ^ t) >>> 0;
  }
  return w;
}
/** Szyfruje jeden blok (cztery słowa big-endian) w miejscu: s[0..3]. */
function blokAes(rk, s) {
  let s0 = s[0] ^ rk[0], s1 = s[1] ^ rk[1], s2 = s[2] ^ rk[2], s3 = s[3] ^ rk[3], t0, t1, t2, t3;
  for (let r = 1; r < 14; r++) {
    const o = r * 4;
    t0 = TE0[s0 >>> 24] ^ TE1[(s1 >>> 16) & 255] ^ TE2[(s2 >>> 8) & 255] ^ TE3[s3 & 255] ^ rk[o];
    t1 = TE0[s1 >>> 24] ^ TE1[(s2 >>> 16) & 255] ^ TE2[(s3 >>> 8) & 255] ^ TE3[s0 & 255] ^ rk[o + 1];
    t2 = TE0[s2 >>> 24] ^ TE1[(s3 >>> 16) & 255] ^ TE2[(s0 >>> 8) & 255] ^ TE3[s1 & 255] ^ rk[o + 2];
    t3 = TE0[s3 >>> 24] ^ TE1[(s0 >>> 16) & 255] ^ TE2[(s1 >>> 8) & 255] ^ TE3[s2 & 255] ^ rk[o + 3];
    s0 = t0; s1 = t1; s2 = t2; s3 = t3;
  }
  s[0] = ((SBOX[s0 >>> 24] << 24) | (SBOX[(s1 >>> 16) & 255] << 16) | (SBOX[(s2 >>> 8) & 255] << 8) | SBOX[s3 & 255]) ^ rk[56];
  s[1] = ((SBOX[s1 >>> 24] << 24) | (SBOX[(s2 >>> 16) & 255] << 16) | (SBOX[(s3 >>> 8) & 255] << 8) | SBOX[s0 & 255]) ^ rk[57];
  s[2] = ((SBOX[s2 >>> 24] << 24) | (SBOX[(s3 >>> 16) & 255] << 16) | (SBOX[(s0 >>> 8) & 255] << 8) | SBOX[s1 & 255]) ^ rk[58];
  s[3] = ((SBOX[s3 >>> 24] << 24) | (SBOX[(s0 >>> 16) & 255] << 16) | (SBOX[(s1 >>> 8) & 255] << 8) | SBOX[s2 & 255]) ^ rk[59];
}
export const blokAes256 = (klucz, blok16) => { const rk = rozwinKlucz(klucz), dv = new DataView(blok16.buffer, blok16.byteOffset, 16), s = new Uint32Array(4); for (let i = 0; i < 4; i++) s[i] = dv.getUint32(i * 4); blokAes(rk, s); const o = new Uint8Array(16), ov = new DataView(o.buffer); for (let i = 0; i < 4; i++) ov.setUint32(i * 4, s[i] >>> 0); return o; };
/** AES-256-CTR: ten sam wynik przy szyfrowaniu i odszyfrowaniu. iv = początkowy blok licznika (16 bajtów, zwiększany jako liczba 128-bitowa big-endian). */
export function ctr(rk, iv, dane) {
  const out = new Uint8Array(dane.length), c = new Uint32Array(4), s = new Uint32Array(4), div = new DataView(iv.buffer, iv.byteOffset, 16); for (let i = 0; i < 4; i++) c[i] = div.getUint32(i * 4);
  for (let o = 0; o < dane.length; o += 16) {
    s[0] = c[0]; s[1] = c[1]; s[2] = c[2]; s[3] = c[3]; blokAes(rk, s);
    const k0 = s[0], k1 = s[1], k2 = s[2], k3 = s[3], n = Math.min(16, dane.length - o);
    for (let i = 0; i < n; i++) { const kw = i < 4 ? k0 : i < 8 ? k1 : i < 12 ? k2 : k3; out[o + i] = dane[o + i] ^ ((kw >>> (24 - 8 * (i & 3))) & 255); }
    for (let i = 3; i >= 0; i--) { c[i] = (c[i] + 1) >>> 0; if (c[i] !== 0) break; }
  }
  return out;
}
export const aesCtr = (klucz, iv, dane) => ctr(rozwinKlucz(klucz), iv, dane);

/* ---------------------------------- koperta: MAGIA | iv | szyfrogram | podpis ---------------------------------- */
const MAGIA = new Uint8Array([0x50, 0x4d, 0x54, 0x31]);      // „PMT1”
export const losowe = n => { const b = new Uint8Array(n); if (globalThis.crypto && crypto.getRandomValues) { for (let i = 0; i < n; i += 65536) crypto.getRandomValues(b.subarray(i, Math.min(n, i + 65536))); return b; } throw new Error('Przeglądarka nie ma generatora liczb losowych'); };
/** Z jednego klucza (DEK albo klucza z hasła) powstają dwa niezależne: do szyfrowania i do podpisu. */
export function klucze(k32) { return { rk: rozwinKlucz(hmac(k32, enc.encode('pmt-szyfr'))), mac: hmac(k32, enc.encode('pmt-podpis')), id: b64(hmac(k32, enc.encode('pmt-id')).slice(0, 6)) }; }
export function szyfruj(kl, bajty) {
  const iv = losowe(16), ct = ctr(kl.rk, iv, bajty), out = new Uint8Array(4 + 16 + ct.length + 32);
  out.set(MAGIA); out.set(iv, 4); out.set(ct, 20);
  out.set(hmac(kl.mac, out.subarray(0, 20 + ct.length)), 20 + ct.length); return out;
}
export const jestZaszyfrowane = d => d && d.length >= 52 && d[0] === 0x50 && d[1] === 0x4d && d[2] === 0x54 && d[3] === 0x31;
/** Odszyfrowuje kopertę; null, gdy podpis się nie zgadza (zły klucz albo zmieniona zawartość) albo to nie koperta. */
export function odszyfruj(kl, d) {
  if (!jestZaszyfrowane(d)) return null;
  const n = d.length - 32, tag = d.subarray(n); if (!rowne(hmac(kl.mac, d.subarray(0, n)), tag)) return null;
  return ctr(kl.rk, d.subarray(4, 20), d.subarray(20, n));
}
export function b64(b) { let s = ''; for (let i = 0; i < b.length; i += 8192) s += String.fromCharCode.apply(null, b.subarray(i, Math.min(b.length, i + 8192))); return btoa(s); }
export function unb64(t) { const s = atob(t), b = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); return b; }
const PREFIKS = 'enc1:';
/** Tekst (JSON konta) → „enc1:…” (base64 koperty). */
export const szyfrujTekst = (kl, tekst) => PREFIKS + b64(szyfruj(kl, enc.encode(tekst)));
export const czyTekstZaszyfrowany = t => typeof t === 'string' && t.startsWith(PREFIKS);
export function odszyfrujTekst(kl, t) { if (!czyTekstZaszyfrowany(t)) return null; try { const o = odszyfruj(kl, unb64(t.slice(PREFIKS.length))); return o ? dec.decode(o) : null; } catch (e) { return null; } }

/* ---------------------------------- sejf konta: zaszyfrowany klucz danych w localStorage ---------------------------------- */
const KLUCZ_SEJFU = kod => `pmt-web-sejf:${kod}`, KLUCZ_SESJI = 'pmt-web-dek';
export const ITERACJE = 600000;      // zalecenie OWASP dla PBKDF2-HMAC-SHA256; liczba zapisana w sejfie, więc można ją później podnieść
const ls = (f, dom) => { try { return f(); } catch (e) { return dom; } };
const wczytajSejf = kod => ls(() => JSON.parse(localStorage.getItem(KLUCZ_SEJFU(kod))), null);
export const maSejf = kod => !!wczytajSejf(kod);
async function opakuj(dek, haslo, iter = ITERACJE) {
  const sol = losowe(16), kek = await pbkdf2(haslo, sol, iter);
  return { v: 1, kdf: 'PBKDF2-SHA256', iter, sol: b64(sol), dek: b64(szyfruj(klucze(kek), dek)) };
}
/** Pierwsze logowanie na tym urządzeniu (albo konto bez sejfu): losowy DEK, zapisany tylko w postaci zaszyfrowanej hasłem. Zwraca DEK. */
export async function utworzSejf(kod, haslo) {
  const dek = losowe(32); const m = await opakuj(dek, haslo);
  localStorage.setItem(KLUCZ_SEJFU(kod), JSON.stringify(m)); return dek;
}
/** Otwiera sejf hasłem: DEK albo null (złe hasło / uszkodzony sejf / brak sejfu). */
export async function otworzSejf(kod, haslo) {
  const m = wczytajSejf(kod); if (!m || !m.sol || !m.dek) return null;
  try { const kek = await pbkdf2(haslo, unb64(m.sol), Number(m.iter) || ITERACJE); return odszyfruj(klucze(kek), unb64(m.dek)); } catch (e) { return null; }
}
/** Zmiana hasła: ten sam DEK, zaszyfrowany nowym hasłem (nowa sól) — dane na dysku zostają nietknięte. */
export async function przepiszSejf(kod, dek, noweHaslo) { const m = await opakuj(dek, noweHaslo); localStorage.setItem(KLUCZ_SEJFU(kod), JSON.stringify(m)); }
export const usunSejf = kod => ls(() => localStorage.removeItem(KLUCZ_SEJFU(kod)));

/* ---------------------------------- klucz danych na czas sesji karty ---------------------------------- */
export const zapamietajKlucz = dek => ls(() => sessionStorage.setItem(KLUCZ_SESJI, b64(dek)));
export const odczytajKlucz = () => ls(() => { const t = sessionStorage.getItem(KLUCZ_SESJI); return t ? unb64(t) : null; }, null);
export const zapomnijKlucz = () => ls(() => sessionStorage.removeItem(KLUCZ_SESJI));
