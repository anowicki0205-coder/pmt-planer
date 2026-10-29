// Sejf (js/sejf.js): szyfrowanie danych konta na urządzeniu. Własny AES-256-CTR, SHA-256, HMAC i PBKDF2 sprawdzone na wektorach z norm i w porównaniu z modułem crypto Node'a
// (inny, niezależny kod); koperta wykrywa każdą zmianę; sejf z hasłem: złe hasło nie otwiera, zmiana hasła zachowuje dane.
// Uruchom: node testy/sejf_test.js
const nc = require('crypto');
(async () => {
  const S = await import('../js/sejf.js'); let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const hex = b => Buffer.from(b).toString('hex'), losowe = n => new Uint8Array(nc.randomBytes(n));
  /* SHA-256 / HMAC */
  ok('SHA-256("abc") zgodny z normą', hex(S.sha256(Buffer.from('abc'))) === 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  let zgodne = true, bl = '';
  for (const n of [0, 1, 55, 56, 63, 64, 65, 119, 120, 128, 1000, 70001]) { const d = losowe(n); if (hex(S.sha256(d)) !== nc.createHash('sha256').update(d).digest('hex')) { zgodne = false; bl = String(n); break; } }
  ok('SHA-256 zgodny z Node dla długości na granicach bloków', zgodne, bl && 'różnica przy ' + bl);
  zgodne = true; for (const kl of [0, 1, 10, 32, 63, 64, 65, 100, 200]) for (const n of [0, 5, 64, 200]) { const k = losowe(kl), d = losowe(n); if (hex(S.hmac(k, d)) !== nc.createHmac('sha256', k).update(d).digest('hex')) { zgodne = false; bl = kl + '/' + n; } }
  ok('HMAC-SHA256 zgodny z Node (klucze krótsze, równe i dłuższe niż blok)', zgodne, bl && 'różnica przy ' + bl);
  /* PBKDF2 */
  zgodne = true; for (const [h, sol, it] of [['passwd', 'salt', 1], ['Password', 'NaCl', 80], ['zażółć gęślą jaźń', 'sól', 1000], ['x'.repeat(100), 'a'.repeat(16), 7], ['', 'sol', 3]]) {
    const a = S.pbkdf2Js(new TextEncoder().encode(h), new TextEncoder().encode(sol), it), b = nc.pbkdf2Sync(h, sol, it, 32, 'sha256'); if (hex(a) !== b.toString('hex')) { zgodne = false; bl = `${h.slice(0, 10)}/${it}`; } }
  ok('PBKDF2-SHA256 (czysty JS) zgodny z Node, także hasło dłuższe niż blok i polskie znaki', zgodne, bl && 'różnica: ' + bl);
  let t0 = Date.now(); const jsT = S.pbkdf2Js(new TextEncoder().encode('haslo'), losowe(16), 600000); const msJs = Date.now() - t0;
  ok('PBKDF2 600 000 iteracji w czystym JS mieści się w kilku sekundach (strona bez https)', msJs < 8000, msJs + ' ms');
  const sol = losowe(16); ok('PBKDF2 przez Web Crypto daje to samo co czysty JS', hex(await S.pbkdf2('Hasło-123', sol, 5000)) === hex(S.pbkdf2Js(new TextEncoder().encode('Hasło-123'), sol, 5000)));
  /* AES-256 */
  const k = Uint8Array.from({ length: 32 }, (_, i) => i), p = Uint8Array.from('00112233445566778899aabbccddeeff'.match(/../g), x => parseInt(x, 16));
  ok('AES-256: wektor z FIPS-197 (C.3)', hex(S.blokAes256(k, p)) === '8ea2b7ca516745bfeafc49904b496089', hex(S.blokAes256(k, p)));
  zgodne = true; for (const n of [0, 1, 15, 16, 17, 31, 32, 100, 1000, 4097]) for (const iv of [losowe(16), new Uint8Array(16).fill(255), Uint8Array.from([...new Uint8Array(12), 255, 255, 255, 254])]) {
    const kk = losowe(32), d = losowe(n), c = nc.createCipheriv('aes-256-ctr', kk, iv); const ref = Buffer.concat([c.update(d), c.final()]);
    if (hex(S.aesCtr(kk, iv, d)) !== ref.toString('hex')) { zgodne = false; bl = String(n); } }
  ok('AES-256-CTR zgodny z Node dla różnych długości i przy przeniesieniu licznika (ff…ff)', zgodne, bl && 'różnica przy ' + bl);
  /* koperta */
  const dek = losowe(32), kl = S.klucze(dek), json = JSON.stringify({ profil: { imie: 'Zażółć Gęślą', pesel: '90010112349', adres: 'ul. Testowa 1, 00-001 Warszawa' } });
  const tekst = S.szyfrujTekst(kl, json);
  ok('tekst zaszyfrowany i odszyfrowany wraca bez zmian (polskie znaki)', S.odszyfrujTekst(kl, tekst) === json);
  const surowe = Buffer.from(tekst.slice(5), 'base64').toString('latin1');
  ok('w zaszyfrowanym tekście nie ma PESEL-u, imienia ani adresu (ani jako tekst, ani jako base64)', !tekst.includes('90010112349') && !surowe.includes('90010112349') && !surowe.includes('Testowa') && !surowe.includes('Gęślą'));
  ok('dwa zapisy tych samych danych dają różny szyfrogram (losowy wektor)', S.szyfrujTekst(kl, json) !== tekst);
  const koperta = S.szyfruj(kl, new TextEncoder().encode('tajne')); let wykryte = true;
  for (let i = 0; i < koperta.length; i++) { const z = koperta.slice(); z[i] ^= 1; if (S.odszyfruj(kl, z) !== null) { wykryte = false; bl = 'bajt ' + i; break; } }
  ok('zmiana DOWOLNEGO bajtu koperty (nagłówek, wektor, treść, podpis) jest wykrywana', wykryte, bl);
  ok('obcięta koperta i śmieci są odrzucane', S.odszyfruj(kl, koperta.slice(0, koperta.length - 1)) === null && S.odszyfruj(kl, losowe(100)) === null && S.odszyfruj(kl, new Uint8Array(0)) === null);
  ok('zły klucz nie odszyfruje', S.odszyfruj(S.klucze(losowe(32)), koperta) === null && S.odszyfrujTekst(S.klucze(losowe(32)), tekst) === null);
  ok('pusty tekst da się zaszyfrować i odczytać', S.odszyfrujTekst(kl, S.szyfrujTekst(kl, '')) === '');
  const duzy = losowe(1048576); t0 = Date.now(); const dk = S.szyfruj(kl, duzy); const msSz = Date.now() - t0; t0 = Date.now(); const dd = S.odszyfruj(kl, dk); const msOd = Date.now() - t0;
  ok('1 MB: szyfrowanie i odszyfrowanie poprawne i szybkie (zapis profilu nie przycina strony)', dd && hex(dd) === hex(duzy) && msSz < 1500 && msOd < 1500, `${msSz} ms / ${msOd} ms`);
  /* sejf z hasłem (localStorage / sessionStorage w pamięci) */
  const mag = () => { const m = new Map(); return { getItem: k => m.has(k) ? m.get(k) : null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k) }; };
  globalThis.localStorage = mag(); globalThis.sessionStorage = mag();
  ok('nowe konto nie ma sejfu', S.maSejf('12345') === false);
  const dek1 = await S.utworzSejf('12345', 'haslo123');
  const zapisany = localStorage.getItem('pmt-web-sejf:12345');
  ok('sejf zapisany na dysku NIE zawiera ani hasła, ani klucza danych jawnie', S.maSejf('12345') && !zapisany.includes('haslo123') && !zapisany.includes(S.b64(dek1)) && !zapisany.includes(hex(dek1)));
  const otw = await S.otworzSejf('12345', 'haslo123');
  ok('dobre hasło otwiera sejf i daje ten sam klucz danych', otw && hex(otw) === hex(dek1));
  ok('złe hasło (też o jeden znak inne, inna wielkość liter) NIE otwiera sejfu', (await S.otworzSejf('12345', 'haslo124')) === null && (await S.otworzSejf('12345', 'Haslo123')) === null && (await S.otworzSejf('12345', '')) === null);
  ok('sejf konta A nie otwiera się hasłem konta B ani na odwrót', (await S.otworzSejf('99999', 'haslo123')) === null);
  const dane = S.szyfrujTekst(S.klucze(dek1), json);
  await S.przepiszSejf('12345', dek1, 'nowehaslo9');
  const po = await S.otworzSejf('12345', 'nowehaslo9');
  ok('po zmianie hasła nowe hasło otwiera sejf, a STARE już nie', po && hex(po) === hex(dek1) && (await S.otworzSejf('12345', 'haslo123')) === null);
  ok('po zmianie hasła dane zaszyfrowane wcześniej nadal da się odczytać (przepisany został tylko klucz)', S.odszyfrujTekst(S.klucze(po), dane) === json);
  const m = JSON.parse(localStorage.getItem('pmt-web-sejf:12345')); m.dek = S.b64((() => { const b = S.unb64(m.dek); b[30] ^= 1; return b; })()); localStorage.setItem('pmt-web-sejf:12345', JSON.stringify(m));
  ok('uszkodzony sejf nie otwiera się (zamiast oddać śmieci)', (await S.otworzSejf('12345', 'nowehaslo9')) === null);
  S.zapamietajKlucz(dek1); ok('klucz na czas sesji karty: zapis i odczyt', hex(S.odczytajKlucz()) === hex(dek1)); S.zapomnijKlucz(); ok('po wylogowaniu klucza w sesji nie ma', S.odczytajKlucz() === null);
  S.usunSejf('12345'); ok('usunięcie sejfu', !S.maSejf('12345'));
  process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
