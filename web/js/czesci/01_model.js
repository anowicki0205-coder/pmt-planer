/* ====================== model miesiąca (dane z silnika) ====================== */
const MIES = ['styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec', 'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień'];
const MIES_D = ['stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia'];
const DN = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela'];
const DK = ['pn', 'wt', 'śr', 'cz', 'pt', 'sb', 'nd'];
let LIMIT_DZIEN = 587.19, LIMIT_POL = 986.34, MIN_KWOTA = 50;   // nadpisywane stałymi z silnika (stale())
const ik = (id, kl = 'ik') => `<svg class="${kl}" aria-hidden="true"><use href="#${id}"/></svg>`;
const silnik = new Silnik();
let PROFIL = null;           // dane pracownika z urządzenia
let M = null;                // aktywny miesiąc (patrz zbudujModel)
let wybrany = 0;             // wybrany dzień miesiąca (1..N) albo 0
let PLAN_DZIS = [];          // plan wizyt na dziś (z importu planu) — pusty do czasu wczytania planu

const dzienTyg = d => (new Date(M.rok, M.mies - 1, d).getDay() + 6) % 7;   // 0 = poniedziałek
const polDla = d => M && M.polecenia.find(p => d >= p.od && d <= p.do);
const typDnia = d => !M ? 'nd' : M.trasy[d] ? 'trasa' : M.wolne.has(d) ? 'urlop' : M.robocze.has(d) ? 'bez' : 'nd';
const dwaCyfry = n => String(n).padStart(2, '0');
const dniMies = (r, m) => new Date(r, m, 0).getDate();
const minuty = s => { const [h, m] = s.split(':').map(Number); return h * 60 + m; };
const hhmm = m => `${dwaCyfry(Math.floor(m / 60) % 24)}:${dwaCyfry(Math.round(m % 60))}`;

/** Model miesiąca: stan 'plan' (przed generowaniem) albo 'gotowe' (jest wynik silnika). rec = rekord z magazynu lub null. */
function zbudujModel(rok, mies, rec, robocze0) {
  const N = dniMies(rok, mies);
  const par = (rec && rec.params) || {};
  const wolne = new Set((par.wolne || (M && M.rok === rok && M.mies === mies && M.stan === 'plan' ? [...M.wolne] : [])).map(Number));
  const m = { rok, mies, N, stan: rec && rec.wynik ? 'gotowe' : 'plan', robocze0: new Set(robocze0), wolne, robocze: new Set(),
    tryb: par.tryb || (PROFIL && PROFIL.tryb) || 'wieczory', silnik: par.silnik_powyzej_900 ?? (PROFIL ? PROFIL.silnik_powyzej_900 : true),
    kwota: par.kwota ?? 0, trasy: {}, dniT: [], polecenia: [], dok: [], rozliczenie: null, stawka: 0, suma: 0, wynik: null,
    podpisane: (rec && rec.podpisane) || [], wyslane: !!(rec && rec.wyslane) };
  for (const d of m.robocze0) if (!wolne.has(d)) m.robocze.add(d);
  if (rec && rec.wynik) {
    const w = rec.wynik; m.wynik = w; m.stawka = w.stawka; m.suma = w.suma;
    for (const dz of w.dni) { const d = Number(dz.data.slice(8)); m.trasy[d] = dz; }
    m.dniT = Object.keys(m.trasy).map(Number).sort((a, b) => a - b);
    m.polecenia = (w.dokumenty || []).map(x => ({ nr: x.nr, od: x.od, do: x.do, kw: x.kw, plik: x.plik }));
    m.rozliczenie = w.rozliczenie || null;
    while (m.podpisane.length < m.polecenia.length + 1) m.podpisane.push(false);
  }
  return m;
}
const razemDok = () => M ? M.polecenia.length + (M.rozliczenie ? 1 : 0) : 0;
const ilePodpisanych = () => M ? M.podpisane.filter(Boolean).length : 0;
const etapMiesiaca = () => !M || M.stan === 'plan' ? 'ustaw' : (M.wyslane ? 'wyslane' : (razemDok() && ilePodpisanych() >= razemDok() ? 'wyslij' : 'podpisz'));

const opisDnia = d => {
  const t = typDnia(d), k = `${DK[dzienTyg(d)]} ${d}.${dwaCyfry(M.mies)}`;
  if (t === 'trasa') return `${k} · <b>${fmt(M.trasy[d].suma)} zł</b> · <span>${fmt(M.trasy[d].km, 1)} km</span>`;
  if (t === 'bez') return `${k} · <span>dzień pracy bez trasy</span>`;
  if (t === 'urlop') return `${k} · <span>bez pracy</span>`;
  return `${k} · <span>dzień wolny</span>`;
};
