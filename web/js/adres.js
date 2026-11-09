// PMT Planer (web) — adres zamieszkania w osobnych polach („Moje dane”) i jego złożenie w jeden napis, który rozumie silnik.
// Na dokumentach adres drukuje się DOKŁADNIE jak dotąd — silnik (waliduj_adres) dostaje ten sam napis co wcześniej: „[ul.|al.|pl.|os.] Nazwa numer[/lokal], kod miejscowość”
// (np. „ul. Polna 5/12, 00-001 Warszawa” albo, bez ulicy, „Dębowa Wola 12, 26-660 Jedlińsk”). Pola tylko ułatwiają wpisywanie: ulica (albo nazwa wsi), numer budynku, numer mieszkania
// (opcjonalny), kod pocztowy i miejscowość. Czyste funkcje — bez dostępu do interfejsu, sprawdza je testy/adres_pola_test.js.

const NUMER = /^\d+[a-zA-Z]?$/;
// ten sam wzór co waliduj_adres w silniku (silnik/pmt_silnik.py), żeby zapisany wcześniej adres dał się rozdzielić na pola tak, jak go rozumie silnik
const WZOR = /^(?:(ul\.|al\.|pl\.|ulica|aleja|plac|os\.|osiedle)\s+)?(.+?)\s+(\d+[a-zA-Z]?)(?:\s*[/\\]\s*(\d+[a-zA-Z]?))?[,\s]+\s*(\d{2}-\d{3})\s+(.+)$/i;
const PRZEDROSTEK = { ulica: 'ul.', aleja: 'al.', plac: 'pl.', osiedle: 'os.', 'ul.': 'ul.', 'al.': 'al.', 'pl.': 'pl.', 'os.': 'os.' };
const spacje = t => String(t ?? '').replace(/\s+/g, ' ').trim();

/** Kod pocztowy w trakcie pisania: same cyfry i myślnik; po trzech–pięciu cyfrach bez myślnika wstawia go sam („00001” → „00-001”). */
export function kodWTrakcieWpisywania(t) {
  const v = String(t ?? '').replace(/[^\d-]/g, '');
  if (!v.includes('-')) return v.length >= 3 ? v.slice(0, 2) + '-' + v.slice(2, 5) : v;      // same cyfry: myślnik po drugiej, nadmiar (więcej niż 5 cyfr) ucięty
  return v.slice(0, 6);
}

/** Adres z jednego napisu (np. zapisanego wcześniej w profilu) → { ulica, nr, lokal, kod, miasto } albo null, gdy napisu nie da się rozdzielić. */
export function rozbierzAdres(tekst) {
  const m = WZOR.exec(spacje(tekst)); if (!m) return null;
  const przedrostek = m[1] ? PRZEDROSTEK[m[1].toLowerCase()] || m[1].toLowerCase() : '';
  return { ulica: (przedrostek ? przedrostek + ' ' : '') + spacje(m[2]), nr: m[3], lokal: m[4] || '', kod: m[5], miasto: spacje(m[6]) };
}

/** Pola → jeden napis dla silnika. Numer mieszkania (opcjonalny) dochodzi po ukośniku: „5/12”. */
export function zlozAdres(c) {
  const ulica = spacje(c.ulica), nr = String(c.nr ?? '').replace(/\s+/g, ''), lokal = String(c.lokal ?? '').replace(/\s+/g, ''), kod = spacje(c.kod), miasto = spacje(c.miasto);
  return `${ulica} ${nr}${lokal ? '/' + lokal : ''}, ${kod} ${miasto}`;
}

/** Sprawdza pola jedno po drugim: { ok, bledy: { ulica?, nr?, lokal?, kod?, miasto? } } — komunikaty po polsku, pod odpowiednimi polami. Numer mieszkania może być pusty. */
export function sprawdzPola(c) {
  const bledy = {}, ulica = spacje(c.ulica), nr = String(c.nr ?? '').replace(/\s+/g, ''), lokal = String(c.lokal ?? '').replace(/\s+/g, ''), kod = spacje(c.kod), miasto = spacje(c.miasto);
  if (!ulica) bledy.ulica = 'Podaj ulicę albo, gdy jej nie ma, nazwę wsi';
  if (!NUMER.test(nr)) bledy.nr = 'Podaj numer budynku, np. 5 albo 12A';
  if (lokal && !NUMER.test(lokal)) bledy.lokal = 'Numer mieszkania: cyfry, ewentualnie litera (3 albo 3a)';
  if (!/^\d{2}-\d{3}$/.test(kod)) bledy.kod = 'Kod pocztowy w formacie 00-000';
  if (!miasto) bledy.miasto = 'Podaj miejscowość';
  return { ok: !Object.keys(bledy).length, bledy };
}
