// PMT Planer (web) — sprawdzanie podpisów elektronicznych po stronie przeglądarki (nic nie opuszcza urządzenia).
//   • PAdES: podpis wbudowany w PDF (/ByteRange + /Contents, CMS/PKCS#7),
//   • XAdES: osobny plik podpisu obok dokumentu (.xades / .xml).
// Sprawdzamy: czy podpis jest, czy obejmuje CAŁY plik, czy plik nie został zmieniony po podpisaniu (skrót), czy sam podpis jest matematycznie poprawny (klucz z certyfikatu),
// kto podpisał (imię i nazwisko, PESEL, jeśli certyfikat go zawiera) i kiedy. NIE sprawdzamy zaufania do urzędu certyfikacji (łańcucha do certyfikatu głównego) — to robi
// urzędowy walidator; aplikacja pokazuje wystawcę certyfikatu, żeby można to ocenić. Czyste funkcje (bez interfejsu), działają w przeglądarce i w Node 22.

import { zawieraOryginal } from './pliki.js';
import { kryptoJs } from './krypto_js.js';

/* ---------------------------------- DER (ASN.1) ---------------------------------- */
function tlv(b, p) {
  if (p + 2 > b.length) throw new Error('uszkodzony podpis (ASN.1)');
  const tag = b[p]; let l = b[p + 1], h = 2;
  if (l & 0x80) {
    const n = l & 0x7f;
    if (n === 0 || n > 4) throw new Error('nieobsługiwany zapis długości (ASN.1)');
    l = 0; for (let i = 0; i < n; i++) l = l * 256 + b[p + 2 + i]; h = 2 + n;
  }
  const start = p + h, end = start + l;
  if (end > b.length) throw new Error('uszkodzony podpis (obcięte dane)');
  return { tag, p, start, end };
}
const dzieci = (b, n) => { const w = []; let p = n.start; while (p < n.end) { const c = tlv(b, p); w.push(c); p = c.end; } return w; };
const tresc = (b, n) => b.subarray(n.start, n.end);
const surowe = (b, n) => b.subarray(n.p, n.end);
function oid(b, n) {
  const t = tresc(b, n); if (!t.length) return '';
  const w = [Math.floor(t[0] / 40), t[0] % 40]; let v = 0;
  for (let i = 1; i < t.length; i++) { v = v * 128 + (t[i] & 0x7f); if (!(t[i] & 0x80)) { w.push(v); v = 0; } }
  return w.join('.');
}
function tekstDer(b, n) {
  const t = tresc(b, n);
  if (n.tag === 0x1e) { let s = ''; for (let i = 0; i + 1 < t.length; i += 2) s += String.fromCharCode(t[i] * 256 + t[i + 1]); return s; }
  if (n.tag === 0x0c) return new TextDecoder('utf-8').decode(t);
  return new TextDecoder('latin1').decode(t);
}
function czasDer(b, n) {
  const s = new TextDecoder('latin1').decode(tresc(b, n)); let m;
  if (n.tag === 0x17 && (m = s.match(/^(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)?Z$/))) { const r = Number(m[1]); return new Date(Date.UTC(r < 50 ? 2000 + r : 1900 + r, m[2] - 1, m[3], m[4], m[5], m[6] || 0)); }
  if (n.tag === 0x18 && (m = s.match(/^(\d{4})(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)?/))) return new Date(Date.UTC(m[1], m[2] - 1, m[3], m[4], m[5], m[6] || 0));
  return null;
}
const liczbaDer = (b, n) => { const t = tresc(b, n); let v = 0; for (const x of t) v = v * 256 + x; return v; };

const NAZWY_ATRYBUTOW = { '2.5.4.3': 'CN', '2.5.4.4': 'SN', '2.5.4.5': 'serialNumber', '2.5.4.6': 'C', '2.5.4.7': 'L', '2.5.4.8': 'ST', '2.5.4.10': 'O', '2.5.4.11': 'OU', '2.5.4.42': 'givenName', '2.5.4.97': 'organizationIdentifier' };
function nazwaDer(b, n) {
  const w = {};
  for (const rdn of dzieci(b, n)) for (const atv of dzieci(b, rdn)) {
    const [o, v] = dzieci(b, atv), k = NAZWY_ATRYBUTOW[oid(b, o)] || oid(b, o);
    (w[k] = w[k] || []).push(tekstDer(b, v));
  }
  return w;
}
const pierwszy = (w, k) => (w[k] && w[k][0]) || '';

