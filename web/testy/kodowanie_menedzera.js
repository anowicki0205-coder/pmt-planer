// menedzer.txt zapisany w Notatniku w różnych kodowaniach (UTF-8, UTF-8 z BOM, UTF-16, ANSI/Windows-1250) daje to samo nazwisko jako czysty UTF-8.
// node kodowanie_menedzera.js
const fs = require('fs'), path = require('path');
const zrodlo = fs.readFileSync(path.join(__dirname, '../js/silnik.worker.js'), 'utf8');
const m = zrodlo.match(/function tekstZPliku\(b\) \{[\s\S]*?\n\}\n/); if (!m) { console.error('PRZERWANO: nie znaleziono tekstZPliku'); process.exit(2); }
const tekstZPliku = new Function(m[0] + '; return tekstZPliku;')();
let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
const NAZWA = 'Łukasz Żółć-Wiśniewski';
const cp1250 = s => Buffer.from([...s].map(c => { const t = 'ĄąĆćĘęŁłŃńÓóŚśŹźŻż', k = [0xA5, 0xB9, 0xC6, 0xE6, 0xCA, 0xEA, 0xA3, 0xB3, 0xD1, 0xF1, 0xD3, 0xF3, 0x8C, 0x9C, 0x8F, 0x9F, 0xAF, 0xBF], i = t.indexOf(c); return i >= 0 ? k[i] : c.charCodeAt(0); }));
const utf16le = s => Buffer.concat([Buffer.from([0xFF, 0xFE]), Buffer.from(s, 'utf16le')]);
const utf16be = s => { const b = Buffer.from(s, 'utf16le'); b.swap16(); return Buffer.concat([Buffer.from([0xFE, 0xFF]), b]); };
const przyp = {
  'UTF-8': Buffer.from(NAZWA + '\n'), 'UTF-8 z BOM i CRLF': Buffer.concat([Buffer.from([0xEF, 0xBB, 0xBF]), Buffer.from(NAZWA + '\r\n')]),
  'UTF-16 LE (Notatnik „Unicode”)': utf16le(NAZWA + '\r\n'), 'UTF-16 BE': utf16be(NAZWA + '\r\n'), 'ANSI / Windows-1250': cp1250(NAZWA + '\r\n'),
  'puste linie i spacje na początku': Buffer.from('\n\n  ' + NAZWA + '  \n\ninne\n'),
};
for (const [n, b] of Object.entries(przyp)) { const w = tekstZPliku(new Uint8Array(b)); ok(n, w === NAZWA, JSON.stringify(w)); }
ok('pusty plik daje pusty tekst', tekstZPliku(new Uint8Array(0)) === '' && tekstZPliku(new Uint8Array(Buffer.from('\r\n  \r\n'))) === '');
console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
