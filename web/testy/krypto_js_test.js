// Własna kryptografia do sprawdzania podpisów (js/krypto_js.js) — używana na stronie bez https, gdzie nie ma Web Crypto.
// Porównanie z Web Crypto z Node 22: skróty (wektory znane i losowe), podpisy RSA (PKCS#1 v1.5 i PSS), ECDSA (P-256/384/521) — poprawne muszą wyjść „prawda”, zmienione „fałsz”.
// Uruchom: node krypto_js_test.js
(async () => {
  const { skrotJs, kryptoJs } = await import('../js/krypto_js.js'); const subtle = globalThis.crypto.subtle;
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join(''), losowe = n => { const b = new Uint8Array(n); for (let i = 0; i < n; i += 65536) crypto.getRandomValues(b.subarray(i, Math.min(n, i + 65536))); return b; };
  const enc = new TextEncoder();

  /* ---- skróty ---- */
  const wektory = { 'SHA-1': 'a9993e364706816aba3e25717850c26c9cd0d89d', 'SHA-256': 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    'SHA-384': 'cb00753f45a35e8bb5a03d699ac65007272c32ab0eded1631a8b605a43ff5bed8086072ba1e7cc2358baeca134c825a7',
    'SHA-512': 'ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f' };
  for (const [a, w] of Object.entries(wektory)) ok(`${a}("abc") zgodny ze wzorcem z norm FIPS`, hex(skrotJs(a, enc.encode('abc'))) === w);
  for (const a of Object.keys(wektory)) {
    let zgodne = true, bledny = '';
    for (const n of [0, 1, 55, 56, 63, 64, 65, 111, 112, 119, 120, 127, 128, 129, 1000, 70001]) {      // długości na granicach bloków i dopełnienia
      const d = losowe(n); if (hex(skrotJs(a, d)) !== hex(await subtle.digest(a, d))) { zgodne = false; bledny = String(n); break; }
    }
    ok(`${a}: zgodny z Web Crypto dla wiadomości o długościach na granicach bloków`, zgodne, bledny && 'różnica przy długości ' + bledny);
  }
  const duzy = losowe(3 * 1048576); let t0 = performance.now(); skrotJs('SHA-256', duzy); const ms256 = performance.now() - t0;
  ok('SHA-256 policzy 3 MB w rozsądnym czasie (typowy PDF to kilkadziesiąt KB)', ms256 < 3000, Math.round(ms256) + ' ms');

  /* ---- RSA ---- */
  const dane = enc.encode('Polecenie wyjazdu służbowego — treść do podpisania'), inne = enc.encode('Polecenie wyjazdu służbowego — treść do podpisania!');
  const rsa = await subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['sign', 'verify']);
  const rsaPss = await subtle.generateKey({ name: 'RSA-PSS', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['sign', 'verify']);
  const spkiRsa = await subtle.exportKey('spki', rsa.publicKey), spkiPss = await subtle.exportKey('spki', rsaPss.publicKey);
  for (const hash of ['SHA-1', 'SHA-256', 'SHA-384', 'SHA-512']) {
    const k = await subtle.importKey('pkcs8', await subtle.exportKey('pkcs8', rsa.privateKey), { name: 'RSASSA-PKCS1-v1_5', hash }, false, ['sign']);
    const podpis = new Uint8Array(await subtle.sign('RSASSA-PKCS1-v1_5', k, dane)), pub = await kryptoJs.importKey('spki', spkiRsa, { name: 'RSASSA-PKCS1-v1_5', hash }, false, ['verify']);
    const zly = podpis.slice(); zly[100] ^= 1;
    ok(`RSA PKCS#1 v1.5 ${hash}: poprawny podpis ✓, zmieniona treść ✗, zmieniony podpis ✗`, await kryptoJs.verify('RSASSA-PKCS1-v1_5', pub, podpis, dane) === true && await kryptoJs.verify('RSASSA-PKCS1-v1_5', pub, podpis, inne) === false && await kryptoJs.verify('RSASSA-PKCS1-v1_5', pub, zly, dane) === false);
  }
  for (const [hash, sol] of [['SHA-1', 20], ['SHA-256', 32], ['SHA-256', 0], ['SHA-384', 48], ['SHA-512', 64]]) {
    const k = await subtle.importKey('pkcs8', await subtle.exportKey('pkcs8', rsaPss.privateKey), { name: 'RSA-PSS', hash }, false, ['sign']);
    const podpis = new Uint8Array(await subtle.sign({ name: 'RSA-PSS', saltLength: sol }, k, dane)), pub = await kryptoJs.importKey('spki', spkiPss, { name: 'RSA-PSS', hash }, false, ['verify']);
    const zly = podpis.slice(); zly[50] ^= 4;
    ok(`RSA-PSS ${hash}, sól ${sol} B: poprawny ✓, zmieniona treść ✗, zmieniony podpis ✗, zła długość soli ✗`, await kryptoJs.verify({ name: 'RSA-PSS', saltLength: sol }, pub, podpis, dane) === true && await kryptoJs.verify({ name: 'RSA-PSS', saltLength: sol }, pub, podpis, inne) === false
      && await kryptoJs.verify({ name: 'RSA-PSS', saltLength: sol }, pub, zly, dane) === false && await kryptoJs.verify({ name: 'RSA-PSS', saltLength: sol + 1 }, pub, podpis, dane) === false);
  }
  /* ---- ECDSA ---- */
  for (const [krzywa, hashe] of [['P-256', ['SHA-1', 'SHA-256', 'SHA-384', 'SHA-512']], ['P-384', ['SHA-256', 'SHA-384', 'SHA-512']], ['P-521', ['SHA-256', 'SHA-512']]]) {
    const para = await subtle.generateKey({ name: 'ECDSA', namedCurve: krzywa }, true, ['sign', 'verify']), spki = await subtle.exportKey('spki', para.publicKey);
    for (const hash of hashe) {
      let wszystkie = true, t = performance.now();
      for (let n = 0; n < 6; n++) {
        const d = losowe(40 + n * 997), podpis = new Uint8Array(await subtle.sign({ name: 'ECDSA', hash }, para.privateKey, d)), pub = await kryptoJs.importKey('spki', spki, { name: 'ECDSA', namedCurve: krzywa }, false, ['verify']);
        const zly = podpis.slice(); zly[5] ^= 8; const d2 = d.slice(); d2[0] ^= 1;
        if (!(await kryptoJs.verify({ name: 'ECDSA', hash }, pub, podpis, d)) || await kryptoJs.verify({ name: 'ECDSA', hash }, pub, podpis, d2) || await kryptoJs.verify({ name: 'ECDSA', hash }, pub, zly, d)) { wszystkie = false; break; }
      }
      ok(`ECDSA ${krzywa} ${hash}: 6 losowych podpisów ✓, zmieniona treść ✗, zmieniony podpis ✗`, wszystkie, Math.round((performance.now() - t) / 6) + ' ms na komplet 3 sprawdzeń');
    }
  }
  const innaPara = await subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']), p1 = await subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  const podpisInny = new Uint8Array(await subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, p1.privateKey, dane)), cudzy = await kryptoJs.importKey('spki', await subtle.exportKey('spki', innaPara.publicKey), { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']);
  ok('podpis złożony INNYM kluczem nie przechodzi', await kryptoJs.verify({ name: 'ECDSA', hash: 'SHA-256' }, cudzy, podpisInny, dane) === false);
  const spkiZly = new Uint8Array(await subtle.exportKey('spki', innaPara.publicKey)); spkiZly[spkiZly.length - 1] ^= 1;
  let blad = ''; try { await kryptoJs.importKey('spki', spkiZly, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']); } catch (e) { blad = e.message; }
  ok('klucz publiczny leżący poza krzywą jest odrzucany już przy wczytaniu', /nie leży na krzywej/.test(blad), blad);
  let brak = ''; try { await kryptoJs.verify({ name: 'HMAC' }, cudzy, podpisInny, dane); } catch (e) { brak = e.message; }
  ok('nieobsługiwany algorytm to błąd z komunikatem, nie cichy „ok”', /nieobsługiwany/.test(brak), brak);
  process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