/* ---------------------------------- certyfikat X.509 ---------------------------------- */
export function certyfikat(b) {
  const c = tlv(b, 0), [tbs] = dzieci(b, c), p = dzieci(b, tbs);
  let i = 0; if (p[0].tag === 0xa0) i = 1;           // wersja
  const serial = p[i], wystawca = p[i + 2], waznosc = p[i + 3], podmiot = p[i + 4], spki = p[i + 5];
  const [od, doo] = dzieci(b, waznosc);
  return { serial: surowe(b, serial), wystawcaSurowy: surowe(b, wystawca), spki: surowe(b, spki), spkiWezly: dzieci(b, spki),
    podmiot: nazwaDer(b, podmiot), wystawca: nazwaDer(b, wystawca), od: czasDer(b, od), do: czasDer(b, doo), bajty: b, ski: skiZRozszerzen(b, p.slice(i + 6)) };
}
function skiZRozszerzen(b, reszta) {
  try {
    const rozsz = reszta.find(x => x.tag === 0xa3); if (!rozsz) return null;
    for (const e of dzieci(b, dzieci(b, rozsz)[0])) {
      const [o, ...pozost] = dzieci(b, e); if (oid(b, o) !== '2.5.29.14') continue;
      const oct = pozost[pozost.length - 1], wew = tlv(b, oct.start); return tresc(b, wew);
    }
  } catch (e) { /* bez SKI */ }
  return null;
}
const rowne = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
/** Rodzaj klucza publicznego z certyfikatu: { oid (RSA albo EC), krzywa (OID krzywej dla EC) }. */
function rodzajKlucza(c) { const [o, par] = dzieci(c.bajty, c.spkiWezly[0]); return { oid: oid(c.bajty, o), krzywa: par ? oid(c.bajty, par) : '' }; }

/* ---------------------------------- CMS (PKCS#7) SignedData ---------------------------------- */
const HASHE = { '1.3.14.3.2.26': 'SHA-1', '2.16.840.1.101.3.4.2.1': 'SHA-256', '2.16.840.1.101.3.4.2.2': 'SHA-384', '2.16.840.1.101.3.4.2.3': 'SHA-512' };
const SIG_HASH = { '1.2.840.113549.1.1.5': 'SHA-1', '1.2.840.113549.1.1.11': 'SHA-256', '1.2.840.113549.1.1.12': 'SHA-384', '1.2.840.113549.1.1.13': 'SHA-512',
  '1.2.840.10045.4.1': 'SHA-1', '1.2.840.10045.4.3.2': 'SHA-256', '1.2.840.10045.4.3.3': 'SHA-384', '1.2.840.10045.4.3.4': 'SHA-512' };
const KRZYWE = { '1.2.840.10045.3.1.7': ['P-256', 32], '1.3.132.0.34': ['P-384', 48], '1.3.132.0.35': ['P-521', 66] };

export function cms(b) {
  const ci = tlv(b, 0), [typ, jawny] = dzieci(b, ci);
  if (oid(b, typ) !== '1.2.840.113549.1.7.2') throw new Error('to nie jest podpis CMS');
  const sd = dzieci(b, tlv(b, jawny.start)), certy = [];
  let podpisujacy = null;
  for (const x of sd) {
    if (x.tag === 0xa0) for (const c of dzieci(b, x)) { try { certy.push(certyfikat(surowe(b, c))); } catch (e) { /* inny rodzaj certyfikatu — pomijam */ } }
  }
  const si = sd[sd.length - 1]; if (si.tag !== 0x31) throw new Error('brak danych podpisującego');
  const [info] = dzieci(b, si); if (!info) throw new Error('brak podpisującego');
  const p = dzieci(b, info); let i = 1;
  const sid = p[i++], algSkrotu = p[i++]; let atrybuty = null;
  if (p[i].tag === 0xa0) atrybuty = p[i++];
  const algPodpisu = p[i++], podpis = p[i++];
  const skrotOid = oid(b, dzieci(b, algSkrotu)[0]), podpisOid = oid(b, dzieci(b, algPodpisu)[0]);
  const wynik = { certy, skrot: HASHE[skrotOid] || null, skrotOid, podpisOid, algPodpisu: dzieci(b, algPodpisu), podpis: tresc(b, podpis), atrybuty: null, wiadomosc: null, czas: null, b, sid };
  if (atrybuty) {
    const surAtr = surowe(b, atrybuty).slice(); surAtr[0] = 0x31;      // do weryfikacji atrybuty podpisuje się jako SET, nie [0]
    wynik.atrybuty = surAtr;
    for (const a of dzieci(b, atrybuty)) {
      const [o, zb] = dzieci(b, a), id = oid(b, o), v = dzieci(b, zb)[0];
      if (id === '1.2.840.113549.1.9.4') wynik.wiadomosc = tresc(b, v).slice();
      else if (id === '1.2.840.113549.1.9.5') wynik.czas = czasDer(b, v);
    }
  }
  // certyfikat podpisującego: po wystawcy i numerze seryjnym albo po identyfikatorze klucza
  if (sid.tag === 0x30) {
    const [wyst, ser] = dzieci(b, sid), w = surowe(b, wyst), s = surowe(b, ser);
    podpisujacy = certy.find(c => rowne(c.wystawcaSurowy, w) && rowne(c.serial, s)) || null;
  } else if (sid.tag === 0x80) {
    const ski = tresc(b, sid); podpisujacy = certy.find(c => c.ski && rowne(c.ski, ski)) || null;
  }
  wynik.cert = podpisujacy || (certy.length === 1 ? certy[0] : null);
  return wynik;
}

