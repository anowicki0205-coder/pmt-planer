// PMT Planer (web) — adres zamieszkania w osobnych polach („Moje dane”) i jego złożenie w jeden napis, który rozumie silnik.
// Na dokumentach adres drukuje się DOKŁADNIE jak dotąd — silnik (waliduj_adres) dostaje ten sam napis co wcześniej: „[ul.|al.|pl.|os.] Nazwa numer[/lokal], kod miejscowość”
// (np. „ul. Polna 5/12, 00-001 Warszawa” albo, dla wsi bez ulicy, „Dębowa Wola 12, 26-660 Jedlińsk”). Pola tylko ułatwiają wpisywanie: rodzaj adresu (ulica albo miejscowość bez ulicy),
// nazwa ulicy (albo wsi), numer budynku, numer mieszkania (opcjonalny), kod pocztowy i miejscowość. Użytkownik wpisuje SAMĄ NAZWĘ ULICY („Polna”) — przedrostek „ul.” dopisuje program;
// aleję, plac i osiedle rozpoznaje po wpisanym przedrostku („al. Róż”, „pl. Wolności”, „os. Słoneczne”). Czyste funkcje — bez dostępu do interfejsu, sprawdza je testy/adres_pola_test.js.

const NUMER = /^\d+[a-zA-Z]?$/;
// ten sam wzór co waliduj_adres w silniku (silnik/pmt_silnik.py), żeby zapisany wcześniej adres dał się rozdzielić na pola tak, jak go rozumie silnik
const WZOR = /^(?:(ul\.|al\.|pl\.|ulica|aleja|plac|os\.|osiedle)\s+)?(.+?)\s+(\d+[a-zA-Z]?)(?:\s*[/\\]\s*(\d+[a-zA-Z]?))?[,\s]+\s*(\d{2}-\d{3})\s+(.+)$/i;
const PRZEDROSTEK = { ulica: 'ul.', aleja: 'al.', aleje: 'al.', plac: 'pl.', osiedle: 'os.', ul: 'ul.', al: 'al.', pl: 'pl.', os: 'os.', 'ul.': 'ul.', 'al.': 'al.', 'pl.': 'pl.', 'os.': 'os.' };
const WPISANY_PRZEDROSTEK = /^(ulica|aleje|aleja|plac|osiedle|ul|al|pl|os)(?:\.\s*|\s+)(.+)$/i;      // „ul. Polna”, „ul Polna”, „ulica Polna”, „ul.Polna”, „Aleja Róż”; „Ulańska” NIE (po „ul” musi być kropka albo spacja)
const spacje = t => String(t ?? '').replace(/\s+/g, ' ').trim();

/** Kod pocztowy w trakcie pisania: same cyfry i myślnik; po trzech–pięciu cyfrach bez myślnika wstawia go sam („00001” → „00-001”). */
export function kodWTrakcieWpisywania(t) {
  const v = String(t ?? '').replace(/[^\d-]/g, '');
  if (!v.includes('-')) return v.length >= 3 ? v.slice(0, 2) + '-' + v.slice(2, 5) : v;      // same cyfry: myślnik po drugiej, nadmiar (więcej niż 5 cyfr) ucięty
  return v.slice(0, 6);
}

