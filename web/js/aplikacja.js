// PMT Planer (web) — aplikacja. Wygląd i ruch: z makiety „Ciekłe szkło" (ciekle szklo + zorza); dane: z silnika (js/silnik.js).
// Plik składany narzędziem narzedzia/zloz_aplikacje.py z mockupu i z js/czesci/ — po złożeniu edytuj js/aplikacja.js bezpośrednio.
import { Silnik } from './silnik.js';
import { profil as magProfil, miesiace as magMiesiace, ustawienia as magUst, pliki as magPliki, nazwaKlucza, plan as magPlan, wizyty as magWizyty, ustawKonto, usunKonto as magUsunKonto, odblokuj as magOdblokuj, migruj as magMigruj, czytelny as magCzytelny, wyczyscMagazyn as magWyczysc } from './magazyn.js';
import * as dostep from './dostep.js';
import * as przen from './przeniesienie.js';
import { zainstalujZywe } from './zywe.js';
import { zainstalujPomoc } from './pomoc.js';
import { zainstalujPodpis } from './podpis.js';

/* Ochrona przed osadzeniem w cudzej ramce (clickjacking: niewidoczna strona z naszym oknem logowania pod kursorem). Nagłówka frame-ancestors nie da się ustawić z meta, więc robi to kod:
   w ramce nic się nie pokazuje, a przeglądarka dostaje polecenie wyjścia z niej. */
if (window.top !== window.self) { document.documentElement.style.display = 'none'; try { window.top.location = window.self.location.href; } catch (e) { /* inna domena: zostaje ukryta strona */ } throw new Error('Aplikacja nie działa w ramce.'); }


/* ====================== czas, pomocnicze ====================== */
const czas = () => performance.now() * (window.__tempo ?? 1);
/* animacje CSS i WAAPI (.animate) biegną w zegarze dokumentu — narzędzie wideo zwalnia je osobno (CDP Animation.setPlaybackRate),
   więc ich czasów NIE dzielimy przez __tempo (inaczej w nagraniu byłyby zwolnione podwójnie) */
const doc = document, root = doc.documentElement;
const $ = (s, r = doc) => r.querySelector(s);
const $$ = (s, r = doc) => [...r.querySelectorAll(s)];
const mq = q => { try { return matchMedia(q); } catch (e) { return { matches: false, addEventListener() {} }; } };
const JASNY = mq('(prefers-color-scheme: light)');
/* CZASOWO (decyzja właściciela, test płynności): animacje są WYŁĄCZONE dla wszystkich — zorza w tle jest narysowana raz (nieruchomo), nie ma efektów kursora (światło kafli, przechylanie, magnes, iskry),
   ciągłych animacji CSS (poświaty, pulsowanie), przejść między widokami, staczania cyfr, konfetti i fanfar. Użytkownik niczego nie wybiera.
   Kod pełnego ruchu zostaje nietknięty: przywrócenie = zmiana jednej linii poniżej na `const spokoj = false` (testy sprawdzające ruch ustawiają hak window.__ruchPelny).
   Drugi hak testowy: window.__zorzaRzadko (testy na grafice programowej) odświeża zorzę rzadko, żeby testy nie czekały godzinami. */
const spokoj = !window.__ruchPelny, rzadko = !!window.__zorzaRzadko;
if (spokoj) document.documentElement.classList.add('spokojne');
/* ŻYCIE kalendarza i fiolek dokumentów (prośba właściciela): lekki, ciągły ruch CSS tylko w tych dwóch kaflach, mimo trybu spokojnego (szczegóły i lista animacji: koniec css/aplikacja.css).
   Wyłączenie: `const zycie = false` (testy używają haka window.__bezZycia). Przy „Ogranicz ruch” w systemie CSS i tak niczego nie rusza. */
const zycie = !window.__bezZycia;
if (zycie) document.documentElement.classList.add('zyje');
const NBSP = ' ';
/* szyna sygnałów: aplikacja ogłasza, co się zmieniło (kalendarz, hero, trasa dnia…), a moduł „żywego interfejsu” (js/zywe.js) dokłada do tego ruch i interakcje */
const sygnal = n => { try { doc.dispatchEvent(new CustomEvent('pmt:' + n)); } catch (e) { /* bez sygnału aplikacja działa tak samo, tylko spokojniej */ } };
const fmt = (n, d = 2) => { let [c, u] = Math.abs(n).toFixed(d).split('.'); c = c.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP); return (n < 0 ? '−' : '') + c + (u ? ',' + u : ''); };
const dwa = n => String(n).padStart(2, '0');
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const pauza = ms => new Promise(res => {
  if (spokoj || ms <= 0) { requestAnimationFrame(() => res()); return; }
  const t0 = czas(); const f = () => (czas() - t0 >= ms) ? res() : requestAnimationFrame(f); requestAnimationFrame(f);
});
const zegar = ms => new Promise(res => setTimeout(res, spokoj ? 0 : ms / (window.__tempo ?? 1)));
const tween = (ms, f, ease = p => 1 - Math.pow(1 - p, 4)) => new Promise(res => {
  if (spokoj) { f(1); res(); return; }
  const t0 = czas(); const k = () => { const p = Math.min(1, (czas() - t0) / ms); f(ease(p)); p < 1 ? requestAnimationFrame(k) : res(); }; requestAnimationFrame(k);
});
const mulberry = a => () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
const token = n => getComputedStyle(root).getPropertyValue(n).trim();
const tokenRGB = n => { const m = token(n).match(/^#([0-9a-f]{6})$/i); if (!m) return [1, 1, 1]; const x = parseInt(m[1], 16); return [(x >> 16 & 255) / 255, (x >> 8 & 255) / 255, (x & 255) / 255]; };
const pamiec = {
  get(k) { try { return localStorage.getItem('pmt-ui-' + k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem('pmt-ui-' + k, v); } catch (e) {} }
};
/* przejście widoku; rodzaj trafia do html[data-vt], by CSS zostawił tylko potrzebne nazwy przejść;
   na czas przejścia zorza stoi (tło szkła się nie zmienia — tańsze przechwycenie i płynniejszy ruch) */
let vtTrwa = null;
function przejscie(zmiana, potem, rodzaj = 'zwykle', szcz = {}) {
  if (vtTrwa) { try { vtTrwa.skipTransition(); } catch (e) {} }
  if (spokoj) { zmiana(); potem && potem(); return null; }
  if (rodzaj !== 'motyw') zorza && zorza.flara(.22);      // zorza rozbłyska przy każdym przejściu
  if (!doc.startViewTransition) { przejscieReczne(zmiana, potem, rodzaj, szcz); return null; }
  root.dataset.vt = rodzaj;
  if (rodzaj !== 'motyw') wstrzymajRuch(true);      // przy zmianie motywu tło płynie dalej przez całe 3 s
  let vt;
  const koniec = () => { if (vtTrwa === vt) vtTrwa = null; if (!vtTrwa) { delete root.dataset.vt; if (rodzaj !== 'motyw') wstrzymajRuch(false); } potem && potem(); };
  try { vt = doc.startViewTransition(zmiana); } catch (e) { zmiana(); delete root.dataset.vt; wstrzymajRuch(false); potem && potem(); return null; }
  vtTrwa = vt;
  vt.ready.catch(() => {}); vt.updateCallbackDone.catch(() => {});
  vt.finished.then(koniec, koniec);
  return vt;
}

/* ---- ten sam ruch bez View Transitions (Firefox, starsze Safari): ręcznie, na Web Animations ----
   Zmiana stanu dzieje się od razu (kod wokół na to liczy), a ruch dokłada się na nowej treści; stare znika przez nakładkę-klon tam, gdzie to ma sens. */
const E_WYJ = 'cubic-bezier(.16,1,.3,1)', E_SPR = 'cubic-bezier(.34,1.56,.64,1)';
function anim(el, klatki, opcje) { if (spokoj) return null; try { return el && el.animate(klatki, { fill: 'backwards', easing: E_WYJ, ...opcje }); } catch (e) { return null; } }
const widoczne = sel => [...doc.querySelectorAll(sel)].filter(e => e.getClientRects().length);
function klonWyjscia(el, kier, czasMs = 240) {
  if (!el || !el.getClientRects().length) return;
  const op = el.offsetParent || el.parentElement, k = el.cloneNode(true);
  k.removeAttribute('id'); [...k.querySelectorAll('[id]')].forEach(x => x.removeAttribute('id')); k.setAttribute('aria-hidden', 'true'); k.setAttribute('inert', '');
  k.style.cssText = `position:absolute;left:${el.offsetLeft}px;top:${el.offsetTop}px;width:${el.offsetWidth}px;height:${el.offsetHeight}px;margin:0;pointer-events:none;view-transition-name:none`;
  op.appendChild(k);
  const a = k.animate([{ opacity: 1, transform: 'none' }, { opacity: 0, transform: `translateX(${-kier * 22}px)` }], { duration: czasMs, easing: 'cubic-bezier(.4,0,1,1)', fill: 'forwards' });
  const kon = () => k.remove(); a.onfinish = kon; a.oncancel = kon; setTimeout(kon, czasMs + 120);
}
function przejscieReczne(zmiana, potem, rodzaj, szcz) {
  const kier = Number(root.style.getPropertyValue('--kier')) || 1;
  if (rodzaj === 'dzien') {
    const el = $('#dzien-tresc'), pier = $('.pierscien'), a = pier && pier.getBoundingClientRect();
    klonWyjscia(el, kier); zmiana();
    anim(el, [{ opacity: 0, transform: `translateX(${kier * 26}px)`, filter: 'blur(3px)' }, { opacity: 1, transform: 'none', filter: 'blur(0)' }], { duration: 560, delay: 70 });
    const b = pier && pier.getBoundingClientRect();
    if (a && b && (Math.abs(a.left - b.left) > 1 || Math.abs(a.top - b.top) > 1)) anim(pier, [{ transform: `translate(${a.left - b.left}px,${a.top - b.top}px)` }, { transform: 'none' }], { duration: 640, easing: E_SPR });
  } else if (rodzaj === 'dzis') {
    zmiana();
    if (szcz.znak != null) {
      const z = $(`.p-znak[data-i="${szcz.znak}"]`); if (z && z.getAttribute('aria-pressed') === 'true') { z.classList.add('pop'); setTimeout(() => z.classList.remove('pop'), 600); const r = z.getBoundingClientRect(); iskry(r.left + r.width / 2, r.top + r.height / 2); }
    } else widoczne('#przystanki .przystanek').slice(0, 10).forEach((r, i) => anim(r, [{ opacity: 0, transform: 'translateX(18px)' }, { opacity: 1, transform: 'none' }], { duration: 460, delay: i * 38 }));
  } else if (rodzaj === 'skupienie') {
    const el = szcz.el, r0 = el.getBoundingClientRect(); zmiana(); const r1 = el.getBoundingClientRect();
    if (szcz.otwiera) {            // rozwinięcie: nowa treść odsłania się z miejsca, które kafel zajmował
      const t = Math.max(0, r0.top - r1.top), l = Math.max(0, r0.left - r1.left), pr = Math.max(0, r1.right - r0.right), d = Math.max(0, r1.bottom - r0.bottom);
      anim(el, [{ clipPath: `inset(${t}px ${pr}px ${d}px ${l}px round 28px)`, opacity: .85 }, { clipPath: 'inset(0px 0px 0px 0px round 28px)', opacity: 1 }], { duration: 640, easing: 'cubic-bezier(.65,0,.2,1)' });
    } else anim(el, [{ opacity: .55, transform: 'scale(1.045)' }, { opacity: 1, transform: 'none' }], { duration: 520 });
  } else if (rodzaj === 'zakladka') {
    zmiana(); widoczne('.bento > .kafel').forEach((k, i) => anim(k, [{ opacity: 0, transform: `translateX(${(szcz.kier || 1) * 34}px) scale(.98)` }, { opacity: 1, transform: 'none' }], { duration: 520, delay: i * 50 }));
  } else {          // zwykle: miesiąc, generowanie — kafle wchodzą po kolei
    zmiana(); widoczne('.bento > .kafel > .w').forEach((w, i) => anim(w, [{ opacity: .25, transform: 'translateY(12px) scale(.992)', filter: 'blur(4px)' }, { opacity: 1, transform: 'none', filter: 'blur(0)' }], { duration: 560, delay: i * 55 }));
  }
  potem && potem();
}
/* iskry i fala dotyku: informacja zwrotna, że aplikacja „poczuła” kliknięcie */
function iskry(x, y, n = 7) {
  if (spokoj) return;
  for (let i = 0; i < n; i++) {
    const d = doc.createElement('i'); d.className = 'iskra'; d.style.left = x + 'px'; d.style.top = y + 'px'; doc.body.appendChild(d);
    const kat = (i / n) * Math.PI * 2 + Math.random() * .6, odl = 22 + Math.random() * 20;
    const a = d.animate([{ transform: 'translate(0,0) scale(1)', opacity: 1 }, { transform: `translate(${Math.cos(kat) * odl}px,${Math.sin(kat) * odl}px) scale(.2)`, opacity: 0 }], { duration: 520 + Math.random() * 180, easing: 'cubic-bezier(.2,.8,.3,1)' });
    a.onfinish = () => d.remove(); setTimeout(() => d.remove(), 900);
  }
}
/** Konfetti: n kolorowych drobin wylatuje z punktu (x, y) i opada. Wszystko rysuje jedno płótno (2D), więc to jedna warstwa kompozycji, a nie setki elementów. */
const KONF = { cv: null, g: null, cz: [], raf: 0, ost: 0, dpr: 1 };
function konfetti(x, y, n, o = {}) {
  if (spokoj) return;
  const st = getComputedStyle(root), kol = ['--burs', '--mieta', '--cyan', '--roz', '--fiolet', '--ziel', '--biel'].map(v => st.getPropertyValue(v).trim() || '#fff');
  for (let i = 0; i < n; i++) {
    const a = (o.kat ?? -Math.PI / 2) + (Math.random() - .5) * (o.roz ?? 1.5), v = (o.v ?? 540) * (.4 + Math.random() * .8), w = 5 + Math.random() * 7;
    KONF.cz.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, w, h: Math.random() < .5 ? w : w * 2.2, r: Math.random() * 6.28, vr: (Math.random() - .5) * 14, c: kol[i % kol.length], kolo: Math.random() < .35, t: 0, zycie: 1.8 + Math.random() * 1.4 });
  }
  if (!KONF.cv) {
    const cv = KONF.cv = doc.createElement('canvas'); cv.className = 'konfetti'; cv.setAttribute('aria-hidden', 'true');
    KONF.dpr = Math.min(2, devicePixelRatio || 1); cv.width = Math.round(innerWidth * KONF.dpr); cv.height = Math.round(innerHeight * KONF.dpr);
    doc.body.appendChild(cv); KONF.g = cv.getContext('2d'); KONF.g.scale(KONF.dpr, KONF.dpr);
  }
  if (!KONF.raf) { KONF.ost = performance.now(); KONF.raf = requestAnimationFrame(krokKonfetti); }
}
function krokKonfetti(t) {
  const g = KONF.g, dt = Math.min(.05, (t - KONF.ost) / 1000); KONF.ost = t;
  g.clearRect(0, 0, innerWidth, innerHeight);
  KONF.cz = KONF.cz.filter(p => (p.t += dt) < p.zycie);
  for (const p of KONF.cz) {
    p.vy += 900 * dt; p.vx *= 1 - 1.1 * dt; p.vy *= 1 - .35 * dt; p.x += p.vx * dt; p.y += p.vy * dt; p.r += p.vr * dt;
    g.globalAlpha = Math.min(1, (p.zycie - p.t) / (p.zycie * .3)); g.fillStyle = p.c;
    g.save(); g.translate(p.x, p.y); g.rotate(p.r);
    if (p.kolo) { g.beginPath(); g.arc(0, 0, p.w / 2, 0, 6.283); g.fill(); } else g.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
    g.restore();
  }
  if (KONF.cz.length) KONF.raf = requestAnimationFrame(krokKonfetti);
  else { KONF.raf = 0; KONF.cv.remove(); KONF.cv = KONF.g = null; }
}
/** Fanfary po odhaczeniu OSTATNIEJ wizyty dnia: rozbłysk zorzy i złota poświata, trzy salwy konfetti, przemiatający połysk kafla i baner „Dzień zrobiony”. */
function fanfary() {
  const kd = $('#kD'), n = PLAN_DZIS.length, km = PLAN_DZIEN ? Math.round(PLAN_DZIEN.km) : 0;
  zorza && (zorza.flara(1), zorza.cieplo(1), zorza.przesun(1.2));
  if (!spokoj) {      // w trybie spokojnym gratulacje to sam baner (bez konfetti i ruchu), ale zawsze widoczny
    const r = kd.getBoundingClientRect(), pr = $('#d-pier').getBoundingClientRect();
    zorza && zorza.cel((r.left + r.width / 2 + 24) / (innerWidth + 48), 1 - (r.top + r.height / 2 + 24) / (innerHeight + 48));
    konfetti(pr.left + pr.width / 2, pr.top + pr.height / 2, 70, { kat: -Math.PI / 4, roz: 1.9 });
    setTimeout(() => konfetti(r.left + r.width / 2, r.top + 36, 60, { roz: 2.8, v: 620 }), 320);
    setTimeout(() => konfetti(r.right - 36, r.top + 56, 46, { kat: -3 * Math.PI / 4, roz: 1.7 }), 640);
    kd.classList.add('hura'); setTimeout(() => kd.classList.remove('hura'), 2200);
  }
  doc.querySelectorAll('.fanfary').forEach(x => x.remove());
  const b = doc.createElement('div'); b.className = 'fanfary'; b.setAttribute('role', 'status');
  b.innerHTML = `<span class="fa-znak">${ik('i-ok')}</span><span class="fa-tekst"><b>Gratulacje! Dzień zrobiony</b><small class="num">${n} z ${n} ${wizyt(n)}${km ? ' · ' + km + ' km' : ''}</small></span>`;
  doc.body.appendChild(b); setTimeout(() => b.remove(), spokoj ? 5500 : 4200);
}
function falaDotyku(x, y) {
  if (spokoj) return;
  const d = doc.createElement('i'); d.className = 'fala-dotyku'; d.style.left = (x - 48) + 'px'; d.style.top = (y - 48) + 'px'; doc.body.appendChild(d);
  const a = d.animate([{ transform: 'scale(.15)', opacity: .8 }, { transform: 'scale(1)', opacity: 0 }], { duration: 640, easing: E_WYJ });
  a.onfinish = () => d.remove(); setTimeout(() => d.remove(), 900);
}
function potrzasnij(el) { anim(el, [{ transform: 'translateX(0)' }, { transform: 'translateX(-7px)' }, { transform: 'translateX(6px)' }, { transform: 'translateX(-4px)' }, { transform: 'translateX(2px)' }, { transform: 'none' }], { duration: 420, easing: 'ease-out' }); }
doc.addEventListener('pointerdown', e => {
  if (spokoj || (e.button || 0) > 0) return;
  const c = e.target.closest && e.target.closest('button, [role="tab"], .dz'); if (!c || c.disabled || c.closest('.ladowanie')) return;
  falaDotyku(e.clientX, e.clientY); zorza && zorza.flara(.07);
}, { passive: true });

/* podpowiedzi przy najechaniu na przyciski bez napisu (ikony): z etykiety dostępności */
function dodajPodpowiedzi(korzen = doc) {
  for (const el of korzen.querySelectorAll('button[aria-label], [role="tab"][aria-label]')) if (!el.title) el.title = el.getAttribute('aria-label');
}
/* ---- pył gwiezdny za kursorem + magnetyczne przyciski ----
   Pył: małe płótno 520×520 podąża za kursorem, rysuje kilkadziesiąt świecących drobin i gaśnie, gdy nic się nie rusza (zero kosztu w bezruchu).
   Magnes: ważniejsze przyciski lekko garną się do kursora (własność CSS „translate”, więc nie koliduje z innymi efektami). */
{
  const cv = $('#pylek'), cx = cv.getContext('2d'), R = 260; let cz = [], petla = 0, px = 0, py = 0, kol = null, ostP = 0;
  const kolor = () => { const k = tokenRGB(motywTeraz() === 'light' ? '--a-cyan' : '--cyan'), m = tokenRGB(motywTeraz() === 'light' ? '--a-ziel' : '--mieta'); kol = [k.map(v => Math.round(v * 255)), m.map(v => Math.round(v * 255))]; };
  const krok = t => {
    if (!kol) kolor();      // po zmianie motywu paleta jest przeliczana na nowo (także gdy kursor stoi, np. motyw przełączony z klawiatury)
    const dt = Math.min(.05, (t - ostP) / 1000 || .016); ostP = t;
    cv.style.transform = `translate3d(${px - R}px,${py - R}px,0)`; cx.clearRect(0, 0, 2 * R, 2 * R);
    cx.globalCompositeOperation = motywTeraz() === 'light' ? 'source-over' : 'lighter';
    cz = cz.filter(p => (p.z -= dt) > 0);
    for (const p of cz) {
      p.vx *= 1 - dt * 1.6; p.vy = p.vy * (1 - dt * 1.6) + 22 * dt; p.x += p.vx * dt; p.y += p.vy * dt;
      const a = Math.min(1, p.z / p.t) * .85, x = p.x - (px - R), y = p.y - (py - R), c = kol[p.k], r = p.r * (.5 + .5 * p.z / p.t) * 3.2;
      if (x < -8 || y < -8 || x > 2 * R + 8 || y > 2 * R + 8) continue;
      const g = cx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, `rgba(${c[0]},${c[1]},${c[2]},${a})`); g.addColorStop(1, `rgba(${c[0]},${c[1]},${c[2]},0)`);
      cx.fillStyle = g; cx.fillRect(x - r, y - r, 2 * r, 2 * r);
    }
    if (cz.length) petla = requestAnimationFrame(krok); else { petla = 0; cx.clearRect(0, 0, 2 * R, 2 * R); }
  };
  addEventListener('pointermove', e => {
    if (spokoj || e.pointerType === 'touch' || doc.hidden) return;
    if (!kol) kolor();
    px = e.clientX; py = e.clientY;
    for (let i = 0; i < 2; i++) { const kat = Math.random() * 6.283, v = 10 + Math.random() * 38, t = .55 + Math.random() * .7; cz.push({ x: px + (Math.random() - .5) * 6, y: py + (Math.random() - .5) * 6, vx: Math.cos(kat) * v, vy: Math.sin(kat) * v - 12, z: t, t, r: 1.1 + Math.random() * 1.9, k: Math.random() < .5 ? 0 : 1 }); }
    if (cz.length > 70) cz.splice(0, cz.length - 70);
    if (!petla) { ostP = performance.now(); petla = requestAnimationFrame(krok); }
  }, { passive: true });
  new MutationObserver(() => { kol = null; }).observe(root, { attributes: true, attributeFilter: ['data-theme'] });
  /* magnes */
  let mag = null;
  const MAG = '.przycisk.glowny,.przycisk,.okr,.ikb,.zakladka,.rok-m,.seg button,.kropla,.dz-oko';
  const odczep = () => { if (mag) { mag.style.translate = ''; mag = null; } };
  addEventListener('pointermove', e => {
    if (spokoj || e.pointerType === 'touch') return;
    const el = e.target.closest && e.target.closest(MAG);
    if (el !== mag) { odczep(); mag = el; }
    if (!el || el.disabled) return;
    const r = el.getBoundingClientRect(), dx = (e.clientX - (r.left + r.width / 2)) / r.width, dy = (e.clientY - (r.top + r.height / 2)) / r.height;
    const sila = el.classList.contains('kropla') ? 0 : Math.min(7, r.width * .05 + 2);       // kropla ma własny, bogatszy ruch
    el.style.translate = `${(dx * sila).toFixed(2)}px ${(dy * sila * .8).toFixed(2)}px`;
  }, { passive: true });
  doc.addEventListener('pointerleave', odczep);
}
/* ?diag w adresie: nakładka z liczbą klatek/s i rodzajem grafiki — do testów właściciela (zwykły użytkownik jej nie widzi) */
{
  if (new URLSearchParams(location.search).has('diag')) {
    const d = $('#diag'); d.hidden = false; let n = 0, t0 = performance.now(), gpu = '?';
    try { const g = doc.createElement('canvas').getContext('webgl'), e = g && g.getExtension('WEBGL_debug_renderer_info'); gpu = e ? String(g.getParameter(e.UNMASKED_RENDERER_WEBGL)) : (g ? 'WebGL' : 'brak WebGL'); } catch (e) { gpu = 'brak WebGL'; }
    let wer = '';
    fetch('sw.js', { cache: 'no-store' }).then(r => r.text()).then(t => { const m = t.match(/WERSJA = '([0-9a-f]+)'/); wer = m ? ' · wersja ' + m[1] : ''; }).catch(() => {});
    const f = t => { n++; if (t - t0 >= 1000) { d.textContent = `${n} kl./s · ${gpu}${wer} · zorza: ${window.__zorzaWyjscie || ''}, odświeżanie co ${krokTla()} ms`; n = 0; t0 = t; } requestAnimationFrame(f); };
    requestAnimationFrame(f);
  }
}
/* Grafika liczona procesorem (SwiftShader, llvmpipe, „Basic Render”…) to najczęstsza przyczyna „mulenia”, a decyduje o niej przeglądarka, nie aplikacja.
   Mówimy to wprost, raz, i podpowiadamy, jak włączyć przyspieszanie sprzętowe. */
function grafikaProgramowa() {
  try {
    const g = doc.createElement('canvas').getContext('webgl'), e = g && g.getExtension('WEBGL_debug_renderer_info'), r = e ? String(g.getParameter(e.UNMASKED_RENDERER_WEBGL)) : '';
    return { programowa: !g || /SwiftShader|llvmpipe|softpipe|Software|Basic Render|Microsoft Basic/i.test(r), nazwa: r || (g ? 'WebGL' : 'brak WebGL') };
  } catch (e) { return { programowa: true, nazwa: 'brak WebGL' }; }
}
function ostrzezGrafike() {
  if ((rzadko && !window.__ostrzezenieGrafiki) || pamiec.get('grafika-info') || arkuszOtwarty || dostepBlokada) return;
  const g = grafikaProgramowa(); if (!g.programowa && !window.__ostrzezenieGrafiki) return;
  pamiec.set('grafika-info', '1');
  otworzArkusz(`${naglowekArkusza('Animacje mogą być wolne')}
    <p class="ark-opis">Ta przeglądarka rysuje grafikę <b>procesorem</b> zamiast karty graficznej (${bezZnacznikow(g.nazwa)}), dlatego ruch tła i szkła bywa przycięty. To ustawienie przeglądarki, nie aplikacji — wystarczy je włączyć:</p>
    <ol class="krok-lista">
      <li><span><b>Edge:</b> Ustawienia → System i wydajność → „Używaj przyspieszania sprzętowego, gdy jest dostępne” → uruchom przeglądarkę ponownie.</span></li>
      <li><span><b>Chrome:</b> Ustawienia → System → „Używaj przyspieszania grafiki, jeśli jest dostępne”.</span></li>
      <li><span><b>Firefox:</b> Ustawienia → Ogólne → Wydajność → odznacz „Użyj zalecanych ustawień wydajności”, zaznacz „Użyj akceleracji sprzętowej, jeśli jest dostępna”.</span></li>
    </ol>
    <p class="ark-opis">Na komputerze firmowym ustawienie bywa zablokowane przez administratora — wtedy wygląd się nie zmienia, ale ruch może być mniej płynny. Tę wiadomość zobaczysz tylko raz.</p>
    <div class="ark-dol"><button type="button" class="przycisk glowny" data-zamknij data-pierwsze>Rozumiem</button></div>`);
}
function wstrzymajRuch(v) { zorza && zorza.wstrzymaj(v); kurtyna && kurtyna.wstrzymaj(v); }

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
let PLAN = null;             // plan wizyt (z importu listy sklepów), zapisany na urządzeniu
let PLAN_DZIS = [], PLAN_DATA = null, PLAN_DZIEN = null;   // wizyty dnia, który pokazuje kafel „Dziś"

const dzienTyg = d => (new Date(M.rok, M.mies - 1, d).getDay() + 6) % 7;   // 0 = poniedziałek
const polDla = d => M && M.polecenia.find(p => d >= p.od && d <= p.do);
const typDnia = d => !M ? 'nd' : M.trasy[d] ? 'trasa' : M.wolne.has(d) ? 'urlop' : M.robocze.has(d) ? 'bez' : 'nd';
const dwaCyfry = n => String(n).padStart(2, '0');
const dniMies = (r, m) => new Date(r, m, 0).getDate();
const minuty = s => { const [h, m] = s.split(':').map(Number); return h * 60 + m; };
const hhmm = m => `${dwaCyfry(Math.floor(m / 60) % 24)}:${dwaCyfry(Math.round(m % 60))}`;