/* ---------------------------------- kryptografia (WebCrypto) ---------------------------------- */
/** Web Crypto, a na stronie bez https (zwykłe http) — własna kryptografia z krypto_js.js (te same wyniki, tylko wolniej). */
const sub = () => (typeof crypto !== 'undefined' && crypto.subtle) || kryptoJs;
export async function skrot(alg, bajty) { const s = sub(); if (!s) throw new Error('brak WebCrypto'); return new Uint8Array(await s.digest(alg, bajty)); }
function derNaRaw(b, dl) {            // podpis ECDSA w CMS (SEQ r, s) → postać „r||s”, której oczekuje WebCrypto
  const [r, s] = dzieci(b, tlv(b, 0)), cz = n => { let t = tresc(b, n); while (t.length > dl && t[0] === 0) t = t.subarray(1); const o = new Uint8Array(dl); o.set(t, dl - t.length); return o; };
  const w = new Uint8Array(2 * dl); w.set(cz(r), 0); w.set(cz(s), dl); return w;
}
/** Czy podpis (CMS) jest poprawny matematycznie dla klucza z certyfikatu: true / false / null (nie umiem tego sprawdzić) + powód. */
async function sprawdzPodpisCms(c) {
  const s = sub();
  if (!c.cert) return { ok: null, powod: 'w podpisie nie ma certyfikatu podpisującego' };
  const dane = c.atrybuty || null;
  if (!dane) return { ok: null, powod: 'podpis bez atrybutów — nieobsługiwany' };
  const { oid: kluczOid, krzywa: krzywaOid } = rodzajKlucza(c.cert);
  const skr = c.skrot || 'SHA-256', spki = c.cert.spki;
  try {
    if (kluczOid === '1.2.840.113549.1.1.1') {          // RSA
      if (c.podpisOid === '1.2.840.113549.1.1.10') {      // RSASSA-PSS
        const par = dzieci(c.b, c.algPodpisu[1] || { start: 0, end: 0 }); let hash = 'SHA-1', sol = 20;
        for (const x of par) {
          if (x.tag === 0xa0) hash = HASHE[oid(c.b, dzieci(c.b, tlv(c.b, x.start))[0])] || hash;
          if (x.tag === 0xa2) sol = liczbaDer(c.b, tlv(c.b, x.start));
        }
        const klucz = await s.importKey('spki', spki, { name: 'RSA-PSS', hash }, false, ['verify']);
        return { ok: await s.verify({ name: 'RSA-PSS', saltLength: sol }, klucz, c.podpis, dane) };
      }
      const hash = SIG_HASH[c.podpisOid] || skr, klucz = await s.importKey('spki', spki, { name: 'RSASSA-PKCS1-v1_5', hash }, false, ['verify']);
      return { ok: await s.verify('RSASSA-PKCS1-v1_5', klucz, c.podpis, dane) };
    }
    if (kluczOid === '1.2.840.10045.2.1') {             // ECDSA
      const [krzywa, dl] = KRZYWE[krzywaOid] || []; if (!krzywa) return { ok: null, powod: 'nieobsługiwana krzywa eliptyczna' };
      const hash = SIG_HASH[c.podpisOid] || skr, klucz = await s.importKey('spki', spki, { name: 'ECDSA', namedCurve: krzywa }, false, ['verify']);
      return { ok: await s.verify({ name: 'ECDSA', hash }, klucz, derNaRaw(c.podpis, dl), dane) };
    }
    return { ok: null, powod: 'nieobsługiwany rodzaj klucza (' + kluczOid + ')' };
  } catch (e) { return { ok: null, powod: 'nie udało się zweryfikować podpisu: ' + e.message }; }
}

