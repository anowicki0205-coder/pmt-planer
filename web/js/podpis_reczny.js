// PMT Planer (web) — czy na skanie (albo zdjęciu) dokumentu jest podpis odręczny w miejscu „podpis pracownika”.
// Program zna dokładne miejsce podpisu na stronie (silnik zapisuje je przy tworzeniu PDF — współrzędne w mm), więc wycina ten fragment ze skanu i szuka śladu pisma:
// pomija proste kreski (linia podpisu, ramki tabeli) i drobny szum, a liczy zakrzywione ślady długopisu. To POMOC, nie dowód: ocenia obecność podpisu, nie jego autentyczność,
// a imienia i nazwiska odręcznie nie da się odczytać — dlatego okno zawsze pokazuje wycinek do obejrzenia i pozwala potwierdzić ręcznie. Działa w przeglądarce (canvas).

const A4 = { w: 210, h: 297 };
/* ---------------------------------- obrazy ze skanów ---------------------------------- */
/** Obrazy JPEG osadzone w PDF-ie ze skanu (typowy PDF z aplikacji skanującej: jeden obraz na stronę), w kolejności w pliku. */
export function obrazyZPdf(bajty) {
  const t = new TextDecoder('latin1').decode(bajty), wynik = []; const re = /\/Filter\s*(?:\[\s*)?\/DCTDecode/g; let m;
  while ((m = re.exec(t))) {
    const naglowek = t.lastIndexOf('obj', m.index), koniecSl = t.indexOf('stream', m.index); if (koniecSl < 0) continue;
    const slownik = t.slice(naglowek, koniecSl); if (!/\/Subtype\s*\/Image/.test(slownik)) continue;
    let s = koniecSl + 6; if (t[s] === '\r') s++; if (t[s] === '\n') s++;
    const dl = (slownik.match(/\/Length\s+(\d+)(?!\s+\d+\s+R)/) || [])[1]; let e = dl ? s + Number(dl) : -1;
    if (e < 0 || t.slice(e, e + 12).search(/endstream/) < 0) e = t.indexOf('endstream', s);
    if (e < 0) continue;
    const dane = bajty.slice(s, e); if (dane[0] === 0xff && dane[1] === 0xd8) wynik.push(dane);
    re.lastIndex = e;
  }
  return wynik;
}
const TYPY_OBRAZOW = { jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp', gif: 'image/gif', bmp: 'image/bmp' };
export const typObrazu = nazwa => TYPY_OBRAZOW[(String(nazwa).toLowerCase().match(/\.([a-z0-9]+)$/) || [, ''])[1]] || '';

/** Strony skanu jako bitmapy: z pliku graficznego albo z PDF-u ze skanem. Zwraca { strony: ImageBitmap[], powod }. */
export async function stronyZeSkanu(bajty, nazwa) {
  try {
    if (/\.pdf$/i.test(nazwa)) {
      const o = obrazyZPdf(bajty); if (!o.length) return { strony: [], powod: 'ten PDF nie zawiera skanu, który umiem odczytać (obrazu JPEG)' };
      return { strony: await Promise.all(o.map(d => createImageBitmap(new Blob([d], { type: 'image/jpeg' })))), powod: '' };
    }
    const typ = typObrazu(nazwa); if (!typ) return { strony: [], powod: 'ten format zdjęcia nie jest odczytywany w tej przeglądarce (np. HEIC)' };
    return { strony: [await createImageBitmap(new Blob([bajty], { type: typ }))], powod: '' };
  } catch (e) { return { strony: [], powod: 'nie udało się odczytać obrazu (' + (e.message || e) + ')' }; }
}

/* ---------------------------------- analiza ---------------------------------- */
const percentyl = (tab, p) => { const k = Uint8Array.from(tab).sort(); return k[Math.min(k.length - 1, Math.floor(k.length * p))]; };
function szarosc(bm, dlugi = 1700) {
  const sk = Math.min(1, dlugi / Math.max(bm.width, bm.height)), w = Math.max(1, Math.round(bm.width * sk)), h = Math.max(1, Math.round(bm.height * sk));
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h; const g = cv.getContext('2d', { willReadFrequently: true });
  g.fillStyle = '#fff'; g.fillRect(0, 0, w, h); g.drawImage(bm, 0, 0, w, h);
  const d = g.getImageData(0, 0, w, h).data, s = new Uint8Array(w * h);
  for (let i = 0; i < s.length; i++) s[i] = (d[4 * i] * 77 + d[4 * i + 1] * 150 + d[4 * i + 2] * 29) >> 8;
  return { s, w, h, cv };
}
/** Prostokąt kartki: gdy obraz jest już przycięty (skan), cały obraz; przy zdjęciu na tle — jasny prostokąt o proporcjach A4. */
function kartka(im) {
  const { s, w, h } = im, bialy = percentyl(s, .9), prog = bialy * .78, wier = new Float32Array(h), kol = new Float32Array(w);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (s[y * w + x] > prog) { wier[y]++; kol[x]++; }
  const gdzie = (t, n, p) => { let a = 0, b = n - 1; while (a < n && t[a] < p) a++; while (b > a && t[b] < p) b--; return [a, b]; };
  const [y0, y1] = gdzie(wier, h, w * .5), [x0, x1] = gdzie(kol, w, h * .5), bw = x1 - x0 + 1, bh = y1 - y0 + 1;
  if (bw < w * .35 || bh < h * .35) return null;
  const proporcja = bw / bh; if (Math.abs(proporcja - A4.w / A4.h) > .07) return null;
  const pokrycie = (bw * bh) / (w * h);
  return { x: x0, y: y0, w: bw, h: bh, bialy, calyObraz: pokrycie > .93 };
}
function skladowe(bin, w, h) {      // składowe spójne (8 sąsiadów): [{ n, x0, y0, x1, y1, piksele: [indeksy] }]
  const et = new Int32Array(w * h), wyn = []; const stos = [];
  for (let i = 0; i < bin.length; i++) {
    if (!bin[i] || et[i]) continue;
    const c = { n: 0, x0: w, y0: h, x1: 0, y1: 0, piksele: [] }; wyn.push(c); et[i] = wyn.length; stos.push(i);
    while (stos.length) {
      const p = stos.pop(), x = p % w, y = (p - x) / w; c.n++; c.piksele.push(p);
      if (x < c.x0) c.x0 = x; if (x > c.x1) c.x1 = x; if (y < c.y0) c.y0 = y; if (y > c.y1) c.y1 = y;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        const q = ny * w + nx; if (bin[q] && !et[q]) { et[q] = wyn.length; stos.push(q); }
      }
    }
  }
  return wyn;
}
function prosta(c, w) {             // czy składowa to prosta kreska (linia podpisu, ramka): rozrzut wokół najlepiej dopasowanej prostej < 2,4 px (kreska z szumem i rozmyciem)
  if (c.n < 20) return false;
  let sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0; const n = c.n;
  for (const p of c.piksele) { const x = p % w, y = (p - x) / w; sx += x; sy += y; sxx += x * x; sxy += x * y; syy += y * y; }
  const mx = sx / n, my = sy / n, vxx = sxx / n - mx * mx, vxy = sxy / n - mx * my, vyy = syy / n - my * my;
  const lam = (vxx + vyy) / 2 + Math.sqrt(Math.pow((vxx - vyy) / 2, 2) + vxy * vxy), lam2 = (vxx + vyy) - lam;      // wariancje wzdłuż i w poprzek głównego kierunku
  return Math.sqrt(Math.max(0, lam2)) < 2.4 && Math.sqrt(lam) > 6;
}

/**
 * Szuka śladu podpisu odręcznego w strefie strony. bitmapa: strona skanu; strefa: { x, y, w, h } w mm na kartce A4 (patrz silnik/most.py).
 * Zwraca { stan: 'jest' | 'brak' | 'nieznany', powod, ink (udział śladu w strefie), podglad (dataURL wycinka) }.
 */
export function szukajPodpisu(bitmapa, strefa) {
  if (bitmapa.width > bitmapa.height * 1.05) return { stan: 'nieznany', powod: 'zdjęcie jest poziome — obróć je tak, żeby kartka stała pionowo', ink: 0, podglad: '' };
  const im = szarosc(bitmapa), k = kartka(im);
  if (!k) return { stan: 'nieznany', powod: 'nie widzę całej kartki na obrazie (zdjęcie pod kątem, ucięty brzeg) — użyj skanu z aplikacji skanującej', ink: 0, podglad: '' };
  const mmX = k.w / A4.w, mmY = k.h / A4.h;
  const x0 = Math.round(k.x + strefa.x * mmX), y0 = Math.round(k.y + strefa.y * mmY), ww = Math.max(8, Math.round(strefa.w * mmX)), hh = Math.max(8, Math.round(strefa.h * mmY));
  const X0 = Math.max(0, x0), Y0 = Math.max(0, y0), X1 = Math.min(im.w, x0 + ww), Y1 = Math.min(im.h, y0 + hh), zw = X1 - X0, zh = Y1 - Y0;
  if (zw < 8 || zh < 8) return { stan: 'nieznany', powod: 'miejsce na podpis wypada poza obrazem', ink: 0, podglad: '' };
  const wycinek = new Uint8Array(zw * zh); for (let y = 0; y < zh; y++) for (let x = 0; x < zw; x++) wycinek[y * zw + x] = im.s[(Y0 + y) * im.w + X0 + x];
  const tlo = Math.max(percentyl(wycinek, .85), k.bialy * .8), prog = tlo * .66, bin = new Uint8Array(zw * zh);
  for (let i = 0; i < bin.length; i++) bin[i] = wycinek[i] < prog ? 1 : 0;
  let ink = 0, kolumny = new Uint8Array(zw);
  for (const c of skladowe(bin, zw, zh)) {
    if (c.n < 6 || prosta(c, zw)) continue;
    if (c.y0 > zh * .86 && (c.y1 - c.y0) < zh * .16) continue;      // drobny napis pod linią (podpis pracownika), który wchodzi do strefy przy przesunięciu skanu
    ink += c.n; for (let x = c.x0; x <= c.x1; x++) kolumny[x] = 1;
  }
  const udzial = ink / (zw * zh), rozpietosc = kolumny.reduce((a, b) => a + b, 0) / zw;
  // wycinek do obejrzenia (powiększony), z zaznaczoną strefą
  const pw = 560, ph = Math.round(pw * (zh + 2 * 14) / zw), cv = document.createElement('canvas'); cv.width = pw; cv.height = ph;
  const g = cv.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, pw, ph);
  g.drawImage(im.cv, X0, Math.max(0, Y0 - 14), zw, Math.min(im.h - Math.max(0, Y0 - 14), zh + 28), 0, 0, pw, ph);
  const jest = udzial >= .004 && ink >= 80 && rozpietosc >= .12;
  return { stan: jest ? 'jest' : 'brak', powod: '', ink: udzial, rozpietosc, podglad: cv.toDataURL('image/jpeg', .8) };
}

/** Strefa podpisu pracownika (mm, kartka A4) wg zapisanych przez silnik współrzędnych dokumentu: { strona, strefa } albo null. */
export function strefaPodpisu(miejsca) {
  if (!miejsca) return null;
  const m = (miejsca.miejsca || [])[0];
  if (m) return { strona: m.strona, strefa: { x: m.x + 5, y: m.y - 11.5, w: Math.max(20, m.w - 10), h: 9.7 }, opis: 'podpis pracownika' };
  // dokument bez wyznaczonego miejsca (rozliczenie miesiąca): podpis pod tabelą, w dolnej części ostatniej strony
  const y0 = Math.min(Math.max(miejsca.ostatni_y + 8, 150), 255);
  return { strona: miejsca.strony || 1, strefa: { x: 15, y: y0, w: 180, h: Math.max(20, 282 - y0) }, opis: 'dół strony pod tabelą' };
}
