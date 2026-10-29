// PMT Planer (web) — operacje na plikach dokumentów: ZIP (zapis do „Pobierz wszystkie” i odczyt paczek z gov.pl), scalanie PDF-ów (jeden plik do wydruku)
// i dopasowanie wgranych, podpisanych plików do właściwych dokumentów. Czyste funkcje — bez dostępu do interfejsu.

/* ---------------------------------- ZIP (bez kompresji; PDF-y są już skompresowane) ---------------------------------- */
const TABELA_CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
export function crc32(b) { let c = 0xFFFFFFFF; for (let i = 0; i < b.length; i++) c = TABELA_CRC[(c ^ b[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }

/** pliki: [{ nazwa, bajty: Uint8Array }] → Blob z archiwum ZIP (nazwy w UTF-8, bez kompresji). */
export function zipuj(pliki) {
  const kod = new TextEncoder(), czesci = [], centralne = [], d = new Date();
  const czas = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1), data = ((Math.max(d.getFullYear(), 1980) - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  let przes = 0;
  for (const p of pliki) {
    const nazwa = kod.encode(p.nazwa), b = p.bajty, crc = crc32(b);
    const lok = new DataView(new ArrayBuffer(30));
    lok.setUint32(0, 0x04034b50, true); lok.setUint16(4, 20, true); lok.setUint16(6, 0x0800, true); lok.setUint16(8, 0, true); lok.setUint16(10, czas, true); lok.setUint16(12, data, true);
    lok.setUint32(14, crc, true); lok.setUint32(18, b.length, true); lok.setUint32(22, b.length, true); lok.setUint16(26, nazwa.length, true); lok.setUint16(28, 0, true);
    czesci.push(new Uint8Array(lok.buffer), nazwa, b);
    const cen = new DataView(new ArrayBuffer(46));
    cen.setUint32(0, 0x02014b50, true); cen.setUint16(4, 20, true); cen.setUint16(6, 20, true); cen.setUint16(8, 0x0800, true); cen.setUint16(10, 0, true); cen.setUint16(12, czas, true); cen.setUint16(14, data, true);
    cen.setUint32(16, crc, true); cen.setUint32(20, b.length, true); cen.setUint32(24, b.length, true); cen.setUint16(28, nazwa.length, true); cen.setUint32(42, przes, true);
    centralne.push(new Uint8Array(cen.buffer), nazwa);
    przes += 30 + nazwa.length + b.length;
  }
  const rozm = centralne.reduce((s, x) => s + x.length, 0), kon = new DataView(new ArrayBuffer(22));
  kon.setUint32(0, 0x06054b50, true); kon.setUint16(8, pliki.length, true); kon.setUint16(10, pliki.length, true); kon.setUint32(12, rozm, true); kon.setUint32(16, przes, true);
  return new Blob([...czesci, ...centralne, new Uint8Array(kon.buffer)], { type: 'application/zip' });
}

/** Rozpakowuje archiwum ZIP (np. paczkę podpisanych plików pobraną z gov.pl) → [{ nazwa, bajty }]. Obsługuje zapis bez kompresji i deflate; katalogi i ukryte pliki pomija. */
export async function rozpakujZip(bajty) {
  const dv = new DataView(bajty.buffer, bajty.byteOffset, bajty.byteLength);
  let e = -1;
  for (let i = bajty.length - 22; i >= Math.max(0, bajty.length - 22 - 65535); i--) if (dv.getUint32(i, true) === 0x06054b50) { e = i; break; }
  if (e < 0) throw new Error('to nie jest archiwum ZIP');
  const ile = dv.getUint16(e + 10, true); let p = dv.getUint32(e + 16, true);
  if (ile === 0xFFFF || p === 0xFFFFFFFF) throw new Error('archiwum ZIP64 nie jest obsługiwane — rozpakuj je na dysku');
  const wynik = [], dekoder = new TextDecoder('utf-8');
  for (let n = 0; n < ile; n++) {
    if (p + 46 > bajty.length || dv.getUint32(p, true) !== 0x02014b50) throw new Error('uszkodzone archiwum ZIP');
    const flagi = dv.getUint16(p + 8, true), metoda = dv.getUint16(p + 10, true), skomp = dv.getUint32(p + 20, true), rozm = dv.getUint32(p + 24, true);
    const dlN = dv.getUint16(p + 28, true), dlE = dv.getUint16(p + 30, true), dlK = dv.getUint16(p + 32, true), lok = dv.getUint32(p + 42, true);
    const pelna = dekoder.decode(bajty.subarray(p + 46, p + 46 + dlN)); p += 46 + dlN + dlE + dlK;
    const nazwa = pelna.split('/').pop();
    if (!nazwa || pelna.endsWith('/') || nazwa.startsWith('.') || /(^|\/)__MACOSX\//.test(pelna)) continue;
    if (flagi & 1) throw new Error('archiwum ZIP jest zaszyfrowane hasłem');
    if (rozm > 200 * 1048576) throw new Error('plik w archiwum jest zbyt duży');
    const start = lok + 30 + dv.getUint16(lok + 26, true) + dv.getUint16(lok + 28, true), dane = bajty.subarray(start, start + skomp);
    if (metoda === 0) wynik.push({ nazwa, bajty: dane.slice() });
    else if (metoda === 8) {
      if (typeof DecompressionStream !== 'function') throw new Error('ta przeglądarka nie rozpakuje ZIP-a — rozpakuj plik na dysku');
      wynik.push({ nazwa, bajty: new Uint8Array(await new Response(new Blob([dane]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).arrayBuffer()) });
    } else throw new Error('nieobsługiwany sposób kompresji w archiwum ZIP');
  }
  return wynik;
}

/* ---------------------------------- scalanie PDF-ów z silnika (fpdf2: zwykła tablica xref, bez strumieni obiektów) ---------------------------------- */
const jakoTekst = b => { let s = ''; for (let i = 0; i < b.length; i += 8192) s += String.fromCharCode.apply(null, b.subarray(i, Math.min(b.length, i + 8192))); return s; };
const jakoBajty = s => { const b = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i) & 255; return b; };

/** Rozbiera PDF na obiekty: Map(numer → { slownik: tekst, strumien: Uint8Array | null }). Zawartość strumieni jest pomijana przy szukaniu kolejnych obiektów. */
function obiektyPdf(b) {
  const s = jakoTekst(b), wynik = new Map(), re = /(?:^|[\r\n])(\d+) (\d+) obj\b/g; let m;
  while ((m = re.exec(s))) {
    const nr = Number(m[1]), start = m.index + m[0].length, iE = s.indexOf('endobj', start), iS = s.indexOf('stream', start);
    if (iE < 0) break;
    if (iS >= 0 && iS < iE && /^\s*<<[\s\S]*>>\s*$/.test(s.slice(start, iS))) {
      const slownik = s.slice(start, iS).trim(); let p = iS + 6; if (s[p] === '\r') p++; if (s[p] === '\n') p++;
      const dl = slownik.match(/\/Length (\d+)(?! \d+ R)/); let koniec;
      if (dl && s.startsWith('endstream', p + Number(dl[1])) || (dl && /^[\r\n]+endstream/.test(s.slice(p + Number(dl[1]), p + Number(dl[1]) + 12)))) koniec = p + Number(dl[1]);
      else { koniec = s.indexOf('endstream', p); if (koniec < 0) break; if (s[koniec - 1] === '\n') koniec--; if (s[koniec - 1] === '\r') koniec--; }
      wynik.set(nr, { slownik, strumien: b.subarray(p, koniec) });
      const ek = s.indexOf('endobj', koniec); if (ek < 0) break; re.lastIndex = ek + 6;
    } else { wynik.set(nr, { slownik: s.slice(start, iE).trim(), strumien: null }); re.lastIndex = iE + 6; }
  }
  return wynik;
}
const refy = (tekst, przes) => tekst.replace(/(\d+) (\d+) R\b/g, (_, n, g) => `${Number(n) + przes} ${g} R`);

/** Skleja kilka PDF-ów (każdy z osobnymi stronami) w jeden: strony idą w podanej kolejności. Rzuca wyjątek, gdy któryś plik ma nietypową budowę. */
export function scalPdf(lista) {
  const obiekty = [], strony = []; let nastepny = 3;                 // 1 = drzewo stron, 2 = katalog
  for (const b of lista) {
    const ob = obiektyPdf(b); if (!ob.size) throw new Error('PDF nie do odczytania');
    const przes = nastepny - 1; let maks = 0, drzewo = null;
    for (const [nr, o] of ob) { maks = Math.max(maks, nr); if (/\/Type\s*\/Pages(?![A-Za-z])/.test(o.slownik)) drzewo = o.slownik; }
    if (!drzewo) throw new Error('PDF bez drzewa stron');
    const kids = (drzewo.match(/\/Kids\s*\[([^\]]*)\]/) || [, ''])[1].match(/\d+(?= \d+ R)/g) || [];
    const odziedziczone = [(drzewo.match(/\/MediaBox\s*\[[^\]]*\]/) || [''])[0], (drzewo.match(/\/Resources\s+\d+ \d+ R/) || [''])[0], (drzewo.match(/\/Rotate\s+\d+/) || [''])[0]];
    for (const [nr, o] of ob) {
      if (/\/Type\s*\/(Pages|Catalog)(?![A-Za-z])/.test(o.slownik)) continue;
      let sl = refy(o.slownik, przes);
      if (/\/Type\s*\/Page(?![A-Za-z])/.test(sl)) {
        sl = sl.replace(/\/Parent\s+\d+ \d+ R/, '/Parent 1 0 R');
        const dod = [['/MediaBox', odziedziczone[0]], ['/Resources', refy(odziedziczone[1], przes)], ['/Rotate', odziedziczone[2]]].filter(([k, v]) => v && !sl.includes(k + ' ') && !sl.includes(k + '[')).map(([, v]) => v).join(' ');
        if (dod) sl = sl.replace(/>>\s*$/, ' ' + dod + ' >>');
      }
      obiekty.push({ nr: nr + przes, slownik: sl, strumien: o.strumien });
    }
    for (const k of kids) strony.push(Number(k) + przes);
    nastepny += maks;
  }
  if (!strony.length) throw new Error('PDF bez stron');
  const czesci = [], przesuniecia = new Map(); let pozycja = 0;
  const dodaj = x => { const bb = typeof x === 'string' ? jakoBajty(x) : x; czesci.push(bb); pozycja += bb.length; };
  dodaj('%PDF-1.4\n%\xE2\xE3\xCF\xD3\n');
  const zapisz = (nr, slownik, strumien) => { przesuniecia.set(nr, pozycja); dodaj(`${nr} 0 obj\n${slownik}\n`); if (strumien) { dodaj('stream\n'); dodaj(strumien); dodaj('\nendstream\n'); } dodaj('endobj\n'); };
  zapisz(1, `<< /Type /Pages /Kids [${strony.map(n => n + ' 0 R').join(' ')}] /Count ${strony.length} >>`);
  zapisz(2, '<< /Type /Catalog /Pages 1 0 R >>');
  for (const o of obiekty) zapisz(o.nr, o.slownik, o.strumien);
  const razem = nastepny, xref = pozycja;
  let tab = `xref\n0 ${razem}\n0000000000 65535 f \n`;
  for (let n = 1; n < razem; n++) tab += przesuniecia.has(n) ? `${String(przesuniecia.get(n)).padStart(10, '0')} 00000 n \n` : '0000000000 65535 f \n';
  dodaj(tab + `trailer\n<< /Size ${razem} /Root 2 0 R >>\nstartxref\n${xref}\n%%EOF\n`);
  const wynik = new Uint8Array(pozycja); let p = 0; for (const c of czesci) { wynik.set(c, p); p += c.length; }
  return wynik;
}

/* ---------------------------------- dopasowanie wgranych plików do dokumentów ---------------------------------- */
const ROZSZERZENIA = /\.(pdf|xades|xml|sig|p7s|p7m|png|jpe?g|heic|heif|tiff?|webp)$/;
/** Nazwa pliku do porównań: bez ogonków, rozszerzeń i dopisków po podpisaniu/skanowaniu, same małe litery i spacje. */
export function normalizujNazwe(nazwa) {
  let s = String(nazwa).normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/gi, 'l').toLowerCase();
  while (ROZSZERZENIA.test(s)) s = s.replace(ROZSZERZENIA, '');
  return s.replace(/[^a-z0-9]+/g, ' ').replace(/\b(podpisany|podpisane|signed|sig|xades|skan|scan|kopia|copy)\b/g, ' ').replace(/\s+/g, ' ').trim();
}
/** Czy podpisany PDF zawiera oryginał: podpis PAdES dopisuje dane na końcu, więc początek i koniec oryginału leżą w tych samych miejscach. */
export function zawieraOryginal(podpisany, oryginal) {
  if (!podpisany || !oryginal || podpisany.length < oryginal.length || oryginal.length < 64) return false;
  const n = Math.min(oryginal.length, 4096); for (let i = 0; i < n; i++) if (podpisany[i] !== oryginal[i]) return false;
  const k = Math.min(oryginal.length, 1024); for (let i = oryginal.length - k; i < oryginal.length; i++) if (podpisany[i] !== oryginal[i]) return false;
  return true;
}
const naturalnie = (a, b) => a.name.localeCompare(b.name, 'pl', { numeric: true, sensitivity: 'base' });

/**
 * Do którego dokumentu należy każdy wgrany plik. dokumenty: [{ i, nazwa, tytul, wolny, bajty?: () => Promise<Uint8Array>, xades?: (tekst) => Promise<boolean> }] (wolny = jeszcze bez podpisu).
 * Kolejność prób: zawartość (PDF z podpisem zawiera oryginał, plik .xades zawiera jego skrót) → nazwa pliku (nazwa dokumentu, „Polecenie 3”, „Rozliczenie”, pojedyncza cyfra) → kolejność wgrania.
 * Zwraca [{ plik, i (numer dokumentu lub null), jak: 'tresc' | 'nazwa' | 'kolejnosc' | null }].
 */
export async function dopasujPliki(pliki, dokumenty, odczyt) {
  const wynik = pliki.map(plik => ({ plik, i: null, jak: null })), zajete = new Set();
  // dwa pliki mogą należeć do jednego dokumentu (np. podpisany PDF i jego .xades albo dwie strony skanu) — dlatego dopasowanie po zawartości i nazwie nie „zużywa” dokumentu
  // 1) zawartość
  for (const w of wynik) {
    const pdf = /\.pdf$/i.test(w.plik.name), xades = /\.(xades|xml)$/i.test(w.plik.name); if (!pdf && !xades) continue;
    const b = await odczyt(w.plik);
    for (const d of dokumenty) {
      if (pdf && d.bajty && zawieraOryginal(b, await d.bajty())) { w.i = d.i; w.jak = 'tresc'; zajete.add(d.i); break; }
      if (xades && d.xades && await d.xades(new TextDecoder('utf-8').decode(b))) { w.i = d.i; w.jak = 'tresc'; zajete.add(d.i); break; }      // podpis XML wskazuje dokument skrótem — rozpoznaję go niezależnie od nazwy pliku
    }
  }
  // 2) nazwa
  for (const w of wynik) {
    if (w.i !== null) continue;
    const n = normalizujNazwe(w.plik.name); let trafiony = null;
    for (const d of dokumenty) { const baza = normalizujNazwe(d.nazwa); if (baza && n.includes(baza)) { trafiony = d; break; } }
    if (!trafiony) { const m = n.match(/(?:polecenie|delegacja)\s*0*(\d+)/); if (m) trafiony = dokumenty.find(d => d.tytul === `Polecenie ${Number(m[1])}`) || null; }
    if (!trafiony && /\brozliczenie\b/.test(n)) trafiony = dokumenty.find(d => d.tytul === 'Rozliczenie') || null;
    if (!trafiony) { const m = n.match(/(?:^| )(\d{1,2})(?: |$)/); if (m) trafiony = dokumenty.find(d => d.tytul === `Polecenie ${Number(m[1])}`) || null; }
    if (trafiony) { w.i = trafiony.i; w.jak = 'nazwa'; zajete.add(trafiony.i); }
  }
  // 3) kolejność wgrania dla reszty: tylko dokumenty, które nie mają jeszcze podpisu ani pliku z tego wgrania
  const reszta = wynik.filter(w => w.i === null).sort((a, b) => naturalnie(a.plik, b.plik)), wolneDok = dokumenty.filter(d => d.wolny !== false && !zajete.has(d.i));
  reszta.forEach((w, k) => { if (wolneDok[k]) { w.i = wolneDok[k].i; w.jak = 'kolejnosc'; zajete.add(w.i); } });
  return wynik;
}