/** Miejscowość w trakcie pisania: tylko litery, spacje, kropka, apostrof i myślnik — cyfry i inne znaki są odrzucane od razu. */
export function miejscowoscWTrakcieWpisywania(t) {
  return String(t ?? '').replace(/[^\p{L}\s.'’\-]/gu, '').replace(/\s{2,}/g, ' ').replace(/^\s+/, '');
}

/** Nazwa ulicy (albo wsi) w trakcie pisania. Numer budynku i mieszkania mają własne pola, więc cyfry są odrzucane od razu — z jednym wyjątkiem:
 *  PIERWSZE słowo nazwy ulicy może być liczbą, bo takie są nazwy („3 Maja”, „11 Listopada”, „1000-lecia”, „Aleja 3 Maja”). Cyfry dopisane po nazwie („Polna 5”) i w środku słowa („Polna5”) znikają.
 *  Wieś (wies: true) nie ma cyfr w ogóle. Przedrostek („ul.”, „al.”, „aleja”…) zostaje nietknięty. */
export function ulicaWTrakcieWpisywania(t, wies = false) {
  const surowe = String(t ?? '').replace(/[^\p{L}\d\s.'’\-]/gu, '').replace(/\s{2,}/g, ' ').replace(/^\s+/, '');
  if (wies) return surowe.replace(/\d/g, '').replace(/\s{2,}/g, ' ');
  const m = /^((?:ulica|aleje|aleja|plac|osiedle|ul|al|pl|os)(?:\.\s*|\s+))?(.*)$/i.exec(surowe), przedrostek = m[1] || '', reszta = m[2];
  let pierwsze = true;
  const wynik = reszta.split(/(\s+)/).map(w => {
    if (!w || /^\s+$/.test(w)) return w;
    const dozwolona = pierwsze && /^\d+(?:-\p{L}*)?$/u.test(w); pierwsze = false;
    if (dozwolona) return w;
    return /^\d/.test(w) ? '' : w.replace(/\d/g, '');      // słowo zaczynające się cyfrą („5”, „5a”, „12-14”) to numer domu — znika w całości; cyfry w środku słowa znikają same
  }).join('').replace(/\s{2,}/g, ' ');
  return przedrostek + wynik;
}

/** Z wpisanej nazwy ulicy → { przedrostek: 'ul.' | 'al.' | 'pl.' | 'os.' | '' (nie wpisano), nazwa }. „Polna” → { '', 'Polna' }, „ul. Polna” → { 'ul.', 'Polna' }, „aleja Róż” → { 'al.', 'Róż' }. */
export function rozpoznajPrzedrostek(tekst) {
  const t = spacje(tekst), m = WPISANY_PRZEDROSTEK.exec(t);
  return m ? { przedrostek: PRZEDROSTEK[m[1].toLowerCase()] || '', nazwa: spacje(m[2]) } : { przedrostek: '', nazwa: t };
}

/** Adres z jednego napisu (np. zapisanego wcześniej w profilu albo z programu na komputerze) → { typ, ulica, nr, lokal, kod, miasto } albo null, gdy napisu nie da się rozdzielić.
 *  Pole „ulica” ma samą nazwę („Polna”); przedrostek „ul.” jest domyślny, więc znika — zostaje tylko inny („al. Róż”). Rodzaj: z jawnego przedrostka = ulica; bez niego bierze się to, co zapisano wcześniej
 *  (typ: 'ulica' | 'wies'), a gdy nic nie wiadomo — ulica (podpowiedź przy wpisywaniu pokaże, czy nazwa to znana miejscowość). */
export function rozbierzAdres(tekst, typ) {
  const m = WZOR.exec(spacje(tekst)); if (!m) return null;
  const przedrostek = m[1] ? PRZEDROSTEK[m[1].toLowerCase()] || m[1].toLowerCase() : '', nazwa = spacje(m[2]);
  const rodzaj = przedrostek ? 'ulica' : typ === 'wies' ? 'wies' : 'ulica';
  return { typ: rodzaj, ulica: przedrostek && przedrostek !== 'ul.' ? przedrostek + ' ' + nazwa : nazwa, nr: m[3], lokal: m[4] || '', kod: m[5], miasto: spacje(m[6]) };
}

/** Pola → jeden napis dla silnika. Ulica: przedrostek (domyślnie „ul.”) + nazwa; wieś bez ulicy: sama nazwa wsi. Numer mieszkania (opcjonalny) dochodzi po ukośniku: „5/12”. */
export function zlozAdres(c) {
  const wies = c.typ === 'wies', { przedrostek, nazwa } = wies ? { przedrostek: '', nazwa: spacje(c.ulica) } : rozpoznajPrzedrostek(c.ulica);
  const nr = String(c.nr ?? '').replace(/\s+/g, ''), lokal = String(c.lokal ?? '').replace(/\s+/g, ''), kod = spacje(c.kod), miasto = spacje(c.miasto);
  return `${wies ? nazwa : (przedrostek || 'ul.') + ' ' + nazwa} ${nr}${lokal ? '/' + lokal : ''}, ${kod} ${miasto}`;
}

/** Ten sam adres BEZ dopisanego „ul.” — do pytania silnika, jak sam zaklasyfikowałby nazwę (znana miejscowość czy ulica); przedrostek wpisany przez użytkownika zostaje. */
export function zlozAdresBezDomyslnego(c) {
  const { przedrostek, nazwa } = rozpoznajPrzedrostek(c.ulica);
  const nr = String(c.nr ?? '').replace(/\s+/g, ''), lokal = String(c.lokal ?? '').replace(/\s+/g, '');
  return `${przedrostek ? przedrostek + ' ' : ''}${nazwa} ${nr}${lokal ? '/' + lokal : ''}, ${spacje(c.kod)} ${spacje(c.miasto)}`;
}

/** Sprawdza pola jedno po drugim: { ok, bledy: { ulica?, nr?, lokal?, kod?, miasto? } } — komunikaty po polsku, pod odpowiednimi polami. Numer mieszkania może być pusty. */
export function sprawdzPola(c) {
  const bledy = {}, wies = c.typ === 'wies', nr = String(c.nr ?? '').replace(/\s+/g, ''), lokal = String(c.lokal ?? '').replace(/\s+/g, ''), kod = spacje(c.kod), miasto = spacje(c.miasto);
  const { nazwa } = wies ? { nazwa: spacje(c.ulica) } : rozpoznajPrzedrostek(c.ulica), sameDrostek = !wies && /^(ulica|aleje|aleja|plac|osiedle|ul|al|pl|os)\.?$/i.test(spacje(c.ulica));      // „ul.” bez nazwy to nie nazwa
  if (!nazwa || sameDrostek) bledy.ulica = wies ? 'Podaj nazwę wsi (miejscowości bez ulicy)' : 'Podaj nazwę ulicy';
  else if (!/\p{L}/u.test(nazwa)) bledy.ulica = 'Nazwa ' + (wies ? 'wsi' : 'ulicy') + ' musi mieć litery';
  else if (/[^\p{L}\d\s.'’\-/]/u.test(nazwa)) bledy.ulica = 'Nazwa ma niedozwolony znak — wpisz samą nazwę, np. Polna albo 3 Maja';
  if (!NUMER.test(nr)) bledy.nr = 'Podaj numer budynku, np. 5 albo 12A';
  if (lokal && !NUMER.test(lokal)) bledy.lokal = 'Numer mieszkania: cyfry, ewentualnie litera (3 albo 3a)';
  if (!/^\d{2}-\d{3}$/.test(kod)) bledy.kod = 'Kod pocztowy w formacie 00-000';
  if (!miasto) bledy.miasto = 'Podaj miejscowość';
  else if (/\d/.test(miasto)) bledy.miasto = 'Miejscowość nie powinna mieć cyfr';
  else if (/[^\p{L}\s.'’\-]/u.test(miasto)) bledy.miasto = 'Miejscowość ma niedozwolony znak';
  return { ok: !Object.keys(bledy).length, bledy };
}
