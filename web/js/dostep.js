// PMT Planer (web) — dostęp: logowanie, sesja i puls przez backend Apps Script (ten sam co w programie na komputerze).
// Zasady przeniesione z PMT_Delegacje.py: hasło nigdy nie jest zapisywane (tylko skrót SHA-256 z solą „PMT|kod|hasło”),
// zapytania podpisuje HMAC-SHA256 sekretem aplikacji (plik sekret.txt obok aplikacji — NIGDY w kodzie), a bez sieci
// wolno wejść tylko kontem, które już raz zalogowało się na tym urządzeniu, i tylko przez OFFLINE_DNI od ostatniego kontaktu z serwerem.
// UWAGA: sekret w paczce webowej to filtr przed botami, nie tajemnica — każdy może go odczytać z przeglądarki (tak samo jak w programie).
// SKRÓT HASŁA nie leży już na dysku (był szybki do złamania, gdyby ktoś dostał profil przeglądarki): zostaje w pamięci strony na czas sesji (do podpisywania pulsu),
// a poprawność hasła przy logowaniu bez sieci i autologowaniu sprawdza SEJF (js/sejf.js) — zaszyfrowany klucz danych, wolny PBKDF2.
import * as sejf from './sejf.js';

export const BACKEND = 'https://script.google.com/macros/s/AKfycbyKUur4Fhs90_I8w5qqB39V5nqSQgQYixkItuxvT3gu4HokQlaMz3yXbiL06S2jZgoYAw/exec';
export const WERSJA = '3.25.1';          // numer najnowszego programu na komputerze (WERSJA_PROGRAMU w PMT_Delegacje.py; test dostep_test.js pilnuje zgodności). Backend porównuje go liczbowo,
                                           // a w arkuszu („Uzytkownicy”, „Sesje”) aplikacja web widnieje z dopiskiem: „web 3.25.1” — tak administrator widzi, że web jest na poziomie najnowszego programu
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
  if (sekretObietnica) return sekretObietnica;
  let brakPliku = false;
  const p = sekretObietnica = (async () => {
    try {
      const r = await fetch('sekret.txt', { cache: 'no-store' }); if (!r.ok) { brakPliku = true; return ''; }
      const t = (await r.text()).split(/\r?\n/)[0].trim(); if (!(t && !t.startsWith('<'))) brakPliku = true; return brakPliku ? '' : t;
    } catch (e) { return ''; }
  })();
  // pusty wynik nie zostaje na całe życie strony: po błędzie sieci następne zapytanie pyta od razu (szybki błąd bez sieci), a gdy pliku po prostu nie ma (wdrożenie
  // lokalne, 404) — dopiero po minucie, żeby nie pobierać go przy każdym zapytaniu (np. tuż przed beaconem przy zamykaniu strony)
  p.then(t => { if (t) return; const zapomnij = () => { if (sekretObietnica === p) sekretObietnica = null; }; if (brakPliku) setTimeout(zapomnij, 60000); else zapomnij(); });
  return p;
}
export const zapomnijSekret = () => { sekretObietnica = null; };
/* Puls i rejestr sesji backend przyjmuje w pełni tylko z podpisem KLUCZEM POCHODNYM OD HASŁA: HMAC, którego kluczem jest skrót hasła „PMT|kod|hasło” (ten sam, który serwer
   trzyma w kolumnie „Haslo hash”, a my mamy zapisany po logowaniu). Samo hasło nie jedzie, a znajomość samego 5-cyfrowego kodu nie wystarcza, by dostać imię, rejon i L4 innego pracownika. */
const AKCJE_Z_HASLEM = ['puls', 'sesja', 'haslo_paczki'];
/* serwer przyjmuje podpis tylko w oknie 600 s od SWOJEGO czasu: zegar urządzenia przestawiony o kwadrans dawał niezrozumiałe odmowy, więc czas podpisu poprawiamy
   o różnicę względem czasu serwera z ostatniej odpowiedzi (czas_serwera) */