/* ---------------------------------- PAdES: podpisy w PDF ---------------------------------- */
const latin1 = b => new TextDecoder('latin1').decode(b);
function hexNaBajty(s) {
  s = s.replace(/[^0-9a-fA-F]/g, ''); if (s.length % 2) s += '0';
  const o = new Uint8Array(s.length / 2); for (let i = 0; i < o.length; i++) o[i] = parseInt(s.substr(i * 2, 2), 16); return o;
}
/** Wszystkie podpisy wbudowane w PDF: [{ zakres: [a,b,c,d], cms: Uint8Array, calosc: bool }]. */
export function podpisyWPdf(bajty) {
  const t = latin1(bajty), re = /\/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]/g, w = []; let m;
  while ((m = re.exec(t))) {
    const [a, b, c, d] = m.slice(1).map(Number);
    if (a !== 0 || b <= 0 || c <= a + b || c + d > bajty.length + 2 || d < 0) continue;
    let hex = t.slice(a + b, c).trim(); if (hex[0] !== '<' || hex[hex.length - 1] !== '>') continue;
    const cmsBajty = hexNaBajty(hex.slice(1, -1)); if (cmsBajty.length < 20 || cmsBajty[0] !== 0x30) continue;      // pusty znacznik miejsca na podpis
    w.push({ zakres: [a, b, c, d], cms: cmsBajty, calosc: c + d >= bajty.length - 2 });
  }
  return w;
}
const polacz = (a, b) => { const o = new Uint8Array(a.length + b.length); o.set(a, 0); o.set(b, a.length); return o; };

/** Pełne sprawdzenie jednego podpisu PAdES. */
export async function sprawdzPades(bajty, p) {
  const w = { rodzaj: 'PAdES', calosc: p.calosc, skrot: null, podpis: null, powody: [], czas: null, podmiot: {}, wystawca: {}, od: null, do: null };
  let c;
  try { c = cms(p.cms); } catch (e) { w.powody.push('nie umiem odczytać podpisu: ' + e.message); w.blad = true; return w; }
  if (c.cert) { w.podmiot = c.cert.podmiot; w.wystawca = c.cert.wystawca; w.od = c.cert.od; w.do = c.cert.do; }
  w.czas = c.czas;
  const [a, b, cc, d] = p.zakres, dane = polacz(bajty.subarray(a, a + b), bajty.subarray(cc, cc + d));
  if (!c.skrot) { w.powody.push('nieobsługiwany algorytm skrótu'); return w; }
  if (c.wiadomosc) { try { const s = await skrot(c.skrot, dane); w.skrot = rowne(s, c.wiadomosc); } catch (e) { w.skrot = null; w.powody.push(e.message); } }
  const kr = await sprawdzPodpisCms(c);
  w.podpis = kr.ok; if (kr.powod) w.powody.push(kr.powod);
  return w;
}

/* ---------------------------------- XAdES: osobny plik podpisu ---------------------------------- */
const NS_DS = 'http://www.w3.org/2000/09/xmldsig#';
const base64 = s => { const t = atob(s.replace(/\s+/g, '')), o = new Uint8Array(t.length); for (let i = 0; i < t.length; i++) o[i] = t.charCodeAt(i); return o; };
const HASH_XML = { 'http://www.w3.org/2000/09/xmldsig#sha1': 'SHA-1', 'http://www.w3.org/2001/04/xmlenc#sha256': 'SHA-256', 'http://www.w3.org/2001/04/xmldsig-more#sha384': 'SHA-384', 'http://www.w3.org/2001/04/xmlenc#sha512': 'SHA-512' };
const SIG_XML = { 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256': 'SHA-256', 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha384': 'SHA-384', 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha512': 'SHA-512', 'http://www.w3.org/2000/09/xmldsig#rsa-sha1': 'SHA-1',
  'http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256': 'SHA-256', 'http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha384': 'SHA-384', 'http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha512': 'SHA-512' };