/** Model miesiąca: stan 'plan' (przed generowaniem) albo 'gotowe' (jest wynik silnika). rec = rekord z magazynu lub null. */
/** Tryb pracy z profilu: „Tydzień” jest domyślny; „Wieczory” dopiero po świadomym wyborze użytkownika (także dla profili zapisanych wcześniej bez tej informacji). */
const trybDom = p => (p && p.tryb_wybrany && p.tryb) || 'tydzien';
function zbudujModel(rok, mies, rec, robocze0) {
  const N = dniMies(rok, mies);
  const par = (rec && rec.params) || {};
  const wolne = new Set((par.wolne || (M && M.rok === rok && M.mies === mies && M.stan === 'plan' ? [...M.wolne] : [])).map(Number));
  const m = { rok, mies, N, stan: rec && rec.wynik ? 'gotowe' : 'plan', robocze0: new Set(robocze0), wolne, robocze: new Set(),
    tryb: par.tryb || trybDom(PROFIL), silnik: par.silnik_powyzej_900 ?? (PROFIL ? PROFIL.silnik_powyzej_900 : true),
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
const etapMiesiaca = () => !M ? 'ustaw' : M.demo ? 'przyklad' : M.stan === 'plan' ? 'ustaw' : (M.wyslane ? 'wyslane' : (razemDok() && ilePodpisanych() >= razemDok() ? 'wyslij' : 'podpisz'));

const opisDnia = d => {
  const t = typDnia(d), k = `${DK[dzienTyg(d)]} ${d}.${dwaCyfry(M.mies)}`;
  if (t === 'trasa') return `${k} · <b>${fmt(M.trasy[d].suma)} zł</b> · <span>${fmt(M.trasy[d].km, 1)} km</span>`;
  if (t === 'bez') return `${k} · <span>dzień pracy bez trasy</span>`;
  if (t === 'urlop') return `${k} · <span>bez pracy</span>`;
  return `${k} · <span>dzień wolny</span>`;
};

const app = $('#aplikacja'), bento = $('#bento');
let zorza = null, kurtyna = null;
/* Jedna, stała, najwyższa jakość — taka sama dla każdego użytkownika i sprzętu (bez poziomów, trybów i automatycznych obniżek):
   – pole zorzy (kosztowne) liczy się w 0,3 piksela CSS; jest gładkie, więc różnica względem pełnej rozdzielczości mieści się w szumie rozpraszającym (pomiar: ~1/255),
   – obraz na ekran trafia w NATYWNEJ rozdzielczości ekranu (z uwzględnieniem skalowania systemu, do 8,4 mln pikseli) przez wygładzające powiększenie bikubiczne,
   – pole odświeża się 33 razy na sekundę (dryf jest wolny), a paralaksa i reszta efektów — przy każdej klatce przeglądarki. */
const ZORZA_POLE = .3, ZORZA_MAX_PIKSELI = 8.4e6;
/* Regulator tła. Koszt strony to (liczba klatek) × (powierzchnia szkła): każda klatka przelicza rozmycie całego szkła pod spodem, więc najtańsze jest NIE rysować klatek, których nikt nie zauważy.
   Jakość pojedynczej klatki jest zawsze ta sama; zmienia się tylko, jak często przesuwa się wolny dryf tła:
   – normalnie 30/s (zorza i kurtyna w TYCH SAMYCH klatkach — jedna kompozycja zamiast dwóch przeplatanych),
   – w trakcie pisania i 1,1 s po nim tło stoi (klawisz od razu daje literę, bez czekania na klatkę z rozmyciem),
   – pod otwartym oknem (logowanie, arkusze, paleta) i po minucie bezczynności — rzadziej, bo i tak jest rozmyte albo nikt nie patrzy,
   – gdy strona REALNIE nie nadąża (poniżej ~40 klatek/s przez kilka sekund), tempo schodzi stopniowo do 20/s → 15/s → 10/s i już nie wraca w tej sesji. */
const RUCH = { poziom: 0, zewn: false, cisza: false, trzymajDo: 0, ostWej: 0 };
const KROKI_TEMPA = [33, 50, 66, 100];
RUCH.okno = () => arkuszOtwarty || dostepBlokada || RUCH.zewn;
const krokTla = () => rzadko ? 5000 : window.__zorzaKrok || (RUCH.okno() ? 125 : RUCH.cisza ? 100 : KROKI_TEMPA[RUCH.poziom]);
const tlaTrzymane = t => t < RUCH.trzymajDo;
const bramkaTla = () => { let ost = -1; return t => { const b = Math.floor(t / krokTla()); if (b === ost) return false; ost = b; return true; }; };
const ustawCisze = v => { RUCH.cisza = v; root.classList.toggle('cisza', v); };
addEventListener('keydown', e => { const el = e.target; if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable)) RUCH.trzymajDo = czas() + 1100; }, true);
for (const ev of ['pointermove', 'pointerdown', 'keydown', 'touchstart', 'wheel']) addEventListener(ev, () => { RUCH.ostWej = czas(); if (RUCH.cisza) ustawCisze(false); }, { passive: true, capture: true });

/* ====================== motyw: Noc / Dzień ====================== */
const motywTeraz = () => { const d = root.dataset.theme; return d === 'light' || d === 'dark' ? d : (JASNY.matches ? 'light' : 'dark'); };
function poMotywie() {
  const m = motywTeraz();
  $$('.przel [data-motyw]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.motyw === m)));
  $('#motyw').setAttribute('aria-label', m === 'light' ? 'Motyw: Dzień — przełącz na Noc' : 'Motyw: Noc — przełącz na Dzień');
  zorza && zorza.kolory();
  kurtyna && kurtyna.kolory();
  szkla.forEach(budujSoczewke); /* stan zawiera motyw → filtr przebudowany, stary usunięty */
  rysujGwiazdy();
}
/* Zmiana motywu: fala dnia/nocy rozchodzi się od przełącznika (3 s). W przeglądarkach z View Transitions (Chrome, Edge, Safari 18) nowy wygląd odsłania się na żywo wewnątrz rosnącego koła,
   w pozostałych (Firefox, starsze Safari/iOS) koło wypełnia się niebem nowego motywu, pod nim zmienia się motyw, a potem niebo rozpływa się i odsłania gotowy interfejs.
   W obu wariantach na krawędzi koła świeci pierścień światła z iskrami: złoty o świcie, zimny turkusowy o zmierzchu. */
const NIEBO_MOTYWU = { dark: 'radial-gradient(60% 40% at 30% 70%,rgb(43 245 166/.22),transparent 70%),radial-gradient(50% 40% at 78% 30%,rgb(107 77 255/.3),transparent 70%),linear-gradient(180deg,#18153F 0%,#0A0E22 55%,#0B1622 100%)',
  light: 'radial-gradient(60% 40% at 30% 70%,rgb(255 214 150/.7),transparent 70%),radial-gradient(50% 40% at 78% 30%,rgb(190 170 255/.6),transparent 70%),linear-gradient(180deg,#C4C0EE 0%,#EADCF0 55%,#FCE6D4 100%)' };
const SWIATLO_FALI = { dark: '64 240 200', light: '255 196 90' };
function pierscienFali(m, x, y, R, czasMs, easing) {
  const r = doc.createElement('i'); r.className = 'fala-pierscien'; r.setAttribute('aria-hidden', 'true');
  r.style.cssText = `left:${x - R}px;top:${y - R}px;width:${2 * R}px;height:${2 * R}px;--sw:${SWIATLO_FALI[m]}`;
  doc.body.appendChild(r);
  const a = r.animate([{ transform: 'scale(0)' }, { transform: 'scale(1)' }], { duration: czasMs, easing, fill: 'forwards' });
  a.onfinish = () => r.remove(); setTimeout(() => r.remove(), czasMs + 6000);
  /* iskry na krawędzi: kilkanaście drobin wylatuje z okręgu w trakcie rozchodzenia się fali */
  for (let i = 0; i < 18; i++) setTimeout(() => { const kat = Math.random() * 6.283, t = (i / 18); const rr = R * (.12 + .88 * Math.pow(t, .8)); iskry(x + Math.cos(kat) * rr, y + Math.sin(kat) * rr, 3); }, czasMs * (i / 22));
}
function ustawMotyw(m, zrodlo) {
  if (m === motywTeraz() && root.dataset.theme) return;
  const zm = () => { root.dataset.theme = m; pamiec.set('motyw', m); poMotywie(); };
  if (spokoj) { zm(); return; }
  const r = zrodlo && zrodlo.getClientRects().length ? zrodlo.getBoundingClientRect() : { left: innerWidth - 40, top: 28, width: 0, height: 0 };
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  const R = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
  const EAS = 'cubic-bezier(.55,0,.25,1)', MC = window.__motywCzas || 1;      // MC: tylko dla testów (spowolnienie)
  if (!doc.startViewTransition) {
    const ov = doc.createElement('div'); ov.className = 'motyw-fala'; ov.setAttribute('aria-hidden', 'true'); ov.style.background = NIEBO_MOTYWU[m]; doc.body.appendChild(ov);
    zorza && zorza.flara(.6);
    const a = ov.animate({ clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${R.toFixed(0)}px at ${x}px ${y}px)`] }, { duration: 1500 * MC, easing: EAS, fill: 'forwards' });
    pierscienFali(m, x, y, R, 1500 * MC, EAS);
    a.onfinish = () => {
      root.classList.add('motyw-plynnie'); zm(); zorza && zorza.restart(); kurtyna && kurtyna.restart();
      const b = ov.animate({ opacity: [1, 0] }, { duration: 1500 * MC, easing: 'cubic-bezier(.3,0,.2,1)', fill: 'forwards' });
      b.onfinish = () => { ov.remove(); root.classList.remove('motyw-plynnie'); };
    };
    return;
  }
  const vt = przejscie(zm, null, 'motyw');
  if (!vt) return;
  vt.ready.then(() => {
    root.animate({ clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${R.toFixed(0)}px at ${x}px ${y}px)`] }, { duration: 3000 * MC, easing: EAS, pseudoElement: '::view-transition-new(root)' });
    pierscienFali(m, x, y, R, 3000 * MC, EAS);
  }).catch(e => console.warn('motyw: ' + (e && e.message)));
}
{ const z = pamiec.get('motyw'); if (z === 'light' || z === 'dark') root.dataset.theme = z; }

/* ====================== kwota: cyfry toczą się ====================== */
function przygotujCyfry(el, tekst) {
  el.textContent = '';
  let i = 0;
  for (const ch of tekst) {
    if (/\d/.test(ch)) {
      const slot = doc.createElement('span'); slot.className = 'slot';
      const t = doc.createElement('span'); t.className = 'tasma';
      /* ruch ograniczony: taśma z jedną cyfrą (od razu stan końcowy, tekst = „3 095,26”) */
      t.innerHTML = spokoj ? `<span>${ch}</span>` : Array.from({ length: 20 }, (_, k) => `<span>${k % 10}</span>`).join('');
      t.style.setProperty('--n', spokoj ? '0' : String(10 + Number(ch)));
      t.style.setProperty('--d', (i * 75) + 'ms');
      slot.appendChild(t); el.appendChild(slot); i++;
    } else {
      const s = doc.createElement('span');
      s.className = 'sep' + (ch === ' ' || ch === NBSP ? ' spacja' : '');
      s.textContent = (ch === ' ' || ch === NBSP) ? NBSP : ch;
      el.appendChild(s);
    }
  }
}

/* ====================== dymek danych ====================== */
const podp = $('#podp');
function pokazPodp(html, x, y) { podp.innerHTML = html; podp.style.left = Math.round(Math.min(innerWidth - 110, Math.max(110, x))) + 'px'; podp.style.top = Math.round(y) + 'px'; podp.classList.add('widoczny'); }
function ukryjPodp() { podp.classList.remove('widoczny'); }

/* ====================== kalendarz miesiąca ====================== */
function budujKalendarz() {
  const siatka = $('#siatka'); if (!M) { siatka.innerHTML = ''; return; }
  const off = dzienTyg(1), N = M.N, plan = M.stan === 'plan';
  siatka.style.setProperty('--wiersze', Math.ceil((off + N) / 7));
  let h = '';
  for (let i = 0; i < off; i++) h += '<div class="dz pusty" aria-hidden="true"></div>';
  const nazwaM = MIES_D[M.mies - 1];
  for (let d = 1, k = 0; d <= N; d++, k++) {
    const t = typDnia(d), wd = dzienTyg(d), tr = M.trasy[d];
    if (t === 'trasa') {
      /* poziom cieczy = kwota dnia / limit dnia */
      h += `<button type="button" class="dz trasa ${klasaPoziomu(Math.min(1, tr.suma / LIMIT_DZIEN))}" data-d="${d}" style="--poziom:${Math.min(1, tr.suma / LIMIT_DZIEN).toFixed(3)};--k:${k}" aria-pressed="false" aria-label="${DN[wd]} ${d} ${nazwaM}: ${fmt(tr.km, 1)} km, ${fmt(tr.suma)} zł, ${Math.round(tr.suma / LIMIT_DZIEN * 100)} % limitu dnia">` +
        `<span class="pl-w" aria-hidden="true"><span class="pl"></span></span><span class="nr">${d}</span><span class="dane num"><span class="km">${fmt(tr.km, 1)} km</span><span class="zl">${fmt(tr.suma)}</span></span></button>`;
    } else if (t === 'urlop') {
      if (plan) {
        h += `<button type="button" class="dz urlop" data-d="${d}" aria-pressed="true" aria-label="${DN[wd]} ${d} ${nazwaM}: wolne — kliknij, aby przywrócić"><span class="nr">${d}</span><span class="etyk">wolne</span></button>`;
      } else {
        let r = 1; while (M.wolne.has(d + r) && d + r <= N && dzienTyg(d + r) !== 0) r++;
        h += `<div class="urlop-pas" role="img" aria-label="${d}–${d + r - 1} ${nazwaM}: bez pracy" style="--k:${k};grid-column:span ${r}"><span class="u-dni" style="grid-template-columns:repeat(${r},minmax(0,1fr))" aria-hidden="true">${Array.from({ length: r }, (_, i) => `<span>${d + i}</span>`).join('')}</span>` +
          (r >= 3 ? `<span class="u-et" aria-hidden="true">bez pracy · ${d}–${d + r - 1}.${dwaCyfry(M.mies)}</span>` : '') + `</div>`;
        d += r - 1; k += r - 1;
      }
    } else if (t === 'nd') {
      h += `<div class="dz nd" data-d="${d}"><span class="nr">${d}</span></div>`;
    } else if (plan) {
      h += `<button type="button" class="dz bez przelacz" data-d="${d}" style="--k:${k};--v:${(1 + ((d * 37) % 11 - 5) * .014).toFixed(3)}" aria-pressed="false" aria-label="${DN[wd]} ${d} ${nazwaM}: dzień roboczy — kliknij, aby oznaczyć jako wolny"><span class="pl-w" aria-hidden="true"><span class="pl"></span></span><span class="nr">${d}</span><span class="etyk">roboczy</span></button>`;
    } else {
      h += `<div class="dz bez" data-d="${d}" aria-label="${DN[wd]} ${d} ${nazwaM}: dzień pracy bez wyjazdu"><span class="nr">${d}</span><span class="etyk">bez trasy</span></div>`;
    }
  }
  siatka.innerHTML = h;
  const pozaMiesiacem = (7 - (off + N) % 7) % 7;
  for (let i = 0; i < pozaMiesiacem; i++) siatka.insertAdjacentHTML('beforeend', '<div class="dz pusty" aria-hidden="true"></div>');
  zaznaczKomorke(); sygnal('kalendarz');
}
function zaznaczKomorke() {
  $$('#siatka .dz.trasa').forEach(b => {
    const on = Number(b.dataset.d) === wybrany;
    b.classList.toggle('wybrany', on); b.setAttribute('aria-pressed', String(on));
    const p = $('.pierscien', b);
    if (on && !p) b.insertAdjacentHTML('beforeend', '<span class="pierscien" aria-hidden="true"></span>');
    if (!on && p) p.remove();
  });
  $$('#ku-os span[data-d]').forEach(s => s.classList.toggle('wyb', Number(s.dataset.d) === wybrany));
  $$('#ku-zapas i[data-d]').forEach(s => s.classList.toggle('wyb', Number(s.dataset.d) === wybrany));
}
function tytulKalendarza() {
  const el = $('#c-tyt'); if (!M) return;
  el.innerHTML = `${cap(MIES[M.mies - 1])} <span>${M.stan === 'gotowe' ? '· ' + M.dniT.length + ' ' + (M.dniT.length === 1 ? 'dzień' : 'dni') + ' z trasą' : '· ' + M.robocze.size + ' dni roboczych'}</span>`;
}

/* ====================== wykres dni miesiąca (płaskie słupki) ====================== */
function budujKurtyneDOM() {
  if (!M || M.stan !== 'gotowe') { $('#ku-os').innerHTML = ''; $('#ku-pol').innerHTML = ''; $('#ku-zapas').innerHTML = ''; return; }
  const N = M.N, pc = d => ((d - .5) / N * 100).toFixed(2) + '%';
  const os = [...new Set([1, 5, 10, 15, 20, 25, N].filter(d => d <= N && (d === N || N - d >= 3 || d === 1)))];
  /* pas „bez pracy" nad najdłuższym ciągiem dni wolnych (od 3 dni); liczb osi w jego obrębie nie rysujemy */
  let najd = null, i = 1;
  while (i <= N) { if (M.wolne.has(i)) { let j = i; while (M.wolne.has(j + 1)) j++; if (j - i + 1 >= 3 && (!najd || j - i > najd[1] - najd[0])) najd = [i, j]; i = j + 1; } else i++; }
  let h = os.filter(d => !najd || d < najd[0] - 1 || d > najd[1] + 1).map(d => `<span data-d="${d}" style="left:${pc(d)}">${d}</span>`).join('');
  if (najd) h += `<span class="urlop" style="left:${((najd[0] - 1) / N * 100).toFixed(2)}%;width:${((najd[1] - najd[0] + 1) / N * 100).toFixed(2)}%">bez pracy</span>`;
  $('#ku-os').innerHTML = h;
  $('#ku-pol').style.gridTemplateColumns = `repeat(${N},minmax(0,1fr))`;
  $('#ku-pol').innerHTML = M.polecenia.map(p => `<span data-pol="${p.nr}" class="${p.do - p.od < 3 ? 'w1' : p.do - p.od < 4 ? 'w2' : ''}" style="grid-column:${p.od}/${p.do + 1}" title="Polecenie ${p.nr}: ${dwa(p.od)}–${dwa(p.do)}.${dwa(M.mies)}, ${fmt(p.kw)} zł"><b>P${p.nr}</b><span class="dl">${fmt(p.kw)}</span><span class="kr">${Math.round(p.kw / LIMIT_POL * 100)}&nbsp;%</span></span>`).join('');
  $('#ku-zapas').innerHTML = Array.from({ length: N }, (_, i) => { const d = i + 1, t = typDnia(d), h = t === 'trasa' ? Math.min(1, M.trasy[d].suma / LIMIT_DZIEN) : 0; return `<i data-d="${d}" class="${t === 'trasa' ? 'tr ' + klasaPoziomu(h) : t === 'bez' ? 'bez' : 'nd'}${d === wybrany ? ' wyb' : ''}" style="--h:${h.toFixed(3)};--i:${i}"></i>`; }).join('');
  const pole = $('#ku-pole'); if (pole) pole.setAttribute('aria-label', `Kwoty dni miesiąca: najwyższa ${fmt(Math.max(...M.dniT.map(d => M.trasy[d].suma)))} zł, najniższa ${fmt(Math.min(...M.dniT.map(d => M.trasy[d].suma)))} zł`);
}