let przesuniecie = 0;
async function podpisz(dane, skrotZ = null) {
  const czas = String(Math.floor(teraz() / 1000 + przesuniecie)), s = await sekret();
  const d = { ...dane, klucz_czas: czas, wersja: WERSJA, klient: 'web' };      // klient: backend nie stosuje do aplikacji web bramki wersji programu (WYMAGANA_WERSJA)
  const baza = `${d.kod || ''}|${d.akcja || ''}|${czas}`;
  if (s) d.podpis = await hmacHex(s, baza); else delete d.podpis;
  const klucz = AKCJE_Z_HASLEM.includes(d.akcja) && skrotNieaktualny !== d.kod ? (skrotZ || skrotSesji(d.kod)) : '';      // skrót odrzucony przez serwer: bez podpisu (każdy zły podpis zużywa limit prób hasła)
  if (klucz) d.podpis_hasla = await hmacHex(klucz, baza); else delete d.podpis_hasla;
  return d;
}

/** Hasło do paczek z dokumentami (jest w nich PESEL) nadaje ADMINISTRATOR — w zakładce „Ustawienia” arkusza, razem z ostatnim dniem ważności i adresem odbiorcy. Aplikacja pobiera je tuż przed wysyłką,
    użytkownik go nie widzi i nie wymyśla własnego; po terminie serwer go nie wydaje. → { ok:true, haslo, wazneDo, adres } albo { ok:false, powod, komunikat }. */
export async function pobierzHasloPaczki() {
  const kod = stan().kod;
  if (!kod || !skrotSesji(kod) || skrotNieaktualny === kod) return { ok: false, powod: 'logowanie', komunikat: 'Wyloguj się i zaloguj ponownie hasłem — wtedy będę mógł pobrać hasło do paczki i wysłać dokumenty.' };
  let odp; try { odp = await wyslij({ akcja: 'haslo_paczki', kod }, 20000); } catch (e) { return { ok: false, powod: 'siec', komunikat: 'Brak połączenia z serwerem — nie mogę pobrać hasła do paczki. Spróbuj, gdy będzie internet.' }; }
  const s = odp && odp.status, data = String(odp && odp.wazne_do || '');
  if (s === 'ok') {
    if (typeof odp.haslo !== 'string' || [...odp.haslo].length < 8 || !/^\d{4}-\d{2}-\d{2}$/.test(data)) return { ok: false, powod: 'odpowiedz', komunikat: 'Hasło do paczek ustawione przez administratora jest nieprawidłowe lub za krótkie (minimum 8 znaków). Napisz do administratora.' };
    const adres = String(odp.adres || '').trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(adres)) return { ok: false, powod: 'odpowiedz', komunikat: 'Administrator nie ustawił poprawnego adresu odbiorcy dokumentów. Napisz do administratora.' };
    return { ok: true, haslo: odp.haslo, wazneDo: data, adres };
  }
  if (s === 'brak') return { ok: false, powod: 'brak', komunikat: 'Wysyłka dokumentów nie jest jeszcze włączona — administrator nie ustawił hasła do paczek, jego terminu ważności albo adresu odbiorcy. Napisz do administratora.' };
  if (s === 'wygaslo') return { ok: false, powod: 'wygaslo', komunikat: `Hasło do paczek wygasło ${data.split('-').reverse().join('.')}. Poczekaj, aż administrator ustawi nowe, i spróbuj ponownie.` };
  if (s === 'wygasla') return { ok: false, powod: 'dostep', komunikat: 'Twój dostęp do aplikacji wygasł — skontaktuj się z administratorem.' };
  if (s === 'blad') return { ok: false, powod: 'siec', komunikat: `${String(odp.opis || 'Serwer chwilowo nie odpowiada')} — spróbuj ponownie za chwilę.` };      // np. „Serwer zajety” (kolejka) — to nie odmowa konta
  if (s === 'odmowa') skrotNieaktualny = kod;
  return { ok: false, powod: 'odmowa', komunikat: 'Serwer nie potwierdził Twojego konta. Wyloguj się, zaloguj ponownie hasłem i spróbuj jeszcze raz.' };
}

