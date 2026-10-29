// SHA-256 i HMAC w czystym JS (zapas, gdy strona nie jest bezpiecznym kontekstem) kontra Web Crypto/Node. node testy/dostep_krypto.mjs
import { sha256Js, hmacJs, sha256Hex, hmacHex } from '../js/dostep.js';
import crypto from 'node:crypto';
let bad = 0;
const hx = b => Buffer.from(b).toString('hex');
for (const s of ['', 'a', 'abc', 'PMT|12345|haslo ąęł', 'x'.repeat(55), 'x'.repeat(56), 'x'.repeat(64), 'x'.repeat(1000)]) {
  const a = hx(sha256Js(s)), b = crypto.createHash('sha256').update(s).digest('hex');
  if (a !== b) { bad++; console.log('SHA różni się', s.length); }
  for (const k of ['k', 'sekret-testowy', 'z'.repeat(100)]) {
    const h1 = hx(hmacJs(k, s)), h2 = crypto.createHmac('sha256', k).update(s).digest('hex');
    if (h1 !== h2) { bad++; console.log('HMAC różni się', s.length, k.length); }
  }
}
console.log('subtle:', await sha256Hex('abc') === crypto.createHash('sha256').update('abc').digest('hex'), await hmacHex('k','abc') === crypto.createHmac('sha256','k').update('abc').digest('hex'));
console.log(bad ? 'BŁĘDY ' + bad : 'OK');