/* kanonizacja XML (C14N 1.0 i wyłączna, bez komentarzy) w zakresie potrzebnym do SignedInfo */
const ucTekst = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\r/g, '&#xD;');
const ucAtr = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;').replace(/\t/g, '&#x9;').replace(/\n/g, '&#xA;').replace(/\r/g, '&#xD;');
const jestNs = a => a.name === 'xmlns' || a.name.startsWith('xmlns:');
function nsWZasiegu(el) {
  const m = new Map();
  for (let e = el; e && e.nodeType === 1; e = e.parentNode) for (const a of e.attributes) if (jestNs(a)) { const p = a.name === 'xmlns' ? '' : a.name.slice(6); if (!m.has(p)) m.set(p, a.value); }
  return m;
}
/** rodzic: przedrostki → adresy już wypisane przez najbliższego przodka w wyniku kanonizacji. */
function kanon(el, wylaczna, rodzic) {
  const zasieg = nsWZasiegu(el), atr = [...el.attributes].filter(a => !jestNs(a));
  const kandydaci = new Set(wylaczna ? [el.prefix || '', ...atr.filter(a => a.prefix).map(a => a.prefix)] : zasieg.keys());
  const wyj = [];
  for (const p of [...kandydaci].sort()) {
    const u = zasieg.get(p); if (u === undefined) continue;
    if (p === '' && u === '' && (rodzic.get('') || '') === '') continue;      // pusta przestrzeń nazw domyślna nic nie zmienia
    if (rodzic.get(p) !== u) wyj.push([p, u]);
  }
  const ten = new Map(rodzic); for (const [p, u] of wyj) ten.set(p, u);
  atr.sort((x, y) => (x.namespaceURI || '').localeCompare(y.namespaceURI || '') || x.localName.localeCompare(y.localName));
  let s = '<' + el.tagName + wyj.map(([p, u]) => ` xmlns${p ? ':' + p : ''}="${ucAtr(u)}"`).join('') + atr.map(a => ` ${a.name}="${ucAtr(a.value)}"`).join('') + '>';
  for (const n of el.childNodes) {
    if (n.nodeType === 1) s += kanon(n, wylaczna, ten);
    else if (n.nodeType === 3 || n.nodeType === 4) s += ucTekst(n.nodeValue);
  }
  return s + '</' + el.tagName + '>';
}
const kanonizuj = (el, alg) => kanon(el, /xml-exc-c14n/.test(alg), new Map());