/* ---------- połączenie z backendem ---------- */
export class BladSieci extends Error { constructor(rodzaj, opis) { super(opis); this.rodzaj = rodzaj; } }
const opisBledu = {
  czas: 'Serwer nie odpowiedział w wyznaczonym czasie. Sprawdź połączenie i spróbuj ponownie — przy słabym zasięgu wystarczy druga próba.',
  siec: 'Nie udało się połączyć z serwerem. Sprawdź internet; jeśli działa, połączenie może blokować sieć firmowa lub VPN (script.google.com).',
  cors: 'Serwer PMT odpowiada, ale przeglądarka nie dopuściła jego odpowiedzi do aplikacji (CORS). To błąd wdrożenia backendu, nie Twojego internetu — napisz do administratora. Program na komputerze działa niezależnie.',
  odpowiedz: 'Serwer odpowiedział w nieoczekiwany sposób. Spróbuj ponownie za chwilę; jeśli błąd wraca, napisz do administratora.',
};
export async function wyslij(dane, limit = CZAS_ODPOWIEDZI, ponowka = false) {
  const uzyte = przesuniecie;      // przesunięcie zegara użyte do TEGO podpisu (równoległa odpowiedź mogła je już poprawić)
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
  let o = null; try { o = JSON.parse(tekst); } catch (e) { /* poniżej */ }
  if (!o || typeof o !== 'object') throw new BladSieci('odpowiedz', opisBledu.odpowiedz);
  const cs = Number(o.czas_serwera); if (cs > 0) przesuniecie = cs - teraz() / 1000;
  if (!ponowka && Math.abs(przesuniecie - uzyte) > 300 && (o.opis === 'odmowa' || o.status === 'odmowa' || o.pelne === false)) return wyslij(dane, limit, true);      // odmowa przez zegar urządzenia: raz jeszcze, już z czasem serwera
  return o;
}
async function serwerOsiagalny() {
  const ac = new AbortController(), t = setTimeout(() => ac.abort(), 5000);
  try { await fetch(BACKEND, { mode: 'no-cors', cache: 'no-store', signal: ac.signal, credentials: 'omit' }); return true; } catch (e) { return false; } finally { clearTimeout(t); }
}
const poZimnymStarcie = async (dane, limit) => { try { return await wyslij(dane, limit); } catch (e) { if (!(e instanceof BladSieci) || e.rodzaj === 'odpowiedz') throw e; await new Promise(r => setTimeout(r, 800)); return wyslij(dane, limit); } };
/* budzi instancję Apps Script, zanim ktoś wpisze hasło (zwykły GET nie wykonuje doPost) */
export function rozgrzej() { try { fetch(BACKEND, { mode: 'no-cors', cache: 'no-store' }).catch(() => {}); } catch (e) { /* bez sieci */ } }

/* ---------- stan na urządzeniu ---------- */
const OSOBISTE = ['status', 'imie', 'rejon', 'wazne_do', 'nieobecnosci', 'dokumenty_sesja', 'plany_sesja', 'kod', 'ostatnia_synchronizacja'];      // kod i data synchronizacji z pulsu też: po wylogowaniu i „Usuń dane” loginu nie ma w statusie
const stan = () => { const d = czytaj(); d.konta = d.konta || {}; d.status = d.status || {}; d.kolejka = d.kolejka || { uruchomienia: 0, dokumenty: 0, minuty: 0 }; return d; };
/* SESJA STRONY: skrót hasła, imię z logowania, znacznik „ta karta jest zalogowana” i klucz danych (sejf) żyją TYLKO w pamięci strony. sessionStorage przeglądarka trzyma
   na dysku i przywraca razem z kartą (Ctrl+Shift+T, „Kontynuuj tam, gdzie skończyłem”, po awarii) — także karty ZAMKNIĘTEJ. Dlatego wpis dla odświeżenia kładziemy tam
   wyłącznie przy ZAMIERZONYM przeładowaniu: F5, Ctrl+R / Cmd+R albo przeładowanie przez samą aplikację (przeladuj()). Zamknięcie karty, okna, przejście na inną stronę,
   przycisk odświeżania w pasku przeglądarki i gest „pociągnij, by odświeżyć” niczego nie zapisują (pokażą logowanie; hasło zapamiętane w przeglądarce loguje od razu).
   Nowa strona przyjmuje wpis tylko przy przeładowaniu, świeży (do 15 s), i od razu go usuwa. */
