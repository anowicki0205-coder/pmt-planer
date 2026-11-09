// PMT Planer (web) — widowisko generowania: zamiast czekania na silnik użytkownik widzi, co się dzieje (punkty GPS zapalają się, trasa się rysuje, kartki układają się w stos),
// a po wyniku stos rozkłada się w wachlarz PRAWDZIWYCH dokumentów (numery i kwoty z silnika, suma liczy się w górę). Silnik zgłasza postęp w trzech krokach (GPS 10 %, trasy 40 %, PDF 85 %),
// więc między nimi pasek „dopełza” sam, żeby nic nie stało w miejscu. Kliknięcie albo Esc w czasie pokazu wyników pomija go (kliknięcie jest połykane, nie trafia w pulpit pod spodem).
// Czysty DOM — niczego nie wie o aplikacji; o tym, czy pokaz w ogóle ma ruszyć („życie”, „Ogranicz ruch” w systemie), decyduje wywołujący.

const NS = 'http://www.w3.org/2000/svg';
const PUNKTY = 7;
const PROGI = [0.10, 0.40, 0.85, 1];      // kroki zgłaszane przez silnik (most.py: generuj)
const SCIEZKA = 'M18 108C82 18 140 138 226 72S372 8 504 54';
const ogranicz = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const el = (nazwa, klasa, tekst) => { const e = document.createElement(nazwa); if (klasa) e.className = klasa; if (tekst !== undefined) e.textContent = tekst; return e; };
const svg = (nazwa, atr = {}) => { const e = document.createElementNS(NS, nazwa); for (const k in atr) e.setAttribute(k, atr[k]); return e; };

