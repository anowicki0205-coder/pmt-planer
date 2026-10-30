// PMT Planer (web) — odczyt pliku przeniesienia danych z programu na komputerze (pmt_przeniesienie.py, format w jego nagłówku).
// Plik jest zaszyfrowany kluczem z kodu i hasła konta (skrót SHA-256 „PMT|kod|hasło”, który aplikacja zna po zalogowaniu), więc PESEL nie leży w nim jawnie.
// Zasada: podpis sprawdzamy PRZED odszyfrowaniem, a wszystko, co wchodzi do aplikacji, jest oczyszczone (tylko teksty, długości i liczby ograniczone).
import * as S from './sejf.js';

const ITERACJE = 100000, FORMAT = 1, MAX_PUNKTOW = 5000, MAX_POLE = 200;
const enc = new TextEncoder(), dec = new TextDecoder();
const hex = t => { if (typeof t !== 'string' || t.length % 2 || /[^0-9a-f]/i.test(t)) throw new Error('hex'); const b = new Uint8Array(t.length / 2); for (let i = 0; i < b.length; i++) b[i] = parseInt(t.substr(i * 2, 2), 16); return b; };
const doHex = b => [...b].map(x => x.toString(16).padStart(2, '0')).join('');
const scal = (...c) => { const o = new Uint8Array(c.reduce((a, x) => a + x.length, 0)); let p = 0; for (const x of c) { o.set(x, p); p += x.length; } return o; };
const rowne = (a, b) => { if (a.length !== b.length) return false; let r = 0; for (let i = 0; i < a.length; i++) r |= a[i] ^ b[i]; return r === 0; };
const pole = v => String(v ?? '').split(/\s+/).filter(Boolean).join(' ').slice(0, MAX_POLE);

/** Kod konta zapisany w pliku (bez sprawdzania podpisu) albo null — żeby powiedzieć „to plik innego konta”, zanim zapytamy o klucz. */
export function kodZPliku(tekst) { try { const k = JSON.parse(tekst); return k && k.pmt === 'przeniesienie' && /^\d{5}$/.test(String(k.kod)) ? String(k.kod) : null; } catch (e) { return null; } }

/** Odczyt pliku: {ok:true, dane:{profil, sklepy, …}} albo {ok:false, powod:'format'|'klucz', komunikat}. */
export async function odczytaj(tekst, skrot) {
  let k, kod, sol, iv, szyfrogram, mac;
  try {
    k = JSON.parse(tekst);
    if (!k || k.pmt !== 'przeniesienie' || k.v !== FORMAT) throw new Error('format');
    kod = String(k.kod); if (!/^\d{5}$/.test(kod)) throw new Error('format');
    sol = hex(k.sol); iv = hex(k.iv); mac = hex(k.mac); szyfrogram = S.unb64(String(k.dane));
    if (sol.length !== 16 || iv.length !== 16 || mac.length !== 32) throw new Error('format');
  } catch (e) { return { ok: false, powod: 'format', komunikat: 'To nie jest plik z danymi z programu PMT (albo jest uszkodzony).' }; }
  if (!skrot) return { ok: false, powod: 'klucz', komunikat: 'Zaloguj się ponownie (hasłem), żeby odczytać plik.' };
  const kl = await S.pbkdf2(String(skrot), sol, ITERACJE), ks = S.hmac(kl, enc.encode('pmt-przen-szyfr')), kp = S.hmac(kl, enc.encode('pmt-przen-podpis'));
  const oczek = S.hmac(kp, scal(enc.encode(`PMT-PRZENIESIENIE|${FORMAT}|${kod}|${doHex(sol)}|${doHex(iv)}|`), szyfrogram));
  if (!rowne(oczek, mac)) return { ok: false, powod: 'klucz', komunikat: 'Nie mogę odczytać pliku: to inne konto albo inne hasło, albo plik został zmieniony.' };
  const strumien = new Uint8Array(szyfrogram.length);
  for (let b = 0, p = 0; p < strumien.length; b++, p += 32) { const blok = S.hmac(ks, scal(iv, Uint8Array.of(b >>> 24 & 255, b >>> 16 & 255, b >>> 8 & 255, b & 255))); strumien.set(blok.subarray(0, Math.min(32, strumien.length - p)), p); }
  let d; try { d = JSON.parse(dec.decode(szyfrogram.map((x, i) => x ^ strumien[i]))); } catch (e) { return { ok: false, powod: 'format', komunikat: 'Plik jest uszkodzony.' }; }
  return { ok: true, kod, dane: oczyscDane(d) };
}