/** Czy podpis XML dotyczy tego dokumentu: skrót któregokolwiek odwołania do pliku zgadza się ze skrótem oryginału. */
export async function xadesDotyczy(tekstXml, oryginal) {
  try {
    const doc = new DOMParser().parseFromString(tekstXml, 'application/xml'); if (doc.getElementsByTagName('parsererror').length) return false;
    for (const r of doc.getElementsByTagNameNS(NS_DS, 'Reference')) {
      const alg = HASH_XML[((r.getElementsByTagNameNS(NS_DS, 'DigestMethod')[0]) || { getAttribute: () => '' }).getAttribute('Algorithm')], dv = r.getElementsByTagNameNS(NS_DS, 'DigestValue')[0];
      if (!alg || !dv || (r.getAttribute('URI') || '').startsWith('#')) continue;
      if (rowne(await skrot(alg, oryginal), base64(dv.textContent))) return true;
    }
  } catch (e) { /* bez WebCrypto lub zepsuty plik — rozpoznam po nazwie */ }
  return false;
}
export async function sprawdzXades(tekstXml, oryginal) {
  const w = { rodzaj: 'XAdES', calosc: true, skrot: null, podpis: null, powody: [], czas: null, podmiot: {}, wystawca: {}, od: null, do: null };
  const doc = new DOMParser().parseFromString(tekstXml, 'application/xml');
  if (doc.getElementsByTagName('parsererror').length) { w.powody.push('plik podpisu nie jest poprawnym XML-em'); w.blad = true; return w; }
  const pierwszyEl = (rodzic, nazwa) => rodzic.getElementsByTagNameNS(NS_DS, nazwa)[0] || null;
  const sig = doc.getElementsByTagNameNS(NS_DS, 'Signature')[0]; if (!sig) { w.powody.push('w pliku nie ma podpisu XML'); w.blad = true; return w; }
  const si = pierwszyEl(sig, 'SignedInfo'), certB64 = pierwszyEl(sig, 'X509Certificate');
  let cert = null; if (certB64) { try { cert = certyfikat(base64(certB64.textContent)); } catch (e) { w.powody.push('nie umiem odczytać certyfikatu: ' + e.message); } }
  if (cert) { w.podmiot = cert.podmiot; w.wystawca = cert.wystawca; w.od = cert.od; w.do = cert.do; }
  const t = (doc.getElementsByTagNameNS('*', 'SigningTime')[0] || {}).textContent; if (t) w.czas = new Date(t.trim());
  // czy podpis dotyczy TEGO dokumentu: skrót któregokolwiek odwołania zgadza się ze skrótem oryginału
  if (oryginal && si) {
    let zgodny = false, sprawdzono = false;
    for (const r of si.getElementsByTagNameNS(NS_DS, 'Reference')) {
      const uri = r.getAttribute('URI') || '', alg = HASH_XML[(pierwszyEl(r, 'DigestMethod') || { getAttribute: () => '' }).getAttribute('Algorithm')], dv = pierwszyEl(r, 'DigestValue');
      if (!alg || !dv || uri.startsWith('#')) continue;
      sprawdzono = true; try { if (rowne(await skrot(alg, oryginal), base64(dv.textContent))) zgodny = true; } catch (e) { w.powody.push(e.message); }
    }
    w.skrot = sprawdzono ? zgodny : null;
  }
  // sam podpis: kanonizacja SignedInfo + weryfikacja kluczem z certyfikatu
  const s = sub(), sv = pierwszyEl(sig, 'SignatureValue'), sm = si && pierwszyEl(si, 'SignatureMethod'), cm = si && pierwszyEl(si, 'CanonicalizationMethod');
  if (cert && sv && sm && cm) {
    try {
      const alg = sm.getAttribute('Algorithm'), hash = SIG_XML[alg], dane = new TextEncoder().encode(kanonizuj(si, cm.getAttribute('Algorithm'))), podpis = base64(sv.textContent);
      const { oid: kluczOid, krzywa: krzywaOid } = rodzajKlucza(cert);
      if (!hash) w.powody.push('nieobsługiwany algorytm podpisu XML');
      else if (kluczOid === '1.2.840.113549.1.1.1') w.podpis = await s.verify('RSASSA-PKCS1-v1_5', await s.importKey('spki', cert.spki, { name: 'RSASSA-PKCS1-v1_5', hash }, false, ['verify']), podpis, dane);
      else if (kluczOid === '1.2.840.10045.2.1') {
        const [krzywa] = KRZYWE[krzywaOid] || []; if (!krzywa) w.powody.push('nieobsługiwana krzywa eliptyczna');
        else w.podpis = await s.verify({ name: 'ECDSA', hash }, await s.importKey('spki', cert.spki, { name: 'ECDSA', namedCurve: krzywa }, false, ['verify']), podpis, dane);      // w XML-u podpis ECDSA jest już w postaci r||s
      } else w.powody.push('nieobsługiwany rodzaj klucza');
    } catch (e) { w.powody.push('nie udało się zweryfikować podpisu XML: ' + e.message); }
  }
  return w;
}

/* ---------------------------------- czyj to podpis ---------------------------------- */
const prosty = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/gi, 'l').toLowerCase();
const tokeny = s => prosty(s).split(/[^a-z]+/).filter(x => x.length > 1);
/** Czy podmiot certyfikatu to wskazana osoba: imię i nazwisko (kolejność dowolna) oraz PESEL, jeśli certyfikat go zawiera. → { osoba: true|false|null, pesel: true|false|null, nazwa } */
export function czyTaOsoba(imieNazwisko, pesel, podmiot) {
  const nazwy = [pierwszy(podmiot, 'CN'), (podmiot.givenName || []).join(' ') + ' ' + (podmiot.SN || []).join(' ')].filter(x => x.trim());
  const nazwa = nazwy[0] || '';
  if (!nazwy.length) return { osoba: null, pesel: null, nazwa: '' };
  const swoje = tokeny(imieNazwisko), cudze = new Set(nazwy.flatMap(tokeny));
  const osoba = swoje.length > 0 && swoje.every(t => cudze.has(t));
  const wszystko = Object.values(podmiot).flat().join(' '), m = wszystko.match(/(?:^|\D)(\d{11})(?!\d)/);
  return { osoba, pesel: m ? m[1] === String(pesel || '').replace(/\s/g, '') : null, nazwa: nazwa.replace(/\s*\(?\bPNO[A-Z]{2}-\d{11}\)?/i, '').trim() || nazwa };
}

