// PMT Planer (web) — dostęp: logowanie, sesja i puls przez backend Apps Script (ten sam co w programie na komputerze).
// Zasady przeniesione z PMT_Delegacje.py: hasło nigdy nie jest zapisywane (tylko skrót SHA-256 z solą „PMT|kod|hasło”),
// zapytania podpisuje HMAC-SHA256 sekretem aplikacji (plik sekret.txt obok aplikacji — NIGDY w kodzie), a bez sieci
// wolno wejść tylko kontem, które już raz zalogowało się na tym urządzeniu, i tylko przez OFFLINE_DNI od ostatniego kontaktu z serwerem.
// UWAGA: sekret w paczce webowej to filtr przed botami, nie tajemnica — każdy może go odczytać z przeglądarki (tak samo jak w programie).
// SKRÓT HASŁA nie leży już na dysku (był szybki do złamania, gdyby ktoś dostał profil przeglądarki): zostaje w sessionStorage karty na czas sesji (do podpisywania pulsu),
// a poprawność hasła przy logowaniu bez sieci i autologowaniu sprawdza SEJF (js/sejf.js) — zaszyfrowany klucz danych, wolny PBKDF2.
import * as sejf from './sejf.js';

export const BACKEND = 'https://script.google.com/macros/s/AKfycbyKUur4Fhs90_I8w5qqB39V5nqSQgQYixkItuxvT3gu4HokQlaMz3yXbiL06S2jZgoYAw/exec';
export const WERSJA = '3.24.0';          // numer wersji programu, z którego pochodzi silnik (backend porównuje go liczbowo)
export const OFFLINE_DNI = 45;
export const PULS_CO_MIN = 15;
const KLUCZ = 'pmt-web-dostep-v1';
const CZAS_ODPOWIEDZI = 28000;           // zimny start Apps Script potrafi trwać ~30 s