const MAX_MIESIECY = 14, MAX_DNI = 400, MAX_WIZYT_W_DNIU = 60, MAX_ODHACZEN = 5000;
const liczba = (v, lo, hi, dom = 0) => { const x = Number(v); return Number.isFinite(x) && x >= lo && x <= hi ? Math.round(x * 10000) / 10000 : dom; };
const wspolrzedna = (v, g) => { if (v === null || v === undefined || v === '') return null; const x = Number(v); return Number.isFinite(x) && Math.abs(x) <= g ? Math.round(x * 1e6) / 1e6 : null; };
const DATA = /^\d{4}-\d{2}-\d{2}$/;
const czyData = t => { if (!DATA.test(t)) return false; const d = new Date(t + 'T00:00:00Z'); return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === t; };

/** Plan wizyt z programu → ten sam kształt, który zwraca silnik; dni i wizyty o niepoprawnym kształcie odpadają, liczby mają granice. null, gdy nic nie zostaje. */
export function oczyscPlan(pl) {
  if (!pl || typeof pl !== 'object') return null;
  const miesiace = []; let dni = 0;
  for (const m of (Array.isArray(pl.miesiace) ? pl.miesiace : []).slice(0, MAX_MIESIECY)) {
    if (!m || typeof m !== 'object') continue;
    const lista = [];
    for (const d of (Array.isArray(m.dni) ? m.dni : [])) {
      if (!d || typeof d !== 'object' || dni >= MAX_DNI || !czyData(String(d.data))) continue;
      const wizyty = [];
      for (const w of (Array.isArray(d.wizyty) ? d.wizyty : []).slice(0, MAX_WIZYT_W_DNIU)) {
        if (w && typeof w === 'object' && pole(w.adres)) wizyty.push({ nazwa: pole(w.nazwa) || pole(w.adres), adres: pole(w.adres), siec: pole(w.siec), miasto: pole(w.miasto), lat: wspolrzedna(w.lat, 90), lng: wspolrzedna(w.lng, 180) });
      }
      if (wizyty.length) { lista.push({ data: String(d.data), km: liczba(d.km, 0, 2000), minuty: liczba(d.minuty, 0, 1440), wizyty }); dni++; }
    }
    if (lista.length) miesiace.push({ rok: Number(lista[0].data.slice(0, 4)), miesiac: Number(lista[0].data.slice(5, 7)), dni: lista });
  }
  return miesiace.length ? { cykliczny: pl.cykliczny === true, cykl_domyslny: Math.round(liczba(pl.cykl_domyslny, 1, 52, 4)), miesiace } : null;
}

/** Odhaczone wizyty: {„RRRR-MM-DD|adres”: {czas}} tylko dla dni planu; czas „dd.mm.RRRR HH:MM” → godzina „HH:MM” (albo pusta). */
export function oczyscOdhaczenia(o, plan) {
  const wynik = {}; if (!o || typeof o !== 'object' || Array.isArray(o) || !plan) return wynik;
  const dni = new Set(plan.miesiace.flatMap(m => m.dni.map(d => d.data)));
  for (const [k, v] of Object.entries(o)) {
    const klucz = String(k); if (klucz.length > 300 || !dni.has(klucz.split('|')[0]) || Object.keys(wynik).length >= MAX_ODHACZEN) continue;
    const m = /(\d{2}):(\d{2})\s*$/.exec(String(v && typeof v === 'object' ? v.czas : '')); wynik[klucz] = { godz: m ? `${m[1]}:${m[2]}` : '' };
  }
  return wynik;
}

/** Wszystko z pliku traktujemy jak dane od użytkownika: tylko znane pola, teksty o ograniczonej długości. */
export function oczyscDane(d) {
  const p = d && d.profil && typeof d.profil === 'object' ? d.profil : null;
  const profil = p ? { imie: pole(p.imie), pesel: String(p.pesel ?? '').replace(/\D/g, '').slice(0, 11), adres: pole(p.adres), stanowisko: String(p.stanowisko) === 'KR' ? 'KR' : 'merchandiser', silnik_powyzej_900: p.silnik_powyzej_900 !== false } : null;
  const sklepy = [];
  for (const x of (d && Array.isArray(d.sklepy) ? d.sklepy : [])) { if (x && typeof x === 'object' && pole(x.adres)) sklepy.push({ adres: pole(x.adres), siec: pole(x.siec), miasto: pole(x.miasto) }); if (sklepy.length >= MAX_PUNKTOW) break; }
  const plan = oczyscPlan(d && d.plan);
  return { profil: profil && (profil.imie || profil.pesel) ? profil : null, sklepy, plan, odhaczenia: oczyscOdhaczenia(d && d.odhaczenia, plan), wersja_programu: pole(d && d.wersja_programu), data: pole(d && d.data) };
}