const PRZEKAZ = 'pmt-web-przekaz', WAZNOSC_PRZEKAZU = 15000;
const przeladowanie = () => bezpiecznie(() => { const n = performance.getEntriesByType('navigation')[0]; return n ? n.type === 'reload' : performance.navigation.type === 1; }, false);
const przekaz = bezpiecznie(() => {
  const t = sessionStorage.getItem(PRZEKAZ); for (const k of [PRZEKAZ, 'pmt-web-dek', 'pmt-web-skrot', 'pmt-web-imie', 'pmt-web-sesja-karty']) sessionStorage.removeItem(k);      // także wpisy wersji, która trzymała je tu przez całą sesję
  const o = t ? JSON.parse(t) : null, wiek = o ? Date.now() - Number(o.t) : -1;
  return o && wiek >= 0 && wiek < WAZNOSC_PRZEKAZU && przeladowanie() ? o : null;
}, null) || {};
let skrotPamiec = przekaz.skrot && przekaz.skrot.kod ? przekaz.skrot : null, imieSesji = String(przekaz.imie || ''), kartaPamiec = String(przekaz.karta || '');
if (przekaz.dek) bezpiecznie(() => sejf.zapamietajKlucz(sejf.unb64(przekaz.dek)));
let doPrzeladowania = 0;      // chwila zamierzonego przeładowania (klawisz albo przeladuj()); 0 = żadnego
if (typeof addEventListener === 'function') addEventListener('keydown', e => { if (e.key === 'F5' || ((e.ctrlKey || e.metaKey) && !e.altKey && /^r$/i.test(e.key))) doPrzeladowania = Date.now(); }, true);
/** Przeładowanie strony bez ponownego logowania (klucz danych przechodzi krótkim wpisem do nowej strony). */
export const przeladuj = () => { doPrzeladowania = Date.now(); location.reload(); };
if (typeof addEventListener === 'function') addEventListener('pagehide', e => {
  const kod = stan().kod, dek = sejf.odczytajKlucz(); if (e.persisted || !kod || kartaPamiec !== kod) return;      // persisted: strona zostaje w pamięci (bfcache), nic nie trzeba przekazywać
  if (!doPrzeladowania || Date.now() - doPrzeladowania > 10000) return;      // zamknięcie karty / okna, inna strona: klucz nie trafia na dysk
  bezpiecznie(() => sessionStorage.setItem(PRZEKAZ, JSON.stringify({ t: Date.now(), karta: kartaPamiec, skrot: skrotPamiec, imie: imieSesji, dek: dek ? sejf.b64(dek) : '' })));
});
/* Skrót hasła, którego serwer nie przyjął (pelne:false w pulsie, odmowa hasła paczki — np. hasło zmienione na innym urządzeniu): do następnego logowania
   karta nie podpisuje nim zapytań. Bez tego otwarta karta ze starym hasłem zużywałaby przy każdym pulsie limit złych podpisów konta. */
let skrotNieaktualny = '';
const ustawSkrot = (kod, skrot) => { skrotPamiec = { kod, skrot }; skrotNieaktualny = ''; };
const skrotSesji = kod => skrotPamiec && skrotPamiec.kod === kod ? skrotPamiec.skrot : '';
const zapomnijSkrot = () => { skrotPamiec = null; imieSesji = ''; };
/* imię z odpowiedzi logowania: tylko na czas sesji (podpowiedź w „Moje dane” przy pierwszym logowaniu); na dysku jawnie go nie trzymamy */
const ustawImie = imie => { imieSesji = String(imie || '').trim(); };
export const imieZSerwera = () => imieSesji;
export const kodAktywny = () => stan().kod || '';
export const skrotAktywny = () => skrotSesji(stan().kod || '');      // skrót hasła zalogowanego konta (tylko na czas sesji) — klucz do pliku z danymi z programu (js/przeniesienie.js)
export const ostatniKod = () => stan().ostatni || '';
export const status = () => stan().status;
/* POSTAĆ HASŁA jak na serwerze: backend przycina odstępy, a telefon porównuje po ostatnich 9 cyfrach. Z tej postaci liczymy skrót sesji (= „Haslo hash”) i klucz sejfu —
   inaczej hasło wklejone ze spacją albo telefon wpisany raz „600 100 200”, raz „600100200” dawały zły podpis hasłem i „obcy” sejf. */
