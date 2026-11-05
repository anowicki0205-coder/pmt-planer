// PMT Planer (web) — gotowa wiadomość pocztowa (plik .eml) z adresatem, tematem, treścią i załącznikiem.
// Strona internetowa nie może dołączyć pliku do linku „mailto:”, ale może dać plik .eml z nagłówkiem „X-Unsent: 1”: Outlook, Thunderbird i Poczta w Windows otwierają go
// jako wiadomość do wysłania (adresat, temat, treść i załącznik już są), wystarczy kliknąć „Wyślij”. Czyste funkcje — bez dostępu do interfejsu.
// Budowa jak w wiadomości zapisanej przez sam Outlook: multipart/mixed → (multipart/alternative: zwykły tekst + HTML) + załącznik, z nagłówkami Date i Message-ID.
// Nowy Outlook dla Windows gubi czasem treść i załącznik z plików .eml z samym zwykłym tekstem albo bez Message-ID — wersja HTML i identyfikator są po to, żeby i on miał komplet.
import { b64, losowe } from './sejf.js';

const enc = new TextEncoder();
const bezKresek = t => String(t ?? '').replace(/[\r\n\0]+/g, ' ').trim();
const zawin = t => (t.match(/.{1,76}/g) || ['']).join('\r\n');
const hex = n => [...losowe(n)].map(x => x.toString(16).padStart(2, '0')).join('');
const ascii = t => /^[\x20-\x7e]*$/.test(t);

/** Nagłówek z polskimi znakami wg RFC 2047 („=?UTF-8?B?…?=”), podzielony na słowa do ok. 45 bajtów, żeby nie przekroczyć 76 znaków w wierszu. */
export function naglowekTekst(t) {
  t = bezKresek(t); if (ascii(t)) return t;
  const slowa = []; let biez = '';
  for (const z of t) { if (enc.encode(biez + z).length > 42) { slowa.push(biez); biez = z; } else biez += z; }
  if (biez) slowa.push(biez);
  return slowa.map(s => `=?UTF-8?B?${b64(enc.encode(s))}?=`).join('\r\n ');
}

/** Nazwa pliku załącznika bez polskich znaków i znaków specjalnych (każda poczta czyta ją tak samo). */
export const nazwaAscii = n => bezKresek(n).normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l').replace(/Ł/g, 'L').replace(/[^A-Za-z0-9._-]+/g, '_').replace(/^_+|_+$/g, '') || 'dokumenty.zip';

/** Data wg RFC 5322 („Thu, 05 Nov 2026 11:15:00 +0100”) w czasie lokalnym. */
export function dataPoczty(d = new Date()) {
  const p = n => String(n).padStart(2, '0'), o = -d.getTimezoneOffset(), zn = o >= 0 ? '+' : '-', a = Math.abs(o);
  return `${['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()]}, ${p(d.getDate())} ${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.getMonth()]} ${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())} ${zn}${p(Math.floor(a / 60))}${p(a % 60)}`;
}
const escHtml = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
/** Treść jako prosty HTML (akapity i nowe wiersze zachowane, krój jak w Outlooku). */
export const trescHtml = tresc => `<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head><body><div style="font-family:Calibri,Arial,sans-serif;font-size:11pt">${escHtml(String(tresc).replace(/\r\n?/g, '\n')).replace(/\n/g, '<br>\r\n')}</div></body></html>`;

/** → Uint8Array z plikiem .eml (wszystko ASCII, końce wierszy CRLF). zalacznik: { nazwa, bajty: Uint8Array, typ }. */
export function zbudujEml({ adres, temat, tresc, zalacznik, data = new Date() }) {
  const gr = '----=_PMT_' + hex(12), grA = '----=_PMT_A_' + hex(12), nazwa = nazwaAscii(zalacznik.nazwa), typ = bezKresek(zalacznik.typ || 'application/octet-stream');
  const tekst = String(tresc).replace(/\r?\n/g, '\r\n');
  const linie = [
    'X-Unsent: 1', 'X-Uniform-Type-Identifier: com.apple.mail-draft', 'MIME-Version: 1.0',
    `Date: ${dataPoczty(data)}`, `Message-ID: <${hex(16)}@pmt-planer.invalid>`,
    `To: ${bezKresek(adres)}`, `Subject: ${naglowekTekst(temat)}`,
    `Content-Type: multipart/mixed;\r\n boundary="${gr}"`, '',
    `--${gr}`, `Content-Type: multipart/alternative;\r\n boundary="${grA}"`, '',
    `--${grA}`, 'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: base64', '', zawin(b64(enc.encode(tekst))), '',
    `--${grA}`, 'Content-Type: text/html; charset=UTF-8', 'Content-Transfer-Encoding: base64', '', zawin(b64(enc.encode(trescHtml(tresc)))), '',
    `--${grA}--`, '',
    `--${gr}`, `Content-Type: ${typ}; name="${nazwa}"`, 'Content-Transfer-Encoding: base64', `Content-Disposition: attachment; filename="${nazwa}"`, '', zawin(b64(zalacznik.bajty)), '',
    `--${gr}--`, ''];
  return enc.encode(linie.join('\r\n'));
}

/** Zapamiętany na urządzeniu sposób wysyłki (osobny w każdej przeglądarce). Wersja 2 wysyłki zeruje dawny wybór jednorazowo — po próbach z poprzednich wersji łatwo było zostawić „otwarcie poczty”,
 *  które otwiera wiadomość BEZ załącznika (mailto: nie umie go dołączyć). mag: localStorage (albo atrapa), metody: dozwolone nazwy; zwraca nazwę albo '' (= sposób domyślny). */
export function wczytajSposobWysylki(mag, metody) {
  try {
    if (mag.getItem('pmt-ui-poczta-v') !== '2') { mag.setItem('pmt-ui-poczta-v', '2'); mag.removeItem('pmt-ui-poczta'); return ''; }
    const v = mag.getItem('pmt-ui-poczta'); return metody.includes(v) ? v : '';
  } catch (e) { return ''; }
}