/* ---------------------------------- skróty oryginału (czy to ten sam dokument) ---------------------------------- */
/** PDF zapisany na nowo przy podpisywaniu nie zaczyna się już od bajtów oryginału, ale zwykle zachowuje jego skompresowane strumienie — po nich poznajemy dokument. */
export function zawieraStrumienie(podpisany, oryginal) {
  const o = latin1(oryginal), p = latin1(podpisany), kawalki = []; let i = 0;
  while ((i = o.indexOf('stream', i)) >= 0 && kawalki.length < 40) {
    if (o.slice(i - 3, i) === 'end') { i += 6; continue; }
    let s = i + 6; if (o[s] === '\r') s++; if (o[s] === '\n') s++;
    const e = o.indexOf('endstream', s); if (e < 0) break;
    if (e - s > 120) kawalki.push(o.slice(s + 20, s + 100)); i = e + 9;
  }
  if (!kawalki.length) return null;
  return kawalki.every(k => p.includes(k));
}

/* ---------------------------------- kompletna ocena podpisanego pliku ---------------------------------- */
const dwa = n => String(n).padStart(2, '0');
export const czasPl = d => d ? `${dwa(d.getDate())}.${dwa(d.getMonth() + 1)}.${d.getFullYear()} ${dwa(d.getHours())}:${dwa(d.getMinutes())}` : '';
const kto = p => [(p.givenName || []).join(' '), (p.SN || []).join(' ')].filter(Boolean).join(' ') || pierwszy(p, 'CN') || 'nieznana osoba';
function stanOgolny(kontrole) { return kontrole.some(k => k.stan === 'zle') ? 'zle' : kontrole.some(k => k.stan === 'uwaga') ? 'uwaga' : 'ok'; }

/**
 * Ocena jednego podpisanego pliku. Wejście: { bajty (PDF z podpisem) albo xades: tekst XML + oryginal (PDF), oryginal: Uint8Array, imie, pesel }.
 * Wynik: { rodzaj: 'PAdES'|'XAdES'|'brak', kontrole: [{ id, stan: 'ok'|'zle'|'uwaga', tekst }], stan, sygnatariusz, czas, wystawca }.
 */