export const postacHasla = h => String(h || '').trim();
const postacTelefonu = h => String(h || '').replace(/\D/g, '').slice(-9);
/** Postaci, którymi mógł być zaszyfrowany sejf: przycięta, telefon (gdy tekst wygląda na numer) i surowy tekst (sejf założony przed ujednoliceniem). */
const postaciSejfu = h => { const t = postacHasla(h), w = [t]; if (/^\+?[\d\s()-]+$/.test(t) && postacTelefonu(t).length === 9) w.push(postacTelefonu(t)); w.push(String(h || '')); return w; };
/** Otwiera sejf pierwszą pasującą postacią; inna niż `docelowa` od razu przepisuje sejf na docelową (następne logowanie trafi za pierwszym razem). */
async function otworzSejfPostacia(kod, postaci, docelowa) {
  for (const p of [...new Set(postaci)]) {
    const dek = await sejf.otworzSejf(kod, p); if (!dek) continue;
    if (docelowa && p !== docelowa) { try { await sejf.przepiszSejf(kod, dek, docelowa); } catch (e) { /* zostaje dawna postać; przepisze się przy następnym logowaniu */ } }
    return dek;
  }
  return null;
}
/** Czy to hasło jest znane na tym urządzeniu (autologowanie): konto z sejfem — próba otwarcia sejfu (PBKDF2, ok. 0,3 s); konto sprzed sejfu — dawny skrót. */
export const czyHasloZnane = async (kod, haslo) => {
  if (sejf.maSejf(kod)) return !!(await otworzSejfPostacia(kod, postaciSejfu(haslo), null));
  const k = stan().konta[kod]; return !!(k && k.skrot && (k.skrot === await skrotHasla(kod, postacHasla(haslo)) || k.skrot === await skrotHasla(kod, String(haslo || ''))));
};

function zapiszKonto(kod, pola) {
  const d = stan(); const k = d.konta[kod] || {}; Object.assign(k, pola); d.konta[kod] = k; zapisz(d); return k;
}
function aktywuj(kod, imie, skrot) {
  const d = stan();
  if (d.kod !== kod) for (const p of OSOBISTE) delete d.status[p];     // nowe konto nie dziedziczy cudzych danych
  const k = d.konta[kod] || {};
  delete d.status.status; delete d.status.wazne_do; delete k.wazne_do;      // logowanie online = świeży kontakt; ważność odświeży zaraz puls (k.zablokowane zdejmie dopiero puls „ok” — samo logowanie nie sprawdza ważności)
  ustawSkrot(kod, skrot); ustawImie(imie); k.kontakt = teraz();      // skrót hasła i imię tylko na czas sesji (imię wraca w wyniku logowania); dawny zapis znika po utworzeniu sejfu (przygotujSejf)
  d.konta[kod] = k; d.kod = kod; d.ostatni = kod; d.status.dokumenty_sesja = 0; d.status.plany_sesja = 0; zapisz(d);
}

