// PMT Planer (web) — własna, czysta kryptografia do SPRAWDZANIA podpisów, gdy przeglądarka nie daje Web Crypto.
// Web Crypto istnieje tylko na stronach „bezpiecznych” (https albo localhost). Gdy aplikacja stoi na zwykłym http, `crypto.subtle` jest puste —
// wtedy weryfikacja.js korzysta z tego pliku: skróty SHA-1/256/384/512, podpis RSA (PKCS#1 v1.5 i PSS) oraz ECDSA na krzywych P-256/384/521.
// To wyłącznie operacje na kluczach PUBLICZNYCH (sprawdzanie podpisu) — nie ma tu żadnego klucza prywatnego, więc nie ma czego wyciec.
// Interfejs jest taki jak w SubtleCrypto (digest / importKey('spki') / verify), żeby weryfikacja.js nie musiała wiedzieć, z czego korzysta.

/* ---------------------------------- skróty ---------------------------------- */
const rr = (x, k) => (x >>> k) | (x << (32 - k));
const K256 = Uint32Array.from([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]);

/** Dopełnienie wiadomości do pełnych bloków (SHA-1/256: blok 64 B, długość 8 B; SHA-384/512: blok 128 B, długość 16 B). */
function dopelnij(m, blok) {
  const dl = m.length, dlugoscPola = blok === 64 ? 8 : 16, n = Math.ceil((dl + 1 + dlugoscPola) / blok) * blok, b = new Uint8Array(n);
  b.set(m); b[dl] = 0x80; const dv = new DataView(b.buffer);
  dv.setUint32(n - 8, Math.floor(dl / 536870912)); dv.setUint32(n - 4, (dl << 3) >>> 0);      // długość w bitach (dla dokumentów < 512 MB wystarczą dolne 64 bity)
  return { b, dv, n };
}
function sha256(m) {
  const { dv, n } = dopelnij(m, 64), h = Uint32Array.from([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]), w = new Uint32Array(64);
  for (let o = 0; o < n; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getUint32(o + i * 4);
    for (let i = 16; i < 64; i++) { const a = rr(w[i - 15], 7) ^ rr(w[i - 15], 18) ^ (w[i - 15] >>> 3), c = rr(w[i - 2], 17) ^ rr(w[i - 2], 19) ^ (w[i - 2] >>> 10); w[i] = (w[i - 16] + a + w[i - 7] + c) >>> 0; }
    let [a, b, c, d, e, f, g, hh] = h;
    for (let i = 0; i < 64; i++) {
      const t1 = (hh + (rr(e, 6) ^ rr(e, 11) ^ rr(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i]) >>> 0, t2 = ((rr(a, 2) ^ rr(a, 13) ^ rr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      hh = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
  }
  const out = new Uint8Array(32), ov = new DataView(out.buffer); h.forEach((x, i) => ov.setUint32(i * 4, x)); return out;
}
function sha1(m) {
  const { dv, n } = dopelnij(m, 64), h = Uint32Array.from([0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0]), w = new Uint32Array(80);
  for (let o = 0; o < n; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getUint32(o + i * 4);
    for (let i = 16; i < 80; i++) w[i] = rr(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 31);
    let [a, b, c, d, e] = h;
    for (let i = 0; i < 80; i++) {
      const [f, k] = i < 20 ? [(b & c) | (~b & d), 0x5a827999] : i < 40 ? [b ^ c ^ d, 0x6ed9eba1] : i < 60 ? [(b & c) | (b & d) | (c & d), 0x8f1bbcdc] : [b ^ c ^ d, 0xca62c1d6];
      const t = (rr(a, 27) + f + e + k + w[i]) >>> 0; e = d; d = c; c = rr(b, 2); b = a; a = t;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e;
  }
  const out = new Uint8Array(20), ov = new DataView(out.buffer); h.forEach((x, i) => ov.setUint32(i * 4, x)); return out;
}
// SHA-384/512: słowa 64-bitowe jako BigInt (rzadko używane w podpisach, dokumenty są małe — prostota ważniejsza od szybkości)
const M64 = (1n << 64n) - 1n, rr64 = (x, k) => ((x >> BigInt(k)) | (x << BigInt(64 - k))) & M64;
const K512 = [
  '428a2f98d728ae22', '7137449123ef65cd', 'b5c0fbcfec4d3b2f', 'e9b5dba58189dbbc', '3956c25bf348b538', '59f111f1b605d019', '923f82a4af194f9b', 'ab1c5ed5da6d8118', 'd807aa98a3030242', '12835b0145706fbe',
  '243185be4ee4b28c', '550c7dc3d5ffb4e2', '72be5d74f27b896f', '80deb1fe3b1696b1', '9bdc06a725c71235', 'c19bf174cf692694', 'e49b69c19ef14ad2', 'efbe4786384f25e3', '0fc19dc68b8cd5b5', '240ca1cc77ac9c65',
  '2de92c6f592b0275', '4a7484aa6ea6e483', '5cb0a9dcbd41fbd4', '76f988da831153b5', '983e5152ee66dfab', 'a831c66d2db43210', 'b00327c898fb213f', 'bf597fc7beef0ee4', 'c6e00bf33da88fc2', 'd5a79147930aa725',
  '06ca6351e003826f', '142929670a0e6e70', '27b70a8546d22ffc', '2e1b21385c26c926', '4d2c6dfc5ac42aed', '53380d139d95b3df', '650a73548baf63de', '766a0abb3c77b2a8', '81c2c92e47edaee6', '92722c851482353b',
  'a2bfe8a14cf10364', 'a81a664bbc423001', 'c24b8b70d0f89791', 'c76c51a30654be30', 'd192e819d6ef5218', 'd69906245565a910', 'f40e35855771202a', '106aa07032bbd1b8', '19a4c116b8d2d0c8', '1e376c085141ab53',
  '2748774cdf8eeb99', '34b0bcb5e19b48a8', '391c0cb3c5c95a63', '4ed8aa4ae3418acb', '5b9cca4f7763e373', '682e6ff3d6b2b8a3', '748f82ee5defb2fc', '78a5636f43172f60', '84c87814a1f0ab72', '8cc702081a6439ec',
  '90befffa23631e28', 'a4506cebde82bde9', 'bef9a3f7b2c67915', 'c67178f2e372532b', 'ca273eceea26619c', 'd186b8c721c0c207', 'eada7dd6cde0eb1e', 'f57d4f7fee6ed178', '06f067aa72176fba', '0a637dc5a2c898a6',
  '113f9804bef90dae', '1b710b35131c471b', '28db77f523047d84', '32caab7b40c72493', '3c9ebe0a15c9bebc', '431d67c49c100d4c', '4cc5d4becb3e42b6', '597f299cfc657e2a', '5fcb6fab3ad6faec', '6c44198c4a475817'].map(x => BigInt('0x' + x));
function sha512(m, wariant) {
  const { dv, n } = dopelnij(m, 128), pocz = wariant === 384
    ? ['cbbb9d5dc1059ed8', '629a292a367cd507', '9159015a3070dd17', '152fecd8f70e5939', '67332667ffc00b31', '8eb44a8768581511', 'db0c2e0d64f98fa7', '47b5481dbefa4fa4']
    : ['6a09e667f3bcc908', 'bb67ae8584caa73b', '3c6ef372fe94f82b', 'a54ff53a5f1d36f1', '510e527fade682d1', '9b05688c2b3e6c1f', '1f83d9abfb41bd6b', '5be0cd19137e2179'];
  const h = pocz.map(x => BigInt('0x' + x)), w = new Array(80);
  for (let o = 0; o < n; o += 128) {
    for (let i = 0; i < 16; i++) w[i] = (BigInt(dv.getUint32(o + i * 8)) << 32n) | BigInt(dv.getUint32(o + i * 8 + 4));
    for (let i = 16; i < 80; i++) {
      const a = rr64(w[i - 15], 1) ^ rr64(w[i - 15], 8) ^ (w[i - 15] >> 7n), c = rr64(w[i - 2], 19) ^ rr64(w[i - 2], 61) ^ (w[i - 2] >> 6n);
      w[i] = (w[i - 16] + a + w[i - 7] + c) & M64;
    }
    let [a, b, c, d, e, f, g, hh] = h;
    for (let i = 0; i < 80; i++) {
      const t1 = (hh + (rr64(e, 14) ^ rr64(e, 18) ^ rr64(e, 41)) + ((e & f) ^ (~e & M64 & g)) + K512[i] + w[i]) & M64;
      const t2 = ((rr64(a, 28) ^ rr64(a, 34) ^ rr64(a, 39)) + ((a & b) ^ (a & c) ^ (b & c))) & M64;
      hh = g; g = f; f = e; e = (d + t1) & M64; d = c; c = b; b = a; a = (t1 + t2) & M64;
    }
    [a, b, c, d, e, f, g, hh].forEach((x, i) => { h[i] = (h[i] + x) & M64; });
  }
  const dl = wariant === 384 ? 48 : 64, out = new Uint8Array(64), ov = new DataView(out.buffer);
  h.forEach((x, i) => { ov.setUint32(i * 8, Number(x >> 32n)); ov.setUint32(i * 8 + 4, Number(x & 0xffffffffn)); });
  return out.subarray(0, dl);
}
const DLUGOSC_SKROTU = { 'SHA-1': 20, 'SHA-256': 32, 'SHA-384': 48, 'SHA-512': 64 };
const nazwaHasha = a => String(typeof a === 'string' ? a : (a.hash && (a.hash.name || a.hash)) || a.name).toUpperCase();
export function skrotJs(alg, bajty) {
  const m = bajty instanceof Uint8Array ? bajty : new Uint8Array(bajty), n = nazwaHasha(alg);
  if (n === 'SHA-256') return sha256(m);
  if (n === 'SHA-1') return sha1(m);
  if (n === 'SHA-384') return sha512(m, 384);
  if (n === 'SHA-512') return sha512(m, 512);
  throw new Error('nieobsługiwany skrót ' + n);
}

/* ---------------------------------- liczby i DER ---------------------------------- */
const mod = (a, m) => { const r = a % m; return r >= 0n ? r : r + m; };
function potega(p, e, m) { let w = 1n; p = mod(p, m); while (e > 0n) { if (e & 1n) w = (w * p) % m; p = (p * p) % m; e >>= 1n; } return w; }
const odwrotnosc = (a, m) => potega(a, m - 2n, m);      // m pierwsze (rząd i ciało krzywych NIST)
const naLiczbe = b => { let x = 0n; for (const v of b) x = (x << 8n) | BigInt(v); return x; };
const naBajty = (x, dl) => { const o = new Uint8Array(dl); for (let i = dl - 1; i >= 0; i--) { o[i] = Number(x & 0xffn); x >>= 8n; } return o; };
const dlugoscBitow = x => x.toString(2).length;
function tlv(b, p) {
  if (p + 2 > b.length) throw new Error('uszkodzony klucz publiczny');
  let l = b[p + 1], h = 2; if (l & 0x80) { const n = l & 0x7f; if (!n || n > 4) throw new Error('uszkodzony klucz publiczny'); l = 0; for (let i = 0; i < n; i++) l = l * 256 + b[p + 2 + i]; h = 2 + n; }
  if (p + h + l > b.length) throw new Error('uszkodzony klucz publiczny');
  return { tag: b[p], start: p + h, end: p + h + l };
}
const dziecko = (b, n) => { const w = []; let p = n.start; while (p < n.end) { const c = tlv(b, p); w.push(c); p = c.end; } return w; };
const oidTekst = (b, n) => { const t = b.subarray(n.start, n.end), w = [Math.floor(t[0] / 40), t[0] % 40]; let v = 0; for (let i = 1; i < t.length; i++) { v = v * 128 + (t[i] & 0x7f); if (!(t[i] & 0x80)) { w.push(v); v = 0; } } return w.join('.'); };

/* ---------------------------------- RSA ---------------------------------- */
const PREFIKS = {       // DigestInfo przed skrótem w podpisie PKCS#1 v1.5 (RFC 8017, uwaga 1)
  'SHA-1': '3021300906052b0e03021a05000414', 'SHA-256': '3031300d060960864801650304020105000420',
  'SHA-384': '3041300d060960864801650304020205000430', 'SHA-512': '3051300d060960864801650304020305000440' };
const hexNaBajty = h => Uint8Array.from(h.match(/../g).map(x => parseInt(x, 16)));
function weryfikujRsaV15(klucz, podpis, dane, hash) {
  const k = Math.ceil(dlugoscBitow(klucz.n) / 8); if (podpis.length !== k) return false;
  const s = naLiczbe(podpis); if (s >= klucz.n) return false;
  const em = naBajty(potega(s, klucz.e, klucz.n), k), t = new Uint8Array([...hexNaBajty(PREFIKS[hash]), ...skrotJs(hash, dane)]);
  if (k < t.length + 11) return false;
  const oczek = new Uint8Array(k); oczek[1] = 1; oczek.fill(0xff, 2, k - t.length - 1); oczek.set(t, k - t.length);
  let roznica = 0; for (let i = 0; i < k; i++) roznica |= em[i] ^ oczek[i]; return roznica === 0;
}
function mgf1(zarodek, dl, hash) {
  const hl = DLUGOSC_SKROTU[hash], wyn = new Uint8Array(Math.ceil(dl / hl) * hl);
  for (let c = 0; c * hl < dl; c++) { const w = new Uint8Array(zarodek.length + 4); w.set(zarodek); new DataView(w.buffer).setUint32(zarodek.length, c); wyn.set(skrotJs(hash, w), c * hl); }
  return wyn.subarray(0, dl);
}
function weryfikujRsaPss(klucz, podpis, dane, hash, sol) {
  const bitowMod = dlugoscBitow(klucz.n), emBits = bitowMod - 1, emLen = Math.ceil(emBits / 8), k = Math.ceil(bitowMod / 8);
  if (podpis.length !== k) return false;
  const s = naLiczbe(podpis); if (s >= klucz.n) return false;
  const em = naBajty(potega(s, klucz.e, klucz.n), k).subarray(k - emLen), hl = DLUGOSC_SKROTU[hash];
  if (emLen < hl + sol + 2 || em[emLen - 1] !== 0xbc) return false;
  const maskowane = em.subarray(0, emLen - hl - 1), h = em.subarray(emLen - hl - 1, emLen - 1), zbedne = 8 * emLen - emBits;
  if (zbedne && (maskowane[0] >> (8 - zbedne)) !== 0) return false;
  const maska = mgf1(h, emLen - hl - 1, hash), db = maskowane.map((x, i) => x ^ maska[i]);
  if (zbedne) db[0] &= 0xff >> zbedne;
  const nZer = emLen - hl - sol - 2; for (let i = 0; i < nZer; i++) if (db[i] !== 0) return false;
  if (db[nZer] !== 1) return false;
  const sola = db.subarray(db.length - sol), m2 = new Uint8Array(8 + hl + sol); m2.set(skrotJs(hash, dane), 8); m2.set(sola, 8 + hl);
  const h2 = skrotJs(hash, m2); let roznica = 0; for (let i = 0; i < hl; i++) roznica |= h2[i] ^ h[i]; return roznica === 0;
}

/* ---------------------------------- krzywe eliptyczne NIST (a = −3), współrzędne Jacobiego ---------------------------------- */
const H = x => BigInt('0x' + x);
const KRZYWE = {
  'P-256': { p: H('ffffffff00000001000000000000000000000000ffffffffffffffffffffffff'), n: H('ffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551'), b: H('5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b'),
    gx: H('6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296'), gy: H('4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5'), dl: 32 },
  'P-384': { p: H('fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffeffffffff0000000000000000ffffffff'), n: H('ffffffffffffffffffffffffffffffffffffffffffffffffc7634d81f4372ddf581a0db248b0a77aecec196accc52973'),
    b: H('b3312fa7e23ee7e4988e056be3f82d19181d9c6efe8141120314088f5013875ac656398d8a2ed19d2a85c8edd3ec2aef'),
    gx: H('aa87ca22be8b05378eb1c71ef320ad746e1d3b628ba79b9859f741e082542a385502f25dbf55296c3a545e3872760ab7'), gy: H('3617de4a96262c6f5d9e98bf9292dc29f8f41dbd289a147ce9da3113b5f0b8c00a60b1ce1d7e819d7a431d7c90ea0e5f'), dl: 48 },
  'P-521': { p: (1n << 521n) - 1n, n: H('01fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffa51868783bf2f966b7fcc0148f709a5d03bb5c9b8899c47aebb6fb71e91386409'),
    b: H('0051953eb9618e1c9a1f929a21a0b68540eea2da725b99b315f3b8b489918ef109e156193951ec7e937b1652c0bd3bb1bf073573df883d2c34f1ef451fd46b503f00'),
    gx: H('00c6858e06b70404e9cd9e3ecb662395b4429c648139053fb521f828af606b4d3dbaa14b5e77efe75928fe1dc127a2ffa8de3348b3c1856a429bf97e7e31c2e5bd66'),
    gy: H('011839296a789a3bc0045c8a5fb42c7d1bd998f54449579b446817afbd17273e662c97ee72995ef42640c550b9013fad0761353c7086a272c24088be94769fd16650'), dl: 66 } };

function podwoj(P, c) {
  const { p } = c; if (P.z === 0n) return P;
  const delta = P.z * P.z % p, gamma = P.y * P.y % p, beta = P.x * gamma % p, alfa = 3n * mod((P.x - delta) * (P.x + delta), p) % p;
  const x = mod(alfa * alfa - 8n * beta, p), z = mod((P.y + P.z) * (P.y + P.z) - gamma - delta, p), y = mod(alfa * (4n * beta - x) - 8n * gamma * gamma, p);
  return { x, y, z };
}
function dodaj(P, Q, c) {
  const { p } = c; if (P.z === 0n) return Q; if (Q.z === 0n) return P;
  const z1z1 = P.z * P.z % p, z2z2 = Q.z * Q.z % p, u1 = P.x * z2z2 % p, u2 = Q.x * z1z1 % p, s1 = P.y * Q.z % p * z2z2 % p, s2 = Q.y * P.z % p * z1z1 % p;
  const h = mod(u2 - u1, p), r = mod(2n * (s2 - s1), p);
  if (h === 0n) return r === 0n ? podwoj(P, c) : { x: 0n, y: 1n, z: 0n };      // ten sam punkt → podwojenie; przeciwne → nieskończoność
  const i = 4n * h * h % p, j = h * i % p, v = u1 * i % p, x = mod(r * r - j - 2n * v, p), y = mod(r * (v - x) - 2n * s1 * j, p), z = mod(((P.z + Q.z) * (P.z + Q.z) - z1z1 - z2z2) * h, p);
  return { x, y, z };
}
function weryfikujEcdsa(klucz, podpis, dane, hash) {
  const c = klucz.krzywa, dl = c.dl; if (podpis.length !== 2 * dl) return false;
  const r = naLiczbe(podpis.subarray(0, dl)), s = naLiczbe(podpis.subarray(dl));
  if (r <= 0n || r >= c.n || s <= 0n || s >= c.n) return false;
  let e = naLiczbe(skrotJs(hash, dane)); const nadmiar = DLUGOSC_SKROTU[hash] * 8 - dlugoscBitow(c.n); if (nadmiar > 0) e >>= BigInt(nadmiar);
  const w = odwrotnosc(s, c.n), u1 = e * w % c.n, u2 = r * w % c.n;
  const G = { x: c.gx, y: c.gy, z: 1n }, Q = { x: klucz.x, y: klucz.y, z: 1n }, GQ = dodaj(G, Q, c);
  let R = { x: 0n, y: 1n, z: 0n };
  for (let bit = Math.max(dlugoscBitow(u1), dlugoscBitow(u2)) - 1; bit >= 0; bit--) {      // sztuczka Shamira: jedno przejście dla u1·G + u2·Q
    R = podwoj(R, c); const a = (u1 >> BigInt(bit)) & 1n, b = (u2 >> BigInt(bit)) & 1n;
    if (a && b) R = dodaj(R, GQ, c); else if (a) R = dodaj(R, G, c); else if (b) R = dodaj(R, Q, c);
  }
  if (R.z === 0n) return false;
  const zi = odwrotnosc(R.z, c.p); return mod(R.x * zi % c.p * zi, c.p) % c.n === r;
}

/* ---------------------------------- interfejs jak w SubtleCrypto ---------------------------------- */
export const kryptoJs = {
  wlasna: true,
  async digest(alg, dane) { return skrotJs(alg, dane); },
  async importKey(format, spki, algo) {
    if (format !== 'spki') throw new Error('obsługuję tylko klucze publiczne SPKI');
    const b = spki instanceof Uint8Array ? spki : new Uint8Array(spki), [alg, bity] = dziecko(b, tlv(b, 0)), [oid, par] = dziecko(b, alg), id = oidTekst(b, oid);
    const klucz = b.subarray(bity.start + 1, bity.end);      // pierwszy bajt BIT STRING = liczba nieużywanych bitów
    const nazwa = String(algo.name || algo);
    if (id === '1.2.840.113549.1.1.1') {
      if (!/^RSA/i.test(nazwa)) throw new Error('klucz RSA, a algorytm ' + nazwa);
      const [n, e] = dziecko(klucz, tlv(klucz, 0)), przytnij = (t) => { let i = 0; while (i < t.length - 1 && t[i] === 0) i++; return t.subarray(i); };
      return { jak: 'rsa', hash: algo.hash, n: naLiczbe(przytnij(klucz.subarray(n.start, n.end))), e: naLiczbe(przytnij(klucz.subarray(e.start, e.end))) };
    }
    if (id === '1.2.840.10045.2.1') {
      const c = KRZYWE[algo.namedCurve]; if (!c) throw new Error('nieobsługiwana krzywa ' + algo.namedCurve);
      if (klucz[0] !== 4 || klucz.length !== 1 + 2 * c.dl) throw new Error('nieobsługiwany zapis punktu krzywej');
      const x = naLiczbe(klucz.subarray(1, 1 + c.dl)), y = naLiczbe(klucz.subarray(1 + c.dl));
      if (mod(y * y - (x * x * x - 3n * x + c.b), c.p) !== 0n) throw new Error('klucz publiczny nie leży na krzywej');      // sprawdzenie poprawności klucza
      return { jak: 'ec', krzywa: c, x, y };
    }
    throw new Error('nieobsługiwany rodzaj klucza');
  },
  async verify(algo, klucz, podpis, dane) {
    const nazwa = String(algo.name || algo), s = podpis instanceof Uint8Array ? podpis : new Uint8Array(podpis), m = dane instanceof Uint8Array ? dane : new Uint8Array(dane);
    if (nazwa === 'RSASSA-PKCS1-v1_5' && klucz.jak === 'rsa') return weryfikujRsaV15(klucz, s, m, nazwaHasha(klucz.hash || algo));
    if (nazwa === 'RSA-PSS' && klucz.jak === 'rsa') return weryfikujRsaPss(klucz, s, m, nazwaHasha(klucz.hash || algo), algo.saltLength);
    if (nazwa === 'ECDSA' && klucz.jak === 'ec') return weryfikujEcdsa(klucz, s, m, nazwaHasha(algo));
    throw new Error('nieobsługiwany algorytm podpisu ' + nazwa);
  },
};