/** opcje: { fmt: liczba → tekst („1 234,50”), naPunkt: (i, n) → () — wywoływane raz dla każdego zapalonego punktu trasy (i-ty z n) }. Zwraca { start(), postep(tekst, v), zakoncz(dane) → Promise, przerwij() }. dane: { polecenia: [{ nr, kw }], suma }. */
export function widowisko(opcje = {}) {
  const fmt = opcje.fmt || (x => Number(x).toFixed(2).replace('.', ','));
  let root = null, sciezka = null, kropki = [], faza = null, proc = null, razem = null, wachlarz = null;
  let vRzecz = 0, vWid = 0, zegar = 0, pominiete = false, czekanie = null, liczenie = null, zapalone = 0;

  function rysuj() {
    if (!root) return;
    const jasne = Math.ceil(ogranicz(vWid / PROGI[1]) * PUNKTY);
    for (; zapalone < jasne; zapalone++) { try { if (opcje.naPunkt) opcje.naPunkt(zapalone, PUNKTY); } catch (e) { /* dźwięk nie psuje pokazu */ } }      // każdy nowo zapalony punkt trasy zgłasza się wywołującemu (dźwięk)
    kropki.forEach((c, i) => c.classList.toggle('on', i < jasne));
    sciezka.style.strokeDashoffset = String(1 - ogranicz((vWid - PROGI[0]) / (PROGI[2] - PROGI[0])));
    proc.textContent = Math.round(ogranicz(vWid) * 100) + '%';
    root.classList.toggle('faza-gps', vRzecz < PROGI[1]); root.classList.toggle('faza-trasa', vRzecz >= PROGI[1] && vRzecz < PROGI[2]); root.classList.toggle('faza-druk', vRzecz >= PROGI[2]);
  }
  function krok() {      // wyświetlany postęp dogania prawdziwy, a między krokami silnika wolno „dopełza” do progu następnego (nigdy go nie przekracza)
    const nast = PROGI.find(p => p > vRzecz + 1e-9) ?? 1, sufit = Math.max(vRzecz, nast - 0.03);
    vWid = vWid < vRzecz ? vWid + (vRzecz - vWid) * 0.3 + 0.002 : Math.min(sufit, vWid + (sufit - vWid) * 0.02 + 0.0005);
    rysuj();
  }
  const czekaj = (ms, przerywalne = true) => new Promise(ok => { if (przerywalne && pominiete) return ok(); const t = setTimeout(() => { czekanie = null; ok(); }, ms); czekanie = () => { clearTimeout(t); czekanie = null; ok(); }; });
  const pominWKliku = e => { if (e.type === 'keydown' && e.key !== 'Escape') return; e.preventDefault(); e.stopPropagation(); pominiete = true; if (liczenie) liczenie(); if (czekanie) czekanie(); };      // bez czekania na klatkę animacji: pominięcie działa od razu, także gdy strona jest obciążona
  function usun() {
    if (liczenie) liczenie(); if (czekanie) czekanie();      // przerwanie w trakcie pokazu nie zostawia wiszącej obietnicy
    clearInterval(zegar); zegar = 0; document.removeEventListener('click', pominWKliku, true); document.removeEventListener('keydown', pominWKliku, true);
    if (root) root.remove(); root = null; kropki = [];
  }

  function start() {
    if (root) return;
    root = el('div', 'gen-scena faza-gps'); root.id = 'gen-scena'; root.setAttribute('aria-hidden', 'true');
    const panel = el('div', 'gen-panel'), gora = el('div', 'gen-gora'), plansza = el('div', 'gen-plansza'), dol = el('div', 'gen-dol');
    faza = el('b', 'gen-faza', 'Start…'); proc = el('span', 'gen-proc num', '0%'); gora.append(faza, proc);
    const rys = svg('svg', { class: 'gen-trasa', viewBox: '0 0 520 130', preserveAspectRatio: 'xMidYMid meet' }), punkty = svg('g', { class: 'gen-punkty' });
    sciezka = svg('path', { d: SCIEZKA, class: 'gen-sciezka', pathLength: '1' });
    rys.append(svg('path', { d: SCIEZKA, class: 'gen-sciezka-tlo' }), sciezka, punkty);
    const stos = el('div', 'gen-stos'); for (let i = 0; i < 4; i++) { const k = el('i'); k.style.setProperty('--k', String(i)); stos.appendChild(k); }
    wachlarz = el('div', 'gen-wachlarz'); razem = el('span', 'gen-razem'); dol.appendChild(razem);
    plansza.append(rys, stos, wachlarz); panel.append(gora, plansza, dol); root.append(el('div', 'gen-tlo'), panel); document.body.appendChild(root);
    const dl = sciezka.getTotalLength ? sciezka.getTotalLength() : 0;      // punkty leżą na ścieżce (długość da się zmierzyć dopiero po wstawieniu do strony)
    for (let i = 0; i < PUNKTY; i++) { const p = dl ? sciezka.getPointAtLength(dl * i / (PUNKTY - 1)) : { x: 18 + i * 81, y: 70 }; const c = svg('circle', { cx: p.x.toFixed(1), cy: p.y.toFixed(1), r: '5.5' }); punkty.appendChild(c); kropki.push(c); }
    vRzecz = vWid = 0; zapalone = 0; pominiete = false; rysuj(); zegar = setInterval(krok, 90);
  }
  function postep(tekst, v) {
    if (!root) return;
    vRzecz = Math.max(vRzecz, Number(v) || 0);
    if (tekst) faza.textContent = String(tekst).replace(/\.{3}$/, '…');
  }
  /** Pokaz wyników: stos rozkłada się w wachlarz dokumentów z prawdziwymi kwotami; kwoty i suma liczą się w górę. Wraca, gdy pokaz się skończy (albo użytkownik go pominie). */
  async function zakoncz(d) {
    if (!root) return;
    clearInterval(zegar); zegar = 0; vRzecz = vWid = 1; rysuj(); faza.textContent = 'Gotowe';
    root.classList.remove('faza-gps', 'faza-trasa', 'faza-druk'); root.classList.add('faza-wynik');
    const wiersze = [...(d.polecenia || []).map(p => ({ znak: 'P' + p.nr, kw: Number(p.kw) || 0 })), { znak: 'R', kw: Number(d.suma) || 0 }], liczniki = [];
    wiersze.forEach((w, i) => {
      const kafel = el('div', 'gen-kafel'), kw = el('span', 'num', fmt(0)); kafel.style.setProperty('--i', String(i));
      const kartka = el('i', 'gen-kartka'); for (let j = 0; j < 4; j++) kartka.appendChild(el('span', 'l'));
      kafel.append(kartka, el('b', '', w.znak), kw); wachlarz.appendChild(kafel); liczniki.push({ el: kw, do: w.kw });
    });
    const poleceń = wiersze.length - 1, ile = poleceń === 1 ? 'polecenie' : poleceń > 1 && poleceń < 5 ? 'polecenia' : 'poleceń';
    const ustawSume = x => { razem.textContent = `Razem ${fmt(x)} zł · ${poleceń} ${ile} i rozliczenie`; };
    ustawSume(0);
    document.addEventListener('click', pominWKliku, true); document.addEventListener('keydown', pominWKliku, true);
    const t0 = performance.now(), DL = 900;
    await new Promise(ok => {
      liczenie = () => { liczenie = null; ok(); };
      const nastepna = () => {      // klatka animacji, a gdy jej nie ma (obciążona strona, karta w tle) — zegar: liczenie zawsze dobiega końca w ~DL, a nie czeka na powrót do karty
        let bylo = false; const raz = () => { if (bylo) return; bylo = true; clearTimeout(t); klatka(); }; const t = setTimeout(raz, 80); requestAnimationFrame(raz);
      };
      const klatka = () => {
        if (!root || !liczenie) return;
        const x = pominiete ? 1 : ogranicz((performance.now() - t0) / DL), e = 1 - Math.pow(1 - x, 3);
        liczniki.forEach(l => { l.el.textContent = fmt(l.do * e); }); ustawSume((Number(d.suma) || 0) * e);
        x < 1 ? nastepna() : liczenie();
      };
      klatka();
    });
    if (!root) return;      // przerwane w trakcie liczenia
    await czekaj(1000);
    if (root && !pominiete) { root.classList.add('gen-znika'); await czekaj(300, false); }
    usun();
  }
  return { start, postep, zakoncz, przerwij: usun };
}
