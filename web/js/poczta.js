// PMT Planer (web) — gotowa wiadomość pocztowa (plik .eml) z adresatem, tematem, treścią i załącznikiem.
// Strona internetowa nie może dołączyć pliku do linku „mailto:”, ale może dać plik .eml z nagłówkiem „X-Unsent: 1”: Outlook, Thunderbird i Poczta w Windows otwierają go
// jako wiadomość do wysłania (adresat, temat, treść i załącznik już są), wystarczy kliknąć „Wyślij”. Czyste funkcje — bez dostępu do interfejsu.
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

/** → Uint8Array z plikiem .eml (wszystko ASCII, końce wierszy CRLF). zalacznik: { nazwa, bajty: Uint8Array, typ }. */
export function zbudujEml({ adres, temat, tresc, zalacznik }) {
  const gr = '----=_PMT_' + hex(12), nazwa = nazwaAscii(zalacznik.nazwa), typ = bezKresek(zalacznik.typ || 'application/octet-stream');
  const linie = [
    'X-Unsent: 1', 'X-Uniform-Type-Identifier: com.apple.mail-draft', 'MIME-Version: 1.0',
    `To: ${bezKresek(adres)}`, `Subject: ${naglowekTekst(temat)}`,
    `Content-Type: multipart/mixed; boundary="${gr}"`, '',
    `--${gr}`, 'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: base64', '', zawin(b64(enc.encode(String(tresc).replace(/\r?\n/g, '\r\n')))), '',
    `--${gr}`, `Content-Type: ${typ}; name="${nazwa}"`, 'Content-Transfer-Encoding: base64', `Content-Disposition: attachment; filename="${nazwa}"`, '', zawin(b64(zalacznik.bajty)), '',
    `--${gr}--`, ''];
  return enc.encode(linie.join('\r\n'));
}