/* Kolor = wysokość kwoty dnia wobec limitu dnia (ta sama skala w kalendarzu i na wykresie): n1 żółty … n5 malinowy. */
const klasaPoziomu = h => h < .3 ? 'n1' : h < .5 ? 'n2' : h < .68 ? 'n3' : h < .86 ? 'n4' : 'n5';
/** Wykres dni w kaflu kwoty: płaskie słupki (DOM, bez WebGL) — wysokość = kwota dnia, kolor = skala poziomu; klik i najechanie jak w kalendarzu. */
function startKurtyna() {
  const fig = $('#kurtyna'), pole = $('#ku-pole'), zap = $('#ku-zapas');
  let dotyk = 0, hv = 0;
  const slup = d => zap.querySelector(`i[data-d="${d}"]`);
  const dzienZ = e => { const r = pole.getBoundingClientRect(), N = M ? M.N : 30; return Math.min(N, Math.max(1, Math.floor((e.clientX - r.left) / r.width * N) + 1)); };
  const zdejmijHover = () => { if (hv) { const o = slup(hv); o && o.classList.remove('hov'); hv = 0; } };
  pole.addEventListener('pointermove', e => {
    if (!M) return;
    const d = dzienZ(e), t = typDnia(d), r = pole.getBoundingClientRect();
    if (d !== hv) { zdejmijHover(); if (t === 'trasa') { hv = d; slup(d).classList.add('hov'); } }
    const h = t === 'trasa' ? Math.min(1, M.trasy[d].suma / LIMIT_DZIEN) : 0;
    pokazPodp(opisDnia(d), r.left + (d - .5) / M.N * r.width, r.top + r.height * (1 - h) - 4);
    pole.style.cursor = t === 'trasa' ? 'pointer' : 'default';
    podswietlPolecenie(polDla(d) ? polDla(d).nr : 0, true, true);
  });
  pole.addEventListener('pointerleave', () => { zdejmijHover(); ukryjPodp(); podswietlPolecenie(0, false); });
  pole.addEventListener('click', e => { if (!M) return; const d = dzienZ(e); if (M.trasy[d]) wybierzDzien(d); });
  pole.addEventListener('pointerup', e => { if (e.pointerType !== 'mouse') { clearTimeout(dotyk); dotyk = setTimeout(() => { zdejmijHover(); ukryjPodp(); podswietlPolecenie(0, false); }, 1600); } });
  const raz = (klasa, ms) => { fig.classList.remove(klasa); if (spokoj) return; void fig.offsetWidth; fig.classList.add(klasa); setTimeout(() => fig.classList.remove(klasa), ms); };
  return {
    tryb() {}, dane() {}, kolory() {}, rozmiar() {}, wstrzymaj() {}, rysuj() {},
    wybierz(d) { const o = slup(d); if (!o || spokoj) return; o.classList.remove('blysk'); void o.offsetWidth; o.classList.add('blysk'); setTimeout(() => o.classList.remove('blysk'), 900); },
    restart() { raz('rosnie', 2200); },
    swieto() { raz('swieto', 1800); }
  };
}
/* ====================== wybrany dzień: podróż ====================== */
/** Przystanki dnia w układzie „odcinków": 0 = dom (wyjazd), 1..n = miejscowości, ostatni = dom (powrót). */
function odcinkiDnia(tr) {
  const e = tr.etapy, o = [];
  o.push({ przyj: '', m: e[0].skad, odj: e[0].wyjazd, dom: true });
  for (let i = 0; i < e.length; i++) {
    const ost = i === e.length - 1;
    o.push({ przyj: e[i].przyjazd, m: e[i].dokad, odj: ost ? '' : e[i + 1].wyjazd, km: e[i].km, zl: e[i].kwota, dom: ost });
  }
  return o;
}
/** Jazda i postoje liczone z godzin na dokumencie (tak jak widzi je człowiek, bez własnych założeń). */
function czasyDnia(odc) {
  let jazda = 0, sklepy = 0;
  for (let i = 1; i < odc.length; i++) {
    jazda += minuty(odc[i].przyj) - minuty(odc[i - 1].odj);
    if (odc[i].odj) sklepy += minuty(odc[i].odj) - minuty(odc[i].przyj);
  }
  return { jazda, sklepy };
}
const dlugosc = m => `${Math.floor(m / 60)} h ${dwa(Math.round(m % 60))} min`.replace(' 00 min', ' h').replace(/^0 h /, '');
function mapkaSVG(tr) {
  const pt = tr.punkty; if (!pt || pt.length < 3) return '';
  const lat0 = pt.reduce((a, p) => a + p.lat, 0) / pt.length, lon0 = pt[0].lng, k = Math.cos(lat0 * Math.PI / 180);
  const P = pt.map(p => [(p.lng - lon0) * k, -(p.lat - lat0)]);
  const xs = P.map(p => p[0]), ys = P.map(p => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const W = 170, H = 112, pad = 15, sk = Math.min((W - 2 * pad) / Math.max(x1 - x0, 1e-4), (H - 2 * pad) / Math.max(y1 - y0, 1e-4));
  const ox = (W - (x1 - x0) * sk) / 2, oy = (H - (y1 - y0) * sk) / 2;
  const Q = P.map(([x, y]) => [ox + (x - x0) * sk, oy + (y - y0) * sk]);
  const N = Q.length - 1; const g = i => Q[(i + N) % N];
  let d = `M${Q[0][0].toFixed(2)} ${Q[0][1].toFixed(2)}`;
  for (let i = 0; i < N; i++) {
    const p0 = g(i - 1), p1 = g(i), p2 = g(i + 1), p3 = g(i + 2), kk = 0.2;
    d += ` C${(p1[0] + (p2[0] - p0[0]) * kk).toFixed(2)} ${(p1[1] + (p2[1] - p0[1]) * kk).toFixed(2)} ${(p2[0] - (p3[0] - p1[0]) * kk).toFixed(2)} ${(p2[1] - (p3[1] - p1[1]) * kk).toFixed(2)} ${p2[0].toFixed(2)} ${p2[1].toFixed(2)}`;
  }
  const [hx, hy] = Q[0];
  /* tło mapy: siatka współrzędnych, poziomice terenu (losowe, ale zawsze takie same dla danej trasy) i wiązka radaru obracająca się od domu */
  const rnd = mulberry(Math.round(Math.abs(pt.reduce((a, p) => a + p.lat * 1000 + p.lng * 777, 0))) % 2147483647 + 11);
  const siatka = (() => { let q = ''; for (let x = 17; x < W; x += 17) q += `M${x} 0V${H}`; for (let y = 14; y < H; y += 14) q += `M0 ${y}H${W}`; return `<path class="tr-siatka" d="${q}"/>`; })();
  const petla = (cx, cy, r) => {
    const n = 10, pts = []; for (let i = 0; i < n; i++) { const a = i / n * 6.2832, rr = r * (.78 + rnd() * .44); pts.push([cx + Math.cos(a) * rr * 1.35, cy + Math.sin(a) * rr]); }
    let dd = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
    for (let i = 0; i < n; i++) { const p0 = pts[(i + n - 1) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n]; dd += ` C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)} ${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)} ${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`; }
    return dd + 'Z';
  };
  let wys = ''; for (const [cx, cy] of [[W * (.2 + rnd() * .25), H * (.25 + rnd() * .5)], [W * (.6 + rnd() * .3), H * (.2 + rnd() * .6)]]) for (const r of [9, 17, 26, 36]) wys += petla(cx, cy, r);
  const wiazka = `<g class="tr-radar" style="transform-origin:${hx.toFixed(1)}px ${hy.toFixed(1)}px"><path d="M${hx.toFixed(1)} ${hy.toFixed(1)}L${(hx + 190).toFixed(1)} ${(hy - 36).toFixed(1)}A190 190 0 0 1 ${(hx + 190).toFixed(1)} ${(hy + 36).toFixed(1)}Z" fill="url(#gr-radar)"/></g>`;
  /* okręgi odległości od domu w tym samym rzucie (1° szer. ≈ 111 km) */
  const kregi = [10, 20].map(km => { const r = km / 111 * sk; return `<circle class="tr-krag" cx="${hx.toFixed(2)}" cy="${hy.toFixed(2)}" r="${r.toFixed(2)}"/><text class="tr-krag-et" x="${(hx - r * .7071 - .8).toFixed(2)}" y="${(hy - r * .7071 - .8).toFixed(2)}" text-anchor="end">${km} km</text>`; }).join('');
  const cx = (Math.min(...Q.map(q => q[0])) + Math.max(...Q.map(q => q[0]))) / 2;
  let pk = '';
  for (let i = 0; i < N; i++) {
    const [x, y] = Q[i], lewo = x < cx, nazwa = pt[i].m;
    const poz = `x="${(x + (lewo ? -6 : 6)).toFixed(1)}" y="${y.toFixed(1)}" text-anchor="${lewo ? 'end' : 'start'}" dominant-baseline="central"`;
    const et = `<text class="tr-et-halo" ${poz} aria-hidden="true">${nazwa}</text><text class="tr-et" ${poz}>${nazwa}</text>`;
    pk += i === 0
      ? `<g class="tr-pkt tr-dom" style="--p:0"><circle class="tr-halo" cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="7"/><circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="4"/><path class="tr-dach" d="M${(x - 2.1).toFixed(2)} ${(y + .3).toFixed(2)} L${x.toFixed(2)} ${(y - 1.9).toFixed(2)} L${(x + 2.1).toFixed(2)} ${(y + .3).toFixed(2)} M${(x - 1.4).toFixed(2)} ${(y - .2).toFixed(2)} V${(y + 1.9).toFixed(2)} H${(x + 1.4).toFixed(2)} V${(y - .2).toFixed(2)}"/></g>${et}`
      : `<g class="tr-pkt" style="--p:${i}"><circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="3.4"/><text x="${x.toFixed(2)}" y="${(y + .2).toFixed(2)}">${i}</text></g>${et}`;
  }
  return `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">${siatka}<path class="tr-wys" d="${wys}"/>${wiazka}${kregi}<path class="tr-cien" d="${d}" filter="url(#poswiata)"/><path class="tr-baza" d="${d}"/><path class="tr-linia" pathLength="1" d="${d}"/><path class="tr-pakiet" pathLength="1" d="${d}"/>${pk}</svg>` +
    `<figcaption class="mapka-pod" title="Schemat w rzucie geograficznym (bez dróg); okręgi 10 i 20 km od domu"><i aria-hidden="true"></i><span class="rz">rzut geograficzny · </span>okręgi <span class="kr-km">10 i 20 km </span>od domu</figcaption>`;
}
function podrozHTML(odc, op, tr) {
  /* kolumny: dom .6fr, przystanki 1fr → szerokość odcinka = połowa własnej + połowa następnej kolumny */
  const sz = i => (i === 0 || i === odc.length - 1) ? .6 : 1;
  let h = '';
  odc.forEach((o, i) => {
    const nast = odc[i + 1];
    const nazwa = o.dom ? 'Dom' : o.m;
    const czasT = o.dom ? (i === 0 ? o.odj : o.przyj) : `${o.przyj}–${o.odj}`;
    const wezel = o.dom ? `<span class="pr-wezel">${ik('i-dom')}</span>` : `<span class="pr-wezel"><span class="pr-nr">${i}</span></span>`;
    const sw = nast ? ((sz(i) / 2 + sz(i + 1) / 2) / sz(i) * 100).toFixed(1) + '%' : '0%';
    const wy = nast ? `<span class="pr-odc"><i></i></span><span class="pr-km wy num"><b>${fmt(nast.km, 1)} km</b><span>${fmt(nast.zl)} zł</span></span>` : '';
    const we = o.km != null ? `<span class="pr-km we num"><b>${fmt(o.km, 1)} km</b><span>${fmt(o.zl)} zł</span></span>` : '<span class="pr-km we num"><span>start</span></span>';
    h += `<li class="pr${o.dom ? ' dom' : ''}" style="--s:${i};--sw:${sw}" title="${o.dom ? o.m : o.m}"><span class="pr-nazwa">${nazwa}</span><span class="pr-czas num">${czasT}</span>` +
      `<span class="pr-os">${wezel}${wy}</span>${we}</li>`;
  });
  return `<ol class="podroz rysuj" style="--op:${op}ms;grid-template-columns:.6fr repeat(${odc.length - 2},minmax(0,1fr)) .6fr" aria-label="Trasa: ${odc.length - 2} miejscowości i powrót; ${odc.length - 1} odcinków, ${fmt(tr.km, 1)} km, ${fmt(tr.suma)} zł">${h}<span class="pr-kometa" aria-hidden="true"></span></ol>`;
}
function wstegaHTML(odc, op) {
  const wszystkie = odc.flatMap(o => [o.przyj, o.odj]).filter(Boolean).map(minuty);
  const A = Math.floor(Math.min(...wszystkie) / 60) * 60, Z = Math.ceil(Math.max(...wszystkie) / 60) * 60 + (Math.max(...wszystkie) % 60 === 0 ? 60 : 0), L = Z - A;
  const pc = v => ((v - A) / L * 100).toFixed(3) + '%';
  let seg = '', k = 0;
  for (let i = 0; i < odc.length - 1; i++) {
    const a = minuty(odc[i].odj), b = minuty(odc[i + 1].przyj);
    seg += `<span class="w-seg j" style="left:${pc(a)};width:calc(${pc(b)} - ${pc(a)});--s:${k++}"></span>`;
    if (odc[i + 1].odj) { const c = minuty(odc[i + 1].odj); seg += `<span class="w-seg s" style="left:${pc(b)};width:calc(${pc(c)} - ${pc(b)});--s:${k++}"></span>`; }
  }
  const okno = M.tryb === 'wieczory' && A <= 16 * 60 + 30 ? `<span class="w-okno" style="left:${pc(16 * 60 + 30)};right:0"></span>` : '';
  const krok = (L / 60) > 8 ? 2 : 1;
  let godz = ''; for (let m = A; m <= Z; m += 60 * krok) godz += `<span>${dwa(m / 60)}:00</span>`;
  return `<div class="wstega rysuj" data-a="${A}" data-z="${Z}" style="--op:${op}ms"><div class="w-tor">${okno}${seg}</div><div class="w-dol num" aria-hidden="true">${godz}</div></div>`;
}
function tabelaHTML(odc, tr) {
  let w = '', nr = 0; const maxKm = Math.max(...odc.filter(o => o.km != null).map(o => o.km), 1);
  for (const o of odc) {
    const znak = o.dom ? `<i class="dom">${ik('i-dom')}</i>` : `<i>${++nr}</i>`;
    const km = o.km != null ? `<span class="kmp"><i style="--p:${(o.km / maxKm).toFixed(3)}" aria-hidden="true"></i>${fmt(o.km, 1)}</span>` : '';
    w += `<tr><td class="s">${o.przyj}</td><td><span class="m">${znak}${o.m}</span></td><td class="odj">${o.odj}</td><td class="r s">${km}</td><td class="r">${o.zl != null ? fmt(o.zl) : ''}</td></tr>`;
  }
  return `<div class="tabela-w"><table class="odcinki"><thead><tr><th>Przyj.</th><th>Miejscowość</th><th class="odj">Odj.</th><th class="r">km</th><th class="r">zł</th></tr></thead><tbody>${w}</tbody>` +
    `<tfoot><tr><td colspan="2" class="s">Razem · ${odc.length - 1} odcinków</td><td class="odj"></td><td class="r">${fmt(tr.km, 1)}</td><td class="r">${fmt(tr.suma)}</td></tr></tfoot></table></div>`;
}
function trescDnia(d, op) {
  const tr = M.trasy[d], odc = odcinkiDnia(tr), cz = czasyDnia(odc), wizyt = odc.length - 2;
  return `<div class="de-top z-mapa"><div class="de-glowna plyta" style="--pl-in:-14% -18% -10% -14%;--pl-o:.7"><p class="de-kwota num">${fmt(tr.suma)}<small>zł</small></p><p class="de-podkwota num">kwota dnia · ${fmt(tr.km, 1)} km</p>` +
    `<p class="de-tel de-podkwota num">${fmt(tr.km, 1)} km · ${odc[0].odj}–${odc[odc.length - 1].przyj} · ${wizyt} ${wizyt === 1 ? 'wizyta' : wizyt < 5 ? 'wizyty' : 'wizyt'}</p>` +
    `<dl class="de-staty num"><div><dt>Wyjazd–powrót</dt><dd>${odc[0].odj}–${odc[odc.length - 1].przyj}</dd></div><div><dt>Wizyty</dt><dd>${wizyt}</dd></div><div><dt><i class="lg j"></i>Jazda</dt><dd>${dlugosc(cz.jazda)}</dd></div><div><dt><i class="lg s"></i>W sklepach</dt><dd>${dlugosc(cz.sklepy)}</dd></div></dl></div>` +
    `<figure class="mapka rysuj" style="--op:${op}ms">${mapkaSVG(tr)}</figure></div>` +
    podrozHTML(odc, op, tr) + wstegaHTML(odc, op + 500) + `<div class="de-szczeg">${tabelaHTML(odc, tr)}</div>`;
}
let kometaRaf = 0;
function kometa(op) {
  cancelAnimationFrame(kometaRaf);
  const pod = $('#dzien-tresc .podroz'); if (!pod || spokoj || !pod.getClientRects().length) return;
  const kom = $('.pr-kometa', pod), wez = $$('.pr-wezel', pod);
  if (!kom || wez.length < 2) return;
  const t0 = czas(), krokMs = 190, cal = krokMs * (wez.length - 1) + 400; /* krok = opóźnienie węzłów w CSS (.podroz.rysuj) */
  const krok = () => {
    const t = czas() - t0 - op;
    if (t < 0) { kometaRaf = requestAnimationFrame(krok); return; }
    const p = Math.min(1, t / cal);
    if (p >= 1 || !kom.isConnected) { kom.style.opacity = '0'; return; }
    const r0 = pod.getBoundingClientRect();
    const f = p * (wez.length - 1), i = Math.min(wez.length - 2, Math.floor(f)), u = f - i;
    const a = wez[i].getBoundingClientRect(), b = wez[i + 1].getBoundingClientRect();
    const x = (a.left + a.width / 2) * (1 - u) + (b.left + b.width / 2) * u - r0.left;
    const y = (a.top + a.height / 2) * (1 - u) + (b.top + b.height / 2) * u - r0.top;
    kom.style.transform = `translate(${x.toFixed(1)}px,${y.toFixed(1)}px)`;
    kom.style.opacity = String(Math.min(1, p * 10, (1 - p) * 6).toFixed(3));
    kometaRaf = requestAnimationFrame(krok);
  };
  kometaRaf = requestAnimationFrame(krok);
}
function rysujDzien(start = false) {
  const tr = $('#dzien-tresc');
  if (!M || M.stan !== 'gotowe' || !M.trasy[wybrany]) {
    $('#e-tyt').textContent = M && M.stan === 'gotowe' ? 'Wybierz dzień' : 'Trasa dnia';
    $('#e-pol').hidden = true; $('#e-wstecz').disabled = $('#e-dalej').disabled = true;
    tr.className = 'dzien-tresc';
    tr.innerHTML = `<div class="pusty-stan"><b>${M && M.stan === 'gotowe' ? 'Wybierz dzień w kalendarzu' : 'Trasy pojawią się po wygenerowaniu'}</b><span>${M && M.stan === 'gotowe' ? 'Zobaczysz godziny, kilometry i kwotę każdego odcinka.' : 'Ustaw kwotę i dni wolne, potem wygeneruj dokumenty.'}</span></div>`;
    sygnal('dzien'); return;
  }
  const d = wybrany, p = polDla(d);
  $('#e-tyt').textContent = `${cap(DN[dzienTyg(d)])}, ${d} ${MIES_D[M.mies - 1]}`;
  $('#e-pol').hidden = !p; if (p) { $('#e-pol').textContent = `Polecenie ${p.nr}`; $('#e-pol').dataset.skrot = `P${p.nr}`; }
  const op = start ? 1100 : 120;
  tr.innerHTML = trescDnia(d, op);
  tr.className = 'dzien-tresc pelny';
  const i = M.dniT.indexOf(d);
  $('#e-wstecz').disabled = i <= 0; $('#e-dalej').disabled = i >= M.dniT.length - 1;
  kometa(op);
  requestAnimationFrame(() => { skalaMapki(); dopasujPodroz(); obserwujMapke(); });
  sygnal('dzien');
}
/* mapa zmienia rozmiar razem z kaflem (zmiana okna, rozwinięcie kafla, wejście animacją) — opisy układamy na nowo po każdej takiej zmianie, nie tylko po narysowaniu dnia */
let obserwatorMapki = null;
function obserwujMapke() {
  const f = $('.mapka'); if (obserwatorMapki) obserwatorMapki.disconnect(); if (!f || !window.ResizeObserver) return;
  let ramka = 0; obserwatorMapki = new ResizeObserver(() => { cancelAnimationFrame(ramka); ramka = requestAnimationFrame(skalaMapki); }); obserwatorMapki.observe(f);
  if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(() => requestAnimationFrame(skalaMapki));
}
/* schemat trasy skaluje się z kaflem: gdy cyfry węzłów / opisy okręgów wyszłyby poniżej ~7,5 px, chowamy je */
function skalaMapki() {
  const f = $('.mapka'), m = f && $('svg', f); if (!m) return;
  const r = m.getBoundingClientRect(); if (!r.width) return;
  const s = Math.min(r.width / 170, r.height / 112);
  f.classList.toggle('bez-nr', s * 4.6 < 7.5);
  f.classList.toggle('bez-kregow-et', s * 6.6 < 8.5);
  /* opisy okręgów i miejscowości, które wystawałyby poza mapę (np. na nagłówek kafla), chowamy — okręgi tłumaczy podpis pod mapą */
  const ramka = m.getBoundingClientRect();
  const pinezki = $$('.tr-pkt', f).map(g => g.getBoundingClientRect()), widoczne = [], etykietyMiejsc = $$('.tr-et', f);
  const styka = (q, z, d) => !(q.right < z.left - d || q.left > z.right + d || q.bottom < z.top - d || q.top > z.bottom + d);
  const ukryj = (t, tak) => { t.style.visibility = tak ? 'hidden' : ''; const h = t.previousElementSibling; if (h && h.classList.contains('tr-et-halo')) h.style.visibility = tak ? 'hidden' : ''; };      // obrys (halo) schowany razem z napisem
  $$('.tr-krag-et, .tr-et', f).forEach(t => {
    ukryj(t, false);
    const q = t.getBoundingClientRect(); if (!q.width) return;
    if (q.top < ramka.top - 1 || q.left < ramka.left - 1 || q.right > ramka.right + 1 || q.bottom > ramka.bottom + 1) { ukryj(t, true); return; }
    /* nazwy miejscowości nie mogą na siebie nachodzić ani zasłaniać cudzych pinezek (własna pinezka przy nazwie jest normalna): pierwsza zostaje, następna, która by kolidowała, jest ukrywana */
    if (t.classList.contains('tr-et')) {
      const wlasna = etykietyMiejsc.indexOf(t);      // k-ta etykieta należy do k-tej pinezki (własna pinezka przy nazwie jest normalna, cudza — nie)
      if (widoczne.some(z => styka(q, z, 1.5)) || pinezki.some((z, j) => j !== wlasna && styka(q, z, 1.5))) { ukryj(t, true); return; }
      widoczne.push(q);
    }
  });
}
/** Oś podróży dopasowana do szerokości kafla: przy wielu przystankach chowamy godziny i skracamy nazwy (nic nie nachodzi). */
function dopasujPodroz() {
  const pod = $('#dzien-tresc .podroz'); if (!pod) return;
  const n = pod.children.length - 1, kol = pod.clientWidth / Math.max(1, n - 0.8);
  pod.classList.toggle('ciasna', kol < 104); pod.classList.toggle('bardzo-ciasna', kol < 74);
}
function wybierzDzien(d, kier) {
  if (!M || !M.trasy[d] || d === wybrany) return;
  root.style.setProperty('--kier', String(kier ?? (d > wybrany ? 1 : -1)));
  zorza && zorza.przesun(d > wybrany ? 1 : -1);
  przejscie(() => { wybrany = d; rysujDzien(); zaznaczKomorke(); }, () => { kurtyna && kurtyna.wybierz(d); }, 'dzien');
}

/* ====================== dziś: plan wizyt ====================== */
let nawigacja = -1;
const wizyt = k => k === 1 ? 'wizyta' : (k % 10 >= 2 && k % 10 <= 4 && (k % 100 < 10 || k % 100 >= 20)) ? 'wizyty' : 'wizyt';
const isoDzis = () => { const t = new Date(); return `${t.getFullYear()}-${dwa(t.getMonth() + 1)}-${dwa(t.getDate())}`; };
const KOLORY_SIECI = { 'żabka': '--s-zabka', 'zabka': '--s-zabka', 'biedronka': '--s-biedronka', 'lidl': '--s-lidl', 'stokrotka': '--s-stokrotka', 'dino': '--s-dino', 'lewiatan': '--s-lewiatan' };
function kolorSieci(nazwa) {
  const k = String(nazwa || '').toLowerCase();
  for (const [n, c] of Object.entries(KOLORY_SIECI)) if (k.includes(n)) return c;
  const t = ['--s-zabka', '--s-biedronka', '--s-lidl', '--s-stokrotka', '--s-dino', '--s-lewiatan']; let h = 0; for (const ch of k) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return t[h % t.length];
}
/** Dzień planu na dziś albo najbliższy późniejszy; wizyty z godzinami szacunkowymi i odhaczeniami z urządzenia. */
function zbudujPlanDzis() {
  PLAN_DZIS = []; PLAN_DATA = null; PLAN_DZIEN = null;
  if (!PLAN) return;
  const dzis = isoDzis(); let najb = null;
  for (const m of PLAN.miesiace) for (const d of m.dni) if (d.data >= dzis && (!najb || d.data < najb.data)) najb = d;
  if (M && M.demo) najb = PLAN.miesiace[0].dni[0] || null;      // przykład: pierwszy dzień przykładowego planu (daty przykładu są z przeszłości)
  if (!najb) return;
  PLAN_DZIEN = najb; PLAN_DATA = najb.data;
  const powtorzenia = new Map();      // ten sam sklep bywa odwiedzany kilka razy w ciągu dnia — każda wizyta jest odhaczana osobno (klucz: adres, a przy kolejnych wizytach „adres#n”)
  najb.wizyty.forEach((w, i) => {
    const siec = w.siec || w.nazwa, n = powtorzenia.get(w.adres) || 0; powtorzenia.set(w.adres, n + 1);
    const klucz = n ? `${w.adres}#${n}` : w.adres, rec = wizytaDaj(najb.data, klucz);
    PLAN_DZIS.push({ g: najb.godziny[i] || '', s: siec, m: w.miasto || '', a: (w.adres || '').split(',')[0] || w.adres, adres: w.adres, klucz, c: kolorSieci(siec), ok: !!(rec && rec.ok), data: najb.data });
  });
}
/* pusty stan „Dziś”: bezszelestna zapowiedź listy — trzy wiersze wjeżdżają jeden po drugim, pierwszy zostaje odhaczony (bez żadnych zmyślonych danych) */
const DUCH_LISTY = '<div class="duch-lista" aria-hidden="true">' + [0, 1, 2].map(i => `<i style="--s:${i}"><span class="dl-znak"></span><span class="dl-pasek"></span><span class="dl-godz"></span></i>`).join('') + '</div>';
const sklepowWPlanie = () => { const z = new Set(); if (PLAN) for (const m of PLAN.miesiace) for (const d of m.dni) for (const w of d.wizyty) z.add(w.adres); return z.size; };
function rysujDzis() {
  zbudujPlanDzis();
  const lista = $('#przystanki'), plan = $('#d-plan'), os = $('#d-os');
  const dataTxt = PLAN_DATA ? (() => { const t = new Date(PLAN_DATA + 'T12:00:00'); return `${DK[(t.getDay() + 6) % 7]} ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}`; })() : '';
  { const bl = $('#kD .blask'); if (bl) bl.dataset.d = String(PLAN_DATA ? Number(PLAN_DATA.slice(8, 10)) : new Date().getDate()); }
  $('#d-tyt').innerHTML = `${M && M.demo ? 'Przykład' : PLAN_DATA && PLAN_DATA !== isoDzis() ? 'Najbliższy dzień' : 'Dziś'} <span id="d-data">${dataTxt ? '· ' + dataTxt : ''}</span>`;
  if (!PLAN_DZIS.length) {
    $('#d-pier-t').textContent = '–'; $('#d-pier').style.setProperty('--p', '0'); $('#kD').classList.remove('komplet');
    $('#d-meta').innerHTML = `<span>${PLAN ? 'plan zakończony' : 'brak planu wizyt'}</span>`;
    lista.innerHTML = PLAN
      ? '<li class="pusty-stan"><b>Plan wizyt się skończył</b><span>Ułóż nowy plan z tej samej listy sklepów.</span><button type="button" class="przycisk glowny" id="plan-otworz">Ułóż nowy plan</button></li>'
      : '<li class="pusty-stan">' + DUCH_LISTY + '<b>Nie ma planu wizyt</b><span>Wczytaj listę sklepów z Excela, a ułożę trasy na kolejne dni. Tu pojawi się dzisiejsza lista z przyciskiem „Nawiguj".</span><button type="button" class="przycisk glowny" id="plan-otworz">Wczytaj plan</button></li>';
    plan.innerHTML = ''; os.innerHTML = '';
    return;
  }
  const ile = PLAN_DZIS.filter(s => s.ok).length, n = PLAN_DZIS.findIndex(s => !s.ok), razem = PLAN_DZIS.length;
  $('#d-pier-t').textContent = `${ile}/${razem}`; $('#d-pier').style.setProperty('--p', (ile / razem).toFixed(4));
  $('#d-meta').innerHTML = `<span><b>${ile} z ${razem}</b> ${wizyt(razem)}</span><span aria-label="trasa około ${Math.round(PLAN_DZIEN.km)} km">trasa<svg class="zn" aria-hidden="true"><use href="#i-prawie"/></svg><b>${Math.round(PLAN_DZIEN.km)} km</b></span><span>baza <b>${sklepowWPlanie()} ${sklepowWPlanie() === 1 ? 'sklep' : 'sklepów'}</b></span>`;
  if (nawigacja !== n) nawigacja = -1;
  lista.innerHTML = PLAN_DZIS.map((s, i) => {
    const teraz = i === n, pr = nawigacja === i;
    return `<li class="przystanek${s.ok ? ' ok' : ''}${teraz ? ' teraz' : ''}" style="--vtn:p${i}">` +
      `<span class="p-godz num" title="godzina szacunkowa">${s.g}</span>` +
      `<button class="p-znak" type="button" data-i="${i}" aria-pressed="${s.ok}" aria-label="${s.ok ? 'Cofnij odhaczenie' : 'Odhacz wizytę'}: ${bezZnacznikow(s.s)}, ${bezZnacznikow(s.m)}">${ik('i-ok')}</button>` +
      (teraz ? `<p class="p-etyk brew">Następny · jedziesz teraz</p>` : '') +
      `<p class="p-nazwa"><i style="--c:var(${s.c})"></i>${bezZnacznikow(s.s)} <span>· ${bezZnacznikow(s.m)}</span></p><p class="p-adres">${bezZnacznikow(s.a)}</p>` +
      (teraz ? `<button class="nawiguj${pr ? ' prowadzi' : ''}" type="button" id="nawiguj" data-i="${i}" aria-pressed="${pr}">${ik('i-nawi')}<span>${pr ? 'Prowadzę' : 'Nawiguj'}</span></button>` : '') + `</li>`;
  }).join('');
  const zost = razem - ile;
  plan.innerHTML = `<div class="dp-k dp-glowny"><span class="dp-et">Przed Tobą</span><b class="num">${zost}</b><span class="dp-op">${zost ? `${wizyt(zost)} · następna ok. ${PLAN_DZIS[n].g}` : 'komplet — trasa zakończona'}</span></div>` +
    `<div class="dp-k"><span class="dp-et">Ostatnia wizyta</span><b class="num">${PLAN_DZIS[razem - 1].g}</b><span class="dp-op">${bezZnacznikow(PLAN_DZIS[razem - 1].s)} · ${bezZnacznikow(PLAN_DZIS[razem - 1].m)}</span></div>`;
  const wszystkie = PLAN_DZIS.map(x => minuty(x.g)), A = Math.floor(Math.min(...wszystkie) / 60) * 60, Z = Math.max(A + 120, Math.ceil((Math.max(...wszystkie) + 30) / 60) * 60), pc = v => ((v - A) / (Z - A) * 100).toFixed(2) + '%';
  const t = i => minuty(PLAN_DZIS[i].g), ost = PLAN_DZIS.reduce((m, x, i) => x.ok ? i : m, -1);
  let h = `<div class="dos-tor">`;
  if (ost >= 0) h += `<span class="dos-zrob" style="left:${pc(t(0))};width:calc(${pc(t(ost))} - ${pc(t(0))})"></span>`;
  if (n >= 0) { const a = n > 0 ? t(n - 1) : A + 12; h += `<span class="dos-jazda" style="left:${pc(a)};width:calc(${pc(t(n))} - ${pc(a)})"></span>`; }
  h += PLAN_DZIS.map((x, i) => `<span class="dos-p${x.ok ? ' ok' : ''}${i === n ? ' teraz' : ''}" style="left:${pc(t(i))}"><i></i><b>${bezZnacznikow(x.s)}</b><small class="num">${x.g}</small></span>`).join('');
  os.innerHTML = h + `</div><div class="dos-skala num"><span>${dwa(A / 60)}:00</span><span>${dwa(Z / 60)}:00</span></div>`;
  oznaczWidoczneWiersze();
  const komplet = PLAN_DZIS.length > 0 && PLAN_DZIS.every(x => x.ok);
  $('#kD').classList.toggle('komplet', komplet); { const bl = $('#kD .blask'); if (bl) bl.dataset.d = komplet ? '✓' : String(PLAN_DATA ? Number(PLAN_DATA.slice(8, 10)) : new Date().getDate()); }
  requestAnimationFrame(sprawdzListe);
}
/** Przejście „Dziś” nadaje nazwy TYLKO wierszom w pełni widocznym w liście: wiersz nazwany wychodzi na czas przejścia poza przycięcie kafla, więc wiersze ukryte pod krawędzią
    (przewinięte) pojawiałyby się na wierzchu, nad sąsiednimi kafelkami. Mniej nazw to też lżejsze przechwytywanie. */
function oznaczWidoczneWiersze() {
  const l = $('#przystanki'); if (!l) return; const c = l.getBoundingClientRect();
  for (const w of $$('.przystanek', l)) { const r = w.getBoundingClientRect(); w.classList.toggle('vt', r.height > 0 && r.top >= c.top - 1 && r.bottom <= c.bottom + 1); }
}
function sprawdzListe() {
  const l = $('#przystanki'); if (!l) return;
  l.classList.toggle('przewijana', l.scrollHeight > l.clientHeight + 2 && l.scrollTop + l.clientHeight < l.scrollHeight - 2);
}

/* ====================== dokumenty: fiolki poleceń wobec limitu ====================== */
function budujFiolki() {
  const box = $('#fiolki'), n = M ? M.polecenia.length : 0;
  if (!M || M.stan !== 'gotowe') {
    box.style.gridTemplateColumns = '1fr';
    box.innerHTML = '<div class="pusty-stan"><b>Dokumenty pojawią się po wygenerowaniu</b><span>Każde polecenie wyjazdu ma limit; zobaczysz, jak bardzo je wykorzystano.</span></div>';
    $('#dok-kolka').innerHTML = ''; $('#podp-ile').textContent = '0'; $('#podp-ile-z').textContent = '–'; $('#lim-pol').textContent = `limit polecenia ${fmt(LIMIT_POL)} zł`;
    sygnal('fiolki'); return;
  }
  box.style.gridTemplateColumns = `repeat(${n},minmax(0,1fr)) minmax(0,1.15fr)`;
  const h = M.polecenia.map((p, i) => {
    const u = p.kw / LIMIT_POL, pr = Math.round(u * 100);
    return `<div class="fiolka${u >= .85 ? ' blisko' : ''}" data-pol="${p.nr}" data-dok="${i}" style="--p:${Math.min(1, u).toFixed(4)};--s:${i}" aria-label="Polecenie ${p.nr}, ${dwa(p.od)}–${dwa(p.do)}.${dwa(M.mies)}: ${fmt(p.kw)} zł, ${pr} % limitu ${fmt(LIMIT_POL)} zł">` +
      `<div class="f-rurka"><span class="f-limit" aria-hidden="true"></span><span class="f-ciecz" aria-hidden="true"></span>` +
      `<span class="f-pieczec" data-dok="${i}" role="img" aria-label="Polecenie ${p.nr}: niepodpisane">${ik('i-ok')}</span></div>` +
      `<p class="f-op num" aria-hidden="true"><b>P${p.nr}<em>${pr}&nbsp;%</em></b><span>${fmt(p.kw)}</span><small>${dwa(p.od)}–${dwa(p.do)}.${dwa(M.mies)}</small></p></div>`;
  }).join('');
  const r = `<div class="fiolka rozl" data-dok="${n}" style="--p:1;--s:${n}" aria-label="Rozliczenie: ${fmt(M.suma)} zł, ${n} poleceń">` +
    `<div class="f-rurka"><span class="f-ciecz" aria-hidden="true"></span><span class="f-pieczec" data-dok="${n}" role="img" aria-label="Rozliczenie: niepodpisane">${ik('i-ok')}</span></div>` +
    `<p class="f-op num" aria-hidden="true"><b>R</b><span>${fmt(M.suma).replace(' ', NBSP)}</span><small>${n} ${n === 1 ? 'polecenie' : n < 5 ? 'polecenia' : 'poleceń'}</small></p></div>`;
  box.innerHTML = h + r;
  $('#dok-kolka').innerHTML = Array.from({ length: n + 1 }, () => '<i></i>').join('');
  $('#podp-ile-z').textContent = String(n + 1);
  $('#lim-pol').textContent = `limit polecenia ${fmt(LIMIT_POL)} zł`;
  odswiezPodpisy(); sygnal('fiolki');
}
function odswiezPodpisy() {
  if (!M) return;
  const razem = razemDok();
  $$('.f-pieczec').forEach(st => {
    const i = Number(st.dataset.dok), ok = !!M.podpisane[i];
    st.classList.toggle('ok', ok);
    st.setAttribute('aria-label', (i < M.polecenia.length ? `Polecenie ${i + 1}` : 'Rozliczenie') + (ok ? ': podpisane' : ': niepodpisane'));
  });
  $$('.fiolka').forEach(f => f.classList.toggle('podp-ok', !!M.podpisane[Number(f.dataset.dok)]));
  $$('#dok-kolka i').forEach((k, i) => k.classList.toggle('ok', !!M.podpisane[i]));
  $('#podp-ile').textContent = String(ilePodpisanych());
  const k3 = $('#k3-ile'); if (k3) k3.textContent = `${ilePodpisanych()} z ${razem}`;
  btn.style.setProperty('--pk', String(razem ? ilePodpisanych() / razem * 100 : 0));
}
function podswietlPolecenie(nr, on, tylkoKurtyna) {
  $$('#siatka .swiec, .fiolka.swiec, #ku-pol .swiec').forEach(c => c.classList.remove('swiec'));
  if (!on || !nr || !M) return;
  const p = M.polecenia.find(x => x.nr === nr); if (!p) return;
  const s = $(`#ku-pol [data-pol="${nr}"]`); s && s.classList.add('swiec');
  const w = $(`.fiolka[data-pol="${nr}"]`); w && w.classList.add('swiec');
  if (!tylkoKurtyna) $$('#siatka .dz.trasa').forEach(c => { const d = Number(c.dataset.d); if (d >= p.od && d <= p.do) c.classList.add('swiec'); });
}

/* ====================== kontrola, termin, bohater ====================== */
function kontrola() {
  if (!M || M.stan !== 'gotowe') return null;
  const w = M.wynik, dni = M.dniT.map(d => M.trasy[d]);
  const zam = Number(M.kwota || 0);
  return [
    { t: 'Suma dni = kwota', ok: !w.niepelna && Math.abs(M.suma - zam) < 0.005 },
    { t: `Dzień ≤ ${fmt(LIMIT_DZIEN)} zł`, ik: 'i-le', ok: dni.every(d => d.suma <= LIMIT_DZIEN + 0.005) },
    { t: `Polecenie ≤ ${fmt(LIMIT_POL)} zł`, ik: 'i-le', ok: M.polecenia.every(p => p.kw <= LIMIT_POL + 0.005) },
    { t: 'Bez tras w dniach wolnych', ok: M.dniT.every(d => !M.wolne.has(d)) },
    { t: 'Bez tras w niedziele i święta', ok: M.dniT.every(d => M.robocze0.has(d)) },
  ];
}
function odswiezKontrole() {
  const lista = $('#ko-lista'), pier = $('#ko-luk'), licz = $('#ko-licz'), pod = $('#ko-podtyt');
  const k = kontrola();
  if (!k) { lista.innerHTML = '<li style="grid-column:1/-1">Po wygenerowaniu sprawdzę limity i dni wolne</li>'; pier.style.strokeDasharray = '0 100'; licz.textContent = '–'; pod.textContent = ''; return; }
  const dobre = k.filter(x => x.ok).length;
  lista.innerHTML = k.map(x => {
    const t = x.t.replace(/≤/, '<svg class="zn" aria-label="nie więcej niż" role="img"><use href="#i-le"/></svg>').replace(' zł', NBSP + 'zł');
    return `<li${x.ok ? '' : ' style="color:var(--a-blad)"'}>${ik(x.ok ? 'i-ok' : 'i-zamknij')}${t}</li>`;
  }).join('');
  pier.style.strokeDasharray = `${dobre / k.length * 100} 100`;
  licz.textContent = `${dobre}/${k.length}`;
  pod.textContent = dobre === k.length ? `${k.length} z ${k.length} w porządku` : `${dobre} z ${k.length} w porządku`;
}
/** Termin wysyłki: 10. dzień następnego miesiąca (jak w programie: „do 10.10" dla września). */
function terminMiesiaca() { return new Date(M.mies === 12 ? M.rok + 1 : M.rok, M.mies === 12 ? 0 : M.mies, 10, 12); }
function odswiezTermin() {
  if (!M) return;
  const t = terminMiesiaca(), dzis = new Date(); dzis.setHours(12, 0, 0, 0);
  const dni = Math.round((t - dzis) / 86400000), dt = `${DN[(t.getDay() + 6) % 7]} ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}.${t.getFullYear()}`;
  const gdy = dni > 1 ? `za ${dni} dni` : dni === 1 ? 'jutro' : dni === 0 ? 'dziś' : `po terminie o ${-dni} ${-dni === 1 ? 'dzień' : 'dni'}`, gdyKrotko = dni < 0 ? 'po terminie' : gdy;
  $('#t-op').innerHTML = `<b>${gdy}</b><span>termin · ${DK[(t.getDay() + 6) % 7]} ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}.${t.getFullYear()}</span>`;
  $('#t-tel').innerHTML = `<b>${gdyKrotko}</b><span>${DK[(t.getDay() + 6) % 7]}. ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}</span>`;
  const chipy = [];
  for (let i = Math.min(3, Math.max(0, dni)); i >= 0; i--) { const x = new Date(t); x.setDate(x.getDate() - i); chipy.push({ x, cel: i === 0, dzis: i === dni }); }
  $('#t-dni').innerHTML = chipy.map(c => `<li class="${c.cel ? 'cel' : ''}${c.dzis ? ' dzis' : ''}">${DK[(c.x.getDay() + 6) % 7]}<b>${dwa(c.x.getDate())}</b></li>`).join('');
  const luk = $('#t-luk'), dobre = Math.max(0, Math.min(7, dni));
  luk.setAttribute('stroke-dasharray', `${dobre} 7`); $('#t-pier').textContent = String(Math.max(0, dni));
}
const tekstSilnika = () => M && M.silnik ? 'powyżej 900 cm³' : 'do 900 cm³';
function odswiezHero() {
  const kA = $('#kA'); if (!M) return;
  const gotowe = M.stan === 'gotowe';
  kA.classList.toggle('przed', !gotowe); kA.classList.toggle('po-gen', gotowe);
  const mn = `${MIES[M.mies - 1]} ${M.rok}`;
  $('#b-etyk').textContent = gotowe ? `Do zwrotu · ${mn}` : `Do rozliczenia · ${mn}`;
  $('#m-nazwa').textContent = cap(mn);
  const kmRazem = M.dniT.reduce((a, d) => a + M.trasy[d].km, 0), wizytRazem = M.dniT.reduce((a, d) => a + M.trasy[d].etapy.length - 1, 0);
  const kw = $('#b-kwota-w');
  if (gotowe) { kw.tabIndex = 0; kw.setAttribute('role', 'button'); } else { kw.removeAttribute('tabindex'); kw.removeAttribute('role'); }
  if (gotowe) {
    const podp = M.demo ? 'Przykład — kliknij, aby wpisać własną kwotę' : 'Zmień kwotę (usunie wygenerowane dokumenty)';
    kw.setAttribute('aria-label', `${fmt(M.suma)} zł`); kw.setAttribute('aria-description', podp); kw.title = podp;
    przygotujCyfry($('#kwota'), fmt(M.suma).replace(/ /g, NBSP));
    $('#b-wzor').innerHTML = `<b>${fmt(kmRazem, 1).replace(' ', NBSP)} km</b>` + (M.demo ? `<span class="znaczek">auto ${tekstSilnika()}</span>`
      : `<button type="button" class="znaczek zmien" id="zmien-ust" aria-label="Zmień tryb pracy lub pojemność silnika" title="Zmień tryb pracy lub silnik (usunie wygenerowane dokumenty)">auto ${tekstSilnika()}${ik('i-pioro')}</button>`);
    $('#b-staty').innerHTML = `<li><b>${M.dniT.length}</b>${M.dniT.length === 1 ? 'dzień' : 'dni'} z trasą</li><li><b>${wizytRazem}</b>${wizyt(wizytRazem)}</li>`;
    $('#ku-st').innerHTML = `<b>${M.dniT.length}</b>${M.dniT.length === 1 ? 'dzień' : 'dni'} z trasą · <b>${wizytRazem}</b>${wizyt(wizytRazem)}`;
    $('#ku-limit').textContent = `limit dnia ${fmt(LIMIT_DZIEN)} zł`;
  }
  const zakresy = dni => { const w = []; let i = 0; while (i < dni.length) { let j = i; while (j + 1 < dni.length && dni[j + 1] === dni[j] + 1) j++; w.push(j - i >= 2 ? `${dni[i]}–${dni[j]}` : dni.slice(i, j + 1).join(', ')); i = j + 1; } return w.join(', '); };
  const wolneTxt = [...M.wolne].sort((a, b) => a - b);
  $('#k1-op').innerHTML = `<span>${tekstSilnika()}</span><span>${M.tryb === 'wieczory' ? 'Wieczory 16:30–22:00 · sb' : 'Tydzień, dni robocze'}</span>` + (wolneTxt.length ? `<span>wolne: ${zakresy(wolneTxt)}.${dwa(M.mies)}</span>` : '');
  $('#k2-op').innerHTML = gotowe ? `<span>${M.polecenia.length} ${M.polecenia.length === 1 ? 'polecenie' : M.polecenia.length < 5 ? 'polecenia' : 'poleceń'}</span><span>${M.dniT.length} ${M.dniT.length === 1 ? 'dzień' : 'dni'} z trasą</span><span>${wizytRazem} ${wizyt(wizytRazem)}</span>` : '<span>do wygenerowania</span>';
  const razem = razemDok(), t = terminMiesiaca();
  $('#k3-op').innerHTML = gotowe ? `<span><b id="k3-ile">${ilePodpisanych()} z ${razem}</b> dokumentów · Profil Zaufany</span>` : '<span>Profil Zaufany</span>';
  $('#k4-op').innerHTML = `<span>Kierownik regionu · do ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}</span>`;
  const e = etapMiesiaca(), nr = { ustaw: 1, podpisz: 3, przyklad: 3, wyslij: 4, wyslane: 5 }[e];
  [1, 2, 3, 4].forEach(i => {
    const kr = $('#krok' + i), zrob = i < nr || e === 'wyslane';
    kr.className = 'krok' + (zrob ? ' zrobiony' : i === nr ? ' aktywny' : '');
    $('.wezel', kr).innerHTML = zrob ? ik('i-ok') : String(i);
    kr.style.setProperty('--k', String(i - 1));
  });
  // po wygenerowaniu tryb pracy i silnik są zablokowane, ale mają się dać zmienić: krok „Ustaw” otwiera arkusz zmiany (z potwierdzeniem usunięcia dokumentów)
  const k1 = $('#krok1'), mozeUst = gotowe && !M.demo;
  k1.classList.toggle('zmien', mozeUst); $('.k-tyt', k1).innerHTML = mozeUst ? `Ustaw${ik('i-pioro')}` : 'Ustaw';
  if (mozeUst) { k1.setAttribute('role', 'button'); k1.tabIndex = 0; k1.title = 'Zmień tryb pracy lub silnik (usunie wygenerowane dokumenty)'; } else { k1.removeAttribute('role'); k1.removeAttribute('tabindex'); k1.removeAttribute('title'); }
  const nap = { ustaw: ['Generuj dokumenty', 'i-pioro'], podpisz: [`Podpisz ${razem} ${razem === 1 ? 'dokument' : razem < 5 ? 'dokumenty' : 'dokumentów'}`, 'i-pioro'], wyslij: ['Wyślij do Kierownika regionu', 'i-nawi'], wyslane: ['Wysłano do Kierownika regionu', 'i-ok'], przyklad: [PROFIL ? 'Wróć do swojego miesiąca' : 'Wpisz swoją kwotę', 'i-pioro'] }[e];
  napis.textContent = nap[0]; $('.kropla-tresc use', btn).setAttribute('href', '#' + nap[1]);
  btn.classList.toggle('wyslij', e === 'wyslij'); btn.classList.toggle('gotowe', e === 'wyslane');
  $('#kA').classList.toggle('po', e === 'wyslane');
  ustawStatus({ ustaw: 'Do wygenerowania', podpisz: 'Wygenerowane', wyslij: 'Podpisane', wyslane: 'Wysłane', przyklad: 'Przykład' }[e], e === 'wyslij' || e === 'wyslane');
  odswiezTermin();
  const stat = $('#kropla-napis'); if (stat) btn.setAttribute('aria-label', nap[0]);
  sygnal('hero');
}
/** „Pokaż przykładowy miesiąc” jest dostępne tylko, dopóki użytkownik nie wygenerował własnych dokumentów — potem program pokazuje wyłącznie jego dane. */
const przykladDostepny = () => !magMiesiace.ile();
function odswiezPrzyciskPrzykladu() { const b = $('#pokaz-przyklad'); if (b) b.hidden = !!(M && M.demo) || !przykladDostepny(); }
function odswiezWszystko(opcje = {}) {
  tytulKalendarza(); budujKalendarz(); budujKurtyneDOM(); budujFiolki(); rysujDzien(!!opcje.start); odswiezKontrole(); odswiezHero(); rysujDzis();
  odswiezParametry(); odswiezPowiadomienia(); odswiezPrzyciskPrzykladu();
  kurtyna && kurtyna.dane && kurtyna.dane();
  zaznaczKomorke();
  requestAnimationFrame(() => { kurtyna && kurtyna.rozmiar(); mierz(); ustawSwiatlo(); szkla.forEach(budujSoczewke); skalaMapki(); dopasujPodroz(); });
}

/* ====================== ciekłe szkło: soczewki SVG ====================== */
const SOCZ = {
  czyste:  { bezel: 58, skala: 140, ab: [1, .97, .94], zr: 2.6, mat: 2.2, nas: 1.6, jas: 1.0, jasB: 1.5, sw: 1.0 },
  mroz:    { bezel: 44, skala: 110, ab: null, mat: 15, nas: 2.25, jas: 1.1, jasB: 1.55, sw: .9 },
  dym:     { bezel: 34, skala: 84, ab: null, mat: 18, nas: 2.0, jas: .72, jasB: 1.4, sw: .75 },
  pigulka: { bezel: 14, skala: 30, ab: null, mat: 6, nas: 1.6, jas: .74, jasB: 1.25, sw: .6 },
  pasek:   { bezel: 20, skala: 44, ab: null, mat: 9, nas: 1.7, jas: .66, jasB: 1.2, sw: .5 }
};
/* Dzień: jasne, mroźne szkło — mniej nasycenia, bez przyciemniania tła */
const SOCZ_DZIEN = {
  czyste: { nas: 1.3, jas: 1.0, jasB: 1.1, sw: 1.0 }, mroz: { nas: 1.35, jas: 1.0, jasB: 1.12, sw: .9 }, dym: { nas: 1.2, jas: 1.03, jasB: 1.1, sw: .8 },
  pigulka: { nas: 1.2, jas: 1.04, jasB: 1.1, sw: .6 }, pasek: { nas: 1.2, jas: 1.04, jasB: 1.1, sw: .5 }
};
/* Szkło BEZ rozmywania tła (decyzja o wydajności): każdy element z backdrop-filter zmusza przeglądarkę do przeliczania całej sceny pod nim w KAŻDEJ klatce, niezależnie od jego rozmiaru
   (pomiar: sam pasek nagłówka z rozmyciem potrafił zabrać ~90% kosztu klatki). Zorza jest gładka, więc przezroczyste, barwione szkło wygląda jak matowe także bez rozmycia. ?szklo=blur przywraca rozmycie (do porównań). */
const UZYJ_SOCZEWKI = false;
if (new URLSearchParams(location.search).get('szklo') === 'blur') root.classList.add('szklo-blur');
const czyChromium = (() => {
  try {
    const ua = navigator.userAgent || '';
    const ios = /iP(hone|ad|od)/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const br = navigator.userAgentData && navigator.userAgentData.brands || [];
    return !ios && br.some(b => /Chromium|Google Chrome|Microsoft Edge|Opera/i.test(b.brand)) && CSS.supports('backdrop-filter', 'url(#a)');
  } catch (e) { return false; }
})();
const mapy = new Map();
/* mapa przemieszczeń (R,G = wektor, B = maska obręczy) + mapa światła (połysk fazy) dla zaokrąglonego prostokąta */
function mapaSoczewki(w, h, r, bezel, sw) {
  const klucz = `${w}x${h}x${r}x${bezel}x${sw}`;
  if (mapy.has(klucz)) return mapy.get(klucz);
  const s = 0.5, W = Math.max(4, Math.round(w * s)), H = Math.max(4, Math.round(h * s));
  const cv = doc.createElement('canvas'); cv.width = W; cv.height = H;
  const g = cv.getContext('2d', { willReadFrequently: true }); const im = g.createImageData(W, H); const d = im.data;
  const cv2 = doc.createElement('canvas'); cv2.width = W; cv2.height = H;
  const g2 = cv2.getContext('2d', { willReadFrequently: true }); const im2 = g2.createImageData(W, H); const d2 = im2.data;
  const hw = w / 2, hh = h / 2, ix = hw - r, iy = hh - r;
  const Lx = -0.55, Ly = -0.835;
  for (let j = 0; j < H; j++) {
    const py = (j + .5) / s, ay = Math.abs(py - hh), sy = py < hh ? -1 : 1, qy = ay - iy;
    for (let i = 0; i < W; i++) {
      const px = (i + .5) / s, ax = Math.abs(px - hw), sx = px < hw ? -1 : 1, qx = ax - ix;
      let dist, nx, ny;
      if (qx > 0 && qy > 0) { const L = Math.hypot(qx, qy) || 1; dist = r - L; nx = qx / L; ny = qy / L; }
      else if (qx > qy) { dist = r - qx; nx = 1; ny = 0; }
      else { dist = r - qy; nx = 0; ny = 1; }
      let vx = 0, vy = 0, mk = 0, sv = 0;
      if (dist < bezel) {
        const t = Math.max(0, dist) / bezel;
        const m = Math.pow(1 - t, 1.6);
        vx = -nx * sx * m; vy = -ny * sy * m;
        mk = Math.pow(1 - t, 1.1);
        const ox = nx * sx, oy = ny * sy;
        const dot = ox * Lx + oy * Ly;
        const pas = Math.pow(1 - t, 3.2) * (1 - Math.pow(1 - t, 40));
        sv = (Math.pow(Math.max(0, dot), 2.2) * 1.0 + Math.pow(Math.max(0, -dot), 3) * 0.35) * pas;
      }
      const o = (j * W + i) * 4;
      d[o] = Math.round(128 + vx * 127); d[o + 1] = Math.round(128 + vy * 127); d[o + 2] = Math.round(mk * 255); d[o + 3] = 255;
      d2[o] = 255; d2[o + 1] = 255; d2[o + 2] = 255; d2[o + 3] = Math.round(Math.min(1, sv * sw) * 255);
    }
  }
  g.putImageData(im, 0, 0); g2.putImageData(im2, 0, 0);
  const wynik = { mapa: cv.toDataURL('image/png'), swiatlo: cv2.toDataURL('image/png') };
  if (mapy.size > 40) mapy.delete(mapy.keys().next().value);
  mapy.set(klucz, wynik);
  return wynik;
}
const filtry = $('#filtry');
let nrFiltra = 0;
const stanSocz = new WeakMap();
function budujSoczewke(el) {
  if (!czyChromium || window.__bezSoczewki || !root.classList.contains('soczewka')) return;
  const w = el.offsetWidth, h = el.offsetHeight;
  if (w < 8 || h < 8) return;
  const r = Math.min(parseFloat(getComputedStyle(el).borderTopLeftRadius) || 0, w / 2, h / 2);
  const typ = el.dataset.soczewka || 'mroz', dzien = motywTeraz() === 'light';
  const P = Object.assign({}, SOCZ[typ] || SOCZ.mroz, dzien ? SOCZ_DZIEN[typ] : null);
  const bezel = Math.min(P.bezel, Math.min(w, h) / 2.2);
  let polka = -1;
  if (el.dataset.polka) {
    const cel = el.querySelector(el.dataset.polka);
    if (cel && cel.offsetParent) { let y = 0, n = cel; while (n && n !== el) { y += n.offsetTop; n = n.offsetParent; } polka = Math.max(0, Math.round(y - 12)); }
  }
  const st = stanSocz.get(el);
  if (st && st.w === w && st.h === h && st.r === r && st.polka === polka && st.dzien === dzien) return;
  const id = 'sz' + (++nrFiltra);
  const M = mapaSoczewki(w, h, Math.round(r * 10) / 10, Math.round(bezel), P.sw);
  const sk = P.skala * Math.min(1, bezel / P.bezel);
  /* przemieszczenie czyta lekko rozmyte tło („zr”) i wygładzoną mapę — bez pikselowego pyłu na gwiazdach */
  const dm = (k, n) => `<feDisplacementMap in="zr" in2="mapa" scale="${(sk * k).toFixed(1)}" xChannelSelector="R" yChannelSelector="G" result="${n}"/>`;
  const lin = (v, wej, wyn) => `<feComponentTransfer in="${wej}" result="${wyn}"><feFuncR type="linear" slope="${v}"/><feFuncG type="linear" slope="${v}"/><feFuncB type="linear" slope="${v}"/></feComponentTransfer>`;
  filtry.insertAdjacentHTML('beforeend',
    `<filter id="${id}" x="0" y="0" width="${w}" height="${h}" filterUnits="userSpaceOnUse" primitiveUnits="userSpaceOnUse" color-interpolation-filters="sRGB">` +
    `<feGaussianBlur in="SourceGraphic" stdDeviation="${P.mat}" edgeMode="duplicate" result="mat"/>` +
    `<feGaussianBlur in="SourceGraphic" stdDeviation="${P.zr || 1.4}" edgeMode="duplicate" result="zr"/>` +
    `<feImage href="${M.mapa}" x="0" y="0" width="${w}" height="${h}" preserveAspectRatio="none" result="mapa0"/>` +
    `<feGaussianBlur in="mapa0" stdDeviation="1.5" edgeMode="duplicate" result="mapa"/>` +
    (P.ab
      ? dm(P.ab[0], 'd1') + dm(P.ab[1], 'd2') + dm(P.ab[2], 'd3') +
        `<feColorMatrix in="d1" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="k1"/>` +
        `<feColorMatrix in="d2" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="k2"/>` +
        `<feColorMatrix in="d3" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="k3"/>` +
        `<feComposite in="k1" in2="k2" operator="arithmetic" k2="1" k3="1" result="k12"/>` +
        `<feComposite in="k12" in2="k3" operator="arithmetic" k2="1" k3="1" result="rgb"/>`
      : dm(1, 'rgb')) +
    lin(P.jasB, 'rgb', 'rgbJ') +
    `<feColorMatrix in="mapa" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 1 0 0" result="maska"/>` +
    `<feComposite in="rgbJ" in2="maska" operator="in" result="brzeg"/>` +
    lin(P.jas, 'mat', 'matJ0') +
    (polka >= 0
      ? `<feGaussianBlur in="SourceGraphic" stdDeviation="15" edgeMode="duplicate" result="szron"/>` + lin(dzien ? 1.04 : .6, 'szron', 'szronJ') +
        `<feFlood flood-opacity="1" x="0" y="${polka}" width="${w}" height="${h - polka}" result="mp"/>` +
        `<feComposite in="szronJ" in2="mp" operator="in" result="szronM"/><feComposite in="szronM" in2="matJ0" operator="over" result="matJ"/>`
      : `<feOffset in="matJ0" dx="0" dy="0" result="matJ"/>`) +
    `<feComposite in="brzeg" in2="matJ" operator="over" result="szk"/>` +
    `<feColorMatrix in="szk" type="saturate" values="${P.nas}" result="nas"/>` +
    `<feImage href="${M.swiatlo}" x="0" y="0" width="${w}" height="${h}" preserveAspectRatio="none" result="swiatlo"/>` +
    `<feComposite in="swiatlo" in2="nas" operator="over"/>` +
    `</filter>`);
  el.style.setProperty('--soczewka', `url(#${id})`);
  el.classList.add('ma-soczewke');
  if (st && st.id) { const stary = doc.getElementById(st.id); stary && requestAnimationFrame(() => requestAnimationFrame(() => stary.remove())); }
  stanSocz.set(el, { w, h, r, id, polka, dzien });
}
const szkla = $$('.szklo[data-soczewka]');
const czasySocz = new Map();
const ro = typeof ResizeObserver === 'function' ? new ResizeObserver(wpisy => {
  for (const w of wpisy) {
    const el = w.target;
    clearTimeout(czasySocz.get(el));
    czasySocz.set(el, setTimeout(() => { budujSoczewke(el); mierz(); if (el.id === 'kA') kurtyna && kurtyna.rozmiar(); if (el.id === 'kE') skalaMapki(); }, 160));
  }
}) : null;

/* ====================== zorza (WebGL, wolumetryczne kurtyny) ====================== */
const FS = `precision highp float;
uniform vec2 uR;uniform float uT;uniform vec2 uM;uniform float uFlara,uCieplo,uFaza,uJasn,uDzien;uniform vec2 uCel;
uniform vec3 cZ,cC,cF,cR,cB,cS0,cS1,cS2;
float h11(float p){p=fract(p*.1031);p*=p+33.33;p*=p+p;return fract(p);}
float h21(vec2 p){vec3 q=fract(vec3(p.xyx)*.1031);q+=dot(q,q.yzx+33.33);return fract((q.x+q.y)*q.z);}
float n1(float x){float i=floor(x),f=fract(x);f=f*f*(3.-2.*f);return mix(h11(i),h11(i+1.),f);}
float f1(float x){return .5*n1(x)+.25*n1(x*2.07+3.1)+.125*n1(x*4.13+7.7)+.0625*n1(x*8.3+1.3);}
float wst(vec2 q,float t,float z0,float A,float k,float s,float w){
 float f=q.y-(z0+A*sin(q.x*k+s+t*.22+1.7*f1(q.x*.9+s+t*.04))+A*.35*(f1(q.x*k*.8-s-t*.1)-.5));
 return exp(-f*f/(w*w));
}
void main(){
 vec2 uv=gl_FragCoord.xy/uR;float asp=uR.x/uR.y;
 float t=uT*.05+uFaza;
 vec3 tlo=mix(cS2,cS1,smoothstep(0.,.42,uv.y));
 tlo=mix(tlo,cS0,smoothstep(.36,1.,uv.y));
 tlo+=cC*.05*exp(-uv.y*6.)*(1.-uDzien);
 vec3 rd=vec3((uv.x-.5)*asp*.85+uM.x*.02,uv.y*.9+.06+uM.y*.01,1.);
 vec3 z=vec3(0.);
 float dz=h21(gl_FragCoord.xy*1.37)*.9;
 for(int i=0;i<KROKI;i++){
  float u=(float(i)+dz)/float(KROKI);
  float h=1.+u*u*1.1+u*.08;
  vec2 q=rd.xz*(h/max(rd.y,.02));
  float d=wst(q,t,1.70,.30,2.5,1.3,.04)+.72*wst(q,t*.9,2.9,.35,1.9,5.3,.06)+.62*wst(q,t*.8,4.9,.75,1.15,9.1,.13);
  float r=.6*n1(q.x*13.+t*.5)+.4*n1(q.x*29.-t*.35);
  float r3=n1(q.x*4.5+t*.2);
  float dens=d*(.3+1.45*r*r)*(.4+r3*1.);
  float wag=(2.2*u+.08)*.8+.06;
  float pad=exp(-u*3.)*(1.+3.2*exp(-u*18.));
  vec3 c=mix(cZ,cC,smoothstep(.06,.5,u));
  c=mix(c,cF,smoothstep(.4,.85,u));
  c=mix(c,cR,smoothstep(.75,1.,u)*.6);
  z+=c*dens*pad*wag;
 }
 z*=.95*30./float(KROKI);
 z+=cZ*.075*exp(-uv.y*4.)+cC*.035*exp(-uv.y*10.)+cF*.03*smoothstep(.5,1.,uv.y);
 z*=mix(1.,.6,smoothstep(.84,.99,uv.y));
 z*=1.+uFlara*1.1;
 z+=cR*uFlara*.08*smoothstep(.3,1.,uv.y);
 vec2 dc=(uv-uCel)*vec2(asp,1.);
 z+=cB*uCieplo*.42*exp(-20.*dot(dc,dc));
 vec3 zt=1.-exp(-z*1.3);
 vec3 noc=(tlo+zt)*uJasn;
 float a=clamp(max(zt.r,max(zt.g,zt.b)),0.,1.);
 vec3 barwa=zt/max(a,.001);
 vec3 dzien=mix(tlo,barwa*.78,min(a*.86,.8)*uJasn);
 vec3 kol=mix(noc,dzien,uDzien);
 kol+=(h21(gl_FragCoord.xy+fract(uT*.37)*100.)-.5)/255.;
 gl_FragColor=vec4(kol,1.);
}`;
/* renderowanie programowe (bez GPU, np. SwiftShader): JEDYNA różnica — zorza odświeżana rzadziej (dryf i tak jest powolny);
   wygląd każdej klatki jest taki sam jak na prawdziwym GPU */
/* Drugi przebieg zorzy: obraz liczony w niskiej rozdzielczości trafia do tekstury, a stąd na płótno przez wygładzające powiększenie bikubiczne (B-spline, 4 odczyty)
   i drobny szum rozpraszający. Dzięki temu nie ma „pikseli” ani siatki, nawet gdy ekran ma skalowanie 125–200% — samo liczenie zorzy zostaje tanie. */
const FS_POW = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform sampler2D uTex; uniform vec2 uTexSize; uniform vec2 uOut;
vec4 cub(float v){ vec4 n=vec4(1.,2.,3.,4.)-v; vec4 s=n*n*n; float x=s.x; float y=s.y-4.*s.x; float z=s.z-4.*s.y+6.*s.x; float w=6.-x-y-z; return vec4(x,y,z,w)*(1./6.); }
vec3 bic(vec2 uv){
  vec2 isz=1./uTexSize; vec2 tc=uv*uTexSize-.5; vec2 f=fract(tc); tc-=f;
  vec4 xc=cub(f.x), yc=cub(f.y);
  vec4 c=tc.xxyy+vec2(-.5,1.5).xyxy;
  vec4 s=vec4(xc.xz+xc.yw, yc.xz+yc.yw);
  vec4 o=(c+vec4(xc.yw,yc.yw)/s)*isz.xxyy;
  vec3 s0=texture2D(uTex,o.xz).rgb, s1=texture2D(uTex,o.yz).rgb, s2=texture2D(uTex,o.xw).rgb, s3=texture2D(uTex,o.yw).rgb;
  float sx=s.x/(s.x+s.y), sy=s.z/(s.z+s.w);
  return mix(mix(s3,s2,sx), mix(s1,s0,sx), sy);
}
float h(vec2 p){ return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453); }
void main(){
  vec2 uv=gl_FragCoord.xy/uOut; vec3 c=bic(uv);
  c+=(h(gl_FragCoord.xy)+h(gl_FragCoord.yx*1.7)-1.)/255.*1.1;
  gl_FragColor=vec4(c,1.);
}`;
function startZorza() {
  const cv = $('#zorza'), gw = $('#gw');
  if (window.__bezZorzy) { cv.classList.add('brak'); return null; }
  let gl = null;
  try { gl = cv.getContext('webgl', { antialias: false, depth: false, stencil: false, alpha: false, premultipliedAlpha: false, preserveDrawingBuffer: false, powerPreference: 'low-power' }); } catch (e) { gl = null; }
  if (!gl) { cv.classList.add('brak'); return null; }
  let prog = null, U = {}, progB = null, UB = {}, fbo = null, tex = null, fw = 2, fh = 2, raf = 0, ostatnia = -1e9, t0 = czas(), zgubiony = false, pauza = false;
  const st = { flara: 0, flaraCel: 0, cieplo: 0, cieploCel: 0, faza: 0, fazaCel: 0, mx: 0, my: 0, mxCel: 0, myCel: 0, jasn: 0, cx: .55, cy: .5 };
  function init() {
    const sh = (typ, src) => { const o = gl.createShader(typ); gl.shaderSource(o, src); gl.compileShader(o); return gl.getShaderParameter(o, gl.COMPILE_STATUS) ? o : null; };
    const vs = sh(gl.VERTEX_SHADER, 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}');
    const fs = sh(gl.FRAGMENT_SHADER, '#define KROKI 28\n' + FS);
    if (!vs || !fs) return false;
    if (prog) { try { gl.deleteProgram(prog); } catch (e) { /* stary program już zwolniony */ } }
    const fsB = sh(gl.FRAGMENT_SHADER, FS_POW);
    if (!fsB) return false;
    prog = gl.createProgram(); gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.bindAttribLocation(prog, 0, 'p'); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return false;
    if (progB) { try { gl.deleteProgram(progB); } catch (e) { /* stary program już zwolniony */ } }
    progB = gl.createProgram(); gl.attachShader(progB, vs); gl.attachShader(progB, fsB); gl.bindAttribLocation(progB, 0, 'p'); gl.linkProgram(progB);
    if (!gl.getProgramParameter(progB, gl.LINK_STATUS)) return false;
    for (const n of ['uTex', 'uTexSize', 'uOut']) UB[n] = gl.getUniformLocation(progB, n);
    tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    fbo = gl.createFramebuffer();
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.useProgram(prog);
    for (const n of ['uR', 'uT', 'uM', 'uFlara', 'uCieplo', 'uFaza', 'uJasn', 'uDzien', 'uCel', 'cZ', 'cC', 'cF', 'cR', 'cB', 'cS0', 'cS1', 'cS2']) U[n] = gl.getUniformLocation(prog, n);
    kolory(); rozmiar();
    return true;
  }
  function kolory() {
    if (zgubiony || !prog) return;
    gl.useProgram(prog);
    const k = (u, n) => gl.uniform3fv(U[u], tokenRGB(n));
    k('cZ', '--zorza-z'); k('cC', '--zorza-c'); k('cF', '--zorza-f'); k('cR', '--zorza-r'); k('cB', '--burs'); k('cS0', '--niebo-0'); k('cS1', '--niebo-1'); k('cS2', '--niebo-2');
    gl.uniform1f(U.uDzien, motywTeraz() === 'light' ? 1 : 0);
  }
  /* rozdzielczość: pole zorzy w 0,3 piksela CSS do tekstury, a na płótno w pikselach urządzenia (natywnie, do ZORZA_MAX_PIKSELI) gładkim powiększeniem bikubicznym */
  function rozmiar() {
    const W = innerWidth + 48, H = innerHeight + 48;
    const dpr = Math.min(2, devicePixelRatio || 1), sk = rzadko ? .6 : Math.min(dpr, Math.sqrt(ZORZA_MAX_PIKSELI / (W * H)));
    const w = Math.max(2, Math.round(W * sk)), h = Math.max(2, Math.round(H * sk));
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    window.__zorzaWyjscie = `${w}×${h} px`;
    fw = Math.max(64, Math.round(W * ZORZA_POLE)); fh = Math.max(36, Math.round(H * ZORZA_POLE));
    gl.bindTexture(gl.TEXTURE_2D, tex); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, fw, fh, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0); gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.useProgram(prog); gl.uniform2f(U.uR, fw, fh);
    gl.useProgram(progB); gl.uniform1i(UB.uTex, 0); gl.uniform2f(UB.uTexSize, fw, fh); gl.uniform2f(UB.uOut, w, h);
  }
  function rysuj(T) {
    if (zgubiony || !prog) return;
    gl.useProgram(prog); gl.bindFramebuffer(gl.FRAMEBUFFER, fbo); gl.viewport(0, 0, fw, fh);
    gl.uniform1f(U.uT, T); gl.uniform2f(U.uM, st.mx, st.my);
    gl.uniform1f(U.uFlara, st.flara); gl.uniform1f(U.uCieplo, st.cieplo); gl.uniform1f(U.uFaza, st.faza); gl.uniform1f(U.uJasn, st.jasn);
    gl.uniform2f(U.uCel, st.cx, st.cy);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, cv.width, cv.height);
    gl.useProgram(progB); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    if (migot) migot.style.opacity = (.64 + .36 * Math.sin(T * .65)).toFixed(3);       // migotanie gwiazd w rytmie zorzy: zero dodatkowych odświeżeń tła pod szkłem
  }
  /* paralaksa: zorza dalej (większy ruch), gwiazdy bliżej horyzontu nieba (mniejszy); wygładzanie i przesunięcie przy KAŻDEJ klatce przeglądarki (płynnie nawet gdy pole zorzy odświeża się 33 razy/s) */
  let ostPar = 0, paraZapis = '';
  function paralaksa(t) {
    const dt = rzadko ? 5 : Math.min(.05, ostPar ? (t - ostPar) / 1000 : .016); ostPar = t;
    const k = 1 - Math.exp(-dt * 2.2);
    st.mx += (st.mxCel - st.mx) * k; st.my += (st.myCel - st.my) * k;
    const z = `${(-st.mx * 16).toFixed(2)}|${(st.my * 10).toFixed(2)}`;
    if (z === paraZapis) return;
    paraZapis = z;
    cv.style.transform = `translate3d(${(-st.mx * 16).toFixed(2)}px,${(st.my * 10).toFixed(2)}px,0)`;
    gw.style.transform = `translate3d(${(-st.mx * 6).toFixed(2)}px,${(st.my * 4).toFixed(2)}px,0)`;
  }
  const migot = $('#migot');
  const bramka = bramkaTla(), startStrony = performance.now(); let oknoFps = 0, oknoN = 0, zleOkna = 0;
  /* pomiar realnej płynności strony: dwa złe okna po 3 s (po rozruchu) obniżają tempo tła o jeden stopień; nigdy w górę */
  function pomiarTempa(t) {
    if (rzadko || doc.hidden || pauza || window.__bezAdaptacji || RUCH.okno() || RUCH.cisza || tlaTrzymane(t)) { oknoFps = 0; return; }
    if (!oknoFps) { oknoFps = t; oknoN = 0; return; }
    oknoN++; if (t - oknoFps < 3000) return;
    const fps = oknoN / ((t - oknoFps) / 1000); oknoFps = t; oknoN = 0;
    if (performance.now() - startStrony < 12000) return;
    if (fps < 40 && RUCH.poziom < KROKI_TEMPA.length - 1) { if (++zleOkna >= 2) { zleOkna = 0; RUCH.poziom++; window.__zorzaPoziom = RUCH.poziom; } } else zleOkna = 0;
  }
  function klatka() {
    raf = requestAnimationFrame(klatka);
    const t = czas();
    paralaksa(t); pomiarTempa(t);
    if (!RUCH.cisza && t - RUCH.ostWej > 60000 && !rzadko) ustawCisze(true);
    if (tlaTrzymane(t) || !bramka(t)) return;
    window.__zorzaKlatki = (window.__zorzaKlatki || 0) + 1;      // licznik dla testów: zorza naprawdę pływa
    /* przy rzadkim odświeżaniu (tylko testy na grafice programowej) stan dociąga się do tego, jaki byłby po 5 s */
    const dt = rzadko ? 5 : Math.min(0.12, (t - ostatnia) / 1000); ostatnia = t;
    const k = 1 - Math.exp(-dt * 2.6);
    st.flaraCel *= Math.exp(-dt * 1.1); st.cieploCel *= Math.exp(-dt * .7);
    st.flara += (st.flaraCel - st.flara) * k; st.cieplo += (st.cieploCel - st.cieplo) * k;
    st.faza += (st.fazaCel - st.faza) * (1 - Math.exp(-dt * 1.6));
    /* wschód zorzy 1,4 s; przy rzadkim odświeżaniu (SwiftShader) od razu pełna jasność, jak na GPU po starcie */
    const p = rzadko ? 1 : Math.min(1, (t - t0) / 1400); st.jasn = 1 - Math.pow(1 - p, 3);
    rysuj((t - t0) / 1000 + 30);
  }
  function stop() { cancelAnimationFrame(raf); raf = 0; }
  function tryb() {
    stop();
    if (spokoj) { st.jasn = 1; st.mx = st.my = 0; st.flara = st.cieplo = 0; rysuj(42); }
    else if (!doc.hidden && !pauza) { ostatnia = -1e9; raf = requestAnimationFrame(klatka); }
  }
  if (!init()) { cv.classList.add('brak'); return null; }
  cv.addEventListener('webglcontextlost', e => { e.preventDefault(); zgubiony = true; stop(); });
  cv.addEventListener('webglcontextrestored', () => { zgubiony = false; if (init()) tryb(); });
  doc.addEventListener('visibilitychange', () => { if (doc.hidden) stop(); else tryb(); });
  tryb();
  return {
    tryb,
    restart() { t0 = czas(); },
    kolory() { kolory(); rysuj(spokoj ? 42 : (czas() - t0) / 1000 + 30); },
    wstrzymaj(v) { pauza = v; if (v) stop(); else tryb(); },
    rozmiar() { if (!zgubiony) { rozmiar(); if (spokoj) rysuj(42); } },
    flara(v) { st.flaraCel = Math.max(st.flaraCel, v); if (rzadko) { st.flara = st.flaraCel; ostatnia = -1e9; } },
    cieplo(v) { st.cieploCel = Math.max(st.cieploCel, v); },
    cel(x, y) { st.cx = x; st.cy = y; },
    przesun(k) { st.fazaCel += 0.55 * k; },
    mysz(x, y) { if (!spokoj) { st.mxCel = x; st.myCel = y; } }
  };
}
function ustawCelCiepla() {
  const t = $('#termin .t-dni .cel') || $('#termin'); if (!t || !zorza) return;
  const r = t.getBoundingClientRect(); if (!r.width) return;
  zorza.cel((r.left + r.width / 2 + 24) / (innerWidth + 48), 1 - (r.top + r.height / 2 + 24) / (innerHeight + 48));
}

/* ====================== gwiazdy i horyzont ====================== */
function rysujGwiazdy() {
  const dpr = Math.min(2, devicePixelRatio || 1), W = Math.round(innerWidth * dpr), H = Math.round(innerHeight * dpr);
  const a = $('#gwiazdy'), b = $('#migot');
  for (const c of [a, b]) { c.width = W; c.height = H; }
  const ga = a.getContext('2d'), gb = b.getContext('2d');
  const rnd = mulberry(20261007);
  const kol = [tokenRGB('--biel'), tokenRGB('--mieta'), tokenRGB('--burs'), tokenRGB('--cyan')].map(c => c.map(v => Math.round(v * 255)));
  const n = Math.round(innerWidth * innerHeight / 1100);
  for (let i = 0; i < n; i++) {
    const x = rnd() * W, y = Math.pow(rnd(), 1.4) * H * 0.9;
    const r = (0.3 + Math.pow(rnd(), 7) * 1.35) * dpr;
    const al = (0.25 + rnd() * 0.7) * (1 - y / H * 0.55);
    const ki = rnd(); const c = ki < .78 ? kol[0] : ki < .88 ? kol[1] : ki < .95 ? kol[3] : kol[2];
    const jasna = r > 0.95 * dpr || rnd() < 0.04;
    const g = jasna ? gb : ga;
    g.fillStyle = `rgba(${c[0]},${c[1]},${c[2]},${Math.min(1, al + (jasna ? .3 : 0)).toFixed(3)})`;
    if (jasna) { g.shadowColor = g.fillStyle; g.shadowBlur = 6 * dpr; } else g.shadowBlur = 0;
    g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
  }
}
function rysujHoryzont() {
  const svg = $('#horyzont'), W = Math.max(1, innerWidth), H = Math.max(40, Math.round(innerHeight * 0.14));
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const rnd = mulberry(77);
  let d1 = `M0 ${H}`;
  for (let x = 0; x <= W + 8; x += 8) d1 += ` L${x} ${(H * .5 + Math.sin(x * .0036 + 1) * H * .13 + Math.sin(x * .011) * H * .05).toFixed(1)}`;
  d1 += ` L${W} ${H} Z`;
  let d2 = `M0 ${H}`, x = -4;
  const baza = x => H * .80 + Math.sin(x * .0028 + 2) * H * .07 + Math.sin(x * .009) * H * .025;
  while (x < W + 10) {
    const tw = 4 + rnd() * 7, th = 5 + Math.pow(rnd(), 1.4) * H * .34, b0 = baza(x);
    d2 += ` L${x.toFixed(1)} ${b0.toFixed(1)} L${(x + tw * .5).toFixed(1)} ${(b0 - th).toFixed(1)} L${(x + tw).toFixed(1)} ${baza(x + tw).toFixed(1)}`;
    x += tw * (0.55 + rnd() * 0.5);
  }
  d2 += ` L${W} ${H} Z`;
  svg.innerHTML = `<path class="g1" d="${d1}"/><path class="g2" d="${d2}"/>`;
}

/* ====================== światło krawędzi + pochylenie ====================== */
const rects = new Map();
function mierz() { for (const el of szkla) rects.set(el, el.getBoundingClientRect()); }
const sw = { x: 0, y: 0, cx: 0, cy: 0 };
const domyslne = () => { sw.cx = innerWidth * 0.28; sw.cy = -innerHeight * 0.22; };
domyslne(); sw.x = sw.cx; sw.y = sw.cy;
let hover = null; const pochyl = new Map();
let petla = 0, ostP = 0;
/* połysk krawędzi podąża za kursorem. Każda zmiana przemalowuje krawędź szkła (maska + gradienty), a to najdroższa rzecz na komputerach bez karty graficznej —
   dlatego w trakcie ruchu aktualizujemy tylko kafle w zasięgu połysku (starego lub nowego położenia); reszta ma go i tak niewidocznego. */
function ustawSwiatlo(stare) {
  const R = (parseFloat(getComputedStyle(root).fontSize) || 16) * 31, R2 = R * R;
  const blisko = (r, x, y) => { const dx = Math.max(r.left - x, 0, x - r.right), dy = Math.max(r.top - y, 0, y - r.bottom); return dx * dx + dy * dy < R2; };
  for (const el of szkla) {
    const r = rects.get(el); if (!r) continue;
    if (stare && !blisko(r, sw.x, sw.y) && !blisko(r, stare.x, stare.y)) continue;
    el.style.setProperty('--lx', (sw.x - r.left).toFixed(1) + 'px');
    el.style.setProperty('--ly', (sw.y - r.top).toFixed(1) + 'px');
  }
}
function krokPetli() {
  petla = 0;
  const t = czas(), dt = Math.min(0.05, Math.max(0.001, (t - ostP) / 1000)); ostP = t;
  const k = 1 - Math.exp(-dt * 14);
  const stare = { x: sw.x, y: sw.y };
  sw.x += (sw.cx - sw.x) * k; sw.y += (sw.cy - sw.y) * k;
  ustawSwiatlo(stare);
  let ruch = Math.abs(sw.cx - sw.x) + Math.abs(sw.cy - sw.y) > 0.5;
  for (const [el, s] of pochyl) {
    const ax = 170 * (s.tx - s.rx) - 18 * s.vx, ay = 170 * (s.ty - s.ry) - 18 * s.vy;
    s.vx += ax * dt; s.vy += ay * dt; s.rx += s.vx * dt; s.ry += s.vy * dt;
    const spi = Math.abs(s.tx - s.rx) + Math.abs(s.ty - s.ry) + Math.abs(s.vx) + Math.abs(s.vy) < 0.002;
    if (spi && s.tx === 0 && s.ty === 0) { el.style.transform = ''; pochyl.delete(el); continue; }
    el.style.transform = `perspective(1600px) rotateX(${s.rx.toFixed(3)}deg) rotateY(${s.ry.toFixed(3)}deg)`;
    if (!spi) ruch = true;
  }
  if (ruch) petla = requestAnimationFrame(krokPetli);
}
const budz = () => { if (!petla) { ostP = czas(); petla = requestAnimationFrame(krokPetli); } };
addEventListener('pointermove', e => {
  if (e.pointerType === 'touch' || spokoj) return;      // światło kafli i przechylanie za kursorem — tylko w pełnym ruchu
  sw.cx = e.clientX; sw.cy = e.clientY;
  zorza && zorza.mysz(e.clientX / innerWidth * 2 - 1, -(e.clientY / innerHeight * 2 - 1));
  const k = e.target.closest && e.target.closest('.kafel');
  if (hover && hover !== k) celPochyl(hover, 0, 0);
  hover = k;
  if (k && !spokoj && !k.classList.contains('skupiony') && !skupiony) {
    const r = rects.get(k) || k.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - .5, py = (e.clientY - r.top) / r.height - .5;
    const mocn = 2.2 * Math.min(1, 520 / Math.max(r.width, r.height));
    celPochyl(k, -py * mocn, px * mocn);
  }
  budz();
}, { passive: true });
doc.addEventListener('pointerleave', () => { domyslne(); zorza && zorza.mysz(0, 0); if (hover) celPochyl(hover, 0, 0); hover = null; budz(); });
function celPochyl(el, tx, ty) {
  let s = pochyl.get(el);
  if (!s) { if (tx === 0 && ty === 0) return; s = { rx: 0, ry: 0, vx: 0, vy: 0, tx: 0, ty: 0 }; pochyl.set(el, s); }
  s.tx = tx; s.ty = ty;
}

/* ====================== tryb skupienia (głębia: kafel do przodu, reszta w głąb) ====================== */
let skupiony = null;
function skupienie(k) {
  if (k === skupiony) return;
  const el = k || skupiony; if (!el) return;
  pochyl.forEach((s, e) => { e.style.transform = ''; }); pochyl.clear();
  el.style.viewTransitionName = 'skupiony';
  zorza && zorza.przesun(k ? 0.8 : -0.8);
  przejscie(() => {
    if (skupiony) skupiony.classList.remove('skupiony');
    skupiony = k || null;
    bento.classList.toggle('skupienie', !!skupiony);
    if (skupiony) skupiony.classList.add('skupiony');
    $$('.rozwin').forEach(b => {
      const t = b.closest('.kafel'), on = t === skupiony;
      b.setAttribute('aria-label', on ? 'Zamknij widok rozwinięty (Esc)' : b.dataset.etykieta);
      b.setAttribute('aria-expanded', String(on));
    });
    $$('.bento>.kafel').forEach(t => { if (skupiony && t !== skupiony) t.setAttribute('inert', ''); else t.removeAttribute('inert'); });
    if (skupiony && skupiony.id === 'kE') kometa(400);
  }, () => { el.style.viewTransitionName = ''; setTimeout(() => { szkla.forEach(budujSoczewke); mierz(); ustawSwiatlo(); sprawdzListe(); skalaMapki(); dopasujPodroz(); }, 30); }, 'skupienie', { el, otwiera: !!k });
}

/* ====================== przycisk główny: kropla ciekłego szkła ====================== */
const btn = $('#podpisz'), napis = $('#kropla-napis');
function zmienNapis(t, ikona) {
  const w0 = btn.offsetWidth;
  btn.style.width = w0 + 'px';
  napis.textContent = t;
  if (ikona) { const u = $('.kropla-tresc use', btn); u && u.setAttribute('href', '#' + ikona); }
  btn.style.width = 'auto'; const w1 = btn.offsetWidth; btn.style.width = w0 + 'px';
  void btn.offsetWidth;
  btn.style.transition = 'width .75s var(--e-gum), transform .55s var(--e-gum)';
  btn.style.width = w1 + 'px';
  zegar(800).then(() => { btn.style.width = ''; btn.style.transition = ''; });
}
btn.addEventListener('pointermove', e => {
  if (spokoj) return;
  const r = btn.getBoundingClientRect();
  const x = Math.max(16, Math.min(r.width - 16, e.clientX - r.left));
  const yRel = (e.clientY - r.top) / r.height;
  const y = yRel < .5 ? 4 : r.height - 4;
  btn.style.setProperty('--bx', (x + 16) + 'px'); btn.style.setProperty('--by', (y + 16) + 'px');
  btn.style.setProperty('--mx2', ((e.clientX - r.left - r.width / 2) / r.width * 6).toFixed(2) + 'px');
  btn.style.setProperty('--my2', ((e.clientY - r.top - r.height / 2) / r.height * 4).toFixed(2) + 'px');
});
function lot(i, x0, y0, cel) {
  return new Promise(res => {
    if (!cel || !cel.getClientRects().length || spokoj) { zegar(260).then(res); return; }
    const r = cel.getBoundingClientRect(), x1 = r.left + r.width / 2, y1 = r.top + r.height / 2;
    const k = doc.createElement('div'); k.className = 'lot'; doc.body.appendChild(k);
    const cx = (x0 + x1) / 2 + (i - 2) * 26, cy = Math.min(y0, y1) - 110 - i * 14;
    const kl = [];
    for (let s = 0; s <= 24; s++) {
      const t = s / 24, u = 1 - t;
      const x = u * u * x0 + 2 * u * t * cx + t * t * x1, y = u * u * y0 + 2 * u * t * cy + t * t * y1;
      const sc = 1 + 0.25 * Math.sin(t * Math.PI) - (t > .9 ? (t - .9) * 4 : 0);
      kl.push({ transform: `translate(${x.toFixed(1)}px,${y.toFixed(1)}px) scale(${sc.toFixed(3)})`, offset: t });
    }
    const a = k.animate(kl, { duration: 640, easing: 'cubic-bezier(.45,.05,.3,1)' });
    let gotowe = false; const kon = () => { if (gotowe) return; gotowe = true; k.remove(); res(); };
    a.onfinish = kon; a.oncancel = kon; zegar(700).then(kon);
  });
}
function ustawStatus(t, kl) {
  for (const s of [$('#status'), $('#status-tel')]) { s.classList.toggle('podpisane', !!kl); $('span', s).textContent = t; }
}

/* ====================== arkusze (okna z treścią) ====================== */
let arkuszOtwarty = null, arkuszPoZamknieciu = null, fokusPrzed = null;
const arkTlo = $('#arkusz-tlo'), arkTresc = $('#arkusz-tresc');
let arkuszKoniec = 0;
function otworzArkusz(html, poZamknieciu, opcje) {
  clearTimeout(arkuszKoniec); arkTlo.classList.remove('zamyka');
  fokusPrzed = doc.activeElement; arkuszPoZamknieciu = poZamknieciu || null;
  $('#arkusz').classList.toggle('szeroki', !!(opcje && opcje.szeroki));
  arkTresc.innerHTML = html; arkTlo.classList.add('otwarty'); arkuszOtwarty = true; root.classList.toggle('okno', !dostepBlokada);      // pulpit pod otwartym oknem blaknie i się rozmywa (poza oknem logowania)
  $('#arkusz').scrollTop = 0;
  const pierwsze = $('[data-pierwsze]', arkTresc) || $('input,select,button', arkTresc); pierwsze && pierwsze.focus({ preventScroll: true });
  dodajPodpowiedzi(arkTresc);
  szkla.forEach(budujSoczewke);
  requestAnimationFrame(() => szkla.forEach(budujSoczewke));
}
/** Podmienia treść otwartego okna (kolejny krok tego samego okna), bez zamykania i otwierania. */
function zmienArkusz(html) {
  arkTresc.innerHTML = html; $('#arkusz').scrollTop = 0;
  const pierwsze = $('[data-pierwsze]', arkTresc) || $('input,select,button', arkTresc); pierwsze && pierwsze.focus({ preventScroll: true });
  dodajPodpowiedzi(arkTresc);
}
let dostepBlokada = false;      // okno logowania nie zamyka się Esc, tłem ani krzyżykiem
function zamknijArkusz() {
  if (!arkuszOtwarty || dostepBlokada) return;
  arkuszOtwarty = false; root.classList.remove('okno');
  if (spokoj) { arkTlo.classList.remove('otwarty'); arkTresc.innerHTML = ''; }
  else { arkTlo.classList.add('zamyka'); arkuszKoniec = setTimeout(() => { arkTlo.classList.remove('otwarty', 'zamyka'); arkTresc.innerHTML = ''; }, 200); }
  const f = arkuszPoZamknieciu; arkuszPoZamknieciu = null; f && f();
  fokusPrzed && fokusPrzed.focus && fokusPrzed.focus({ preventScroll: true });
}
arkTlo.addEventListener('click', e => { if (e.target === arkTlo) zamknijArkusz(); });
arkTresc.addEventListener('click', e => { if (e.target.closest('[data-zamknij]')) zamknijArkusz(); });
const naglowekArkusza = (tytul) => `<div class="ark-gora"><h2 id="ark-tyt">${tytul}</h2><button type="button" class="ark-zam" data-zamknij aria-label="Zamknij">${ik('i-zamknij')}</button></div>`;
const bezZnacznikow = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ====================== Moje dane ====================== */
const peselPoprawny = p => { p = String(p).replace(/\s/g, ''); if (!/^\d{11}$/.test(p)) return false; const w = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]; let s = 0; for (let i = 0; i < 10; i++) s += w[i] * +p[i]; return (10 - s % 10) % 10 === +p[10]; };
function otworzMojeDane(pierwsze) {
  const p = PROFIL || { imie: dostep.imieZSerwera(), pesel: '', adres: '', stanowisko: 'merchandiser', silnik_powyzej_900: true, tryb: 'tydzien' };
  otworzArkusz(`${naglowekArkusza(pierwsze ? 'Zacznijmy od Twoich danych' : 'Moje dane')}
    <p class="ark-opis">Imię i PESEL zostają tylko na tym urządzeniu (trafiają na dokumenty). Sam adres wysyłam do mapy OpenStreetMap, żeby policzyć kilometry.</p>
    <div class="przenos"><label class="przycisk" id="przenos-etykieta">Wczytaj dane z programu na komputerze<input type="file" id="plik-program" accept=".pmtdane,.json,application/json" hidden></label><small id="przenos-info" aria-live="polite">Pracowałeś w programie na komputerze? Wskaż plik z danymi, który zapisał (PMT_dane_do_aplikacji.pmtdane) — nie musisz niczego wpisywać od nowa.</small></div>
    <form id="form-dane" class="ark-pola" novalidate autocomplete="off">
      <label class="pole pelne"><span>Imię i nazwisko</span><input id="d-imie" data-pierwsze value="${bezZnacznikow(p.imie)}" autocomplete="name" required><small></small></label>
      <label class="pole"><span>PESEL</span><input id="d-pesel" inputmode="numeric" maxlength="11" value="${bezZnacznikow(p.pesel)}" autocomplete="off" required><small></small></label>
      <label class="pole"><span>Stanowisko</span><select id="d-stan"><option value="merchandiser"${p.stanowisko === 'KR' ? '' : ' selected'}>merchandiser</option><option value="KR"${p.stanowisko === 'KR' ? ' selected' : ''}>KR</option></select><small></small></label>
      <label class="pole pelne"><span>Adres zamieszkania</span><input id="d-adres" value="${bezZnacznikow(p.adres)}" placeholder="ul. Polna 5, 00-001 Warszawa  albo  Dębowa Wola 12, 26-660 Jedlińsk" autocomplete="street-address" required><small></small></label>
      <div class="pole pelne" id="typ-adresu" hidden><span>Rodzaj adresu</span><div class="seg" role="group" aria-label="Rodzaj adresu"><button type="button" data-typ="ulica" aria-pressed="false">Ulica</button><button type="button" data-typ="wies" aria-pressed="false">Miejscowość bez ulicy</button></div><small id="typ-opis" aria-live="polite"></small></div>
    </form>
    <div class="ark-dol">${pierwsze ? '' : '<button type="button" class="przycisk" id="usun-dane" title="Usuń z tego urządzenia PESEL, miesiące, plan i dokumenty">Usuń dane z urządzenia</button><button type="button" class="przycisk" data-zamknij>Anuluj</button>'}<button type="button" class="przycisk glowny" id="zapisz-dane">Zapisz</button></div>`);
  const usunBtn = $('#usun-dane', arkTresc); if (usunBtn) usunBtn.addEventListener('click', arkuszUsunDane);
  const f = $('#form-dane', arkTresc);
  f.addEventListener('click', e => { const b = e.target.closest('.seg button'); if (!b) return; $$('button', b.parentElement).forEach(x => x.setAttribute('aria-pressed', String(x === b))); });
  /* adres bez ulicy (wieś): silnik rozpoznaje go sam, a gdy nazwa jest niejednoznaczna („Dębowa Wola”, „Zielona Ścieżka”), pytamy — tak jak program na komputerze */
  let wybor = p.typ_adresu || null, nrSpr = 0, tAdres = 0;
  const blokTypu = $('#typ-adresu', arkTresc), opisTypu = $('#typ-opis', arkTresc);
  const sprawdzAdres = async () => {
    const pole = $('#d-adres', arkTresc); if (!pole || !doc.contains(blokTypu)) return;      // okno „Moje dane” zdążyło się zamknąć przed odliczeniem
    const adres = pole.value.trim(), nr = ++nrSpr;
    if (!adres) { blokTypu.hidden = true; return; }
    let a; try { a = await silnik.adres({ adres, wymus_typ: wybor || undefined }); } catch (e) { a = { ok: false }; }
    if (nr !== nrSpr || !doc.contains(blokTypu)) return;
    if (!a.ok) { blokTypu.hidden = true; return; }
    blokTypu.hidden = false;
    const typ = a.niejednoznaczne ? null : (a.to_wies ? 'wies' : 'ulica');
    $$('[data-typ]', blokTypu).forEach(b => b.setAttribute('aria-pressed', String(b.dataset.typ === typ)));
    opisTypu.classList.remove('zle');
    opisTypu.textContent = typ ? `${typ === 'wies' ? 'Miejscowość bez ulicy. ' : ''}Start i meta trasy: ${a.baza_miasto}.` : `„${a.nazwa_do_pytania}” — to nazwa ulicy czy miejscowości? Wybierz, żebym wiedział, skąd liczyć trasy.`;
  };
  blokTypu.addEventListener('click', e => { const b = e.target.closest('[data-typ]'); if (!b) return; wybor = b.dataset.typ; sprawdzAdres(); });
  $('#d-adres', arkTresc).addEventListener('input', () => { wybor = null; clearTimeout(tAdres); tAdres = setTimeout(sprawdzAdres, 450); });
  if (p.adres) sprawdzAdres();
  /* dane z programu na komputerze: plik jest zaszyfrowany kodem i hasłem tego konta; wypełniamy formularz (nic nie zapisuje się samo — sprawdzasz i klikasz „Zapisz”), a lista sklepów czeka w oknie „Plan” */
  let silnikZPliku = null, sklepyZPliku = null;
  const infoPrzenos = (html, klasa = '') => { const i = $('#przenos-info', arkTresc); if (i) { i.innerHTML = html; i.className = klasa; } };
  const wczytajZProgramu = async plik => {
    infoPrzenos('Odczytuję plik…');
    let tekst = ''; try { tekst = await plik.text(); } catch (e) { return infoPrzenos('Nie udało się otworzyć pliku.', 'zle'); }
    const kodPliku = przen.kodZPliku(tekst);
    if (kodPliku === null) return infoPrzenos('To nie jest plik z danymi z programu PMT (PMT_dane_do_aplikacji.pmtdane).', 'zle');
    if (kodPliku !== dostep.kodAktywny()) return infoPrzenos(`Ten plik jest z konta ${bezZnacznikow(kodPliku)}, a jesteś zalogowany jako ${bezZnacznikow(dostep.kodAktywny())}. Wyloguj się i zaloguj kodem z pliku.`, 'zle');
    const w = await przen.odczytaj(tekst, dostep.skrotAktywny());
    if (!w.ok) return infoPrzenos(bezZnacznikow(w.komunikat), 'zle');
    const d = w.dane, czesci = [];
    if (d.profil) {
      $('#d-imie', arkTresc).value = d.profil.imie; $('#d-pesel', arkTresc).value = d.profil.pesel; $('#d-stan', arkTresc).value = d.profil.stanowisko; $('#d-adres', arkTresc).value = d.profil.adres;
      silnikZPliku = d.profil.silnik_powyzej_900; wybor = null; sprawdzAdres(); czesci.push('imię, PESEL, adres i stanowisko');
    }
    if (d.sklepy.length) { sklepyZPliku = d.sklepy; czesci.push(`listę <b>${d.sklepy.length}</b> sklepów`); }
    if (!czesci.length) return infoPrzenos('W pliku nie ma niczego do wczytania (program nie miał zapisanych danych tego konta).', 'zle');
    infoPrzenos(`Wczytano: ${czesci.join(' oraz ')}. Sprawdź dane i kliknij <b>Zapisz</b>.${d.sklepy.length ? ' Lista sklepów czeka w oknie „Plan”.' : ''} Po zapisaniu możesz usunąć plik z komputera.`, 'ok');
  };
  $('#plik-program', arkTresc).addEventListener('change', e => { const f = e.target.files[0]; e.target.value = ''; if (f) wczytajZProgramu(f); });
  const zle = (id, t) => { const s = $('#' + id, arkTresc).parentElement.querySelector('small'); s.textContent = t || ''; s.classList.toggle('zle', !!t); if (t) potrzasnij($('#' + id, arkTresc)); return !t; };
  $('#zapisz-dane', arkTresc).addEventListener('click', async () => {
    const imie = $('#d-imie', arkTresc).value.split(/\s+/).filter(Boolean).join(' '), pesel = $('#d-pesel', arkTresc).value.replace(/\s/g, ''), adres = $('#d-adres', arkTresc).value.trim();
    let ok = true;
    ok = zle('d-imie', imie.split(' ').length < 2 ? 'Wpisz imię i nazwisko' : '') && ok;
    ok = zle('d-pesel', peselPoprawny(pesel) ? '' : 'PESEL jest niepoprawny') && ok;
    let adr = null;
    if (adres) { try { adr = await silnik.adres({ adres, wymus_typ: wybor || undefined }); } catch (e) { adr = { ok: false }; } }
    ok = zle('d-adres', adr && adr.ok ? '' : 'Podaj numer domu, kod pocztowy i miejscowość, np. ul. Polna 5, 00-001 Warszawa albo, bez ulicy, Dębowa Wola 12, 26-660 Jedlińsk') && ok;
    if (ok && adr.niejednoznaczne && !wybor) {      // nie wiadomo, czy to ulica, czy wieś — bez rozstrzygnięcia nie zapisujemy
      blokTypu.hidden = false; opisTypu.textContent = `„${adr.nazwa_do_pytania}” — to nazwa ulicy czy miejscowości? Wybierz, żebym wiedział, skąd liczyć trasy.`; opisTypu.classList.add('zle'); potrzasnij(blokTypu); ok = false;
    }
    if (!ok) return;
    PROFIL = { imie, pesel, adres: adr.adres_caly, typ_adresu: wybor || (adr.to_wies ? 'wies' : 'ulica'), stanowisko: $('#d-stan', arkTresc).value, silnik_powyzej_900: silnikZPliku ?? p.silnik_powyzej_900 ?? true, tryb: trybDom(p), tryb_wybrany: !!p.tryb_wybrany };   // silnik i tryb pracy zmieniają się co miesiąc: ustawia je kafel miesiąca, tu zostaje ostatni wybór
    magProfil.zapisz(PROFIL);
    if (sklepyZPliku && sklepyZPliku.length) magUst.ustaw('sklepy-z-programu', { pozycje: sklepyZPliku, zapisano: new Date().toISOString() });      // czeka w oknie „Plan wizyt”, aż ułożysz plan
    if (M && M.stan === 'plan') { M.silnik = PROFIL.silnik_powyzej_900; M.tryb = trybDom(PROFIL); }
    zamknijArkusz(); odswiezProfilWNaglowku(); if (M && M.demo) await wyjdzZPrzykladu(true); else await przeladujMiesiac(M.rok, M.mies, true);
    pokazToast(sklepyZPliku && sklepyZPliku.length ? `Zapisano Twoje dane. Lista ${sklepyZPliku.length} sklepów z programu czeka — kliknij „Plan” w kaflu Dziś i ułóż plan.` : 'Zapisano Twoje dane'); sygnal('profil');
  });
}
function odswiezProfilWNaglowku() {
  const ini = PROFIL ? PROFIL.imie.split(' ').map(x => x[0]).slice(0, 2).join('').toUpperCase() : '?';
  $('#awatar').textContent = ini; $('#awatar-menu').textContent = ini;
  $('#imie-pasek').textContent = PROFIL ? PROFIL.imie : 'Moje dane'; $('#konto-imie').textContent = PROFIL ? PROFIL.imie : 'Moje dane';
  $('#konto-opis').textContent = PROFIL ? PROFIL.stanowisko : 'uzupełnij dane';
  $('#konto').setAttribute('aria-label', PROFIL ? `Konto: ${PROFIL.imie}` : 'Konto');
  const o = dostep.ocenaSesji();
  $('#konto-dostep').textContent = `Login ${dostep.kodAktywny()}` + (o.wazneDo ? ` · dostęp do ${o.wazneDo.split('-').reverse().join('.')}` : '');
}

/* ====================== Rok: przegląd miesięcy ====================== */
function stanRekordu(rec) {
  if (!rec || !rec.wynik) return 'brak';
  if (rec.wyslane) return 'wyslane';
  const n = ((rec.wynik.dokumenty || []).length) + (rec.wynik.rozliczenie ? 1 : 0), pod = (rec.podpisane || []).filter(Boolean).length;
  return n && pod >= n ? 'podpisane' : 'gotowe';
}
const NAZWY_STANU = { brak: 'do wygenerowania', gotowe: 'do podpisu', podpisane: 'do wysłania', wyslane: 'wysłane' };
function arkuszRok(rok) {
  const rekordy = Array.from({ length: 12 }, (_, i) => magMiesiace.daj(rok, i + 1));
  let suma = 0, dok = 0, wyslane = 0;
  const komorki = rekordy.map((rec, i) => {
    const st = stanRekordu(rec), kw = rec && rec.wynik ? rec.wynik.suma : 0, n = rec && rec.wynik ? (rec.wynik.dokumenty || []).length + (rec.wynik.rozliczenie ? 1 : 0) : 0;
    suma += kw; dok += n; if (st === 'wyslane') wyslane++;
    const biezacy = M && M.rok === rok && M.mies === i + 1;
    return `<button type="button" class="rok-m" data-mies="${i + 1}" data-st="${st}"${biezacy ? ' aria-current="true" data-pierwsze' : ''} aria-label="${cap(MIES[i])} ${rok}: ${NAZWY_STANU[st]}${kw ? ', ' + fmt(kw) + ' zł' : ''}"><b>${cap(MIES[i])}</b><span class="rok-st"><i aria-hidden="true"></i>${NAZWY_STANU[st]}</span><span class="rok-kw">${kw ? fmt(kw) + ' zł' : ''}</span></button>`;
  }).join('');
  otworzArkusz(`<div class="ark-gora rok-nav"><button type="button" class="okr ikb" id="rok-wstecz" aria-label="Poprzedni rok">${ik('i-lewo')}</button><h2 id="ark-tyt">${rok}</h2><button type="button" class="okr ikb" id="rok-dalej" aria-label="Następny rok">${ik('i-prawo')}</button><button type="button" class="ark-zam" data-zamknij aria-label="Zamknij">${ik('i-zamknij')}</button></div>
    <div class="rok-siatka" id="rok-siatka">${komorki}</div>
    <p class="rok-razem">${suma ? `W ${rok}: <b>${fmt(suma)} zł</b> · ${dok} ${dok === 1 ? 'dokument' : dok < 5 ? 'dokumenty' : 'dokumentów'} · wysłane miesiące: <b>${wyslane}</b>` : `W ${rok} nie ma jeszcze wygenerowanych dokumentów.`}</p>`);
  const tresc = arkTresc;
  $('#rok-wstecz', tresc).addEventListener('click', () => arkuszRok(rok - 1));
  $('#rok-dalej', tresc).addEventListener('click', () => arkuszRok(rok + 1));
  $('#rok-siatka', tresc).addEventListener('click', e => { const b = e.target.closest('[data-mies]'); if (!b) return; const m = Number(b.dataset.mies); zamknijArkusz(); przeladujMiesiac(rok, m); });
}

/* ====================== parametry przed generowaniem ====================== */
const parsujKwote = t => { const n = Number(String(t).replace(/\s/g, '').replace(',', '.')); return Number.isFinite(n) ? Math.round(n * 100) / 100 : 0; };
const parametrySilnika = () => ({ imie: PROFIL ? PROFIL.imie : '', pesel: PROFIL ? PROFIL.pesel : '', adres: PROFIL ? PROFIL.adres : '', stanowisko: PROFIL ? PROFIL.stanowisko : 'merchandiser',
  kwota: M.kwota, rok: M.rok, miesiac: M.mies, tryb: M.tryb, silnik_powyzej_900: M.silnik, wolne: [...M.wolne].sort((a, b) => a - b),
  wymus_typ: PROFIL && PROFIL.typ_adresu ? PROFIL.typ_adresu : undefined });
let infoNr = 0, odswiezParametryTimer = 0;
/** Ustawia kwotę z zewnątrz (suwak, paleta): pole, model i — po chwili — sprawdzenie maksimum w silniku. trwale = zapamiętaj też na urządzeniu. */
function ustawKwote(v, trwale) {
  if (!M || M.stan !== 'plan') return;
  M.kwota = Math.round(Math.max(0, v) * 100) / 100;
  const wej = $('#kwota-in'); wej.value = M.kwota ? fmt(M.kwota) : '';
  clearTimeout(odswiezParametryTimer); odswiezParametryTimer = setTimeout(odswiezParametry, 140);
  if (trwale) magUst.ustaw('kwota-' + magMiesiace.klucz(M.rok, M.mies), M.kwota);
  sygnal('kwota');
}
async function odswiezParametry() {
  if (!M) return;
  $$('#parametry [data-tryb]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.tryb === M.tryb)));
  $$('#parametry [data-silnik]').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.silnik === '1') === M.silnik)));
  const wej = $('#kwota-in'); if (M.stan === 'plan' && doc.activeElement !== wej) wej.value = M.kwota ? fmt(M.kwota).replace(/\s/g, '') : '';
  const info = $('#par-info'), nr = ++infoNr;
  if (M.stan !== 'plan') { info.innerHTML = ''; btn.classList.remove('zablok'); sygnal('parametry'); return; }
  let w; try { w = await silnik.maks(parametrySilnika()); } catch (e) { return; }
  if (nr !== infoNr) return;
  M.maksymalna = w.maks; M.stawkaPodglad = w.stawka;
  const kw = M.kwota; let blad = '';
  if (!kw) blad = 'Wpisz kwotę do rozliczenia.';
  else if (kw < MIN_KWOTA) blad = `Minimum to ${fmt(MIN_KWOTA, 0)} zł.`;
  else if (kw > w.maks) blad = `Za dużo: dla tylu dni maksimum to ${fmt(w.maks, 0)} zł. Odznacz dni wolne albo zmniejsz kwotę.`;
  if (!PROFIL) blad = 'Najpierw uzupełnij Moje dane.';
  info.innerHTML = blad ? `<span class="zle">${blad}</span>` : '';   // tylko to, co trzeba poprawić — bez podsumowania dni, stawki i maksimum
  btn.classList.toggle('zablok', !!blad);
  sygnal('parametry');
}

/* ====================== generowanie: prawdziwy silnik ====================== */
let generowanie = false;
/** Pytanie z programu na komputerze: „X” — to nazwa ulicy czy miejscowości? Zwraca 'ulica', 'wies' albo null (zamknięto bez wyboru). */
function zapytajOTypAdresu(nazwa) {
  return new Promise(res => {
    let wybrano = null;
    otworzArkusz(`${naglowekArkusza('Doprecyzuj adres')}
      <p class="ark-opis">„<b>${bezZnacznikow(nazwa)}</b>” — to nazwa ulicy czy miejscowości? Od tego zależy, skąd liczę trasy: z miejscowości zamieszkania czy z poczty.</p>
      <div class="ark-dol"><button type="button" class="przycisk" data-typ-adresu="ulica">To ulica</button><button type="button" class="przycisk glowny" data-typ-adresu="wies" data-pierwsze>To miejscowość</button></div>`, () => res(wybrano));
    $$('[data-typ-adresu]', arkTresc).forEach(b => b.addEventListener('click', () => { wybrano = b.dataset.typAdresu; zamknijArkusz(); }));
  });
}
/** Ostatnie sprawdzenie przed generowaniem: kwota i dane, które trafią na dokumenty. true = potwierdzono. */
function arkuszPotwierdzenia(pr) {
  return new Promise(res => {
    let potwierdzono = false;
    const wolne = [...M.wolne].sort((a, b) => a - b);
    const zakres = (() => { const w = []; let i = 0; while (i < wolne.length) { let j = i; while (j + 1 < wolne.length && wolne[j + 1] === wolne[j] + 1) j++; w.push(j - i >= 2 ? `${wolne[i]}–${wolne[j]}` : wolne.slice(i, j + 1).join(', ')); i = j + 1; } return w.join(', '); })();
    otworzArkusz(`${naglowekArkusza('Sprawdź, zanim wygeneruję')}
      <p class="ark-opis">Te dane trafią na dokumenty delegacji. Jeśli coś się nie zgadza, wróć i popraw.</p>
      <div class="potw"><p class="potw-kwota num" id="potw-kwota">${fmt(M.kwota)}<small>zł</small></p><p class="potw-pod">kwota do rozliczenia · ${cap(MIES[M.mies - 1])} ${M.rok}</p></div>
      <dl class="potw-lista">
        <div><dt>Dni pracy</dt><dd>${pr.liczba_dni}${wolne.length ? ` · wolne: ${zakres}.${dwa(M.mies)}` : ''}</dd></div>
        <div><dt>Tryb pracy</dt><dd>${M.tryb === 'wieczory' ? 'Wieczory 16:30–22:00 · sb' : 'Tydzień, dni robocze'}</dd></div>
        <div><dt>Auto</dt><dd>${tekstSilnika()}</dd></div>
        <div><dt>Start i meta trasy</dt><dd><span id="potw-adres">${bezZnacznikow(pr.adres_caly || pr.baza_miasto)}</span><small class="potw-mala">trasy liczone z miejscowości: <b id="potw-baza">${bezZnacznikow(pr.baza_miasto)}</b></small></dd></div>
        <div><dt>Na dokumentach</dt><dd id="potw-osoba">${bezZnacznikow(PROFIL.imie)}</dd></div>
        <div><dt>PESEL</dt><dd id="potw-pesel" class="num">${bezZnacznikow(String(PROFIL.pesel || '').replace(/\s/g, ''))}</dd></div>
      </dl>
      <div class="ark-dol"><button type="button" class="przycisk" data-zamknij>Popraw</button><button type="button" class="przycisk glowny" id="potwierdz-gen" data-pierwsze>Potwierdzam i generuję</button></div>`, () => res(potwierdzono));
    $('#potwierdz-gen', arkTresc).addEventListener('click', () => { potwierdzono = true; zamknijArkusz(); });
  });
}
function postepGeneracji(tekst, v) {
  const p = Math.max(0, Math.min(1, v || 0));
  btn.style.setProperty('--pk', String(p * 100)); $('#licz-k').textContent = String(Math.round(p * 100));
  zorza && zorza.flara(.12);
}
/** Brak menedzer.txt: konkretna diagnoza (adres, odpowiedź serwera, typowa pomyłka z nazwą) i „Sprawdź ponownie” bez odświeżania strony. */
function arkuszBrakuMenedzera(d) {
  const podwojone = d.sugestia === 'podwojone-txt';
  otworzArkusz(`${naglowekArkusza('Brakuje pliku menedzer.txt')}
    <p class="ark-opis">${podwojone ? 'Znalazłem plik <b>menedzer.txt.txt</b> — Windows ukrył rozszerzenie i dopisał drugie „.txt”. Zmień nazwę na dokładnie <b>menedzer.txt</b>.'
      : 'Nazwisko przełożonego na dokumentach czytam z pliku <b>menedzer.txt</b> leżącego obok <b>index.html</b>.'}</p>
    <ol class="krok-lista">
      <li><span>Plik ma nazywać się dokładnie <b>menedzer.txt</b> (w Eksploratorze: Widok → Pokaż → „Rozszerzenia nazw plików”, żeby było widać, czy nie ma drugiego „.txt”).</span></li>
      <li><span>W środku jedna linia: imię i nazwisko przełożonego. Zapis w Notatniku w UTF-8 lub ANSI jest w porządku.</span></li>
      <li><span>Plik musi leżeć w tym samym folderze co <b>index.html</b> (ten uruchomiony przez URUCHOM_LOKALNIE.bat). Odświeżać strony nie trzeba — kliknij „Sprawdź ponownie”.</span></li>
    </ol>
    <p class="ark-opis" style="font-size:.8rem;opacity:.8">Szukałem tutaj: ${bezZnacznikow(d.url || 'menedzer.txt')} — odpowiedź: ${d.status ? 'HTTP ' + d.status : bezZnacznikow(d.blad || 'brak odpowiedzi')}.</p>
    <div class="ark-dol"><button type="button" class="przycisk" data-zamknij>Zamknij</button><button type="button" class="przycisk glowny" id="menedzer-ponow" data-pierwsze>Sprawdź ponownie</button></div>`);
  const b = $('#menedzer-ponow', arkTresc); b && b.addEventListener('click', () => { zamknijArkusz(); setTimeout(generuj, 250); });
}
async function generuj() {
  if (generowanie) { silnik.przerwij(); return; }
  if (M && M.demo) { zacznijOdSwoich(); return; }      // dane pokazowe nigdy nie wchodzą w liczenie delegacji
  if (!PROFIL) { otworzMojeDane(true); return; }
  M.kwota = parsujKwote($('#kwota-in').value);
  const par = parametrySilnika();
  let pr; try { pr = await silnik.przygotuj(par); } catch (e) { pokazToast('Silnik nie odpowiada — spróbuj ponownie'); return; }
  if (!pr.ok && pr.powod === 'brak menedzer.txt') { arkuszBrakuMenedzera(pr.szczegoly || {}); return; }
  if (!pr.ok) {
    const opisy = { 'brak menedzer.txt': 'Brakuje pliku menedzer.txt obok aplikacji (nazwisko przełożonego na dokumentach).', 'PESEL': 'PESEL jest niepoprawny — popraw go w Moich danych.', 'adres': 'Adres jest niepoprawny — popraw go w Moich danych.', 'brak dni': 'Ten miesiąc nie ma dni roboczych przy tych ustawieniach.' };
    pokazToast(opisy[pr.powod] || ('Nie można generować: ' + pr.powod)); await odswiezParametry(); return;
  }
  if (pr.niejednoznaczne && !PROFIL.typ_adresu) {          // profil zapisany zanim zapytaliśmy o rodzaj adresu
    const typ = await zapytajOTypAdresu(pr.nazwa_do_pytania); if (!typ) return;
    PROFIL.typ_adresu = typ; magProfil.zapisz(PROFIL); par.wymus_typ = typ;
    try { pr = await silnik.przygotuj(par); } catch (e) { pokazToast('Silnik nie odpowiada — spróbuj ponownie'); return; }
    if (!pr.ok) { pokazToast('Nie można generować: ' + pr.powod); return; }
  }
  if (!(await arkuszPotwierdzenia(pr))) return;            // użytkownik sprawdza dane, zanim cokolwiek powstanie
  magUst.ustaw('kwota-' + magMiesiace.klucz(M.rok, M.mies), M.kwota);
  generowanie = true; btn.classList.add('zbiera'); btn.setAttribute('aria-busy', 'true'); btn.setAttribute('aria-label', 'Przerwij generowanie');
  btn.style.setProperty('--hh', (btn.offsetHeight / 2) + 'px'); postepGeneracji('', 0.02); zorza && zorza.flara(.35);
  let w;
  try {
    w = await silnik.generuj(par, (t, v) => postepGeneracji(t, v));
  } catch (e) {
    generowanie = false; btn.classList.remove('zbiera'); btn.removeAttribute('aria-busy');
    if (e.przerwano) { pokazToast('Przerwano — nic nie zostało zapisane'); } else {
      otworzArkusz(`${naglowekArkusza('Nie udało się wygenerować')}<p class="ark-opis">${bezZnacznikow(e.message)}</p><div class="ark-dol"><button type="button" class="przycisk glowny" data-zamknij data-pierwsze>Rozumiem</button></div>`);
    }
    odswiezHero(); await odswiezParametry(); return;
  }
  const rec = { params: par, wynik: w.wynik, podpisane: [], wyslane: false, utworzono: new Date().toISOString() };
  magMiesiace.zapisz(M.rok, M.mies, rec);
  dostep.policzDokumenty(w.pdf.length);
  await magPliki.usunMiesiac(magMiesiace.klucz(M.rok, M.mies) + '/');
  for (const p of w.pdf) await magPliki.zapisz(nazwaKlucza(M.rok, M.mies, p.nazwa), p.bajty);
  postepGeneracji('', 1); await zegar(450);
  generowanie = false; btn.classList.remove('zbiera'); btn.removeAttribute('aria-busy');
  M = zbudujModel(M.rok, M.mies, rec, [...M.robocze0]); wybrany = M.dniT[0] || 0;
  przejscie(() => odswiezWszystko(), () => { kurtyna && kurtyna.restart(); kurtyna && kurtyna.wybierz(wybrany); });
  zorza && zorza.flara(1); kurtyna && kurtyna.swieto();
  pokazToast(`Gotowe: ${M.polecenia.length} ${M.polecenia.length === 1 ? 'polecenie' : M.polecenia.length < 5 ? 'polecenia' : 'poleceń'} i rozliczenie na ${fmt(M.suma)} zł${w.wynik.niepelna ? ' (silnik nie dobił do zamówionej kwoty)' : ''}`);
  if (w.wynik.zrodlo && w.wynik.zrodlo.etykieta && /szacunek/i.test(w.wynik.zrodlo.etykieta)) setTimeout(() => pokazToast('Kilometry z szacunku — bez internetu nie sprawdzę dróg. Dokument to zaznacza.'), 3300);
}
/** Dni robocze miesiąca z silnika. Przy chwilowym błędzie (np. silnik jeszcze się rozgrzewa) próbuje jeszcze dwa razy, zamiast po cichu pokazać miesiąc bez dni roboczych. */
async function dniRoboczeZSilnika(rok, mies, trybWym) {
  const tryb = trybWym || ((magMiesiace.daj(rok, mies) || {}).params ? magMiesiace.daj(rok, mies).params.tryb : trybDom(PROFIL));
  for (let i = 0; i < 3; i++) {
    try { return await silnik.dni({ rok, miesiac: mies, tryb, wolne: [] }); }
    catch (e) { console.error('DNI-BLAD ' + (e && e.message)); if (i < 2) await new Promise(r => setTimeout(r, 700 * (i + 1))); }
  }
  pokazToast('Nie udało się wczytać dni miesiąca — odśwież stronę');
  return { dni: [] };
}
/* ====================== przykład na pierwsze uruchomienie ====================== */
/** Zamiast pustego programu użytkownik, który nie ma jeszcze żadnych danych, widzi przykładowy, w pełni wygenerowany miesiąc (przyklad/*.json: wynik prawdziwego silnika dla wymyślonej osoby).
    Dane przykładowe nie są nigdzie zapisywane i znikają przy pierwszym własnym kroku (Moje dane, zmiana miesiąca). Dokumenty PDF w przykładzie nie istnieją — przyciski prowadzą do własnych danych. */
let PRZYKLAD = null, WIZYTY_DEMO = {};
async function wczytajPrzyklad() {
  if (PRZYKLAD !== null) return PRZYKLAD;
  try { const [miesiac, plan] = await Promise.all(['przyklad/miesiac.json', 'przyklad/plan.json'].map(u => fetch(u).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }))); PRZYKLAD = { miesiac, plan }; }
  catch (e) { console.error('PRZYKLAD-BLAD ' + (e && e.message)); PRZYKLAD = false; }
  return PRZYKLAD;
}
const wizytaDaj = (data, adres) => M && M.demo ? (WIZYTY_DEMO[`${data}|${adres}`] || null) : magWizyty.daj(data, adres);
function wizytaUstaw(data, adres, ok, godz) {
  if (M && M.demo) { if (ok) WIZYTY_DEMO[`${data}|${adres}`] = { ok: true, godz: godz || '' }; else delete WIZYTY_DEMO[`${data}|${adres}`]; }
  else magWizyty.ustaw(data, adres, ok, godz);
}
function opuscPrzyklad() { if (!M || !M.demo) return; root.classList.remove('przyklad'); PLAN = magPlan.wczytaj(); WIZYTY_DEMO = {}; const b = $('#pokaz-przyklad'); if (b) b.hidden = false; }
async function pokazPrzyklad() {
  const pr = await wczytajPrzyklad(); if (!pr) return false;
  const { rok, mies, params, wynik } = pr.miesiac;
  const r0 = await dniRoboczeZSilnika(rok, mies, params.tryb);
  M = zbudujModel(rok, mies, { params, wynik, podpisane: [], wyslane: false }, r0.dni.map(s => Number(s.slice(8))));
  M.demo = true; PLAN = pr.plan; WIZYTY_DEMO = {}; root.classList.add('przyklad'); const b = $('#pokaz-przyklad'); if (b) b.hidden = true;
  wybrany = M.dniT[0] || 0; odswiezWszystko(); return true;
}
function miesiacDomyslny() { const d = new Date(); let r = d.getFullYear(), m = d.getMonth(); if (m === 0) { r--; m = 12; } const ost = magUst.daj('ostatni-miesiac', null); return ost ? { r: ost.rok, m: ost.mies } : { r, m }; }
/** Opuszcza przykład i pokazuje własny miesiąc do ustawienia; fokusKwoty = od razu kursor w polu kwoty (do wpisania). */
async function wyjdzZPrzykladu(fokusKwoty) { const { r, m } = miesiacDomyslny(); await przeladujMiesiac(r, m, false, fokusKwoty); }
const zacznijOdSwoich = () => wyjdzZPrzykladu(true);      // dane osobowe program poprosi o przy generowaniu — najpierw można wpisać kwotę
const demoToast = () => pokazToast('To przykład — kliknij kwotę i wpisz własną, a przygotuję Twoje dokumenty');
/** Kursor w polu kwoty (z zaznaczoną zawartością, żeby pierwsza cyfra zastępowała starą wartość). */
function fokusujKwote() {
  const w = $('#kwota-in'); if (!w || !M || M.stan !== 'plan' || !w.getClientRects().length) return;
  w.value = M.kwota ? fmt(M.kwota).replace(/\s/g, '') : '';      // pole w fokusie nie jest odświeżane w tle, więc wartość ustawiamy tu
  w.focus({ preventScroll: true }); try { w.select(); } catch (e) {}
}
async function przeladujMiesiac(rok, mies, cicho, fokusKwoty) {
  opuscPrzyklad();
  const r0 = await dniRoboczeZSilnika(rok, mies);
  const rec = magMiesiace.daj(rok, mies);
  const robocze = r0.dni.map(s => Number(s.slice(8)));
  const pred = M && M.rok === rok && M.mies === mies ? M : null;
  M = zbudujModel(rok, mies, rec, robocze);
  if (!rec) { M.kwota = magUst.daj('kwota-' + magMiesiace.klucz(rok, mies), 0); if (pred && pred.stan === 'plan') { M.tryb = pred.tryb; M.silnik = pred.silnik; M.wolne = pred.wolne; for (const d of M.robocze0) if (!M.wolne.has(d)) M.robocze.add(d); } }
  wybrany = M.stan === 'gotowe' ? (M.trasy[wybrany] ? wybrany : M.dniT[0]) : 0;
  const odswiez = () => { odswiezWszystko(); if (fokusKwoty && M.stan === 'plan') fokusujKwote(); };
  if (cicho) odswiez(); else przejscie(odswiez, () => { kurtyna && kurtyna.wybierz(wybrany); });
}
async function przelaczTryb(tryb) {
  if (M.stan !== 'plan' || M.tryb === tryb) return; M.tryb = tryb;
  if (PROFIL) { PROFIL.tryb = tryb; PROFIL.tryb_wybrany = true; magProfil.zapisz(PROFIL); }
  M.wolne = new Set(); await przeladujMiesiac(M.rok, M.mies, true);
}
async function przelaczWolne(d) {
  if (M.stan !== 'plan') return;
  if (M.wolne.has(d)) M.wolne.delete(d); else M.wolne.add(d);
  M.robocze = new Set([...M.robocze0].filter(x => !M.wolne.has(x)));
  tytulKalendarza(); budujKalendarz(); odswiezHero(); await odswiezParametry();
}
/** Wiele dni naraz (przeciąganie po kalendarzu): wolne = true oznacza dni jako wolne, false przywraca je do pracy. */
async function ustawWolne(dni, wolne) {
  if (!M || M.stan !== 'plan') return;
  for (const d of dni) { if (!M.robocze0.has(d)) continue; if (wolne) M.wolne.add(d); else M.wolne.delete(d); }
  M.robocze = new Set([...M.robocze0].filter(x => !M.wolne.has(x)));
  tytulKalendarza(); budujKalendarz(); odswiezHero(); await odswiezParametry();
}

/* ====================== plan wizyt: import listy sklepów i układanie tras ====================== */
let POZYCJE_PLANU = null;
async function arkuszPlan() {
  if (M && M.demo) await wyjdzZPrzykladu();      // plan dotyczy własnych danych; dalej poprosimy o dane (jeśli ich jeszcze nie ma)
  if (!PROFIL) { otworzMojeDane(true); return; }
  const p = PLAN, cykl = magUst.daj('plan-cykliczny', false), hor = magUst.daj('plan-horyzont', 3), cyk = magUst.daj('plan-cykl', 4);
  const dniPlanu = p ? p.miesiace.reduce((a, m) => a + m.dni.length, 0) : 0;
  otworzArkusz(`${naglowekArkusza('Plan wizyt')}
    <div class="plan-info" id="plan-stan">${p ? `Plan ułożony: <b>${p.suma_wizyt}</b> ${wizyt(p.suma_wizyt)} w <b>${dniPlanu}</b> ${dniPlanu === 1 ? 'dniu' : 'dniach'}, ok. <b>${fmt(p.suma_km, 0)} km</b>, ${sklepowWPlanie()} ${sklepowWPlanie() === 1 ? 'sklep' : 'sklepów'}.${(p.bez_pozycji || []).length ? `<br><span class="zle">Bez lokalizacji (pominięte): ${p.bez_pozycji.slice(0, 4).map(bezZnacznikow).join(', ')}${p.bez_pozycji.length > 4 ? '…' : ''}</span>` : ''}` : 'Nie ma jeszcze planu wizyt.'}</div>
    <p class="ark-opis">Wczytaj listę sklepów z Excela (<b>.xlsx</b>) albo <b>.csv</b>. Kolumny rozpoznam po nagłówkach: miasto, ulica, numer, kod pocztowy, sieć. Trasy ruszają z Twojego adresu: <b>${bezZnacznikow(PROFIL.adres)}</b>.</p>
    <label class="przycisk" style="cursor:pointer;align-self:flex-start">Wybierz plik z listą sklepów<input type="file" id="plan-plik" accept=".xlsx,.csv,text/csv" hidden></label>
    <div class="plan-info" id="plan-plik-info" hidden></div>
    <div class="par-w"><span>Układanie</span><div class="seg" role="group" aria-label="Rodzaj planu"><button type="button" data-cykl="0" aria-pressed="${!cykl}">Każdy sklep raz</button><button type="button" data-cykl="1" aria-pressed="${!!cykl}">Powtarzaj cyklicznie</button></div></div>
    <div class="ark-pola" id="plan-cykl-pola"${cykl ? '' : ' hidden'}>
      <label class="pole"><span>Na ile miesięcy</span><select id="plan-hor">${[1, 2, 3, 6].map(x => `<option value="${x}"${x === hor ? ' selected' : ''}>${x} ${x === 1 ? 'miesiąc' : x < 5 ? 'miesiące' : 'miesięcy'}</option>`).join('')}</select></label>
      <label class="pole"><span>Odwiedzaj co</span><select id="plan-cyk">${[1, 2, 3, 4, 6, 8].map(x => `<option value="${x}"${x === cyk ? ' selected' : ''}>${x} ${x === 1 ? 'tydzień' : x < 5 ? 'tygodnie' : 'tygodni'}</option>`).join('')}</select></label>
    </div>
    <div class="pasek-ark" id="plan-pasek"><i></i></div><p class="ark-opis" id="plan-postep" hidden></p>
    <div class="ark-dol">${p ? '<button type="button" class="przycisk" id="plan-usun">Usuń plan</button>' : ''}<button type="button" class="przycisk" data-zamknij>Zamknij</button><button type="button" class="przycisk glowny" id="plan-uloz" disabled>Ułóż plan</button></div>`);
  POZYCJE_PLANU = p && p.pozycje ? p.pozycje : null;
  const ulozBtn = $('#plan-uloz', arkTresc), info = $('#plan-plik-info', arkTresc);
  const zProgramu = !POZYCJE_PLANU ? magUst.daj('sklepy-z-programu', null) : null;
  if (zProgramu && Array.isArray(zProgramu.pozycje) && zProgramu.pozycje.length) { POZYCJE_PLANU = zProgramu.pozycje; ulozBtn.disabled = false; ulozBtn.textContent = 'Ułóż plan'; info.hidden = false; info.innerHTML = `Lista sklepów przeniesiona z programu: <b>${POZYCJE_PLANU.length}</b> adresów. Wybierz układanie i kliknij „Ułóż plan” — albo wskaż inny plik.`; }
  else if (POZYCJE_PLANU) { ulozBtn.disabled = false; ulozBtn.textContent = 'Ułóż plan ponownie'; info.hidden = false; info.innerHTML = `Lista sklepów z poprzedniego planu: <b>${POZYCJE_PLANU.length}</b> adresów. Możesz ją zmienić, wybierając nowy plik.`; }
  arkTresc.addEventListener('click', function nasluch(e) {
    if (!arkuszOtwarty) { arkTresc.removeEventListener('click', nasluch); return; }
    const b = e.target.closest('[data-cykl]'); if (!b) return;
    $$('[data-cykl]', arkTresc).forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    $('#plan-cykl-pola', arkTresc).hidden = b.dataset.cykl !== '1';
  });
  $('#plan-plik', arkTresc).addEventListener('change', async e => {
    const f = e.target.files[0]; if (!f) return;
    info.hidden = false; info.textContent = 'Wczytuję plik…';
    let w; try { w = await silnik.planWczytaj({ nazwa: f.name, bajty: new Uint8Array(await f.arrayBuffer()) }); } catch (err) { w = { ok: false, blad: err.message }; }
    if (!w.ok) { info.innerHTML = `<span class="zle">${bezZnacznikow(w.blad)}</span>`; ulozBtn.disabled = !POZYCJE_PLANU; return; }
    POZYCJE_PLANU = w.pozycje; ulozBtn.disabled = false; ulozBtn.textContent = 'Ułóż plan';
    const nazwyRol = { miasto: 'miasto', ulica: 'ulica', numer: 'numer', kod: 'kod', siec: 'sieć' };
    info.innerHTML = `Wczytano <b>${w.pozycje.length}</b> adresów z pliku <b>${bezZnacznikow(f.name)}</b>. Rozpoznane kolumny: ${w.kolumny.map(k => nazwyRol[k] || k).join(', ')}.`;
  });
  const usun = $('#plan-usun', arkTresc);
  usun && usun.addEventListener('click', () => { magPlan.usun(); PLAN = null; zamknijArkusz(); rysujDzis(); pokazToast('Usunięto plan wizyt'); });
  ulozBtn.addEventListener('click', async () => {
    if (!POZYCJE_PLANU) return;
    const cyklicznie = $('[data-cykl][aria-pressed="true"]', arkTresc).dataset.cykl === '1', horyzont = Number($('#plan-hor', arkTresc).value), cykl2 = Number($('#plan-cyk', arkTresc).value);
    magUst.ustaw('plan-cykliczny', cyklicznie); magUst.ustaw('plan-horyzont', horyzont); magUst.ustaw('plan-cykl', cykl2);
    ulozBtn.disabled = true; const pasek = $('#plan-pasek', arkTresc), tekst = $('#plan-postep', arkTresc); pasek.classList.add('widoczny'); tekst.hidden = false;
    const dzis = new Date();
    try {
      const w = await silnik.planGeneruj({ pozycje: POZYCJE_PLANU, adres_bazy: PROFIL.adres, cykliczny: cyklicznie, cykl_domyslny: cykl2, horyzont, rok: dzis.getFullYear(), miesiac: dzis.getMonth() + 1,
        tryb: trybDom(PROFIL), siec: navigator.onLine, od_daty: isoDzis() }, (t, v) => { tekst.textContent = t; pasek.style.setProperty('--p', Math.round(Math.max(3, v * 100)) + '%'); zorza && zorza.flara(.08); });
      w.pozycje = POZYCJE_PLANU; w.zapisano = new Date().toISOString();
      if (!w.suma_wizyt) { tekst.innerHTML = '<span style="color:var(--a-burs)">Nie udało się ułożyć ani jednej wizyty. Sprawdź, czy lista zawiera miejscowości.</span>'; ulozBtn.disabled = false; pasek.classList.remove('widoczny'); return; }
      magPlan.zapisz(w); PLAN = w; magUst.ustaw('sklepy-z-programu', null); dostep.policzPlan(); zamknijArkusz(); przejscie(() => rysujDzis(), null, 'dzis'); zorza && zorza.flara(.8);
      pokazToast(`Plan gotowy: ${w.suma_wizyt} ${wizyt(w.suma_wizyt)} w ${w.miesiace.reduce((a, m) => a + m.dni.length, 0)} dniach`);
    } catch (err) { tekst.innerHTML = `<span style="color:var(--a-blad)">${bezZnacznikow(err.message)}</span>`; ulozBtn.disabled = false; pasek.classList.remove('widoczny'); }
  });
}

/* ====================== dokumenty, podpis, wysyłka ====================== */
const nazwyDok = () => { const n = M.polecenia.length; return [...M.polecenia.map((p, i) => ({ i, nazwa: p.plik, tytul: `Polecenie ${p.nr}`, opis: `${dwa(p.od)}–${dwa(p.do)}.${dwa(M.mies)} · ${fmt(p.kw)} zł` })), ...(M.rozliczenie ? [{ i: n, nazwa: M.rozliczenie, tytul: 'Rozliczenie', opis: `${n} ${n === 1 ? 'polecenie' : 'polecenia'} · ${fmt(M.suma)} zł` }] : [])]; };
const klucz = n => nazwaKlucza(M.rok, M.mies, n);
const kluczPodp = (n, nazwaPliku) => nazwaKlucza(M.rok, M.mies, 'podpisane/' + n + '/' + nazwaPliku);
const URL_PODPIS = 'https://www.gov.pl/web/gov/podpisz-dokument-elektronicznie-wykorzystaj-podpis-zaufany';
function zapiszRekord() { const rec = magMiesiace.daj(M.rok, M.mies) || {}; rec.podpisane = M.podpisane; rec.wyslane = M.wyslane; rec.podpisaniPliki = M.podpisaniPliki || rec.podpisaniPliki || {}; rec.metodaPodpisu = M.metodaPodpisu || rec.metodaPodpisu || {}; rec.pierwotneNazwy = M.pierwotneNazwy || rec.pierwotneNazwy || {}; rec.weryfikacje = M.weryfikacje || rec.weryfikacje || {}; magMiesiace.zapisz(M.rok, M.mies, rec); }
const blobPdf = (bajty) => new Blob([bajty], { type: 'application/pdf' });
const bezOgonkow = t => String(t).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l').replace(/Ł/g, 'L');   /* nazwy plików bezpieczne w każdej przeglądarce i poczcie */
function pobierzBlob(blob, nazwa) { const a = doc.createElement('a'); a.href = URL.createObjectURL(blob); a.download = bezOgonkow(nazwa); doc.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000); }
async function otworzPdf(nazwa) { const b = await magPliki.daj(klucz(nazwa)); if (!b) { pokazToast('Nie znalazłem pliku — wygeneruj dokumenty ponownie'); return; } const u = URL.createObjectURL(blobPdf(b)); const w = window.open(u, '_blank'); if (!w) pobierzBlob(blobPdf(b), nazwa); setTimeout(() => URL.revokeObjectURL(u), 60000); }
/* okno „Dokumenty do podpisu”, podpis elektroniczny / odręczny i wysyłka: js/podpis.js */
const podpis = zainstalujPodpis({ $, $$, ik, arkTresc, bezZnacznikow, bezOgonkow, pokazToast, magPliki, magMiesiace, magUst, MIES, URL_PODPIS, blobPdf, pobierzBlob, otworzPdf,
  M: () => M, PROFIL: () => PROFIL, nazwyDok, klucz, kluczPodp, zapiszRekord, odswiezPodpisy, odswiezHero, ilePodpisanych, razemDok, zorza: () => zorza, kurtyna: () => kurtyna,
  otworzArkusz, zmienArkusz, zamknijArkusz });
const arkuszPodpis = () => M && M.demo ? demoToast() : podpis.otworz(), arkuszWyslij = () => M && M.demo ? demoToast() : podpis.otworzWyslij();
/** Pamięć silnika (trasy, współrzędne, liczniki) leży w IndexedDB wspólnej dla wszystkich kont tej przeglądarki: czyścimy ją przy wylogowaniu i przy zmianie konta,
 *  żeby kolejna osoba na tym komputerze nie zobaczyła śladów cudzych adresów. Najwyżej 4 s czekania — brak silnika nie blokuje wylogowania. */
async function czyscSilnik() {
  try { await Promise.race([silnik.start().then(() => silnik.czysc()), zegar(4000)]); } catch (e) { /* silnik nie wstał: nie ma czego czyścić */ }
  try { localStorage.removeItem('pmt-silnik-wlasciciel'); } catch (e) { /* bez pamięci */ }
}
/** „Usuń dane z tego urządzenia”: profil z PESEL-em, miesiące, plan, wygenerowane PDF-y, ślady silnika i zapamiętane konto. Na serwerze nic nie ma — dane są tylko tu. */
function arkuszUsunDane() {
  const kod = dostep.kodAktywny(); if (!kod) return;
  otworzArkusz(`${naglowekArkusza('Usunąć dane z tego urządzenia?')}
    <p class="ark-opis">Usunę stąd <b>wszystko, co zapisałeś w aplikacji</b>: imię, PESEL i adres, miesiące, plan wizyt, wygenerowane i podpisane dokumenty oraz zapamiętane konto <b>${bezZnacznikow(kod)}</b>. Nie da się tego cofnąć. Dokumentów nie odzyskasz, ale możesz je wygenerować od nowa po ponownym wpisaniu danych.</p>
    <div class="ark-dol"><button type="button" class="przycisk glowny" data-zamknij data-pierwsze>Zostaw dane</button><button type="button" class="przycisk" id="usun-dane-tak">Usuń wszystko</button></div>`);
  $('#usun-dane-tak', arkTresc).addEventListener('click', async e => {
    e.currentTarget.disabled = true; e.currentTarget.textContent = 'Usuwam…';
    await magUsunKonto(); dostep.zapomnijKonto(kod); await czyscSilnik(); location.reload();
  });
}
/** Dokumenty powstają dla jednej, konkretnej kwoty, więc jej zmiana = wygenerowanie od nowa. zKwoty: otwarte kliknięciem w dużą kwotę (kursor od razu w polu kwoty). */
function arkuszOdNowa(zKwoty) {
  if (M && M.demo) { demoToast(); return; }
  const pod = ilePodpisanych(), mn = `${MIES[M.mies - 1]} ${M.rok}`;
  otworzArkusz(`${naglowekArkusza(zKwoty ? 'Zmienić kwotę?' : 'Wygenerować od nowa?')}
    <p class="ark-opis">${zKwoty ? `Dokumenty za <b>${mn}</b> powstały dla kwoty <b>${fmt(M.suma)} zł</b>. Żeby ją zmienić, usunę je` : `Usunę dokumenty za <b>${mn}</b>`}${pod ? ` razem z <b>${pod} wgranymi podpisami</b>` : ''}. ${zKwoty ? 'Wpiszesz nową kwotę i wygenerujesz je ponownie; dni wolne zostawię.' : 'Kwotę i dni wolne zostawię, żebyś mógł je poprawić.'}</p>
    <div class="ark-dol"><button type="button" class="przycisk glowny" data-zamknij data-pierwsze>Zostaw jak jest</button><button type="button" class="przycisk" id="od-nowa-tak">${zKwoty ? 'Usuń i wpisz nową kwotę' : 'Usuń i zacznij od nowa'}</button></div>`);
  $('#od-nowa-tak', arkTresc).addEventListener('click', async () => {
    const par = (magMiesiace.daj(M.rok, M.mies) || {}).params || {}, rok = M.rok, mies = M.mies;
    magMiesiace.usun(rok, mies); await magPliki.usunMiesiac(magMiesiace.klucz(rok, mies) + '/');
    magUst.ustaw('kwota-' + magMiesiace.klucz(rok, mies), par.kwota || 0);
    zamknijArkusz(); await przeladujMiesiac(rok, mies, !!zKwoty, !!zKwoty);
    if (par.wolne && par.wolne.length) { M.wolne = new Set(par.wolne); M.robocze = new Set([...M.robocze0].filter(x => !M.wolne.has(x))); odswiezWszystko(); if (zKwoty) fokusujKwote(); }
    pokazToast(zKwoty ? 'Usunięto dokumenty — wpisz nową kwotę i wygeneruj ponownie' : 'Usunięto dokumenty — ustaw dane i wygeneruj ponownie');
  });
}
/** Tryb pracy i pojemność silnika zmieniają się (inny miesiąc, inne auto), a dokumenty powstały dla konkretnych. Po wygenerowaniu zmiana = ponowne generowanie, więc idzie przez arkusz
    z potwierdzeniem (jak zmiana kwoty): wybór, a dopiero „Zmień i usuń dokumenty” kasuje dokumenty, zapisuje wybór w profilu (domyślny w kolejnych miesiącach) i wraca do ustawiania miesiąca. */
function arkuszUstawienia() {
  if (!M) return; if (M.demo) { demoToast(); return; } if (M.stan !== 'gotowe') return;
  const pod = ilePodpisanych(), mn = `${MIES[M.mies - 1]} ${M.rok}`, stary = { tryb: M.tryb, silnik: M.silnik }; let tryb = stary.tryb, silnik = stary.silnik;
  const opisTrybu = t => t === 'wieczory' ? 'Wieczory 16:30–22:00 · sb' : 'Tydzień, dni robocze';
  otworzArkusz(`${naglowekArkusza('Tryb pracy i auto')}
    <p class="ark-opis">Dokumenty za <b>${mn}</b> powstały dla: <b>${opisTrybu(stary.tryb)}</b>, auto <b>${tekstSilnika()}</b>. Zmiana oznacza ponowne generowanie: usunę dokumenty${pod ? ` razem z <b>${pod} wgranymi podpisami</b>` : ''}. Kwotę zostawię, dni wolne też — chyba że zmieniasz tryb pracy (dni robocze są wtedy inne).</p>
    <div class="ust-pola">
      <div class="par-w"><span>Tryb pracy</span><div class="seg" role="group" aria-label="Tryb pracy"><button type="button" data-u-tryb="tydzien" aria-pressed="${stary.tryb === 'tydzien'}">Tydzień</button><button type="button" data-u-tryb="wieczory" aria-pressed="${stary.tryb === 'wieczory'}">Wieczory 16:30–22:00</button></div></div>
      <div class="par-w"><span>Silnik auta</span><div class="seg" role="group" aria-label="Pojemność silnika"><button type="button" data-u-silnik="1" aria-pressed="${stary.silnik}">powyżej 900 cm³</button><button type="button" data-u-silnik="0" aria-pressed="${!stary.silnik}">do 900 cm³</button></div></div>
    </div>
    <div class="ark-dol"><button type="button" class="przycisk glowny" data-zamknij data-pierwsze>Zostaw jak jest</button><button type="button" class="przycisk" id="ust-tak" disabled>Zmień i usuń dokumenty</button></div>`);
  const odswiez = () => {
    $$('[data-u-tryb]', arkTresc).forEach(b => b.setAttribute('aria-pressed', String(b.dataset.uTryb === tryb)));
    $$('[data-u-silnik]', arkTresc).forEach(b => b.setAttribute('aria-pressed', String((b.dataset.uSilnik === '1') === silnik)));
    $('#ust-tak', arkTresc).disabled = tryb === stary.tryb && silnik === stary.silnik;
  };
  $$('[data-u-tryb]', arkTresc).forEach(b => b.addEventListener('click', () => { tryb = b.dataset.uTryb; odswiez(); }));
  $$('[data-u-silnik]', arkTresc).forEach(b => b.addEventListener('click', () => { silnik = b.dataset.uSilnik === '1'; odswiez(); }));
  $('#ust-tak', arkTresc).addEventListener('click', async () => {
    const par = (magMiesiace.daj(M.rok, M.mies) || {}).params || {}, rok = M.rok, mies = M.mies, zmianaTrybu = tryb !== stary.tryb;
    magMiesiace.usun(rok, mies); await magPliki.usunMiesiac(magMiesiace.klucz(rok, mies) + '/');
    magUst.ustaw('kwota-' + magMiesiace.klucz(rok, mies), par.kwota || 0);
    if (PROFIL) { PROFIL.tryb = tryb; PROFIL.tryb_wybrany = true; PROFIL.silnik_powyzej_900 = silnik; magProfil.zapisz(PROFIL); odswiezProfilWNaglowku(); }
    zamknijArkusz(); await przeladujMiesiac(rok, mies, true, false);
    if (!zmianaTrybu && par.wolne && par.wolne.length) { M.wolne = new Set(par.wolne); M.robocze = new Set([...M.robocze0].filter(x => !M.wolne.has(x))); odswiezWszystko(); }
    pokazToast('Ustawienia zmienione — sprawdź kwotę i wygeneruj dokumenty ponownie');
  });
}
/** Klik w dużą kwotę: w przykładzie → własny miesiąc z kursorem w polu kwoty; po wygenerowaniu → zmiana kwoty (z potwierdzeniem, bo kasuje dokumenty). */
function kliknietoKwote() { if (!M) return; if (M.demo) zacznijOdSwoich(); else if (M.stan === 'gotowe') arkuszOdNowa(true); }
function cofnijWyslanie() { M.wyslane = false; zapiszRekord(); odswiezHero(); pokazToast('Przywrócono stan przed wysyłką'); }
async function klikGlowny() {
  const e = etapMiesiaca();
  if (e === 'przyklad') return zacznijOdSwoich();
  if (e === 'ustaw') return generuj();
  if (e === 'podpisz') return arkuszPodpis();
  if (e === 'wyslij') return arkuszWyslij();
  pokazToast('Dokumenty są już wysłane');
}

/* ====================== drobne: toast, dymki, zakładki ====================== */
let toastNr = 0;
async function pokazToast(t) {
  const el = $('#toast'), nr = ++toastNr;
  $('#toast-tekst').textContent = t; el.classList.add('widoczny');
  await zegar(2800);
  if (nr === toastNr) el.classList.remove('widoczny');
}
function ustawZakladke(t, animuj = true) {
  const zm = () => {
    app.dataset.tab = t;
    $$('.zakladka').forEach((b, i) => { const on = b.dataset.tab === t; b.setAttribute('aria-selected', String(on)); if (on) $('#wskaznik').style.setProperty('--t', String(i)); });
    if (t === 'miesiac') kometa(300);
  };
  const kolej = ['dzis', 'miesiac', 'dokumenty'], kier = kolej.indexOf(t) >= kolej.indexOf(app.dataset.tab) ? 1 : -1;
  if (animuj) przejscie(zm, () => { szkla.forEach(budujSoczewke); mierz(); }, 'zakladka', { kier }); else zm();
  pamiec.set('zakladka', t);
  requestAnimationFrame(() => { szkla.forEach(budujSoczewke); mierz(); sprawdzListe(); });
}
const dymki = [[$('#dzwonek'), $('#dymek')], [$('#konto'), $('#konto-menu')]];
function zamknijDymki(oprocz) {
  for (const [b, d] of dymki) if (d !== oprocz && d.classList.contains('otwarty')) { d.classList.remove('otwarty'); b.setAttribute('aria-expanded', 'false'); }
}
/* ====================== powiadomienia (dzwonek) ====================== */
function odswiezPowiadomienia() {
  const box = $('#powiadomienia'), bad = $('#dzwonek b'); if (!M) return;
  const poz = [];
  if (!M.wyslane) {
    const t = terminMiesiaca(), dzis = new Date(); dzis.setHours(12, 0, 0, 0);
    const dni = Math.round((t - dzis) / 86400000);
    poz.push({ c: false, t: 'Termin podpisu i wysyłki', s: `${DN[(t.getDay() + 6) % 7]} ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}.${t.getFullYear()} · ${dni > 1 ? `za ${dni} dni` : dni === 1 ? 'jutro' : dni === 0 ? 'dziś' : 'po terminie'}` });
  }
  if (M.demo) { box.innerHTML = '<div class="pow"><i class="c"></i><div><b>To jest przykład</b><span>Zacznij od swoich danych — przykładowy miesiąc zniknie.</span></div></div>'; if (bad) bad.remove(); $('#dzwonek').setAttribute('aria-label', 'Powiadomienia'); return; }
  const sesja = dostep.ocenaSesji();
  if (sesja.wazna && sesja.wazneDo && sesja.dni <= 14) poz.push({ c: false, t: 'Dostęp do aplikacji wygasa', s: `${sesja.dni === 0 ? 'dziś' : sesja.dni === 1 ? 'jutro' : `za ${sesja.dni} dni`} (${sesja.wazneDo.split('-').reverse().join('.')}) · skontaktuj się z administratorem` });
  if (M.stan === 'gotowe') poz.push({ c: true, t: `Dokumenty za ${MIES[M.mies - 1]} gotowe`, s: `${M.polecenia.length} ${M.polecenia.length === 1 ? 'polecenie' : 'polecenia'} i rozliczenie · ${fmt(M.suma)} zł` });
  box.innerHTML = poz.length ? poz.map(p => `<div class="pow"><i class="${p.c ? 'c' : ''}"></i><div><b>${p.t}</b><span>${p.s}</span></div></div>`).join('') : '<div class="pow"><i class="c"></i><div><b>Wszystko załatwione</b><span>Nic nie czeka na Ciebie.</span></div></div>';
  if (poz.length) { if (bad) bad.textContent = String(poz.length); else $('#dzwonek').insertAdjacentHTML('beforeend', `<b>${poz.length}</b>`); } else if (bad) bad.remove();
  $('#dzwonek').setAttribute('aria-label', poz.length ? `Powiadomienia: ${poz.length}` : 'Powiadomienia');
}

/* ====================== zdarzenia ====================== */
function zdarzenia() {
  const siatka = $('#siatka');
  siatka.addEventListener('click', e => {
    const b = e.target.closest('button.dz'); if (!b) return;
    const d = Number(b.dataset.d);
    if (b.classList.contains('trasa')) wybierzDzien(d); else przelaczWolne(d);
  });
  siatka.addEventListener('pointerover', e => {
    const c = e.target.closest('.dz.trasa, .dz.bez, .dz.urlop');
    if (!c || !M) { ukryjPodp(); podswietlPolecenie(0, false); return; }
    const d = Number(c.dataset.d), r = c.getBoundingClientRect();
    pokazPodp(opisDnia(d), r.left + r.width / 2, r.top - 2);
    const p = polDla(d); if (c.classList.contains('trasa') && p) podswietlPolecenie(p.nr, true, true);
  });
  siatka.addEventListener('pointerleave', () => { ukryjPodp(); podswietlPolecenie(0, false); });
  siatka.addEventListener('focusin', e => { const c = e.target.closest('.dz.trasa'); if (c) { const r = c.getBoundingClientRect(); pokazPodp(opisDnia(Number(c.dataset.d)), r.left + r.width / 2, r.top - 2); } });
  siatka.addEventListener('focusout', ukryjPodp);
  $('#fiolki').addEventListener('pointerover', e => { const w = e.target.closest('.fiolka[data-pol]'); if (w) podswietlPolecenie(Number(w.dataset.pol), true); else podswietlPolecenie(0, false); });
  $('#fiolki').addEventListener('pointerleave', () => podswietlPolecenie(0, false));
  $('#fiolki').addEventListener('click', e => { if (M && M.stan === 'gotowe' && e.target.closest('.fiolka')) arkuszPodpis(); });
  $('#ku-pol').addEventListener('pointerover', e => { const s = e.target.closest('[data-pol]'); if (s) podswietlPolecenie(Number(s.dataset.pol), true); });
  $('#ku-pol').addEventListener('pointerleave', () => podswietlPolecenie(0, false));
  $('#e-wstecz').addEventListener('click', () => { const i = M.dniT.indexOf(wybrany); if (i > 0) wybierzDzien(M.dniT[i - 1], -1); });
  $('#e-dalej').addEventListener('click', () => { const i = M.dniT.indexOf(wybrany); if (i < M.dniT.length - 1) wybierzDzien(M.dniT[i + 1], 1); });
  $$('.rozwin').forEach(b => { b.dataset.etykieta = b.getAttribute('aria-label'); b.setAttribute('aria-expanded', 'false'); b.addEventListener('click', e => { e.stopPropagation(); const k = b.closest('.kafel'); skupienie(k === skupiony ? null : k); }); });
  bento.addEventListener('click', e => { if (skupiony && !skupiony.contains(e.target)) skupienie(null); });
  btn.addEventListener('click', klikGlowny);
  $('#cofnij').addEventListener('click', cofnijWyslanie);
  $('#od-nowa').addEventListener('click', () => arkuszOdNowa());
  $('#b-wzor').addEventListener('click', e => { if (e.target.closest('#zmien-ust')) arkuszUstawienia(); });
  const krok1 = $('#krok1');
  krok1.addEventListener('click', () => { if (krok1.classList.contains('zmien')) arkuszUstawienia(); });
  krok1.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && krok1.classList.contains('zmien')) { e.preventDefault(); arkuszUstawienia(); } });
  const kwotaKlik = $('#b-kwota-w');
  kwotaKlik.addEventListener('click', kliknietoKwote);
  kwotaKlik.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); kliknietoKwote(); } });
  $('#parametry').addEventListener('click', e => {
    const t = e.target.closest('[data-tryb]'); if (t) { przelaczTryb(t.dataset.tryb); return; }
    const s = e.target.closest('[data-silnik]'); if (s && M.stan === 'plan') { M.silnik = s.dataset.silnik === '1'; if (PROFIL) { PROFIL.silnik_powyzej_900 = M.silnik; magProfil.zapisz(PROFIL); odswiezProfilWNaglowku(); } odswiezParametry(); }
  });
  let tK = 0;
  const wej = $('#kwota-in');
  wej.addEventListener('input', () => { M.kwota = parsujKwote(wej.value); clearTimeout(tK); tK = setTimeout(odswiezParametry, 250); });
  wej.addEventListener('blur', () => { M.kwota = parsujKwote(wej.value); wej.value = M.kwota ? fmt(M.kwota).replace(/\s/g, '') : ''; magUst.ustaw('kwota-' + magMiesiace.klucz(M.rok, M.mies), M.kwota); odswiezParametry(); });
  wej.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); wej.blur(); } });
  $('#przystanki').addEventListener('scroll', sprawdzListe, { passive: true });
  $('#przystanki').addEventListener('click', e => {
    if (e.target.closest('#plan-otworz')) { arkuszPlan(); return; }
    const nav = e.target.closest('.nawiguj');
    if (nav) {
      const i = Number(nav.dataset.i), on = nawigacja !== i; nawigacja = on ? i : -1;
      nav.classList.toggle('prowadzi', on); nav.setAttribute('aria-pressed', String(on)); $('span', nav).textContent = on ? 'Prowadzę' : 'Nawiguj';
      if (on) { zorza && zorza.flara(.18); const w = PLAN_DZIS[i]; window.open('https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=' + encodeURIComponent(w.adres), '_blank', 'noopener'); }
      return;
    }
    const b = e.target.closest('.p-znak'); if (!b) return;
    const i = Number(b.dataset.i), w = PLAN_DZIS[i]; w.ok = !w.ok;
    const t = new Date(); wizytaUstaw(w.data, w.klucz, w.ok, `${dwa(t.getHours())}:${dwa(t.getMinutes())}`);
    oznaczWidoczneWiersze();
    const vt = przejscie(rysujDzis, () => { const nb = $(`.p-znak[data-i="${i}"]`); nb && nb.focus({ preventScroll: true }); }, 'dzis', { znak: i });
    if (w.ok) {
      if (PLAN_DZIS.every(x => x.ok)) { const start = () => setTimeout(fanfary, 140); vt ? vt.finished.then(start, start) : start(); }      // fanfary dopiero po zakończeniu przejścia (w jego trakcie widać tylko przechwycony obraz)
      else { zorza && zorza.flara(.2); pokazToast(`Odhaczono: ${w.s} · ${w.m}`); }
    }
  });
  $('#plan-btn').addEventListener('click', arkuszPlan);
  for (const [b, d] of dymki) {
    b.addEventListener('click', e => {
      e.stopPropagation(); const o = !d.classList.contains('otwarty'); zamknijDymki(d);
      d.classList.toggle('otwarty', o); b.setAttribute('aria-expanded', String(o));
    });
  }
  doc.addEventListener('click', e => { if (!e.target.closest('.dymek')) zamknijDymki(null); });
  $('#moje-dane').addEventListener('click', () => { zamknijDymki(null); otworzMojeDane(false); });
  $('#pokaz-przyklad').addEventListener('click', () => { zamknijDymki(null); pokazPrzyklad(); });
  $('#zmien-haslo').addEventListener('click', () => { zamknijDymki(null); arkuszZmianyHasla(false); });
  $('#wyloguj').addEventListener('click', () => { zamknijDymki(null); wylogujICzysc(); });
  $$('.przel [data-motyw]').forEach(b => b.addEventListener('click', () => { ustawMotyw(b.dataset.motyw, b); zegar(700).then(() => zamknijDymki(null)); }));
  $('#motyw').addEventListener('click', e => ustawMotyw(motywTeraz() === 'light' ? 'dark' : 'light', e.currentTarget));
  const zmienMiesiac = k => { let r = M.rok, m = M.mies + k; if (m < 1) { m = 12; r--; } if (m > 12) { m = 1; r++; } przeladujMiesiac(r, m); };
  $('#m-wstecz').addEventListener('click', () => zmienMiesiac(-1));
  $('#m-nazwa').addEventListener('click', () => arkuszRok(M.rok));
  $('#m-dalej').addEventListener('click', () => zmienMiesiac(1));
  $('#termin').addEventListener('pointerenter', () => { ustawCelCiepla(); zorza && zorza.cieplo(1); });
  $$('.zakladka').forEach(b => b.addEventListener('click', () => ustawZakladke(b.dataset.tab)));
  $('#zakladki').addEventListener('keydown', e => {
    const z = $$('.zakladka'), i = z.indexOf(doc.activeElement); if (i < 0) return;
    const j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: z.length - 1 }[e.key]; if (j === undefined) return;
    e.preventDefault(); const c = z[(j + z.length) % z.length]; c.focus(); ustawZakladke(c.dataset.tab);
  });
  try { JASNY.addEventListener('change', () => { if (!root.dataset.theme) poMotywie(); }); } catch (e) {}
  addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if (arkuszOtwarty) { zamknijArkusz(); return; }
    for (const [b, d] of dymki) if (d.classList.contains('otwarty')) { zamknijDymki(null); b.focus(); return; }
    if (skupiony) { const k = skupiony; skupienie(null); const b = $('.rozwin', k); b && b.focus({ preventScroll: true }); }
  });
  let rt = 0;
  addEventListener('resize', () => {
    clearTimeout(rt);
    rt = setTimeout(() => { dopasujPodroz(); zorza && zorza.rozmiar(); kurtyna && kurtyna.rozmiar(); rysujGwiazdy(); rysujHoryzont(); domyslne(); mierz(); ustawCelCiepla(); budz(); sprawdzListe(); }, 120);
  });
}

/* ====================== dostęp: logowanie, hasło, sesja ====================== */
/* Okno logowania to ten sam arkusz co reszta okien (szkło, ruch), tylko bez zamykania; aplikacja pod spodem jest ukryta do zalogowania. */
const powitanie = () => { const g = new Date().getHours(); return g >= 5 && g < 18 ? 'Dzień dobry' : 'Dobry wieczór'; };
const poleHasla = (id, etykieta, auto) => `<label class="pole"><span>${etykieta}</span><div class="dz-haslo"><input id="${id}" type="password" autocomplete="${auto}" autocapitalize="off" spellcheck="false"><button type="button" class="dz-oko" data-oko aria-label="Pokaż hasło" aria-pressed="false">${ik('i-oko')}</button></div></label>`;
arkTresc.addEventListener('click', e => {
  const b = e.target.closest('[data-oko]'); if (!b) return;
  const i = $('input', b.parentElement), pokaz = i.type === 'password'; i.type = pokaz ? 'text' : 'password';
  b.setAttribute('aria-pressed', String(pokaz)); b.setAttribute('aria-label', pokaz ? 'Ukryj hasło' : 'Pokaż hasło'); b.innerHTML = ik(pokaz ? 'i-oko-zam' : 'i-oko');
});
const dzInfo = (t, kl = '') => { const i = $('#dz-info', arkTresc); if (i) { i.className = 'dz-info' + (kl ? ' ' + kl : ''); i.textContent = t; if (kl === 'zle' && t) potrzasnij($('#arkusz')); } };
/* przycisk „pracuje”: światło płynie, a po 4 s mówimy wprost, na co czekamy (zimny start Apps Script bywa długi) */
function oczekiwanie(przycisk, tekst) {
  const t0 = performance.now(), stary = przycisk.textContent; przycisk.disabled = true; przycisk.classList.add('pracuje'); przycisk.textContent = tekst;
  const z = setInterval(() => { const sek = Math.floor((performance.now() - t0) / 1000); if (sek >= 4) dzInfo(`Czekam na serwer… ${sek} s (wybudzenie trwa czasem ok. 30 s)`); }, 500);
  return () => { clearInterval(z); przycisk.disabled = false; przycisk.classList.remove('pracuje'); przycisk.textContent = stary; };
}
const znakDostepu = (tytul, pod) => `<div class="dz-gora"><img src="ikony/logo-128.webp" alt="" width="56" height="56"><div><h2 id="ark-tyt">${tytul}</h2><p>${pod}</p></div></div>`;
function ekranLogowania(wstep, kodStart) {
  return new Promise(rozwiaz => {
    dostepBlokada = true; arkTlo.classList.add('dostep');
    const proby = new Set();
    const widokLogowania = (info, kod, haslo, auto) => {
      otworzArkusz(`${znakDostepu(powitanie(), 'PMT Planer · zaloguj się swoim loginem')}
        <form id="dz-form" class="dz-pola" novalidate>
          <label class="pole"><span>Login (5 cyfr)</span><input id="dz-kod" ${kod ? '' : 'data-pierwsze'} inputmode="numeric" maxlength="5" autocomplete="username" autocapitalize="off" value="${bezZnacznikow(kod || '')}"></label>
          ${poleHasla('dz-haslo', 'Hasło', 'current-password').replace('<input ', kod ? '<input data-pierwsze ' : '<input ')}
          <p class="dz-info" id="dz-info" role="status" aria-live="polite"></p>
          <button class="przycisk glowny dz-ok" id="dz-ok" type="submit" disabled>Zaloguj</button>
        </form>
        <div class="dz-linki"><button type="button" class="dz-link" id="dz-reset">Nie pamiętam hasła</button></div>
        <p class="dz-pod">Pierwsze logowanie? Jako hasło wpisz numer telefonu z kartoteki — potem ustawisz własne. Logowanie rusza samo po wpisaniu hasła.</p>`);
      const kodEl = $('#dz-kod', arkTresc), hasloEl = $('#dz-haslo', arkTresc), ok = $('#dz-ok', arkTresc);
      let wToku = false, zegarAuto = 0;
      const sprawdz = () => { ok.disabled = wToku || !(/^\d{5}$/.test(kodEl.value) && hasloEl.value.length >= 4); };
      /* odmowy, które trzeba pokazać zawsze, także po próbie automatycznej (sieć, blokada, wygaśnięcie…); zwykłe „złe hasło” po automacie to tylko łagodna podpowiedź */
      const wazny = t => /sieć|sieci|internet|serwer|wersj|zablok|certyf|połącz|wygas|dni od|aktualiz|czasie|vpn|cors|ustawione haslo/i.test(t || '');
      const zaloguj = async (auto = false) => {
        if (wToku || !doc.contains(hasloEl)) return; const k = kodEl.value.trim(), h = hasloEl.value; if (!/^\d{5}$/.test(k) || h.length < 4) return;
        proby.add(k + '|' + h); wToku = true; clearTimeout(zegarAuto); dzInfo('');
        const koniec = oczekiwanie(ok, 'Sprawdzam…'); if (!auto) kodEl.disabled = hasloEl.disabled = true;   // przy automacie pole hasła zostaje aktywne: żaden znak nie ginie
        let w; try { w = await dostep.zaloguj(k, h); } catch (e) { w = { ok: false, komunikat: 'Nie udało się zalogować: ' + e.message }; }
        koniec(); wToku = false; kodEl.disabled = hasloEl.disabled = false; sprawdz();
        if (w.ok) { rozwiaz({ ...w, kod: k, haslo: h }); return; }
        if (auto && (kodEl.value.trim() !== k || hasloEl.value !== h)) { probuj('tekst'); return; }    // odpowiedź dotyczy starego tekstu — pisano dalej
        if (auto && !wazny(w.komunikat)) { dzInfo('Dokończ wpisywanie hasła albo naciśnij Enter.'); return; }
        dzInfo(w.komunikat, 'zle'); hasloEl.focus(); if (!auto) hasloEl.select();
      };
      /* AUTOLOGOWANIE jak w programie: hasło znane na tym urządzeniu loguje od razu; nowe — po 1,3 s pauzy w pisaniu. Każda para login+hasło sprawdzana jest raz. */
      const probuj = async zrodlo => {
        if (wToku || !doc.contains(hasloEl)) return; const k = kodEl.value.trim(), h = hasloEl.value;
        if (!/^\d{5}$/.test(k) || h.length < 5 || proby.has(k + '|' + h)) return;
        const znane = await dostep.czyHasloZnane(k, h);
        if (zrodlo === 'tekst' && !znane) return;
        if (kodEl.value.trim() !== k || hasloEl.value !== h) return;
        zaloguj(true);
      };
      kodEl.addEventListener('input', () => { kodEl.value = kodEl.value.replace(/\D/g, '').slice(0, 5); sprawdz(); if (kodEl.value.length === 5 && !hasloEl.value) hasloEl.focus(); else if (kodEl.value.length === 5) probuj('tekst'); });
      hasloEl.addEventListener('input', () => { sprawdz(); clearTimeout(zegarAuto); probuj('tekst'); zegarAuto = setTimeout(() => probuj('zegar'), 1300); });
      $('#dz-form', arkTresc).addEventListener('submit', e => { e.preventDefault(); zaloguj(false); });
      $('#dz-reset', arkTresc).addEventListener('click', () => widokResetu(kodEl.value));
      if (haslo) hasloEl.value = haslo; sprawdz();
      if (info) dzInfo(info.t, info.kl);
      if (auto) zaloguj(false);
    };
    const widokResetu = (kod) => {
      otworzArkusz(`${znakDostepu('Reset hasła', 'Telefon z kartoteki to Twój dowód tożsamości')}
        <form id="dr-form" class="dz-pola" novalidate>
          <label class="pole"><span>Login (5 cyfr)</span><input id="dr-kod" inputmode="numeric" maxlength="5" autocomplete="username" value="${bezZnacznikow(kod || '')}"></label>
          <label class="pole"><span>Numer telefonu z kartoteki</span><input id="dr-tel" ${/^\d{5}$/.test(kod || '') ? 'data-pierwsze' : ''} inputmode="tel" autocomplete="tel" placeholder="np. 600100200"></label>
          ${poleHasla('dr-nowe', 'Nowe hasło (min. 6 znaków)', 'new-password')}
          ${poleHasla('dr-pow', 'Powtórz nowe hasło', 'new-password')}
          <p class="dz-info" id="dz-info" role="status" aria-live="polite"></p>
          <div class="ark-dol"><button type="button" class="przycisk" id="dr-wstecz">Wróć</button><button type="submit" class="przycisk glowny" id="dr-ok">Zresetuj i ustaw</button></div>
        </form>`);
      if (!/^\d{5}$/.test(kod || '')) $('#dr-kod', arkTresc).focus();
      $('#dr-wstecz', arkTresc).addEventListener('click', () => widokLogowania(null, $('#dr-kod', arkTresc).value));
      $('#dr-form', arkTresc).addEventListener('submit', async e => {
        e.preventDefault();
        const k = $('#dr-kod', arkTresc).value.trim(), tel = $('#dr-tel', arkTresc).value, nowe = $('#dr-nowe', arkTresc).value.trim(), pow = $('#dr-pow', arkTresc).value.trim();
        if (nowe !== pow) { dzInfo('Nowe hasła nie są takie same.', 'zle'); return; }
        const koniec = oczekiwanie($('#dr-ok', arkTresc), 'Resetuję…'); dzInfo('');
        let w; try { w = await dostep.resetujHaslo(k, tel, nowe); } catch (err) { w = { ok: false, komunikat: 'Nie udało się: ' + err.message }; }
        koniec();
        if (w.ok) { widokLogowania({ t: 'Hasło ustawione i sprawdzone na serwerze. Loguję…', kl: 'ok' }, k, nowe, true); return; }
        dzInfo(w.komunikat, 'zle');
      });
    };
    widokLogowania(wstep ? { t: wstep, kl: 'zle' } : null, kodStart);
  });
}
async function zalogujSie(wstep) {
  const w = await ekranLogowania(wstep, dostep.ostatniKod());
  dostepBlokada = false; arkTlo.classList.remove('dostep'); zamknijArkusz();
  return w;
}
/** Dane na tym urządzeniu są zaszyfrowane POPRZEDNIM hasłem (hasło zmieniono na innym urządzeniu albo zresetowano — wtedy stary klucz nie pasuje do nowego hasła).
 *  Poprzednie hasło odblokowuje je i przenosi pod nowe; bez niego zostaje tylko usunięcie danych z urządzenia (dokumenty da się wygenerować od nowa). Okno nie zamyka się Esc ani tłem. */
function arkuszOdzyskaniaSejfu(kod, noweHaslo) {
  return new Promise(rozwiaz => {
    dostepBlokada = true; arkTlo.classList.add('dostep');
    const koniec = dek => { dostepBlokada = false; arkTlo.classList.remove('dostep'); zamknijArkusz(); rozwiaz({ stan: 'ok', dek }); };
    otworzArkusz(`${znakDostepu('Dane z tego urządzenia', 'są zaszyfrowane poprzednim hasłem')}
      <p class="ark-opis">Hasło tego konta zostało zmienione (albo zresetowane), a Twoje dane na tym urządzeniu — PESEL, plan, dokumenty — są zaszyfrowane hasłem, które obowiązywało wcześniej. Wpisz je, żeby je odblokować. Jeśli go nie pamiętasz, usuń dane z tego urządzenia i zacznij od nowa: dokumenty wygenerujesz ponownie.</p>
      <form id="sj-form" class="dz-pola" novalidate>
        ${poleHasla('sj-stare', 'Poprzednie hasło', 'current-password').replace('<input ', '<input data-pierwsze ')}
        <p class="dz-info" id="dz-info" role="status" aria-live="polite"></p>
        <div class="ark-dol"><button type="button" class="przycisk" id="sj-usun">Usuń dane i zacznij od nowa</button><button type="submit" class="przycisk glowny" id="sj-ok">Odblokuj</button></div>
      </form>`);
    $('#sj-form', arkTresc).addEventListener('submit', async e => {
      e.preventDefault(); const stare = $('#sj-stare', arkTresc).value; if (!stare) return;
      const k = oczekiwanie($('#sj-ok', arkTresc), 'Sprawdzam…'); dzInfo('');
      let dek = null; try { dek = await dostep.odzyskajSejf(kod, stare, noweHaslo); } catch (err) { dek = null; }
      k(); if (dek) { koniec(dek); return; } dzInfo('To hasło nie pasuje do zaszyfrowanych danych.', 'zle');
    });
    $('#sj-usun', arkTresc).addEventListener('click', async () => {
      const k = oczekiwanie($('#sj-usun', arkTresc), 'Usuwam…');
      try { await magUsunKonto(); const dek = await dostep.nowySejf(kod, noweHaslo); koniec(dek); } catch (err) { k(); dzInfo('Nie udało się usunąć danych: ' + err.message, 'zle'); }
    });
  });
}
/** Zaszyfrowane dane konta nie przechodzą kontroli podpisu (uszkodzone albo zmienione): pokazujemy to wprost i pozwalamy je usunąć. Okno nie zamyka się Esc ani tłem. */
function arkuszUszkodzonychDanych() {
  return new Promise(rozwiaz => {
    dostepBlokada = true; arkTlo.classList.add('dostep');
    otworzArkusz(`${znakDostepu('Dane na tym urządzeniu', 'są uszkodzone')}
      <p class="ark-opis">Nie mogę odczytać Twoich zapisanych danych (PESEL, plan, miesiące): nie przechodzą kontroli integralności — mogły się uszkodzić albo ktoś je zmienił. Usunę je z tego urządzenia, a Ty wpiszesz je od nowa i wygenerujesz dokumenty ponownie.</p>
      <div class="ark-dol"><button type="button" class="przycisk glowny" id="uszk-usun">Usuń uszkodzone dane</button></div>`);
    $('#uszk-usun', arkTresc).addEventListener('click', () => { magWyczysc(); dostepBlokada = false; arkTlo.classList.remove('dostep'); zamknijArkusz(); rozwiaz(); });
  });
}
/** Wylogowanie: koniec sesji, czyszczenie pamięci silnika i klucza danych (zniknie z sessionStorage), przeładowanie. */
async function wylogujICzysc() { dostep.wyloguj(); await czyscSilnik(); location.reload(); }
/* zmiana hasła z menu konta albo „ustaw własne” po pierwszym logowaniu telefonem (wtedy stare = telefon, wpisany przed chwilą) */
function arkuszZmianyHasla(pierwsze, telefon, poZamknieciu) {
  otworzArkusz(`${naglowekArkusza(pierwsze ? 'Ustaw własne hasło' : 'Zmiana hasła')}
    <p class="ark-opis">${pierwsze ? 'Zalogowałeś się numerem telefonu. Ustaw własne hasło — telefon zostanie już tylko kluczem do jego resetu.' : 'Podaj dotychczasowe hasło i dwa razy nowe. Hasła są zapisywane na serwerze, więc zmiana wymaga internetu.'}</p>
    <form id="zh-form" class="dz-pola" novalidate>
      ${pierwsze ? '' : poleHasla('zh-stare', 'Dotychczasowe hasło', 'current-password').replace('<input ', '<input data-pierwsze ')}
      ${poleHasla('zh-nowe', 'Nowe hasło (min. 6 znaków)', 'new-password').replace('<input ', pierwsze ? '<input data-pierwsze ' : '<input ')}
      ${poleHasla('zh-pow', 'Powtórz nowe hasło', 'new-password')}
      <p class="dz-info" id="dz-info" role="status" aria-live="polite"></p>
      <div class="ark-dol"><button type="button" class="przycisk" data-zamknij>${pierwsze ? 'Później' : 'Anuluj'}</button><button type="submit" class="przycisk glowny" id="zh-ok">Zapisz hasło</button></div>
    </form>`, poZamknieciu);
  $('#zh-form', arkTresc).addEventListener('submit', async e => {
    e.preventDefault();
    const stare = pierwsze ? telefon : $('#zh-stare', arkTresc).value, nowe = $('#zh-nowe', arkTresc).value.trim(), pow = $('#zh-pow', arkTresc).value.trim();
    if (nowe !== pow) { dzInfo('Nowe hasła nie są takie same.', 'zle'); return; }
    const koniec = oczekiwanie($('#zh-ok', arkTresc), 'Zapisuję…'); dzInfo('');
    let w; try { w = await dostep.zmienHaslo(stare, nowe); } catch (err) { w = { ok: false, komunikat: 'Nie udało się: ' + err.message }; }
    koniec();
    if (!w.ok) { dzInfo(w.komunikat, 'zle'); return; }
    zamknijArkusz(); pokazToast('Hasło zmienione i sprawdzone na serwerze');
  });
}
const komunikatBlokady = s => s.powod === 'offline' ? `Minęło ponad ${dostep.OFFLINE_DNI} dni od ostatniego kontaktu z serwerem. Połącz się z internetem i zaloguj się ponownie.` : 'Dostęp do konta wygasł. Skontaktuj się z administratorem — po przedłużeniu zaloguj się ponownie.';
function zablokujDostep(komunikat) {
  try { sessionStorage.setItem('pmt-dostep-komunikat', komunikat); } catch (e) { /* bez pamięci karty komunikat po prostu nie wróci */ }
  dostep.wyloguj(); location.reload();
}
let ostatniPuls = 0;
async function sprawdzDostep() {
  ostatniPuls = Date.now();
  const o = await dostep.puls();
  const s = dostep.ocenaSesji();
  if ((o && o.status === 'wygasla') || !s.wazna) { zablokujDostep(komunikatBlokady(o && o.status === 'wygasla' ? { powod: 'wygasla' } : s)); return; }
  odswiezProfilWNaglowku(); odswiezPowiadomienia();
}

/* ====================== start ====================== */
const pierwszaKlatka = () => new Promise(res => {
  let gotowe = false; const ok = () => { if (!gotowe) { gotowe = true; res(); } };
  requestAnimationFrame(() => requestAnimationFrame(ok)); setTimeout(ok, 1200);
});
function ladowanie(widoczne, tekst, p) {
  const l = $('#ladowanie'); l.classList.toggle('widoczny', widoczne);
  if (tekst) $('#lad-tekst').textContent = tekst;
  if (p != null) $('#lad-pasek').style.setProperty('--p', Math.round(p * 100) + '%');
}
async function start() {
  app.classList.add('czeka', 'zamknieta');
  rysujGwiazdy(); rysujHoryzont(); zorza = startZorza();         // scena żyje już za oknem logowania
  let postepStartu = ['Uruchamianie…', .03], pokazLadowanie = false;
  const silnikGotowy = silnik.start((t, v) => { postepStartu = [t, v]; if (pokazLadowanie) ladowanie(true, t, v); });
  silnikGotowy.catch(() => {});                                   // błąd silnika obsługujemy po zalogowaniu
  dostep.rozgrzej();
  let kom = ''; try { kom = sessionStorage.getItem('pmt-dostep-komunikat') || ''; sessionStorage.removeItem('pmt-dostep-komunikat'); } catch (e) { /* bez pamięci karty */ }
  let sesja = null, ocena = dostep.ocenaSesji();
  if (dostep.kodAktywny() && !ocena.wazna) { await dostep.puls(); ocena = dostep.ocenaSesji(); }   // po długiej przerwie najpierw próbujemy odnowić kontakt z serwerem
  if (!(dostep.kodAktywny() && ocena.wazna && dostep.sesjaTejKarty() && dostep.kluczDanych())) sesja = await zalogujSie(kom || (ocena.powod === 'offline' || ocena.powod === 'wygasla' ? komunikatBlokady(ocena) : ''));      // logowanie przy każdym uruchomieniu (nowa karta), jak w programie na komputerze
  const kodKonta = dostep.kodAktywny() || (sesja && sesja.kod);
  ustawKonto(kodKonta); dostep.uruchomienie();
  /* SEJF: dane konta (PESEL, adres, miesiące, plan, PDF-y) są zaszyfrowane kluczem, który odblokowuje hasło. Odświeżenie karty bierze klucz z sessionStorage; po logowaniu otwieramy (albo zakładamy) sejf tym hasłem. */
  let dek = sesja ? (sesja.dek || null) : dostep.kluczDanych();
  if (!dek && sesja) {
    let s = await dostep.przygotujSejf(kodKonta, sesja.haslo);
    if (s.stan === 'obcy') s = await arkuszOdzyskaniaSejfu(kodKonta, sesja.haslo);
    dek = s.dek;
  }
  if (dek) { dostep.zapamietajKluczDanych(dek); magOdblokuj(dek); }
  if (dek && !magCzytelny()) await arkuszUszkodzonychDanych();      // zaszyfrowany magazyn nie daje się odczytać właściwym kluczem: dane uszkodzone albo zmienione — nie nadpisujemy ich po cichu
  if (dek) magMigruj().catch(() => {});
  pokazLadowanie = true; ladowanie(true, postepStartu[0], postepStartu[1]);
  PROFIL = magProfil.wczytaj(); PLAN = magPlan.wczytaj();
  try {
    await silnikGotowy;
    if ((() => { try { return localStorage.getItem('pmt-silnik-wlasciciel'); } catch (e) { return null; } })() !== kodKonta) await czyscSilnik();      // pamięć silnika należała do innego konta (albo do nikogo)
    try { localStorage.setItem('pmt-silnik-wlasciciel', kodKonta); } catch (e) { /* bez pamięci */ }
    const st = await silnik.stale(); LIMIT_DZIEN = st.limit_dnia; LIMIT_POL = st.limit_dokumentu; MIN_KWOTA = st.min_kwota;
  } catch (e) {
    $('#lad-tekst').innerHTML = `Nie udało się uruchomić silnika delegacji.<br><small>${bezZnacznikow(e.message)}</small><br><br><button class="przycisk" type="button" id="lad-ponow">Spróbuj ponownie</button>`;
    $('#lad-ponow').addEventListener('click', () => location.reload());
    return;
  }
  /* start na miesiącu, który minął (jak w programie): w październiku — wrzesień */
  const dzis = new Date(); let r = dzis.getFullYear(), m = dzis.getMonth(); if (m === 0) { r--; m = 12; }
  const ost = magUst.daj('ostatni-miesiac', null);
  if (ost) { r = ost.rok; m = ost.mies; }
  const pokazDemo = !PROFIL && !magMiesiace.ile() && pamiec.get('przyklad') !== 'nie';      // pierwsze uruchomienie: przykładowy, pełny miesiąc zamiast pustego programu
  if (!(pokazDemo && await pokazPrzyklad())) await przeladujMiesiac(r, m, true);
  const zak = pamiec.get('zakladka');
  if (zak && ['dzis', 'miesiac', 'dokumenty'].includes(zak)) ustawZakladke(zak, false);
  odswiezProfilWNaglowku();
  kurtyna = startKurtyna();
  szkla.forEach(el => { ro && ro.observe(el); });
  mierz(); ustawSwiatlo(); poMotywieUI();
  zdarzenia();
  try { navigator.storage && navigator.storage.persist && navigator.storage.persist(); } catch (e) { /* bez trwałego magazynu też działa */ }      // prosi przeglądarkę, by nie czyściła danych użytkownika (Safari/iOS i Chrome zwykle zgadzają się dla zainstalowanej aplikacji)
  const pomoc = zainstalujPomoc({ $, doc, otworzArkusz, naglowekArkusza, zamknijArkusz, arkTresc, bezZnacznikow, pokazToast, zamknijDymki });
  zainstalujZywe({
    $, $$, doc, root, app, bento, pomoc, ruchOkno: v => { RUCH.zewn = v; }, fmt, dwa, cap, DK, DN, MIES, MIES_D, minuty, hhmm, czas, spokoj, anim, iskry, falaDotyku, pamiec, E_SPR, E_WYJ,
    stan: () => ({ M, wybrany, PROFIL, PLAN, LIMIT_DZIEN, LIMIT_POL, MIN_KWOTA, skupiony, arkuszOtwarty: !!arkuszOtwarty || dostepBlokada }),
    zorza: () => zorza, odcinkiDnia, czasyDnia,
    wybierzDzien, przelaczWolne, ustawWolne, ustawKwote, ustawZakladke, ustawMotyw, motywTeraz, skupienie, otworzMojeDane, arkuszPlan, arkuszRok, arkuszZmianyHasla, arkuszPodpis,
    klikGlowny, etapMiesiaca, przeladujMiesiac, pokazPrzyklad, przykladDostepny, pokazToast, przejscie, wyloguj: wylogujICzysc
  });
  kurtyna && kurtyna.dane && kurtyna.dane();
  ladowanie(false); app.classList.remove('zamknieta');
  await pierwszaKlatka();
  app.classList.remove('czeka');
  zorza && zorza.restart(); kurtyna && kurtyna.restart();
  if (czyChromium && UZYJ_SOCZEWKI) { root.classList.add('soczewka'); szkla.forEach(budujSoczewke); }
  if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(() => { mierz(); ustawSwiatlo(); sprawdzListe(); kurtyna && kurtyna.rozmiar(); }).catch(() => {});
  await zegar(700);
  let licznikiGotowe = false;
  $$('[data-licz]').forEach(el => { const cel = Number(el.dataset.licz); tween(1300, p => { if (!licznikiGotowe) el.textContent = String(Math.round(cel * p)); }); });
  zegar(2700).then(() => { licznikiGotowe = true; $$('[data-licz]').forEach(el => { el.textContent = el.dataset.licz; }); });
  await zegar(1500);
  ustawCelCiepla();
  zorza && zorza.cieplo(.55);
  await zegar(2000);
  app.classList.remove('wejscie');
  mierz(); ustawSwiatlo();
  dodajPodpowiedzi();
  if (PROFIL && PROFIL.imie) setTimeout(() => pokazToast(`${powitanie()}, ${PROFIL.imie.split(' ')[0]}`), 1800);
  const potem = () => { if (!PROFIL && !(M && M.demo)) otworzMojeDane(true); };
  if (sesja && sesja.telefon) arkuszZmianyHasla(true, sesja.haslo, potem); else potem();
  sprawdzDostep(); setInterval(sprawdzDostep, dostep.PULS_CO_MIN * 60000);
  setTimeout(ostrzezGrafike, 3500);
  doc.addEventListener('visibilitychange', () => { if (!doc.hidden && Date.now() - ostatniPuls > 5 * 60000) sprawdzDostep(); });
  addEventListener('pagehide', e => { if (!e.persisted) { dostep.dopiszMinuty(); dostep.zdarzenieSesji('zamkniecie', true); } });
  /* dane żyją w przeglądarce: prosimy o trwały magazyn, żeby system nie sprzątał ich przy braku miejsca */
  try { navigator.storage && navigator.storage.persist && navigator.storage.persist(); } catch (e) { /* bez tej funkcji dane działają jak zwykle */ }
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {
    const mielSw = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.register('sw.js').catch(() => {});
    navigator.serviceWorker.addEventListener('controllerchange', () => { if (mielSw) pokazToast('Jest nowa wersja aplikacji — odśwież stronę, aby z niej skorzystać'); });
  }
}

function poMotywieUI() {
  const m = motywTeraz();
  $$('.przel [data-motyw]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.motyw === m)));
}

start();