const bezpiecznie = (f, dom) => { try { return f(); } catch (e) { return dom; } };
const czytaj = () => bezpiecznie(() => JSON.parse(localStorage.getItem(KLUCZ)) || {}, {});
const zapisz = d => bezpiecznie(() => localStorage.setItem(KLUCZ, JSON.stringify(d)));
const teraz = () => Date.now();
const dzis = () => { const t = new Date(); return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`; };
const dniMiedzy = (a, b) => Math.round((Date.parse(a + 'T12:00:00') - Date.parse(b + 'T12:00:00')) / 86400000);

/* ---------- SHA-256 i HMAC (Web Crypto, a gdy strona nie jest „bezpiecznym kontekstem” — czysty JS) ---------- */
const enc = new TextEncoder();
const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
const P = (() => { const p = []; for (let n = 2; p.length < 64; n++) if (p.every(q => n % q)) p.push(n); return p; })();
const ulamek = x => Math.floor((x - Math.floor(x)) * 4294967296) >>> 0;
const K = P.map(n => ulamek(Math.cbrt(n))), H0 = P.slice(0, 8).map(n => ulamek(Math.sqrt(n)));
export function sha256Js(wej) {
  const m = wej instanceof Uint8Array ? wej : enc.encode(wej), dl = m.length, n = (((dl + 9 + 63) >> 6) << 6);
  const b = new Uint8Array(n); b.set(m); b[dl] = 0x80;
  const dv = new DataView(b.buffer); dv.setUint32(n - 8, Math.floor(dl / 536870912)); dv.setUint32(n - 4, (dl << 3) >>> 0);
  const h = Uint32Array.from(H0), w = new Uint32Array(64);
  const rr = (x, k) => (x >>> k) | (x << (32 - k));
  for (let o = 0; o < n; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getUint32(o + i * 4);
    for (let i = 16; i < 64; i++) { const a = rr(w[i - 15], 7) ^ rr(w[i - 15], 18) ^ (w[i - 15] >>> 3), c = rr(w[i - 2], 17) ^ rr(w[i - 2], 19) ^ (w[i - 2] >>> 10); w[i] = (w[i - 16] + a + w[i - 7] + c) >>> 0; }
    let [a, bb, c, d, e, f, g, hh] = h;
    for (let i = 0; i < 64; i++) {
      const t1 = (hh + (rr(e, 6) ^ rr(e, 11) ^ rr(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) >>> 0;
      const t2 = ((rr(a, 2) ^ rr(a, 13) ^ rr(a, 22)) + ((a & bb) ^ (a & c) ^ (bb & c))) >>> 0;
      hh = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = bb; bb = a; a = (t1 + t2) >>> 0;
    }
    h[0] += a; h[1] += bb; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
  }
  const out = new Uint8Array(32), ov = new DataView(out.buffer); h.forEach((x, i) => ov.setUint32(i * 4, x)); return out;
}
export function hmacJs(klucz, tekst) {
  let k = enc.encode(klucz); if (k.length > 64) k = sha256Js(k);
  const ip = new Uint8Array(64).fill(0x36), op = new Uint8Array(64).fill(0x5c); k.forEach((x, i) => { ip[i] ^= x; op[i] ^= x; });
  const w = enc.encode(tekst), a = new Uint8Array(64 + w.length); a.set(ip); a.set(w, 64);
  const in2 = sha256Js(a), c = new Uint8Array(96); c.set(op); c.set(in2, 64); return sha256Js(c);
}
const sub = () => (globalThis.crypto && crypto.subtle) || null;
export async function sha256Hex(tekst) { const s = sub(); return hex(s ? await s.digest('SHA-256', enc.encode(tekst)) : sha256Js(tekst)); }
export async function hmacHex(klucz, tekst) {
  const s = sub(); if (!s) return hex(hmacJs(klucz, tekst));
  const k = await s.importKey('raw', enc.encode(klucz), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return hex(await s.sign('HMAC', k, enc.encode(tekst)));
}
export const skrotHasla = (kod, haslo) => sha256Hex(`PMT|${kod}|${haslo}`);

/* ---------- sekret aplikacji (plik obok index.html; brak = zapytania bez podpisu) ---------- */
let sekretObietnica = null;
export function sekret() {
  return sekretObietnica || (sekretObietnica = (async () => {
    try {
      const r = await fetch('sekret.txt', { cache: 'no-store' }); if (!r.ok) return '';
      const t = (await r.text()).split(/\r?\n/)[0].trim(); return t && !t.startsWith('<') ? t : '';
    } catch (e) { return ''; }
  })());
}
export const zapomnijSekret = () => { sekretObietnica = null; };
/* Puls i rejestr sesji backend przyjmuje w pełni tylko z podpisem KLUCZEM POCHODNYM OD HASŁA: HMAC, którego kluczem jest skrót hasła „PMT|kod|hasło” (ten sam, który serwer
   trzyma w kolumnie „Haslo hash”, a my mamy zapisany po logowaniu). Samo hasło nie jedzie, a znajomość samego 5-cyfrowego kodu nie wystarcza, by dostać imię, rejon i L4 innego pracownika. */
const AKCJE_Z_HASLEM = ['puls', 'sesja'];
async function podpisz(dane, skrotZ = null) {
  const czas = String(Math.floor(teraz() / 1000)), s = await sekret();
  const d = { ...dane, klucz_czas: czas, wersja: WERSJA };
  const baza = `${d.kod || ''}|${d.akcja || ''}|${czas}`;
  if (s) d.podpis = await hmacHex(s, baza); else delete d.podpis;
  const klucz = AKCJE_Z_HASLEM.includes(d.akcja) ? (skrotZ || skrotSesji(d.kod)) : '';
  if (klucz) d.podpis_hasla = await hmacHex(klucz, baza); else delete d.podpis_hasla;
  return d;
}

/* ---------- połączenie z backendem ---------- */
export class BladSieci extends Error { constructor(rodzaj, opis) { super(opis); this.rodzaj = rodzaj; } }
const opisBledu = {
  czas: 'Serwer nie odpowiedział w wyznaczonym czasie. Sprawdź połączenie i spróbuj ponownie — przy słabym zasięgu wystarczy druga próba.',
  siec: 'Nie udało się połączyć z serwerem. Sprawdź internet; jeśli działa, połączenie może blokować sieć firmowa lub VPN (script.google.com).',
  cors: 'Serwer PMT odpowiada, ale przeglądarka nie dopuściła jego odpowiedzi do aplikacji (CORS). To błąd wdrożenia backendu, nie Twojego internetu — napisz do administratora. Program na komputerze działa niezależnie.',
  odpowiedz: 'Serwer odpowiedział w nieoczekiwany sposób. Spróbuj ponownie za chwilę; jeśli błąd wraca, napisz do administratora.',
};
export async function wyslij(dane, limit = CZAS_ODPOWIEDZI) {
  const cialo = JSON.stringify(await podpisz(dane)), ac = new AbortController(), t = setTimeout(() => ac.abort(), limit);
  let tekst;
  try {
    // text/plain = zapytanie „proste” (bez preflight), którego Apps Script wymaga przy wywołaniu z przeglądarki
    const r = await fetch(BACKEND, { method: 'POST', body: cialo, headers: { 'Content-Type': 'text/plain;charset=utf-8' }, signal: ac.signal, credentials: 'omit', redirect: 'follow' });
    tekst = await r.text();
  } catch (e) {
    if (e && e.name === 'AbortError') throw new BladSieci('czas', opisBledu.czas);
    // zapytanie padło: sprawdzamy, czy sam serwer jest osiągalny (GET bez odczytu odpowiedzi) — wtedy to nie brak internetu, tylko odpowiedź zablokowana przez przeglądarkę
    if (await serwerOsiagalny()) throw new BladSieci('cors', opisBledu.cors);
    throw new BladSieci('siec', opisBledu.siec);
  } finally { clearTimeout(t); }
  try { const o = JSON.parse(tekst); if (o && typeof o === 'object') return o; } catch (e) { /* poniżej */ }
  throw new BladSieci('odpowiedz', opisBledu.odpowiedz);
}
async function serwerOsiagalny() {
  const ac = new AbortController(), t = setTimeout(() => ac.abort(), 5000);
  try { await fetch(BACKEND, { mode: 'no-cors', cache: 'no-store', signal: ac.signal, credentials: 'omit' }); return true; } catch (e) { return false; } finally { clearTimeout(t); }
}
const poZimnymStarcie = async (dane, limit) => { try { return await wyslij(dane, limit); } catch (e) { if (!(e instanceof BladSieci) || e.rodzaj === 'odpowiedz') throw e; await new Promise(r => setTimeout(r, 800)); return wyslij(dane, limit); } };
/* budzi instancję Apps Script, zanim ktoś wpisze hasło (zwykły GET nie wykonuje doPost) */
export function rozgrzej() { try { fetch(BACKEND, { mode: 'no-cors', cache: 'no-store' }).catch(() => {}); } catch (e) { /* bez sieci */ } }

/* ---------- stan na urządzeniu ---------- */
const OSOBISTE = ['status', 'imie', 'rejon', 'wazne_do', 'nieobecnosci', 'dokumenty_sesja', 'plany_sesja'];
const stan = () => { const d = czytaj(); d.konta = d.konta || {}; d.status = d.status || {}; d.kolejka = d.kolejka || { uruchomienia: 0, dokumenty: 0, minuty: 0 }; return d; };
/* skrót hasła na czas sesji karty: pamięć + sessionStorage (odświeżenie strony go nie gubi, zamknięcie karty tak) */
const KLUCZ_SKROTU = 'pmt-web-skrot'; let skrotPamiec = null;
const ustawSkrot = (kod, skrot) => { skrotPamiec = { kod, skrot }; bezpiecznie(() => sessionStorage.setItem(KLUCZ_SKROTU, JSON.stringify(skrotPamiec))); };
const skrotSesji = kod => { if (!skrotPamiec) skrotPamiec = bezpiecznie(() => JSON.parse(sessionStorage.getItem(KLUCZ_SKROTU)), null); return skrotPamiec && skrotPamiec.kod === kod ? skrotPamiec.skrot : ''; };
const zapomnijSkrot = () => { skrotPamiec = null; bezpiecznie(() => sessionStorage.removeItem(KLUCZ_SKROTU)); bezpiecznie(() => sessionStorage.removeItem(KLUCZ_IMIENIA)); };
/* imię z odpowiedzi logowania: tylko na czas sesji karty (podpowiedź w „Moje dane” przy pierwszym logowaniu); na dysku jawnie go nie trzymamy */
const KLUCZ_IMIENIA = 'pmt-web-imie'; let imieSesji = '';
const ustawImie = imie => { imieSesji = String(imie || '').trim(); bezpiecznie(() => sessionStorage.setItem(KLUCZ_IMIENIA, imieSesji)); };
export const imieZSerwera = () => imieSesji || bezpiecznie(() => sessionStorage.getItem(KLUCZ_IMIENIA) || '', '');
export const kodAktywny = () => stan().kod || '';
export const skrotAktywny = () => skrotSesji(stan().kod || '');      // skrót hasła zalogowanego konta (tylko na czas sesji) — klucz do pliku z danymi z programu (js/przeniesienie.js)
export const ostatniKod = () => stan().ostatni || '';
export const status = () => stan().status;
/** Czy to hasło jest znane na tym urządzeniu (autologowanie): konto z sejfem — próba otwarcia sejfu (PBKDF2, ok. 0,3 s); konto sprzed sejfu — dawny skrót. */
export const czyHasloZnane = async (kod, haslo) => {
  if (sejf.maSejf(kod)) return !!(await sejf.otworzSejf(kod, haslo));
  const k = stan().konta[kod]; return !!(k && k.skrot && k.skrot === await skrotHasla(kod, haslo));
};

function zapiszKonto(kod, pola) {
  const d = stan(); const k = d.konta[kod] || {}; Object.assign(k, pola); d.konta[kod] = k; zapisz(d); return k;
}
function aktywuj(kod, imie, skrot) {
  const d = stan();
  if (d.kod !== kod) for (const p of OSOBISTE) delete d.status[p];     // nowe konto nie dziedziczy cudzych danych
  const k = d.konta[kod] || {};
  delete d.status.status; delete d.status.wazne_do; delete k.wazne_do;      // logowanie online = świeży kontakt; ważność odświeży zaraz puls
  ustawSkrot(kod, skrot); ustawImie(imie); k.kontakt = teraz();      // skrót hasła i imię tylko na czas sesji (imię wraca w wyniku logowania); dawny zapis znika po utworzeniu sejfu (przygotujSejf)
  d.konta[kod] = k; d.kod = kod; d.ostatni = kod; d.status.dokumenty_sesja = 0; d.status.plany_sesja = 0; zapisz(d);
}

/* ---------- ocena sesji (jak online_status_sesji + _sesja_z_historii_urzadzenia) ---------- */
export function ocenaSesji() {
  const d = stan(), kod = d.kod; if (!kod) return { wazna: false, powod: 'brak' };
  const k = d.konta[kod] || {}, st = d.status || {};
  if (st.status === 'wygasla') return { wazna: false, dni: 0, powod: 'wygasla' };
  // zablokowane w arkuszu konto nie może żyć w nieskończoność na danych z pamięci: po OFFLINE_DNI bez kontaktu z serwerem trzeba go odnowić
  if (k.kontakt && (teraz() - k.kontakt) / 86400000 > OFFLINE_DNI) return { wazna: false, dni: 0, powod: 'offline' };
  const wd = String(st.wazne_do || k.wazne_do || '');
  if (wd) { const dni = dniMiedzy(wd, dzis()); return { wazna: dni >= 0, dni: Math.max(0, dni), powod: dni >= 0 ? '' : 'wygasla', wazneDo: wd }; }
  if (k.kontakt) {      // konto logowało się na tym urządzeniu (skrót hasła nie leży już na dysku — poprawność hasła sprawdza sejf)
    const dni = Math.floor((teraz() - k.kontakt) / 86400000);
    return dni <= OFFLINE_DNI ? { wazna: true, dni: OFFLINE_DNI - dni, powod: '' } : { wazna: false, dni: 0, powod: 'offline' };
  }
  return { wazna: false, powod: 'brak' };
}
/* okno pracy bez sieci: liczone od ostatniego udanego kontaktu z serwerem (logowanie albo puls) */
const offlineDozwolone = k => !k || !k.kontakt || (teraz() - k.kontakt) / 86400000 <= OFFLINE_DNI;

/* ---------- logowanie ---------- */
/* SESJA KARTY: jak w programie na komputerze, logowanie jest wymagane przy KAŻDYM uruchomieniu (nowa karta, ponowne otwarcie przeglądarki), a nie „na zawsze” po pierwszym razie.
   Odświeżenie tej samej karty (F5) logowania nie powtarza — znacznik leży w sessionStorage, który ginie z kartą. Hasło znane na urządzeniu loguje potem od razu (autologowanie). */
const KLUCZ_KARTY = 'pmt-web-sesja-karty';
const pamiecKarty = (() => { try { sessionStorage.setItem('__p', '1'); sessionStorage.removeItem('__p'); return true; } catch (e) { return false; } })();
const oznaczKarte = kod => { try { sessionStorage.setItem(KLUCZ_KARTY, kod); } catch (e) { /* bez pamięci karty logowanie nie będzie pamiętane do odświeżenia */ } };
const odznaczKarte = () => { try { sessionStorage.removeItem(KLUCZ_KARTY); } catch (e) { /* jak wyżej */ } };
export const sesjaTejKarty = () => { const kod = stan().kod; if (!kod) return false; if (!pamiecKarty) return true; try { return sessionStorage.getItem(KLUCZ_KARTY) === kod; } catch (e) { return true; } };
const jestKod = k => /^\d{5}$/.test(k);
export async function zaloguj(kod, haslo) {
  kod = String(kod || '').trim(); haslo = String(haslo || '');
  if (!jestKod(kod)) return { ok: false, komunikat: 'Login to dokładnie 5 cyfr.' };
  if (haslo.length < 4) return { ok: false, komunikat: 'Podaj hasło (lub numer telefonu).' };
  let odp;
  try { odp = await wyslij({ akcja: 'logowanie', kod, haslo, telefon: haslo, zrodlo: 'www' }); }
  catch (b) {
    if (!(b instanceof BladSieci) || b.rodzaj === 'odpowiedz') return { ok: false, komunikat: b.message };
    // bez sieci: porównanie skrótu z zapisanym przy poprzednim udanym logowaniu tego konta
    const k = stan().konta[kod], skrot = await skrotHasla(kod, haslo);
    // konto z sejfem: hasło sprawdza otwarcie sejfu (zwraca też klucz danych); konto sprzed sejfu: dawny skrót (po zalogowaniu powstanie sejf)
    const dek = sejf.maSejf(kod) ? await sejf.otworzSejf(kod, haslo) : null, znane = sejf.maSejf(kod) ? !!dek : !!(k && k.skrot === skrot);
    if (k && znane) {
      if (!offlineDozwolone(k)) return { ok: false, komunikat: `Minęło ponad ${OFFLINE_DNI} dni od ostatniego kontaktu z serwerem. Połącz się z internetem i zaloguj raz online — potem znów zadziała logowanie bez zasięgu.` };
      const d = stan(); if (d.kod !== kod) for (const p of OSOBISTE) delete d.status[p];
      d.kod = kod; d.ostatni = kod; zapisz(d); oznaczKarte(kod); ustawSkrot(kod, skrot);
      return { ok: true, imie: '', offline: true, dek };      // imienia nie trzymamy na dysku jawnie (jest w zaszyfrowanym profilu)
    }
    return { ok: false, komunikat: b.message };
  }
  if (odp.status !== 'ok') return { ok: false, komunikat: String(odp.opis || 'Logowanie nie powiodło się.') };
  aktywuj(kod, String(odp.imie || ''), await skrotHasla(kod, haslo));
  /* ważność dostępu sprawdzamy OD RAZU (dawniej dopiero po wejściu do programu: użytkownik widział prośbę o nowe hasło, a po kilku sekundach wracał na ekran logowania) */
  let ocena = null; try { ocena = await Promise.race([puls(), new Promise(r => setTimeout(() => r(null), 12000))]); } catch (e) { ocena = null; }
  if (ocena && ocena.status === 'wygasla') {
    const d = stan(); d.ostatni = kod; delete d.kod; for (const p of OSOBISTE) delete d.status[p]; zapisz(d);
    const wd = String(ocena.wazne_do || '');
    return { ok: false, komunikat: wd
      ? `Dostęp tego konta wygasł (ważny był do ${wd.split('-').reverse().join('.')}). Skontaktuj się z administratorem — po przedłużeniu zaloguj się ponownie.`
      : 'Konto jest w bazie, ale nie ma ustawionej ważności dostępu (kolumna „Ważne do” w arkuszu Użytkownicy jest pusta) — dostęp wygasł. Poproś administratora o uzupełnienie daty.' };
  }
  oznaczKarte(kod);
  zdarzenieSesji('logowanie');
  const cyfry = haslo.replace(/[\s+-]/g, '');
  return { ok: true, imie: String(odp.imie || ''), telefon: /^\d{9,}$/.test(cyfry) && !(stan().konta[kod] || {}).maHaslo };   // logowanie telefonem = konto bez hasła
}

export function wyloguj() {
  const d = stan(), kod = d.kod; if (!kod) return;
  zdarzenieSesji('wylogowanie', true);
  d.ostatni = kod; delete d.kod; for (const p of OSOBISTE) delete d.status[p]; zapisz(d); odznaczKarte(); zapomnijSkrot(); sejf.zapomnijKlucz();
}

/** Zapomina konto na tym urządzeniu: login, skrót hasła do wejścia bez sieci i ostatni status (bez tego nie da się wejść bez internetu, a okno logowania nie podpowiada loginu). */
export function zapomnijKonto(kod) {
  const d = stan(); if (d.kod === kod) { zdarzenieSesji('wylogowanie', true); delete d.kod; for (const p of OSOBISTE) delete d.status[p]; odznaczKarte(); }
  delete d.konta[kod]; if (d.ostatni === kod) delete d.ostatni; zapisz(d); zapomnijSkrot(); sejf.zapomnijKlucz(); sejf.usunSejf(kod);
}

/* ---------- sejf danych konta ---------- */
export const kluczDanych = () => sejf.odczytajKlucz();
/** Po zalogowaniu: otwiera sejf konta tym hasłem albo (pierwsze logowanie na tym urządzeniu) zakłada go. Zwraca { stan: 'ok', dek } albo { stan: 'obcy' } — sejf istnieje, ale to hasło go nie otwiera
 *  (hasło zmieniono na innym urządzeniu albo zresetowano). Konto sprzed sejfu traci wtedy dawny zapis skrótu hasła z dysku. */
export async function przygotujSejf(kod, haslo) {
  let dek, nowy = false;
  if (sejf.maSejf(kod)) { dek = await sejf.otworzSejf(kod, haslo); if (!dek) return { stan: 'obcy' }; } else { dek = await sejf.utworzSejf(kod, haslo); nowy = true; }
  sejf.zapamietajKlucz(dek);
  const d = stan(), k = d.konta[kod]; if (k) { delete k.skrot; delete k.imie; } for (const f of ['imie', 'rejon', 'nieobecnosci']) delete d.status[f]; zapisz(d);      // sprzątanie po wersji sprzed szyfrowania: skrót hasła, imię, rejon i nieobecności nie leżą już jawnie na dysku
  return { stan: 'ok', dek, nowy };
}
/** Sejf zaszyfrowany POPRZEDNIM hasłem: poprzednie hasło odblokowuje go i przepisuje pod bieżące. null = to hasło nie pasuje. */
export async function odzyskajSejf(kod, stareHaslo, noweHaslo) {
  const dek = await sejf.otworzSejf(kod, stareHaslo); if (!dek) return null;
  await sejf.przepiszSejf(kod, dek, noweHaslo); sejf.zapamietajKlucz(dek); return dek;
}
/** „Zacznij od nowa”: stary sejf (i dane) znikają, powstaje nowy pod bieżącym hasłem. Dane z urządzenia kasuje wołający (magazyn). */
export async function nowySejf(kod, haslo) { sejf.usunSejf(kod); const dek = await sejf.utworzSejf(kod, haslo); sejf.zapamietajKlucz(dek); return dek; }
export const zapamietajKluczDanych = dek => sejf.zapamietajKlucz(dek);

/* ---------- puls i sesja ---------- */
let startSesji = teraz(), dokSesja = 0, planySesja = 0;
export const policzDokumenty = n => { dokSesja += n; const d = stan(); d.kolejka.dokumenty += n; zapisz(d); };
export const policzPlan = () => { planySesja += 1; };
export function dopiszMinuty() {
  const min = Math.round((teraz() - startSesji) / 60000); if (min < 1) return;
  startSesji += min * 60000; const d = stan(); d.kolejka.minuty += min; zapisz(d);
}
export function uruchomienie() { const d = stan(); d.kolejka.uruchomienia += 1; zapisz(d); startSesji = teraz(); }

export async function puls() {
  const d0 = stan(), kod = d0.kod; if (!kod) return null;
  dopiszMinuty();
  const q = stan().kolejka;
  let odp;
  try { odp = await wyslij({ akcja: 'puls', kod, system: 'Web', uruchomienia: q.uruchomienia, dokumenty: q.dokumenty, minuty: q.minuty }); }
  catch (e) { return null; }
  if (odp.status !== 'ok' && odp.status !== 'wygasla') return null;
  const d = stan();
  if (d.kod !== kod) return null;                                    // w międzyczasie ktoś się wylogował
  d.kolejka = { uruchomienia: Math.max(0, d.kolejka.uruchomienia - q.uruchomienia), dokumenty: Math.max(0, d.kolejka.dokumenty - q.dokumenty), minuty: Math.max(0, d.kolejka.minuty - q.minuty) };
  const pelne = odp.pelne !== false;      // false: serwer nie rozpoznał podpisu hasłem i oddał tylko status i datę — zapamiętanych danych nie nadpisujemy pustymi
  Object.assign(d.status, { kod, status: odp.status, wazne_do: odp.wazne_do || '', ostatnia_synchronizacja: dzis() });      // imię, rejon i nieobecności (L4) odpowiedzi nie są zapisywane: aplikacja ich nie używa, a nie ma po co trzymać ich jawnie na dysku
  const k = d.konta[kod] || {}; k.kontakt = teraz();
  if (odp.wazne_do) k.wazne_do = odp.wazne_do; else delete k.wazne_do;
  d.konta[kod] = k; zapisz(d);
  return odp;
}
/* wpis w rejestrze sesji (kto, kiedy, jak długo). Wylogowanie/zamknięcie: sendBeacon, żeby przeżyło zamykanie karty. */
export function zdarzenieSesji(rodzaj, beacon = false) {
  const kod = kodAktywny() || ostatniKod(); if (!kod) return;
  const min = Math.round(((teraz() - startSesji) / 60000) * 10) / 10;
  const dane = { akcja: 'sesja', kod, rodzaj, minuty: min, dokumenty: dokSesja, plany: planySesja };
  const skrot = skrotSesji(kod);      // odczyt OD RAZU: zaraz po wylogowaniu skrót jest zapominany, zanim podpis zdąży się policzyć
  podpisz(dane, skrot).then(p => {
    const cialo = JSON.stringify(p);
    if (beacon && navigator.sendBeacon) { try { navigator.sendBeacon(BACKEND, new Blob([cialo], { type: 'text/plain;charset=utf-8' })); return; } catch (e) { /* zwykłe zapytanie poniżej */ } }
    fetch(BACKEND, { method: 'POST', body: cialo, headers: { 'Content-Type': 'text/plain;charset=utf-8' }, credentials: 'omit', keepalive: true }).catch(() => {});
  }).catch(() => {});
}

/* ---------- hasło ---------- */
const jakJestOdp = o => (o && o.status === 'ok') ? true : (o && o.status === 'blad' ? false : null);
async function sprobujLogowania(kod, haslo, zrodlo) {
  try { return jakJestOdp(await wyslij({ akcja: 'logowanie', kod, haslo, telefon: haslo, zrodlo }, 14000)); } catch (e) { return null; }
}
export async function zmienHaslo(stare, nowe) {
  const kod = kodAktywny(); stare = String(stare || '').trim(); nowe = String(nowe || '').trim();
  if (!kod) return { ok: false, komunikat: 'Najpierw zaloguj się.' };
  if (!stare) return { ok: false, komunikat: 'Podaj dotychczasowe hasło.' };
  if (nowe.length < 6) return { ok: false, komunikat: 'Nowe hasło musi mieć co najmniej 6 znaków.' };
  let odp;
  try { odp = await poZimnymStarcie({ akcja: 'zmien_haslo', kod, stare_haslo: stare, nowe_haslo: nowe, haslo_stare: stare, haslo_nowe: nowe }, 20000); }
  catch (b) { odp = { status: 'blad', opis: b.message, siec: true }; }
  const nowe_ok = await sprobujLogowania(kod, nowe, 'weryfikacja');
  if (nowe_ok === true) {
    ustawSkrot(kod, await skrotHasla(kod, nowe)); zapiszKonto(kod, { maHaslo: true, kontakt: teraz() });
    const dek = sejf.odczytajKlucz(); if (dek) { try { await sejf.przepiszSejf(kod, dek, nowe); } catch (e) { /* dane zostają czytelne tym samym kluczem; sejf przepisze się przy następnym logowaniu */ } }      // zmiana hasła = ten sam klucz danych pod nowym hasłem; dane na dysku zostają
    return { ok: true };
  }
  if (odp.status === 'blad') return { ok: false, komunikat: odp.siec ? odp.opis : `${odp.opis || 'Serwer odrzucił zmianę'}. Twoje dotychczasowe hasło dalej działa.` };
  return { ok: false, komunikat: 'Nie udało się potwierdzić zmiany (brak odpowiedzi serwera). Spróbuj zalogować się nowym hasłem; jeśli nie zadziała — starym.' };
}
/* reset zapomnianego hasła: telefon z kartoteki jako dowód tożsamości, nowe hasło od razu, weryfikacja próbnym logowaniem */
export async function resetujHaslo(kod, telefon, nowe) {
  kod = String(kod || '').trim(); const tel = String(telefon || '').replace(/\D/g, ''); nowe = String(nowe || '').trim();
  if (!jestKod(kod)) return { ok: false, komunikat: 'Login to 5 cyfr — ten sam, którym się logujesz.' };
  if (tel.length < 9) return { ok: false, komunikat: 'Podaj 9-cyfrowy numer telefonu z kartoteki.' };
  if (nowe.length < 6) return { ok: false, komunikat: 'Nowe hasło musi mieć co najmniej 6 znaków.' };
  const poST = async dane => { try { return await poZimnymStarcie(dane, 20000); } catch (b) { return { status: 'blad', opis: b.message, siec: true }; } };
  const o1 = await poST({ akcja: 'reset_hasla', kod, telefon: tel });
  if (o1.status !== 'ok') return { ok: false, komunikat: `Reset odrzucony: ${o1.opis || o1.status}` };
  const o2 = await poST({ akcja: 'zmien_haslo', kod, stare_haslo: tel, nowe_haslo: nowe, haslo_stare: tel, haslo_nowe: nowe });
  const ok = await sprobujLogowania(kod, nowe, 'weryfikacja_resetu');
  if (ok === true) { ustawSkrot(kod, await skrotHasla(kod, nowe)); zapiszKonto(kod, { maHaslo: true }); return { ok: true }; }      // sejf na tym urządzeniu zna jeszcze STARE hasło — po zalogowaniu aplikacja zapyta o nie (albo usunie dane)
  if (ok === null) return { ok: false, komunikat: 'Reset najprawdopodobniej przeszedł, ale weryfikacja nie dostała odpowiedzi (sieć). Spróbuj zalogować się nowym hasłem.' };
  return { ok: false, komunikat: `Ustawienie nowego hasła nie powiodło się: ${o2.opis || o2.status || 'serwer odrzucił zmianę'}` };
}