/* ---------- ocena sesji (jak online_status_sesji + _sesja_z_historii_urzadzenia) ---------- */
export function ocenaSesji() {
  const d = stan(), kod = d.kod; if (!kod) return { wazna: false, powod: 'brak' };
  const k = d.konta[kod] || {}, st = d.status || {};
  if (st.status === 'wygasla' || k.zablokowane) return { wazna: false, dni: 0, powod: 'wygasla' };
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
/* SESJA KARTY: jak w programie na komputerze, logowanie jest wymagane przy KAŻDYM uruchomieniu (nowa karta, ponowne otwarcie przeglądarki, przywrócona karta), a nie „na zawsze”
   po pierwszym razie. Odświeżenie tej samej karty (F5) logowania nie powtarza — znacznik przechodzi przez krótkie przekazanie przy przeładowaniu (wyżej). Hasło znane na urządzeniu loguje potem od razu (autologowanie). */
const oznaczKarte = kod => { kartaPamiec = kod; };
const odznaczKarte = () => { kartaPamiec = ''; };
export const sesjaTejKarty = () => { const kod = stan().kod; return !!kod && kartaPamiec === kod; };
const jestKod = k => /^\d{5}$/.test(k);
export async function zaloguj(kod, haslo) {
  const wpisane = String(haslo || ''); kod = String(kod || '').trim(); haslo = postacHasla(wpisane);
  if (!jestKod(kod)) return { ok: false, komunikat: 'Login to dokładnie 5 cyfr.' };
  if (haslo.length < 4) return { ok: false, komunikat: 'Podaj hasło (lub numer telefonu).' };
  let odp;
  try { odp = await wyslij({ akcja: 'logowanie', kod, haslo, telefon: haslo, zrodlo: 'www' }); }
  catch (b) {
    if (!(b instanceof BladSieci) || b.rodzaj === 'odpowiedz') return { ok: false, komunikat: b.message };
    // bez sieci: porównanie skrótu z zapisanym przy poprzednim udanym logowaniu tego konta
    const k = stan().konta[kod], skrot = await skrotHasla(kod, haslo);
    // konto z sejfem: hasło sprawdza otwarcie sejfu (zwraca też klucz danych); konto sprzed sejfu: dawny skrót (po zalogowaniu powstanie sejf)
    const dek = sejf.maSejf(kod) ? await otworzSejfPostacia(kod, postaciSejfu(wpisane), null) : null, znane = sejf.maSejf(kod) ? !!dek : !!(k && (k.skrot === skrot || k.skrot === await skrotHasla(kod, wpisane)));
    if (k && znane) {
      if (k.zablokowane) return { ok: false, komunikat: 'Dostęp do tego konta wygasł — skontaktuj się z administratorem. Po przedłużeniu zaloguj się raz z internetem.' };
      if (!offlineDozwolone(k)) return { ok: false, komunikat: `Minęło ponad ${OFFLINE_DNI} dni od ostatniego kontaktu z serwerem. Połącz się z internetem i zaloguj raz online — potem znów zadziała logowanie bez zasięgu.` };
      const d = stan(); if (d.kod !== kod) for (const p of OSOBISTE) delete d.status[p];
      d.kod = kod; d.ostatni = kod; zapisz(d); oznaczKarte(kod); ustawSkrot(kod, skrot);
      return { ok: true, imie: '', offline: true, dek, haslo, wpisane };      // imienia nie trzymamy na dysku jawnie (jest w zaszyfrowanym profilu)
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
  const telefon = odp.przez ? odp.przez === 'telefon' : /^\d{9,}$/.test(cyfry) && !(stan().konta[kod] || {}).maHaslo;   // logowanie telefonem = konto bez hasła (starszy backend nie mówi „przez”: zgadujemy po treści)
  return { ok: true, imie: String(odp.imie || ''), telefon, haslo: telefon ? postacTelefonu(haslo) : haslo, wpisane };      // haslo = postać do sejfu (telefon zawsze jako 9 cyfr), wpisane = tekst z pola
}

export function wyloguj() {
  const d = stan(), kod = d.kod; if (!kod) return;
  zdarzenieSesji('wylogowanie', true);
  d.ostatni = kod; delete d.kod; for (const p of OSOBISTE) delete d.status[p]; zapisz(d); odznaczKarte(); zapomnijSkrot(); sejf.zapomnijKlucz();
}

/** Zapomina konto na tym urządzeniu: login, skrót hasła do wejścia bez sieci i ostatni status (bez tego nie da się wejść bez internetu, a okno logowania nie podpowiada loginu). */
export function zapomnijKonto(kod) {
  const d = stan(); if (d.kod === kod) { zdarzenieSesji('wylogowanie', true); delete d.kod; for (const p of OSOBISTE) delete d.status[p]; odznaczKarte(); }
  if (d.status.kod === kod) { delete d.status.kod; delete d.status.ostatnia_synchronizacja; }
  delete d.konta[kod]; if (d.ostatni === kod) delete d.ostatni; zapisz(d); zapomnijSkrot(); sejf.zapomnijKlucz(); sejf.usunSejf(kod);
}

/* ---------- sejf danych konta ---------- */
export const kluczDanych = () => sejf.odczytajKlucz();
/** Po zalogowaniu: otwiera sejf konta tym hasłem albo (pierwsze logowanie na tym urządzeniu) zakłada go. Zwraca { stan: 'ok', dek } albo { stan: 'obcy' } — sejf istnieje, ale to hasło go nie otwiera
 *  (hasło zmieniono na innym urządzeniu albo zresetowano). Konto sprzed sejfu traci wtedy dawny zapis skrótu hasła z dysku. */
export async function przygotujSejf(kod, haslo, wpisane = haslo) {
  let dek, nowy = false; haslo = postacHasla(haslo);
  if (sejf.maSejf(kod)) { dek = await otworzSejfPostacia(kod, [haslo, ...postaciSejfu(wpisane)], haslo); if (!dek) return { stan: 'obcy' }; } else { dek = await sejf.utworzSejf(kod, haslo); nowy = true; }
  sejf.zapamietajKlucz(dek);
  const d = stan(), k = d.konta[kod]; if (k) { delete k.skrot; delete k.imie; } for (const f of ['imie', 'rejon', 'nieobecnosci']) delete d.status[f]; zapisz(d);      // sprzątanie po wersji sprzed szyfrowania: skrót hasła, imię, rejon i nieobecności nie leżą już jawnie na dysku
  return { stan: 'ok', dek, nowy };
}
/** Sejf zaszyfrowany POPRZEDNIM hasłem: poprzednie hasło odblokowuje go i przepisuje pod bieżące. null = to hasło nie pasuje. */
export async function odzyskajSejf(kod, stareHaslo, noweHaslo) {
  const dek = await otworzSejfPostacia(kod, postaciSejfu(stareHaslo), null); if (!dek) return null;
  await sejf.przepiszSejf(kod, dek, postacHasla(noweHaslo)); sejf.zapamietajKlucz(dek); return dek;
}
/** „Zacznij od nowa”: stary sejf (i dane) znikają, powstaje nowy pod bieżącym hasłem. Dane z urządzenia kasuje wołający (magazyn). */
export async function nowySejf(kod, haslo) { sejf.usunSejf(kod); const dek = await sejf.utworzSejf(kod, postacHasla(haslo)); sejf.zapamietajKlucz(dek); return dek; }
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

/* jeden puls naraz: drugi wołający (logowanie i koniec startu, interwał i powrót karty) dostaje tę samą odpowiedź, inaczej serwer dopisałby tę samą kolejkę przyrostów dwa razy */
let pulsWToku = null;
export const puls = () => pulsWToku || (pulsWToku = pulsWlasciwy().finally(() => { pulsWToku = null; }));
async function pulsWlasciwy() {
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
  if (!pelne && skrotSesji(kod)) skrotNieaktualny = kod;      // podpisany, a nieprzyjęty (powtórka z czasem serwera już była w wyslij): dalej bez podpisu hasłem
  Object.assign(d.status, { kod, status: odp.status, wazne_do: odp.wazne_do || '', ostatnia_synchronizacja: dzis() });      // imię, rejon i nieobecności (L4) odpowiedzi nie są zapisywane: aplikacja ich nie używa, a nie ma po co trzymać ich jawnie na dysku
  /* odebrany dostęp zapisujemy przy koncie (poza OSOBISTE), żeby przeżył wylogowanie — bez tego logowanie bez sieci działałoby jeszcze OFFLINE_DNI; blokada nie odnawia też okna pracy bez sieci */
  const k = d.konta[kod] || {}; if (odp.status === 'ok') { k.kontakt = teraz(); delete k.zablokowane; } else k.zablokowane = true;
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