export async function ocenPodpisElektroniczny({ bajty, xades, oryginal, imie, pesel }) {
  const kontrole = [], dodaj = (id, stan, tekst) => kontrole.push({ id, stan, tekst });
  let podpisy = [], rodzaj = 'brak';
  if (xades != null) {
    rodzaj = 'XAdES';
    const p = await sprawdzXades(xades, oryginal); podpisy = [p];
    if (p.blad) { dodaj('podpis', 'zle', p.powody[0] || 'plik podpisu jest uszkodzony'); return { rodzaj, kontrole, stan: 'zle', sygnatariusz: '', czas: null, wystawca: '' }; }
    dodaj('podpis', 'ok', 'Jest podpis elektroniczny (osobny plik podpisu XAdES)');
    if (p.skrot === true) dodaj('dokument', 'ok', 'Podpis dotyczy właśnie tego dokumentu (zgadza się skrót pliku)');
    else if (p.skrot === false) dodaj('dokument', 'zle', 'Podpis dotyczy INNEGO pliku niż ten dokument (skrót się nie zgadza)');
    else dodaj('dokument', 'uwaga', 'Nie mogę potwierdzić, którego pliku dotyczy podpis');
  } else {
    const sy = podpisyWPdf(bajty);
    if (!sy.length) { dodaj('podpis', 'zle', 'W tym pliku nie ma podpisu elektronicznego — podpisz go na gov.pl i wgraj ponownie'); return { rodzaj, kontrole, stan: 'zle', sygnatariusz: '', czas: null, wystawca: '' }; }
    rodzaj = 'PAdES'; for (const p of sy) podpisy.push(await sprawdzPades(bajty, p));
    dodaj('podpis', 'ok', podpisy.length === 1 ? 'Jest podpis elektroniczny' : `Są ${podpisy.length} podpisy elektroniczne`);
    if (podpisy.some(p => p.blad)) dodaj('podpis', 'zle', podpisy.find(p => p.blad).powody[0]);
    if (sy.some(p => p.calosc)) dodaj('calosc', 'ok', 'Podpis obejmuje cały dokument');
    else dodaj('calosc', 'zle', 'Po podpisaniu do pliku dopisano dane — podpis nie obejmuje całego dokumentu');
    if (oryginal) {
      if (zawieraOryginal(bajty, oryginal)) dodaj('dokument', 'ok', 'To ten sam dokument, który wygenerowałem (treść bez zmian)');
      else if (zawieraStrumienie(bajty, oryginal)) dodaj('dokument', 'ok', 'To ten sam dokument (plik zapisano na nowo przy podpisywaniu, treść bez zmian)');
      else dodaj('dokument', 'uwaga', 'Nie mogę potwierdzić, że to ten sam dokument, który wygenerowałem — sprawdź, czy to właściwy plik');
    }
    const zle = podpisy.filter(p => p.skrot === false);
    if (zle.length) dodaj('skrot', 'zle', 'Dokument został zmieniony po podpisaniu (skrót się nie zgadza) — podpis jest nieważny');
    else if (podpisy.every(p => p.skrot === true)) dodaj('skrot', 'ok', 'Dokument nie został zmieniony po podpisaniu');
    else dodaj('skrot', 'uwaga', 'Nie mogę sprawdzić, czy dokument został zmieniony po podpisaniu');
  }
  // kryptografia
  if (podpisy.some(p => p.podpis === false)) dodaj('kryptografia', 'zle', 'Podpis nie zgadza się z kluczem z certyfikatu — jest nieprawidłowy');
  else if (podpisy.every(p => p.podpis === true)) dodaj('kryptografia', 'ok', 'Podpis jest matematycznie poprawny (zgadza się z kluczem z certyfikatu)');
  else dodaj('kryptografia', 'uwaga', (podpisy.find(p => p.powody.length) || { powody: ['Nie umiem sprawdzić matematycznej poprawności podpisu'] }).powody[0]);
  // kto podpisał
  const oceny = podpisy.map(p => ({ p, o: czyTaOsoba(imie, pesel, p.podmiot) }));
  const moj = oceny.find(x => x.o.osoba === true), inny = oceny.find(x => x.o.osoba === false), nieznany = oceny.every(x => x.o.osoba === null);
  let sygnatariusz = '', czas = null, wystawca = '';
  if (moj) {
    sygnatariusz = kto(moj.p.podmiot); czas = moj.p.czas; wystawca = pierwszy(moj.p.wystawca, 'CN') || pierwszy(moj.p.wystawca, 'O');
    dodaj('osoba', 'ok', `Podpisał(a): ${sygnatariusz} — zgadza się z osobą na dokumencie`);
    if (moj.o.pesel === true) dodaj('pesel', 'ok', 'PESEL w certyfikacie zgadza się z PESEL-em na dokumencie');
    else if (moj.o.pesel === false) dodaj('pesel', 'zle', 'PESEL w certyfikacie jest INNY niż na dokumencie');
  } else if (inny) {
    sygnatariusz = kto(inny.p.podmiot); czas = inny.p.czas; wystawca = pierwszy(inny.p.wystawca, 'CN') || pierwszy(inny.p.wystawca, 'O');
    dodaj('osoba', 'zle', `Podpisała inna osoba: ${sygnatariusz} (na dokumencie: ${imie})`);
  } else if (nieznany) dodaj('osoba', 'uwaga', 'Certyfikat nie zawiera imienia i nazwiska — nie sprawdzę, kto podpisał');
  const wazny = (moj || inny || oceny[0] || {}).p;
  if (wazny && wazny.czas && wazny.od && wazny.do) {
    if (wazny.czas < wazny.od || wazny.czas > wazny.do) dodaj('termin', 'uwaga', `Podpis złożono poza okresem ważności certyfikatu (${czasPl(wazny.czas)})`);
  }
  if (!czas && wazny) czas = wazny.czas;
  if (czas) dodaj('czas', 'ok', `Podpisano: ${czasPl(czas)}`);
  return { rodzaj, kontrole, stan: stanOgolny(kontrole), sygnatariusz, czas, wystawca };
}
