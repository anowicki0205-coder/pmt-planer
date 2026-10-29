// Sprawdzanie podpisów elektronicznych (js/weryfikacja.js) na PRAWDZIWYCH podpisanych PDF-ach (pyHanko: dane/podpisy/, utworzone przez dane/generuj_podpisy.py) i plikach XAdES.
// Test działa w przeglądarce (potrzebny DOMParser i WebCrypto). Dodatkowo poppler (pdfsig) niezależnie ocenia te same pliki.
// NODE_PATH=/opt/node22/lib/node_modules node weryfikacja_test.js
const { chromium } = require('playwright'); const { serwer } = require('./wspolne'); const fs = require('fs'), path = require('path'), cp = require('child_process');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const kat = path.join(__dirname, 'dane/podpisy'), b64 = f => fs.readFileSync(path.join(kat, f)).toString('base64');
  const sv = await serwer({}); const b = await chromium.launch(); const p = await b.newPage(); if (process.env.BEZ_WEBCRYPTO) await p.addInitScript(() => { Object.defineProperty(Crypto.prototype, 'subtle', { get() { return undefined; } }); });      // BEZ_WEBCRYPTO=1: jak strona na zwykłym http — sprawdzanie podpisów musi działać na własnej kryptografii
  await p.route('**/__pusta.html', r => r.fulfill({ contentType: 'text/html', body: '<!doctype html><title>t</title>' })); await p.goto(sv.adres + '/__pusta.html');
  if (process.env.BEZ_WEBCRYPTO) ok('tryb bez Web Crypto: w stronie nie ma crypto.subtle (sprawdzanie idzie na własnej kryptografii)', await p.evaluate(() => typeof crypto.subtle) === 'undefined');
  const oceń = (plik, opcje = {}) => p.evaluate(async ([plik, dane, opcje]) => {
    const m = await import('/js/weryfikacja.js'); const bin = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
    const wej = { imie: opcje.imie || 'Jan Testowy', pesel: opcje.pesel || '90010112349', oryginal: bin(dane.oryg) };
    if (/\.xades$/.test(plik)) wej.xades = new TextDecoder().decode(bin(dane.plik)); else wej.bajty = bin(dane.plik);
    return m.ocenPodpisElektroniczny(wej);
  }, [plik, { oryg: b64('oryg.pdf'), plik: b64(plik) }, opcje]);
  const k = (r, id) => (r.kontrole.filter(x => x.id === id).pop() || {}).stan;
  const opis = r => r.kontrole.map(x => `${x.id}:${x.stan}`).join(' ');

  let r = await oceń('ok_jan.pdf');
  ok('poprawny podpis Jana: wszystko na zielono', r.stan === 'ok' && r.rodzaj === 'PAdES' && r.sygnatariusz === 'Jan Testowy', opis(r));
  ok('  …podpis obejmuje cały dokument, skrót się zgadza, kryptografia poprawna, to ten sam dokument', k(r, 'calosc') === 'ok' && k(r, 'skrot') === 'ok' && k(r, 'kryptografia') === 'ok' && k(r, 'dokument') === 'ok');
  ok('  …imię i nazwisko oraz PESEL zgadzają się z dokumentem, jest czas podpisu', k(r, 'osoba') === 'ok' && k(r, 'pesel') === 'ok' && !!r.czas && /Testowe Centrum/.test(r.wystawca), JSON.stringify([r.czas, r.wystawca]));
  r = await oceń('ok_jan.pdf', { imie: 'Testowy Jan' });
  ok('kolejność imienia i nazwiska nie ma znaczenia', k(r, 'osoba') === 'ok');
  r = await oceń('inna_osoba.pdf');
  ok('podpis INNEJ osoby (Anna Kowalska) jest odrzucony z nazwiskiem podpisującej', r.stan === 'zle' && k(r, 'osoba') === 'zle' && /Anna Kowalska/.test(r.kontrole.find(x => x.id === 'osoba').tekst), r.kontrole.find(x => x.id === 'osoba').tekst);
  r = await oceń('inny_pesel.pdf');
  ok('to samo imię i nazwisko, ale INNY PESEL w certyfikacie — odrzucone', r.stan === 'zle' && k(r, 'pesel') === 'zle', opis(r));
  r = await oceń('bez_pesela_w_certyfikacie.pdf');
  ok('certyfikat bez PESEL-u: osoba ok, bez uwag o PESEL-u (nie ma czego porównać)', r.stan === 'ok' && k(r, 'osoba') === 'ok' && k(r, 'pesel') === undefined, opis(r));
  r = await oceń('zmieniony_po_podpisie.pdf');
  ok('dokument zmieniony po podpisaniu (jeden bajt) — wykryte przez skrót', r.stan === 'zle' && k(r, 'skrot') === 'zle', opis(r));
  r = await oceń('dopisek_po_podpisie.pdf');
  ok('dane dopisane po podpisie — podpis nie obejmuje całego pliku', r.stan === 'zle' && k(r, 'calosc') === 'zle', opis(r));
  r = await oceń('ecdsa_jan.pdf');
  ok('podpis ECDSA (krzywa P-256) też jest sprawdzany matematycznie', r.stan === 'ok' && k(r, 'kryptografia') === 'ok', opis(r));
  r = await oceń('dwa_podpisy.pdf');
  ok('dwa podpisy (Jan, potem Anna): znajduje podpis właściwej osoby; wcześniejszy podpis nie musi obejmować całości', r.stan === 'ok' && r.sygnatariusz === 'Jan Testowy' && /Są 2 podpisy/.test(r.kontrole[0].tekst), opis(r));
  r = await oceń('przepisany.pdf');
  ok('PDF zapisany na nowo przy podpisywaniu: rozpoznany po strumieniach treści', k(r, 'dokument') === 'ok' && r.stan === 'ok', r.kontrole.find(x => x.id === 'dokument').tekst);
  r = await oceń('pole_bez_podpisu.pdf');
  ok('PDF bez podpisu (puste pole) — odrzucony z wyjaśnieniem', r.stan === 'zle' && r.rodzaj === 'brak' && /nie ma podpisu/.test(r.kontrole[0].tekst), r.kontrole[0].tekst);
  r = await oceń('oryg.pdf');
  ok('zwykły niepodpisany PDF — odrzucony', r.stan === 'zle' && r.rodzaj === 'brak');

  // XAdES
  r = await oceń('ok.xades');
  ok('XAdES (kanonizacja wyłączna): skrót dokumentu, podpis i osoba zgadzają się', r.stan === 'ok' && r.rodzaj === 'XAdES' && k(r, 'dokument') === 'ok' && k(r, 'kryptografia') === 'ok' && k(r, 'osoba') === 'ok', opis(r));
  r = await oceń('ok_c14n_klasyczna.xades');
  ok('XAdES (kanonizacja klasyczna C14N 1.0) też', r.stan === 'ok' && k(r, 'kryptografia') === 'ok', opis(r));
  r = await oceń('zly_skrot.xades');
  ok('XAdES dotyczący innego pliku — odrzucony', r.stan === 'zle' && k(r, 'dokument') === 'zle', opis(r));
  r = await oceń('zepsuty_podpis.xades');
  ok('XAdES z naruszoną wartością podpisu — odrzucony', r.stan === 'zle' && k(r, 'kryptografia') === 'zle', opis(r));

  // niezależna kontrola: poppler widzi te same pliki tak samo
  const pdfsig = f => cp.spawnSync('pdfsig', [path.join(kat, f)], { encoding: 'utf8' }).stdout;
  ok('poppler (pdfsig) potwierdza: ok_jan.pdf poprawny, zmieniony_po_podpisie.pdf = „Digest Mismatch”', /Signature is Valid/.test(pdfsig('ok_jan.pdf')) && /Digest Mismatch/.test(pdfsig('zmieniony_po_podpisie.pdf')));
  console.log('  błędy:', 0); await b.close(); sv.s.close();
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
