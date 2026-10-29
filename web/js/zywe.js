// PMT Planer (web) — „żywy interfejs": interakcje, które wciągają. Moduł nie zna wnętrza aplikacji: dostaje uchwyty (k) i nasłuchuje sygnałów „pmt:*".
//   suwak kwoty z podglądem cieczy w dniach · kalendarz (lupa, fala, malowanie dni wolnych) · teatr trasy (▶, przewijanie osi, pojazd na mapie)
//   fiolki (bąbelki, chlupot) · paleta poleceń (Ctrl+K) · wycieczka po aplikacji · przesuwanie zakładek na telefonie
export function zainstalujZywe(k) {
  const { $, $$, doc, root, app, bento, fmt, dwa, hhmm, minuty, anim, iskry, pamiec, spokoj } = k;
  const S = () => k.stan();
  const slucha = (n, f) => doc.addEventListener('pmt:' + n, f);
  const el = (tag, kl, html) => { const e = doc.createElement(tag); if (kl) e.className = kl; if (html != null) e.innerHTML = html; return e; };
  const svgEl = (tag, kl, html) => { const e = doc.createElementNS('http://www.w3.org/2000/svg', tag); if (kl) e.setAttribute('class', kl); if (html != null) e.innerHTML = html; return e; };
  const ogr = (v, a, b) => Math.min(b, Math.max(a, v));
  const ik = (id, kl = 'ik') => `<svg class="${kl}" aria-hidden="true"><use href="#${id}"/></svg>`;
  const telefon = () => matchMedia('(max-width:899px)').matches;
  const widoczny = e => !!e && e.getClientRects().length > 0;
  const norm = s => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l');
  const zorza = () => k.zorza();
  const wibruj = ms => { try { navigator.vibrate && navigator.vibrate(ms); } catch (e) { /* bez wibracji */ } };
  /** Krótki błysk obręczy wokół kafla — „tu jesteś / to zrobiłem". */
  function blysk(cel) {
    if (!widoczny(cel)) return;
    const r = cel.getBoundingClientRect(), b = el('i', 'blysk'), prom = getComputedStyle(cel).borderRadius;
    b.style.cssText = `left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;border-radius:${prom}`; doc.body.appendChild(b);
    const a = b.animate([{ opacity: 0, scale: '.985' }, { opacity: 1, scale: '1', offset: .25 }, { opacity: 0, scale: '1.02' }], { duration: 900, easing: 'ease-out' });
    a.onfinish = () => b.remove(); setTimeout(() => b.remove(), 1300);
  }

  /* ============================================================ SUWAK KWOTY ============================================================ */
  /* Linia pod kwotą może być suwakiem: przeciągnięcie ustawia kwotę od minimum do maksimum dla wybranych dni, a w kalendarzu rośnie poziom cieczy.
     WYŁĄCZONY (decyzja właściciela: kwotę się wpisuje, bo to bezpieczniejsze — jeden przypadkowy ruch nie zmieni pieniędzy). Włącza go ta jedna stała. */
  const SUWAK_KWOTY = false;
  const tuner = el('div', 'tuner bez-maks', '<span class="tu-tor"><i class="tu-ciecz"></i><span class="tu-zn" aria-hidden="true"></span></span><span class="tu-kulka" aria-hidden="true"><i></i></span>');
  tuner.setAttribute('role', 'slider'); tuner.tabIndex = 0; tuner.id = 'tuner';
  tuner.setAttribute('aria-label', 'Kwota do rozliczenia: przeciągnij albo użyj strzałek');
  if (SUWAK_KWOTY) {
    const pole = $('.pole-kwota'); if (pole) pole.after(tuner);
    let ciagnie = false, ostTik = -1;
    const zakres = () => { const { M, MIN_KWOTA } = S(); return M && M.stan === 'plan' && M.maksymalna > MIN_KWOTA ? [MIN_KWOTA, Math.floor(M.maksymalna)] : null; };
    const rysuj = () => {
      const { M } = S(), z = zakres();
      tuner.classList.toggle('bez-maks', !z);
      if (!z) { tuner.style.setProperty('--f', '0'); return; }
      const f = ogr((M.kwota - z[0]) / (z[1] - z[0]), 0, 1);
      tuner.style.setProperty('--f', f.toFixed(4)); tuner.classList.toggle('ponad', M.kwota > z[1] + .004);
      tuner.setAttribute('aria-valuemin', String(z[0])); tuner.setAttribute('aria-valuemax', String(z[1]));
      tuner.setAttribute('aria-valuenow', String(Math.round(M.kwota))); tuner.setAttribute('aria-valuetext', `${fmt(M.kwota)} zł`);
    };
    const zX = x => {
      const z = zakres(); if (!z) return;
      const r = $('.tu-tor', tuner).getBoundingClientRect(), f = ogr((x - r.left) / r.width, 0, 1);
      const v = f >= .999 ? z[1] : Math.round(z[0] + f * (z[1] - z[0]));
      k.ustawKwote(v, false);
      const tik = Math.round(f * 20); if (tik !== ostTik) { ostTik = tik; if (ciagnie) wibruj(2); }
      const zo = zorza(); zo && zo.flara(.05 + .1 * f);
    };
    tuner.addEventListener('pointerdown', e => {
      if ((e.button || 0) > 0 || !zakres()) return;
      ciagnie = true; ostTik = -1; tuner.classList.add('ciagnie'); try { tuner.setPointerCapture(e.pointerId); } catch (x) { /* bez przechwycenia kursor nadal działa na linii */ }
      e.preventDefault(); tuner.focus({ preventScroll: true }); zX(e.clientX); const zo = zorza(); zo && zo.cieplo(.7);
    });
    tuner.addEventListener('pointermove', e => { if (ciagnie) zX(e.clientX); });
    const puszcz = () => { if (!ciagnie) return; ciagnie = false; tuner.classList.remove('ciagnie'); const { M } = S(); k.ustawKwote(M.kwota, true); };
    tuner.addEventListener('pointerup', puszcz); tuner.addEventListener('pointercancel', puszcz); tuner.addEventListener('lostpointercapture', puszcz);
    tuner.addEventListener('keydown', e => {
      const z = zakres(); if (!z) return; const { M } = S();
      const krok = (e.shiftKey ? 100 : 10), v = { ArrowRight: M.kwota + krok, ArrowUp: M.kwota + krok, ArrowLeft: M.kwota - krok, ArrowDown: M.kwota - krok, PageUp: M.kwota + 500, PageDown: M.kwota - 500, Home: z[0], End: z[1] }[e.key];
      if (v === undefined) return; e.preventDefault(); k.ustawKwote(ogr(Math.round(v), z[0], z[1]), true);
    });
    slucha('parametry', rysuj); slucha('kwota', rysuj); slucha('hero', rysuj);
    const wej = $('#kwota-in'); wej && wej.addEventListener('input', () => setTimeout(rysuj, 0));
  }

  /* ============================================================ KALENDARZ ============================================================ */
  const siatka = $('#siatka');
  {
    /* poziom cieczy w dniach roboczych (przed generowaniem) = kwota wobec maksimum; po generowaniu dni mają prawdziwe poziomy */
    let pierwszy = true;
    const podglad = () => {
      const { M } = S(); let f = 0, ponad = false;
      if (M && M.stan === 'plan' && M.maksymalna > 0 && M.kwota > 0) { f = ogr(M.kwota / M.maksymalna, 0, 1); ponad = M.kwota > M.maksymalna + .004; }
      if (pierwszy && f > 0) { pierwszy = false; siatka.style.setProperty('--podglad', '0'); requestAnimationFrame(() => requestAnimationFrame(() => siatka.style.setProperty('--podglad', f.toFixed(4)))); }
      else siatka.style.setProperty('--podglad', f.toFixed(4));
      siatka.classList.toggle('ponad', ponad);
    };
    slucha('kalendarz', podglad); slucha('parametry', podglad); slucha('kwota', podglad);

    /* lupa jak w doku systemu: dni pod kursorem rosną, sąsiednie trochę mniej */
    let rect = null, mx = 0, my = 0, raf = 0;
    const KOMORKI = '.dz[data-d]:not(.nd)';
    const zmierz = () => { rect = $$(KOMORKI, siatka).map(e => { const r = e.getBoundingClientRect(); return { e, x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width }; }); };
    const lupa = () => {
      raf = 0; if (!rect) return;
      for (const c of rect) {
        const d = Math.hypot(c.x - mx, c.y - my), s = 1 + .2 * Math.exp(-Math.pow(d / (c.w * 1.25), 2));
        c.e.style.scale = s > 1.004 ? s.toFixed(3) : ''; c.e.style.zIndex = s > 1.004 ? String(Math.round((s - 1) * 100)) : '';
      }
    };
    const zwin = () => { cancelAnimationFrame(raf); raf = 0; if (rect) for (const c of rect) { c.e.style.scale = ''; c.e.style.zIndex = ''; } rect = null; };
    siatka.addEventListener('pointerenter', e => { if (e.pointerType !== 'touch') zmierz(); });
    siatka.addEventListener('pointermove', e => { if (spokoj || e.pointerType === 'touch') return; if (!rect) zmierz(); mx = e.clientX; my = e.clientY; if (!raf) raf = requestAnimationFrame(lupa); }, { passive: true });
    siatka.addEventListener('pointerleave', zwin);
    slucha('kalendarz', () => { if (rect) zmierz(); });
    addEventListener('resize', () => { rect = null; });

    /* fala po wybraniu dnia: pierścień rozchodzi się po sąsiednich dniach */
    siatka.addEventListener('click', e => {
      const c = e.target.closest('button.dz'); if (!c) return;
      const r0 = c.getBoundingClientRect(), x0 = r0.left + r0.width / 2, y0 = r0.top + r0.height / 2;
      for (const b of $$(KOMORKI, siatka)) {
        if (b === c) continue; const r = b.getBoundingClientRect(), d = Math.hypot(r.left + r.width / 2 - x0, r.top + r.height / 2 - y0);
        if (d > r0.width * 6) continue;
        anim(b, [{ scale: '1' }, { scale: String(1 + .14 * Math.exp(-d / (r0.width * 2.4))) }, { scale: '1' }], { duration: 640, delay: d * .9, easing: 'ease-in-out', fill: 'none' });
      }
    });

    /* malowanie dni wolnych: przeciągnij po kilku dniach (mysz / rysik); dotyk zostaje przy dotknięciu pojedynczego dnia */
    let mal = null, stlum = false;
    const KOM_PLAN = 'button.dz.przelacz, button.dz.urlop';
    const pod = (x, y) => { const e = doc.elementFromPoint(x, y); return e && e.closest ? e.closest(KOM_PLAN) : null; };
    const stos = (c, wolne) => { c.classList.remove('maluj-w', 'maluj-r'); c.classList.add(wolne ? 'maluj-w' : 'maluj-r'); };
    siatka.addEventListener('pointerdown', e => {
      if (e.pointerType === 'touch' || (e.button || 0) > 0 || S().M.stan !== 'plan') return;
      const c = e.target.closest(KOM_PLAN); if (!c) return;
      mal = { d0: Number(c.dataset.d), wolne: !c.classList.contains('urlop'), dni: new Set(), ruszyl: false, c0: c };
    });
    doc.addEventListener('pointermove', e => {
      if (!mal) return;
      const c = pod(e.clientX, e.clientY);
      if (!mal.ruszyl) { if (!c || Number(c.dataset.d) === mal.d0) return; mal.ruszyl = true; mal.dni.add(mal.d0); stos(mal.c0, mal.wolne); siatka.classList.add('maluje'); }
      if (c) { const d = Number(c.dataset.d); if (!mal.dni.has(d)) { mal.dni.add(d); stos(c, mal.wolne); falaDo(c); } }
    });
    const falaDo = c => { const r = c.getBoundingClientRect(); iskry(r.left + r.width / 2, r.top + r.height / 2, 4); };
    const koniecMal = anuluj => {
      if (!mal) return; const m = mal; mal = null; siatka.classList.remove('maluje');
      $$('.maluj-w,.maluj-r', siatka).forEach(c => c.classList.remove('maluj-w', 'maluj-r'));
      if (!m.ruszyl) return;
      stlum = true; setTimeout(() => { stlum = false; }, 0);
      if (!anuluj) k.ustawWolne([...m.dni], m.wolne);
    };
    doc.addEventListener('pointerup', () => koniecMal(false)); doc.addEventListener('pointercancel', () => koniecMal(true));
    siatka.addEventListener('click', e => { if (stlum) { e.stopImmediatePropagation(); e.preventDefault(); stlum = false; } }, true);
  }

  /* ============================================================ TEATR TRASY ============================================================ */
  /* ▶ odtwarza dzień: pojazd jedzie po mapie, zegar tyka, kwota rośnie. Przesuwanie kursora po osi (albo palcem) przewija dzień jak film. */
  const dzTresc = $('#dzien-tresc');
  const graj = el('button', 'okr graj', `${ik('i-graj', 'ik i-gr')}${ik('i-pauza', 'ik i-pa')}`);
  graj.type = 'button'; graj.id = 'e-graj'; graj.setAttribute('aria-label', 'Odtwórz dzień na mapie'); graj.title = 'Odtwórz dzień na mapie';
  { const nav = $('.de-nav'); nav && nav.prepend(graj); }
  const TE = { aktywny: false, gra: false, tau: 0, ost: 0, raf: 0, wygas: 0, kwota: false, dane: null };
  const CZAS_FILMU = 11;                       // sekundy dla całego dnia; postoje i jazda dostają proporcjonalne części
  function przygotujTeatr() {
    cancelAnimationFrame(TE.raf); clearTimeout(TE.wygas); TE.gra = false; TE.aktywny = false; TE.dane = null; TE.tau = 0;
    graj.classList.remove('gra'); graj.setAttribute('aria-label', 'Odtwórz dzień na mapie'); graj.title = 'Odtwórz dzień na mapie';
    const { M, wybrany } = S();
    const ok = !!(M && M.stan === 'gotowe' && M.trasy[wybrany]);
    graj.disabled = !ok;
    if (!ok) { duchTrasy(); return; }
    const tr = M.trasy[wybrany], odc = k.odcinkiDnia(tr), n = odc.length;
    const przyj = odc.map(o => o.przyj ? minuty(o.przyj) : 0), odj = odc.map(o => o.odj ? minuty(o.odj) : 0);
    const kmS = [], zlS = [], cumKm = [0], cumZl = [0];
    for (let j = 0; j < n - 1; j++) { kmS.push(odc[j + 1].km || 0); zlS.push(odc[j + 1].zl || 0); cumKm.push(cumKm[j] + kmS[j]); cumZl.push(cumZl[j] + zlS[j]); }
    /* oś czasu filmu: jazda i postoje z wagami (krótkie postoje i tak widać) */
    const maxKm = Math.max(...kmS, 1), kawalki = []; let suma = 0;
    for (let j = 0; j < n - 1; j++) {
      kawalki.push({ typ: 'j', j, d: .5 + 1.5 * Math.pow(kmS[j] / maxKm, .6), t0: odj[j], t1: przyj[j + 1] });
      if (j + 1 < n - 1) kawalki.push({ typ: 'p', j: j + 1, d: .42, t0: przyj[j + 1], t1: odj[j + 1] });
    }
    for (const c of kawalki) suma += c.d; const skala = ogr(CZAS_FILMU / suma, .6, 1.3); let t = 0;
    for (const c of kawalki) { c.d *= skala; c.s0 = t; t += c.d; c.s1 = t; }
    const D = { tr, odc, n, przyj, odj, kmS, zlS, cumKm, cumZl, kawalki, razem: t, A: odj[0], Z: przyj[n - 1] };
    /* mapa: długości łuku do kolejnych węzłów */
    const svg = $('.mapka svg', dzTresc), sciezka = svg && $('.tr-linia', svg);
    if (sciezka) {
      try {
        const L = sciezka.getTotalLength(), N = n - 1;
        const pkt = []; $$('.tr-pkt', svg).forEach(g => { const c = $('circle:not(.tr-halo)', g), i = Number(g.style.getPropertyValue('--p')); pkt[i] = { x: Number(c.getAttribute('cx')), y: Number(c.getAttribute('cy')) }; });
        if (pkt.length === N && pkt.every(Boolean)) {
          const PR = 720, P = []; for (let i = 0; i <= PR; i++) P.push(sciezka.getPointAtLength(L * i / PR));
          const dl = [0]; let od = 0;
          for (let j = 1; j < N; j++) { let naj = 1e18, bi = od; for (let i = od; i <= PR; i++) { const d = (P[i].x - pkt[j].x) ** 2 + (P[i].y - pkt[j].y) ** 2; if (d < naj) { naj = d; bi = i; } } dl.push(L * bi / PR); od = Math.min(PR, bi + 1); }
          dl.push(L);
          const poj = svgEl('g', 'tr-poj', '<circle class="tr-poj-aura" r="8"/><circle class="tr-poj-rdz" r="3.1"/><path class="tr-poj-strz" d="M-3.4 -2.4 L4 0 L-3.4 2.4 L-1.9 0 Z"/>');
          const slad = svgEl('path', 'tr-slad'); slad.setAttribute('d', sciezka.getAttribute('d')); slad.setAttribute('pathLength', '1');
          sciezka.after(slad); svg.appendChild(poj);
          D.mapa = { svg, sciezka, L, dl, poj, slad, wezly: $$('.tr-pkt', svg).sort((a, b) => Number(a.style.getPropertyValue('--p')) - Number(b.style.getPropertyValue('--p'))) };
        }
      } catch (e) { D.mapa = null; }
    }
    if (D.mapa) { const fig = D.mapa.svg.parentNode; D.chip = el('span', 'mapa-chip', '<b></b><i></i>'); fig.appendChild(D.chip); D.chipKlucz = ''; }
    const pod = $('.podroz', dzTresc);
    if (pod) { D.pod = pod; D.pr = $$('.pr', pod); D.poj = el('span', 'pr-poj', '<i></i><b class="num"></b>'); pod.appendChild(D.poj); }
    const ws = $('.wstega', dzTresc);
    if (ws) { D.ws = ws; D.wa = Number(ws.dataset.a), D.wz = Number(ws.dataset.z); D.glowica = el('span', 'w-glowica', '<b class="num"></b>'); ws.appendChild(D.glowica); D.wiersze = $$('.odcinki tbody tr', dzTresc); }
    D.kw = $('.de-kwota', dzTresc); D.pk = $('.de-podkwota', dzTresc);
    D.kwOrg = D.kw ? D.kw.firstChild.nodeValue : ''; D.pkOrg = D.pk ? D.pk.innerHTML : '';
    TE.dane = D;
  }
  /** stan filmu w sekundzie tau → {f, t, zl, km, post, j, u} */
  function stanFilmu(tau) {
    const D = TE.dane; tau = ogr(tau, 0, D.razem);
    const c = D.kawalki.find(x => tau <= x.s1) || D.kawalki[D.kawalki.length - 1], u = c.s1 > c.s0 ? ogr((tau - c.s0) / (c.s1 - c.s0), 0, 1) : 1;
    if (c.typ === 'j') return { f: c.j + u, j: c.j, u, post: false, t: c.t0 + (c.t1 - c.t0) * u, zl: D.cumZl[c.j] + D.zlS[c.j] * u, km: D.cumKm[c.j] + D.kmS[c.j] * u };
    return { f: c.j, j: c.j, u: 0, post: true, t: c.t0 + (c.t1 - c.t0) * u, zl: D.cumZl[c.j], km: D.cumKm[c.j] };
  }
  const tauZFilmu = (f) => { const D = TE.dane, j = ogr(Math.floor(f), 0, D.n - 2), u = ogr(f - j, 0, 1), c = D.kawalki.find(x => x.typ === 'j' && x.j === j); return c.s0 + (c.s1 - c.s0) * u; };
  const tauZCzasu = (t) => { const D = TE.dane; t = ogr(t, D.A, D.Z); const c = D.kawalki.find(x => t <= x.t1) || D.kawalki[D.kawalki.length - 1]; return c.s0 + (c.s1 - c.s0) * (c.t1 > c.t0 ? ogr((t - c.t0) / (c.t1 - c.t0), 0, 1) : 1); };
  function centraPodrozy() {
    const D = TE.dane; if (!D.pod) return null; const r0 = D.pod.getBoundingClientRect();
    const w = $$('.pr-wezel', D.pod); if (w.length < 2) return null;
    return { x: w.map(e => { const r = e.getBoundingClientRect(); return r.left + r.width / 2 - r0.left; }), y: (() => { const r = w[0].getBoundingClientRect(); return r.top + r.height / 2 - r0.top; })(), r0 };
  }
  function rysujFilm(opcje = {}) {
    const D = TE.dane; if (!D) return; const s = stanFilmu(TE.tau);
    /* mapa */
    if (D.mapa) {
      const m = D.mapa, a = m.dl[s.post ? s.j : s.j] ?? 0, b = m.dl[s.post ? s.j : s.j + 1] ?? m.L, arc = s.post ? m.dl[s.j] : a + (b - a) * s.u;
      const p = m.sciezka.getPointAtLength(ogr(arc, 0, m.L)), p1 = m.sciezka.getPointAtLength(ogr(arc + .7, 0, m.L)), p0 = m.sciezka.getPointAtLength(ogr(arc - .7, 0, m.L));
      m.poj.setAttribute('transform', `translate(${p.x.toFixed(2)} ${p.y.toFixed(2)}) rotate(${(Math.atan2(p1.y - p0.y, p1.x - p0.x) * 180 / Math.PI).toFixed(1)})`);
      m.slad.style.strokeDasharray = `${(arc / m.L).toFixed(4)} 2`;
      /* kamera: po starcie filmu mapa płynnie przybliża się do pojazdu (1× → 1,5×), na końcu wraca */
      { const fig = D.chip ? D.chip.parentNode : null; if (fig) { const rf0 = fig.getBoundingClientRect(), ctm0 = m.svg.getScreenCTM();
          if (ctm0 && rf0.width) { const vx = (ctm0.a * p.x + ctm0.c * p.y + ctm0.e - rf0.left) / rf0.width, vy = (ctm0.b * p.x + ctm0.d * p.y + ctm0.f - rf0.top) / rf0.height, cam = 1 + .5 * ogr(TE.tau / 1.6, 0, 1);
            fig.style.setProperty('--cx', (vx * 100).toFixed(1) + '%'); fig.style.setProperty('--cy', (vy * 100).toFixed(1) + '%'); fig.style.setProperty('--cs', cam.toFixed(3)); } } }
      if (D.chip) {
        /* pływająca etykieta przy pojeździe: dokąd jedzie i ile jeszcze, a na postoju — gdzie stoi i do której godziny */
        const nast = D.odc[s.j + 1], tu = D.odc[s.j];
        const g = s.post ? (tu && tu.m || '') : '→ ' + (nast && nast.m || ''), d = s.post ? `${tu && tu.przyj || ''}–${tu && tu.odj || ''}` : `${fmt(D.kmS[s.j] * (1 - s.u), 1)} km`;
        const klucz = g + '|' + d + '|' + s.post;
        if (klucz !== D.chipKlucz) { D.chipKlucz = klucz; $('b', D.chip).textContent = g; $('i', D.chip).textContent = d; D.chip.classList.toggle('post', s.post); D.chipW = D.chip.offsetWidth; D.chipH = D.chip.offsetHeight; }
        const ctm = m.svg.getScreenCTM(), rf = D.chip.parentNode.getBoundingClientRect();
        if (ctm && rf.width) {
          const px = ctm.a * p.x + ctm.c * p.y + ctm.e - rf.left, py = ctm.b * p.x + ctm.d * p.y + ctm.f - rf.top, w = D.chipW || 80, h = D.chipH || 24;
          let x = px + 13, y = py - h - 11; if (x + w > rf.width - 3) x = px - w - 13; if (y < 3) y = py + 13;
          D.chip.style.translate = `${ogr(x, 3, Math.max(3, rf.width - w - 3)).toFixed(1)}px ${ogr(y, 3, Math.max(3, rf.height - h - 3)).toFixed(1)}px`;
        }
      }
      m.wezly.forEach((g, i) => { g.classList.toggle('minal', s.f >= i - .02); g.classList.toggle('tu', s.post && s.j % m.wezly.length === i); });
      const dom = m.wezly[0]; if (dom) dom.classList.toggle('minal', true);
    }
    /* oś podróży */
    if (D.pod && D.poj) {
      if (!D.centra) D.centra = centraPodrozy();
      const c = D.centra;
      if (c) {
        const i = ogr(Math.floor(s.f), 0, c.x.length - 2), u = s.f - i, x = c.x[i] + (c.x[i + 1] - c.x[i]) * ogr(u, 0, 1);
        D.poj.style.translate = `${x.toFixed(1)}px ${c.y.toFixed(1)}px`; $('b', D.poj).textContent = hhmm(Math.round(s.t));
        D.poj.classList.toggle('post', s.post);
      }
      D.pr.forEach((li, i) => { li.classList.toggle('minal', s.f >= i - .02); li.classList.toggle('tu', s.post && s.j === i); const sg = $('.pr-odc i', li); if (sg) sg.style.transform = `scaleX(${ogr(s.f - i, 0, 1).toFixed(3)})`; });
    }
    /* wstęga i tabela (widoczne w widoku rozwiniętym) */
    if (D.ws && D.glowica) { D.glowica.style.left = `${((s.t - D.wa) / (D.wz - D.wa) * 100).toFixed(3)}%`; $('b', D.glowica).textContent = hhmm(Math.round(s.t)); }
    if (D.wiersze) D.wiersze.forEach((tr, i) => tr.classList.toggle('teraz', i === (s.post ? s.j : s.j + 1)));
    /* liczniki: kwota dnia rośnie w trakcie filmu (przy samym przeglądaniu osi kwota stoi) */
    if (opcje.kwota && D.kw) {
      D.kw.firstChild.nodeValue = fmt(s.zl);
      if (D.pk) D.pk.textContent = `kwota dnia · ${fmt(s.km, 1)} km`;
    }
  }
  function wlaczFilm(kwota) {
    const D = TE.dane; if (!D) return; clearTimeout(TE.wygas);
    if (!TE.aktywny) { TE.aktywny = true; D.centra = null; $('.mapka', dzTresc) && $('.mapka', dzTresc).classList.add('gra'); D.pod && D.pod.classList.add('gra'); D.ws && D.ws.classList.add('gra'); }
    if (kwota && !TE.kwota) { TE.kwota = true; D.kw && D.kw.classList.add('liczy'); }
  }
  function wylaczFilm() {
    const D = TE.dane; cancelAnimationFrame(TE.raf); clearTimeout(TE.wygas); TE.gra = false; TE.aktywny = false; TE.kwota = false;
    graj.classList.remove('gra'); graj.setAttribute('aria-label', 'Odtwórz dzień na mapie'); graj.title = 'Odtwórz dzień na mapie';
    if (!D) return;
    const mapka = $('.mapka', dzTresc); mapka && mapka.classList.remove('gra'); D.pod && D.pod.classList.remove('gra'); D.ws && D.ws.classList.remove('gra');
    if (D.kw) { D.kw.firstChild.nodeValue = D.kwOrg; D.kw.classList.remove('liczy'); } if (D.pk) D.pk.innerHTML = D.pkOrg;
    D.pr && D.pr.forEach(li => { li.classList.remove('minal', 'tu'); const sg = $('.pr-odc i', li); if (sg) sg.style.transform = ''; });
    D.mapa && D.mapa.wezly.forEach(g => g.classList.remove('minal', 'tu'));
    D.wiersze && D.wiersze.forEach(tr => tr.classList.remove('teraz'));
  }
  function krokFilmu() {
    if (!TE.gra) return; const D = TE.dane; if (!D) return;
    const t = k.czas(), dt = Math.min(.5, (t - TE.ost) / 1000); TE.ost = t; TE.tau += dt;
    if (TE.tau >= D.razem) { TE.tau = D.razem; rysujFilm({ kwota: true }); koniecFilmu(); return; }
    rysujFilm({ kwota: true }); TE.raf = requestAnimationFrame(krokFilmu);
  }
  function koniecFilmu() {
    TE.gra = false; graj.classList.remove('gra'); graj.setAttribute('aria-label', 'Odtwórz dzień jeszcze raz'); graj.title = 'Odtwórz dzień jeszcze raz';
    const D = TE.dane; if (D && D.kw) { D.kw.firstChild.nodeValue = fmt(D.tr.suma); }
    const zo = zorza(); zo && zo.flara(.5); const { M, wybrany } = S(); if (D && D.mapa) { const p = D.mapa.poj; blysk($('.mapka', dzTresc)); }
    TE.wygas = setTimeout(wylaczFilm, 2600);
  }
  function startFilmu() {
    if (!TE.dane) przygotujTeatr(); const D = TE.dane; if (!D) return;
    wlaczFilm(true);
    if (TE.tau >= D.razem - .05) TE.tau = 0;
    TE.gra = true; TE.ost = k.czas(); graj.classList.add('gra'); graj.setAttribute('aria-label', 'Wstrzymaj'); graj.title = 'Wstrzymaj';
    const zo = zorza(); zo && zo.flara(.25);
    rysujFilm({ kwota: true }); cancelAnimationFrame(TE.raf); TE.raf = requestAnimationFrame(krokFilmu);
  }
  function pauzaFilmu() { TE.gra = false; cancelAnimationFrame(TE.raf); graj.classList.remove('gra'); graj.setAttribute('aria-label', 'Wznów'); graj.title = 'Wznów'; clearTimeout(TE.wygas); TE.wygas = setTimeout(wylaczFilm, 6000); }
  graj.addEventListener('click', () => { if (graj.disabled) return; if (TE.gra) pauzaFilmu(); else startFilmu(); });
  slucha('dzien', () => { wylaczFilm(); przygotujTeatr(); });
  addEventListener('resize', () => { if (TE.dane) TE.dane.centra = null; });
  /* przewijanie: kursor po osi podróży albo po wstędze */
  {
    let trzyma = false, mysz = true;
    const poOsi = (x) => {
      const D = TE.dane; if (!D || !D.pod) return null; const w = $$('.pr-wezel', D.pod).map(e => { const r = e.getBoundingClientRect(); return r.left + r.width / 2; });
      if (w.length < 2) return null; if (x <= w[0]) return 0; if (x >= w[w.length - 1]) return w.length - 1;
      let i = 0; while (i < w.length - 2 && x > w[i + 1]) i++; return i + (x - w[i]) / (w[i + 1] - w[i]);
    };
    const przewin = (tau, kwota) => {
      const D = TE.dane; if (!D) return; if (TE.gra) pauzaFilmu();
      wlaczFilm(kwota); TE.tau = ogr(tau, 0, D.razem); rysujFilm({ kwota });
    };
    const odlicz = ms => { clearTimeout(TE.wygas); TE.wygas = setTimeout(wylaczFilm, ms); };
    dzTresc.addEventListener('pointermove', e => {
      const D = TE.dane; if (!D || TE.gra) return;
      const nad = e.target.closest && e.target.closest('.podroz, .w-tor'); if (!nad) return;
      if (e.pointerType !== 'mouse' && !trzyma) return;
      if (nad.classList.contains('podroz')) { const f = poOsi(e.clientX); if (f != null) przewin(tauZFilmu(f), trzyma); }
      else { const r = nad.getBoundingClientRect(); const t = D.wa + (D.wz - D.wa) * ogr((e.clientX - r.left) / r.width, 0, 1); przewin(tauZCzasu(t), trzyma); }
    });
    dzTresc.addEventListener('pointerleave', () => { if (!TE.gra && TE.aktywny && !trzyma) odlicz(700); });
    dzTresc.addEventListener('pointerdown', e => {
      const nad = e.target.closest && e.target.closest('.podroz, .w-tor'); if (!nad || (e.button || 0) > 0) return; trzyma = true;
      try { nad.setPointerCapture(e.pointerId); } catch (x) { /* bez przechwycenia przewijanie działa w obrębie osi */ }
      const D = TE.dane; if (!D) return; clearTimeout(TE.wygas);
      if (nad.classList.contains('podroz')) { const f = poOsi(e.clientX); if (f != null) przewin(tauZFilmu(f), true); }
      else { const r = nad.getBoundingClientRect(); przewin(tauZCzasu(D.wa + (D.wz - D.wa) * ogr((e.clientX - r.left) / r.width, 0, 1)), true); }
    });
    const puszczono = () => { if (!trzyma) return; trzyma = false; if (TE.aktywny && !TE.gra) odlicz(2400); };
    doc.addEventListener('pointerup', puszczono); doc.addEventListener('pointercancel', puszczono);
    /* węzeł na osi i na mapie świecą razem */
    dzTresc.addEventListener('pointerover', e => {
      const D = TE.dane; if (!D) return; let i = -1;
      const li = e.target.closest && e.target.closest('.pr'); if (li && D.pr) i = D.pr.indexOf(li);
      const g = e.target.closest && e.target.closest('.tr-pkt'); if (g && D.mapa) i = D.mapa.wezly.indexOf(g);
      $$('.zwrot', dzTresc).forEach(x => x.classList.remove('zwrot'));
      if (i >= 0) { D.pr && D.pr[i] && D.pr[i].classList.add('zwrot'); D.mapa && D.mapa.wezly[i] && D.mapa.wezly[i].classList.add('zwrot'); }
    });
    dzTresc.addEventListener('pointerleave', () => $$('.zwrot', dzTresc).forEach(x => x.classList.remove('zwrot')));
    /* klik w mapę = odtwórz / wstrzymaj */
    dzTresc.addEventListener('click', e => { if (e.target.closest && e.target.closest('.mapka svg') && !graj.disabled) { if (TE.gra) pauzaFilmu(); else startFilmu(); } });
  }
  /* pusty stan: duch trasy — pokazuje, co tu będzie */
  function duchTrasy() {
    const p = $('.pusty-stan', dzTresc); if (!p || $('.duch', p)) return;
    const sc = 'M38 84 C52 42 92 28 120 44 S170 62 160 94 S96 110 70 98 S30 92 38 84';
    p.insertAdjacentHTML('afterbegin', `<svg class="duch" viewBox="0 0 200 124" aria-hidden="true"><circle class="duch-krag" cx="38" cy="84" r="26"/><circle class="duch-krag" cx="38" cy="84" r="54"/>
      <path class="duch-baza" d="${sc}"/><path class="duch-linia" pathLength="1" d="${sc}"/>
      ${[[64, 50], [112, 36], [150, 60], [158, 94], [108, 106], [66, 98]].map(([x, y], i) => `<circle class="duch-wezel" style="--p:${i}" cx="${x}" cy="${y}" r="3.4"/>`).join('')}
      <circle class="duch-dom" cx="38" cy="84" r="5"/><circle class="duch-poj" r="3.4"><animateMotion dur="7.5s" repeatCount="indefinite" path="${sc}"/></circle></svg>`);
  }

  /* ============================================================ KONTROLA ============================================================ */
  /* najechanie na punkt kontroli pokazuje, czego dotyczy: dni z trasą, najdroższy dzień, najpełniejsze polecenie */
  {
    const lista = $('#ko-lista');
    const cele = i => {
      const { M } = S(); if (!M || M.stan !== 'gotowe') return [];
      if (i === 0) return $$('#siatka .dz.trasa');
      if (i === 1) { let b = M.dniT[0]; for (const d of M.dniT) if (M.trasy[d].suma > M.trasy[b].suma) b = d; const c = $(`#siatka .dz.trasa[data-d="${b}"]`); return c ? [c] : []; }
      if (i === 2) { let b = M.polecenia[0]; for (const p of M.polecenia) if (p.kw > b.kw) b = p; const f = $(`.fiolka[data-pol="${b.nr}"]`); return f ? [f] : []; }
      return [];
    };
    const zgas = () => $$('#siatka .swiec, #fiolki .swiec').forEach(e => e.classList.remove('swiec'));
    lista.addEventListener('pointerover', e => { const li = e.target.closest('li'); if (!li) return; zgas(); cele([...lista.children].indexOf(li)).forEach(c => c.classList.add('swiec')); });
    lista.addEventListener('pointerleave', zgas);
  }

  /* ============================================================ FIOLKI ============================================================ */
  {
    const fio = $('#fiolki');
    /* puste probówki pokazujemy tylko, gdy kafel ma na nie miejsce (nic nie nachodzi na tekst i legendę) */
    const miesci = () => {
      const g = $('.duch-fiolki', fio); if (!g) return; g.hidden = false;
      const r = fio.getBoundingClientRect(), z = [...g.parentElement.children].map(c => c.getBoundingClientRect());
      g.hidden = Math.min(...z.map(q => q.top)) < r.top - 1 || Math.max(...z.map(q => q.bottom)) > r.bottom + 1;
    };
    const duchFiolek = () => {
      const p = $('.pusty-stan', fio); if (!p) return;
      if (!$('.duch-fiolki', p)) p.insertAdjacentHTML('afterbegin', `<div class="duch-fiolki" aria-hidden="true">${[.62, .8, .45, .7, 1].map((h, i) => `<i style="--s:${i};--h:${h}"><b></b></i>`).join('')}</div>`);
      miesci(); requestAnimationFrame(miesci);
    };
    try { new ResizeObserver(() => miesci()).observe(fio); } catch (e) { addEventListener('resize', () => requestAnimationFrame(miesci)); }      // przy każdej zmianie rozmiaru kafla, jeszcze przed namalowaniem
    if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(() => miesci()).catch(() => {});
    const babelki = () => {
      const { M } = S(); if (!M || M.stan !== 'gotowe') { duchFiolek(); return; }
      $$('.f-ciecz', fio).forEach((c, i) => { if ($('.babel', c)) return; for (let b = 0; b < 4; b++) c.appendChild(el('i', 'babel')).style.cssText = `--x:${18 + ((b * 29 + i * 13) % 58)}%;--r:${2 + (b + i) % 3}px;--t:${3.2 + ((b * 7 + i * 5) % 9) / 3}s;--o:${-((b * 17 + i * 11) % 30) / 10}s`; });
    };
    slucha('fiolki', babelki);
    if ($('.f-ciecz', fio)) babelki();      // fiolki narysowane, zanim moduł się załadował (sygnał już przeminął) — bąbelki dokładamy od razu
    /* chlupot: ruch kursora po fiolkach kołysze probówki, a ciecz opóźnia się za szkłem (dwie sprężyny) */
    const F = new Map(); let raf = 0, ost = 0;
    const krok = t => {
      const dt = Math.min(.04, (t - ost) / 1000 || .016); ost = t; let zyje = false;
      for (const [f, s] of F) {
        s.va += (-70 * s.a - 5.5 * s.va) * dt; s.a += s.va * dt;
        s.vb += (-38 * (s.b + s.a * 1.7) - 3.2 * s.vb) * dt; s.b += s.vb * dt;
        if (Math.abs(s.a) + Math.abs(s.va) + Math.abs(s.b) + Math.abs(s.vb) > .02) { zyje = true; f.style.rotate = `${s.a.toFixed(2)}deg`; f.style.setProperty('--sl', s.b.toFixed(2)); }
        else { f.style.rotate = ''; f.style.removeProperty('--sl'); F.delete(f); }
      }
      raf = zyje ? requestAnimationFrame(krok) : 0;
    };
    fio.addEventListener('pointermove', e => {
      if (spokoj || e.pointerType === 'touch' || !e.movementX) return;      // chlupot probówek za kursorem — tylko w pełnym ruchu
      for (const f of $$('.fiolka', fio)) {
        const r = f.getBoundingClientRect(), d = Math.abs(e.clientX - (r.left + r.width / 2));
        if (d > r.width * 1.4 || e.clientY < r.top - 20 || e.clientY > r.bottom + 20) continue;
        let s = F.get(f); if (!s) { s = { a: 0, va: 0, b: 0, vb: 0 }; F.set(f, s); }
        s.va = ogr(s.va + e.movementX * .55 * (1 - d / (r.width * 1.4)), -90, 90);
      }
      if (!raf) { ost = performance.now(); raf = requestAnimationFrame(krok); }
    }, { passive: true });
  }

  /* ============================================================ PALETA POLECEŃ ============================================================ */
  const paleta = el('div', 'paleta-tlo', `<div class="paleta szklo dym" role="dialog" aria-modal="true" aria-label="Szukaj polecenia"><div class="pod" aria-hidden="true"></div>
    <div class="w"><label class="pal-szukaj">${ik('i-szukaj')}<input id="pal-in" type="text" role="combobox" aria-expanded="true" aria-controls="pal-lista" aria-autocomplete="list" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Co chcesz zrobić? np. luty, 14, motyw"></label>
    <ul class="pal-lista" id="pal-lista" role="listbox"><span class="pal-wyb" aria-hidden="true"></span></ul>
    <p class="pal-pod" aria-hidden="true"><kbd>↑</kbd><kbd>↓</kbd> wybór <kbd>Enter</kbd> uruchom <kbd>Esc</kbd> zamknij</p></div></div>`);
  paleta.hidden = true; doc.body.appendChild(paleta);
  const palIn = $('#pal-in', paleta), palLista = $('#pal-lista', paleta), palWyb = $('.pal-wyb', paleta);
  let palOtw = false, palWyniki = [], palIdx = 0, palFokus = null;
  /** Na telefonie „przejdź do” przełącza zakładkę, na komputerze błyska kafel (wszystkie są na ekranie). */
  const idz = (kafel, tab) => { if (telefon()) k.ustawZakladke(tab); setTimeout(() => blysk($(kafel)), telefon() ? 520 : 80); };
  const polecenia = (q) => {
    const { M, PROFIL, PLAN, MIN_KWOTA } = S(); const plan = M && M.stan === 'plan', gotowe = M && M.stan === 'gotowe', L = [];
    const dodaj = (tytul, opis, ikona, slowa, f, warunek = true, bonus = 0) => { if (warunek) L.push({ tytul, opis, ikona, bonus, h: norm(`${tytul} ${opis || ''} ${slowa || ''}`), f }); };
    const et = M ? k.etapMiesiaca() : 'ustaw';
    dodaj('Generuj dokumenty', 'Zrobię je na tym urządzeniu', 'i-pioro', 'wygeneruj delegacje start', () => k.klikGlowny(), plan && !!PROFIL);
    dodaj('Podpisz dokumenty', 'Profil Zaufany, krok po kroku', 'i-pioro', 'podpis profil zaufany pdf', () => k.arkuszPodpis(), gotowe && et !== 'wyslane');
    dodaj('Wyślij do Kierownika regionu', 'Gdy wszystko podpisane', 'i-nawi', 'wysylka mail poczta', () => k.klikGlowny(), gotowe && et === 'wyslij');
    dodaj('Odtwórz trasę dnia', 'Pojazd przejedzie cały dzień na mapie', 'i-graj', 'film pokaz mapa jazda play', () => { idz('#kE', 'miesiac'); setTimeout(startFilmu, telefon() ? 700 : 250); }, gotowe && !graj.disabled);
    dodaj('Dziś — plan wizyt', 'Lista sklepów na dziś', 'i-cel', 'dzis dzisiaj sklepy nawiguj', () => idz('#kD', 'dzis'));
    dodaj('Kalendarz miesiąca', 'Dni, urlop, poziom kwoty', 'i-kal', 'dni miesiac wolne urlop', () => idz('#kC', 'miesiac'));
    dodaj('Dokumenty i limity', 'Probówki poleceń wobec limitu', 'i-dok', 'fiolki polecenia limit podpisy', () => idz('#kF', 'dokumenty'));
    dodaj('Następny miesiąc', '', 'i-prawo', 'dalej miesiac', () => $('#m-dalej').click());
    dodaj('Poprzedni miesiąc', '', 'i-lewo', 'wstecz miesiac', () => $('#m-wstecz').click());
    dodaj('Przegląd roku', 'Wszystkie miesiące na jednym ekranie', 'i-kal', 'rok miesiace lista', () => k.arkuszRok(M ? M.rok : new Date().getFullYear()));
    if (M) for (let m = 1; m <= 12; m++) if (m !== M.mies) dodaj(`Przejdź do miesiąca: ${k.cap(k.MIES[m - 1])} ${M.rok}`, '', 'i-kal', `${k.MIES[m - 1]} ${M.rok}`, () => k.przeladujMiesiac(M.rok, m));
    dodaj('Plan wizyt', PLAN ? 'Zmień lub wczytaj nową listę sklepów' : 'Wczytaj listę sklepów z Excela', 'i-cel', 'sklepy lista excel csv', () => k.arkuszPlan());
    dodaj('Moje dane', 'Imię, PESEL, adres', 'i-pioro', 'profil dane adres pesel', () => k.otworzMojeDane(false));
    dodaj('Zmień hasło', '', 'i-klucz', 'haslo konto', () => k.arkuszZmianyHasla(false));
    dodaj(`Przełącz motyw: ${k.motywTeraz() === 'light' ? 'Noc' : 'Dzień'}`, '', k.motywTeraz() === 'light' ? 'i-ksiezyc' : 'i-slonce', 'motyw jasny ciemny dzien noc styl', () => k.ustawMotyw(k.motywTeraz() === 'light' ? 'dark' : 'light', $('#motyw')));
    dodaj('Napisz uwagę', 'Zgłoś problem albo pomysł (z danymi technicznymi)', 'i-info', 'uwaga blad problem zgloszenie pomysl opinia', () => k.pomoc.otworzUwagi());
    if (!k.pomoc.czyZainstalowana()) dodaj('Zainstaluj na telefonie', 'Ikona na ekranie głównym, kod QR', 'i-pobierz', 'instalacja telefon pobierz aplikacja qr iphone android ios', () => k.pomoc.otworzInstalacje());
    dodaj('Pokaż wycieczkę po aplikacji', 'Kilka kroków: gdzie co jest', 'i-info', 'pomoc wprowadzenie tour', () => setTimeout(() => wycieczka.start(true), 260));
    if (!(S().M && S().M.demo) && k.przykladDostepny()) dodaj('Pokaż przykładowy miesiąc', 'Zobacz, jak wygląda gotowy miesiąc (dane przykładowe)', 'i-oko', 'przyklad przykład demo pokaz', () => k.pokazPrzyklad());
    dodaj('Wyloguj', '', 'i-wyjdz', 'wyjdz konto', () => k.wyloguj());
    /* polecenia zależne od wpisanego tekstu: dzień miesiąca albo kwota */
    const t = norm(q).trim();
    if (M && /^\d{1,2}$/.test(t)) {
      const d = Number(t);
      if (gotowe && M.trasy[d]) dodaj(`Pokaż trasę z dnia ${d} ${k.MIES_D[M.mies - 1]}`, `${fmt(M.trasy[d].suma)} zł · ${fmt(M.trasy[d].km, 1)} km`, 'i-cel', t, () => { k.wybierzDzien(d); idz('#kE', 'miesiac'); }, true, 100);
      if (plan && M.robocze0.has(d)) dodaj(`${M.wolne.has(d) ? 'Przywróć do pracy' : 'Oznacz jako wolny'}: dzień ${d} ${k.MIES_D[M.mies - 1]}`, '', 'i-kal', t, () => k.przelaczWolne(d), true, 100);
    }
    const kw = t.match(/^(\d[\d ]*(?:[.,]\d{1,2})?)\s*(zl)?$/);
    if (plan && kw) { const v = Number(kw[1].replace(/ /g, '').replace(',', '.')); if (v >= MIN_KWOTA) dodaj(`Ustaw kwotę ${fmt(v)} zł`, 'Sprawdzę, czy mieści się w maksimum', 'i-pioro', t, () => { k.ustawKwote(v, true); idz('#kA', 'dzis'); }, true, 100); }
    return L;
  };
  const filtruj = q => {
    const wszystko = polecenia(q), tok = norm(q).split(/\s+/).filter(Boolean);
    if (!tok.length) return wszystko.slice(0, 9);
    const pkt = p => { let s = 0; for (const x of tok) { const i = p.h.indexOf(x); if (i < 0) return -1; s += i === 0 || p.h[i - 1] === ' ' ? 3 : 1; if (norm(p.tytul).startsWith(x)) s += 2; } return s; };
    return wszystko.map(p => ({ p, s: pkt(p) < 0 ? -1 : pkt(p) + p.bonus })).filter(x => x.s >= 0).sort((a, b) => b.s - a.s).map(x => x.p).slice(0, 9);
  };
  const rysujPal = () => {
    palWyniki = filtruj(palIn.value); palIdx = Math.min(palIdx, Math.max(0, palWyniki.length - 1));
    $$('li', palLista).forEach(x => x.remove());
    palLista.insertAdjacentHTML('beforeend', palWyniki.length ? palWyniki.map((p, i) => `<li role="option" id="pal-o${i}" data-i="${i}" style="--i:${i}">${ik(p.ikona)}<span class="pal-t"><b>${p.tytul.replace(/[<>&]/g, '')}</b>${p.opis ? `<small>${p.opis}</small>` : ''}</span></li>`).join('') : '<li class="pal-brak" aria-disabled="true">Nic takiego nie znalazłem — spróbuj innego słowa</li>');
    zaznaczPal(palIdx, false);
  };
  const zaznaczPal = (i, przewin = true) => {
    palIdx = i; const li = $$('li[role="option"]', palLista); li.forEach((x, j) => x.setAttribute('aria-selected', String(j === i)));
    const c = li[i]; if (!c) { palWyb.style.opacity = '0'; palIn.removeAttribute('aria-activedescendant'); return; }
    palIn.setAttribute('aria-activedescendant', c.id); palWyb.style.opacity = '1';
    palWyb.style.translate = `0 ${c.offsetTop}px`; palWyb.style.height = `${c.offsetHeight}px`; if (przewin) c.scrollIntoView({ block: 'nearest' });
  };
  const uruchomPal = i => { const p = palWyniki[i]; if (!p) return; zamknijPal(); setTimeout(() => p.f(), 140); };
  function otworzPal() {
    const { arkuszOtwarty } = S(); if (palOtw || arkuszOtwarty || wycieczka.trwa()) return;
    k.ruchOkno(true); palOtw = true; palFokus = doc.activeElement; palIdx = 0; palIn.value = ''; paleta.hidden = false; paleta.classList.remove('zamyka'); void paleta.offsetWidth; paleta.classList.add('otwarta');
    app.inert = true; rysujPal(); palIn.focus({ preventScroll: true });
    requestAnimationFrame(() => zaznaczPal(palIdx, false));
    const zo = zorza(); zo && zo.flara(.15);
  }
  function zamknijPal() {
    if (!palOtw) return; k.ruchOkno(false); palOtw = false; app.inert = false; paleta.classList.add('zamyka'); paleta.classList.remove('otwarta');
    setTimeout(() => { if (!palOtw) paleta.hidden = true; }, 220);
    palFokus && palFokus.focus && palFokus.focus({ preventScroll: true });
  }
  palIn.addEventListener('input', () => { palIdx = 0; rysujPal(); });
  paleta.addEventListener('pointerdown', e => { if (e.target === paleta) zamknijPal(); });
  palLista.addEventListener('pointermove', e => { const li = e.target.closest('li[role="option"]'); if (li && Number(li.dataset.i) !== palIdx) zaznaczPal(Number(li.dataset.i), false); });
  palLista.addEventListener('click', e => { const li = e.target.closest('li[role="option"]'); if (li) uruchomPal(Number(li.dataset.i)); });
  addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === 'k') { e.preventDefault(); e.stopImmediatePropagation(); palOtw ? zamknijPal() : otworzPal(); return; }
    if (!palOtw) { if (e.key === '/' && !e.ctrlKey && !e.metaKey && !/^(INPUT|TEXTAREA|SELECT)$/.test((e.target.tagName || '')) && !e.target.isContentEditable) { e.preventDefault(); otworzPal(); } return; }
    if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); zamknijPal(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); if (palWyniki.length) zaznaczPal((palIdx + 1) % palWyniki.length); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); if (palWyniki.length) zaznaczPal((palIdx - 1 + palWyniki.length) % palWyniki.length); }
    else if (e.key === 'Enter') { e.preventDefault(); uruchomPal(palIdx); }
    else if (e.key === 'Tab') { e.preventDefault(); }
  }, true);
  for (const id of ['#szukaj', '#szukaj-menu']) { const b = $(id); b && b.addEventListener('click', () => { const d = b.closest('.dymek'); if (d) { d.classList.remove('otwarty'); $('#konto').setAttribute('aria-expanded', 'false'); } palOtw ? zamknijPal() : otworzPal(); }); }

  /* ============================================================ WYCIECZKA ============================================================ */
  const wycieczka = (() => {
    let wyc = null, krok = 0, kroki = [], trwa = false, wtorna = false;
    const KROKI = () => {
      const { M } = S(), plan = M && M.stan === 'plan';
      return [
        ...(M && M.demo ? [{ cel: '#kA', tab: 'dzis', tytul: 'To jest przykład', tekst: 'Zobacz, jak wygląda miesiąc po wygenerowaniu: kalendarz z trasami, trasa dnia z ▶, dokumenty i lista „Dziś”. Gdy będziesz gotowy, naciśnij „Zacznij od swoich danych” — przykład zniknie.' }] : []),
        { cel: '#kA .b-lewa', tab: 'dzis', tytul: 'Zacznij od kwoty', tekst: plan ? 'Wpisz kwotę do rozliczenia. W kalendarzu rośnie poziom cieczy — im więcej do rozliczenia, tym pełniejsze dni, a przy maksimum robią się bursztynowe. Przed generowaniem jeszcze to sprawdzisz.' : 'Tu jest kwota do zwrotu za ten miesiąc.' },
        { cel: '#kC', tab: 'miesiac', tytul: 'Dni wolne jednym ruchem', tekst: 'Kliknij dzień albo przeciągnij po kilku, żeby zamalować urlop. Najedź kursorem: dni zbliżają się do Ciebie.' },
        { cel: '#kE', tab: 'miesiac', tytul: 'Trasa każdego dnia', tekst: 'Po wygenerowaniu naciśnij ▶ albo przesuwaj kursor po osi: pojazd przejedzie ten dzień na mapie, a kwota będzie rosła.' },
        { cel: '#podpisz', tab: 'dzis', tytul: 'Generuj, podpisz, wyślij', tekst: 'Jeden przycisk prowadzi przez cały miesiąc. Dokumenty powstają na tym urządzeniu.' },
        { cel: '#kF', tab: 'dokumenty', tytul: 'Dokumenty wobec limitu', tekst: 'Każda probówka to jedno polecenie. Im bliżej kreski, tym bliżej limitu.' },
        { cel: '#kD', tab: 'dzis', tytul: 'Dziś w terenie', tekst: 'Wczytaj listę sklepów z Excela (przycisk „Plan”), a ułożę trasy na kolejne dni. Odhaczaj odwiedzone sklepy — po ostatnim aplikacja uczci cały dzień.' },
        { cel: telefon() ? '#konto' : '#szukaj', tab: null, tytul: 'Wszystko pod ręką', tekst: telefon() ? 'W menu konta jest „Szukaj poleceń”: wpisz, co chcesz zrobić — „luty”, „14”, „motyw”.' : 'Naciśnij Ctrl+K albo ten przycisk i wpisz, co chcesz zrobić: „luty”, „14”, „motyw”.' },
        ...(telefon() ? [] : [{ cel: '#motyw', tab: null, tytul: 'Noc czy Dzień', tekst: 'Ten przycisk przełącza wygląd między ciemnym (Noc) a jasnym (Dzień). Aplikacja pamięta wybór; bez wyboru idzie za ustawieniem systemu.' }]),
        { cel: '#dzwonek', tab: null, tytul: 'Ważne informacje', tekst: 'Dzwonek zbiera to, o czym warto pamiętać: termin wysyłki do Kierownika regionu, wygasanie dostępu i inne komunikaty.' },
        { cel: '#konto', tab: null, tytul: 'Uwagi, telefon i wygląd', tekst: telefon() ? 'W menu konta: „Napisz uwagę” (zgłoś problem lub pomysł — dołączę dane techniczne), „Na telefon” (instalacja jak zwykła aplikacja), Moje dane oraz przełącznik Noc / Dzień.' : 'W menu konta: „Napisz uwagę” (zgłoś problem lub pomysł — dołączę dane techniczne), „Na telefon” (instalacja i kod QR), Moje dane i zmiana hasła.' }
      ];
    };
    const zbuduj = () => {
      wyc = el('div', 'wyc', `<div class="wyc-swiatlo" aria-hidden="true"></div><div class="wyc-karta" role="dialog" aria-modal="true" aria-labelledby="wyc-tyt" tabindex="-1"><p class="wyc-licz num"></p><h3 id="wyc-tyt"></h3><p class="wyc-tekst"></p>
        <div class="wyc-dol"><button type="button" class="wyc-pomin" data-w="pomin">Pomiń</button><span class="wyc-kropki" aria-hidden="true"></span><button type="button" class="przycisk" data-w="wstecz">Wstecz</button><button type="button" class="przycisk glowny" data-w="dalej">Dalej</button></div></div>`);
      doc.body.appendChild(wyc);
      wyc.addEventListener('click', e => { const b = e.target.closest('[data-w]'); if (!b) return; if (b.dataset.w === 'dalej') idz2(krok + 1); else if (b.dataset.w === 'wstecz') idz2(krok - 1); else koniec(); });
    };
    const ustawKarte = (cel) => {
      const sw = $('.wyc-swiatlo', wyc), karta = $('.wyc-karta', wyc), r = cel.getBoundingClientRect(), pad = 8;
      sw.style.cssText = `left:${r.left - pad}px;top:${r.top - pad}px;width:${r.width + 2 * pad}px;height:${r.height + 2 * pad}px;border-radius:${Math.min(36, parseFloat(getComputedStyle(cel).borderRadius) + pad || 24)}px`;
      const kw = karta.offsetWidth, kh = karta.offsetHeight, W = innerWidth, H = innerHeight, m = 14;
      let x, y;
      if (r.bottom + pad + m + kh <= H) { y = r.bottom + pad + m; x = r.left + r.width / 2 - kw / 2; }
      else if (r.top - pad - m - kh >= 0) { y = r.top - pad - m - kh; x = r.left + r.width / 2 - kw / 2; }
      else if (r.right + pad + m + kw <= W) { x = r.right + pad + m; y = r.top + r.height / 2 - kh / 2; }
      else if (r.left - pad - m - kw >= 0) { x = r.left - pad - m - kw; y = r.top + r.height / 2 - kh / 2; }
      else { x = W / 2 - kw / 2; y = Math.max(m, H - kh - 24); }
      karta.style.translate = `${ogr(x, 12, Math.max(12, W - kw - 12)).toFixed(0)}px ${ogr(y, 12, Math.max(12, H - kh - 12)).toFixed(0)}px`;
    };
    const pokaz = (i) => {
      const s = kroki[i], cel = $(s.cel);
      if (s.tab && telefon()) k.ustawZakladke(s.tab, false);
      requestAnimationFrame(() => requestAnimationFrame(() => {
        if (!trwa || i !== krok) return;          // w międzyczasie przeskoczono dalej albo zakończono
        const c = $(s.cel); if (!c || !widoczny(c)) { if (i < kroki.length - 1) idz2(i + 1); else koniec(); return; }
        $('.wyc-licz', wyc).textContent = `${i + 1} z ${kroki.length}`; $('#wyc-tyt', wyc).textContent = s.tytul; $('.wyc-tekst', wyc).textContent = s.tekst;
        $('.wyc-kropki', wyc).innerHTML = kroki.map((_, j) => `<i class="${j === i ? 'a' : ''}"></i>`).join('');
        $('[data-w="wstecz"]', wyc).hidden = i === 0; $('[data-w="dalej"]', wyc).textContent = i === kroki.length - 1 ? 'Zaczynamy' : 'Dalej';
        $('[data-w="pomin"]', wyc).hidden = i === kroki.length - 1;
        ustawKarte(c); const zo = zorza(); zo && zo.flara(.2);
      }));
    };
    const idz2 = i => { if (i < 0) return; if (i >= kroki.length) { koniec(); return; } krok = i; pokaz(i); };
    function start(reczny) {
      if (trwa) return; if (palOtw) zamknijPal();
      kroki = KROKI(); krok = 0; trwa = true; wtorna = !!reczny; if (!wyc) zbuduj();
      wyc.classList.remove('zamyka'); wyc.hidden = false; void wyc.offsetWidth; wyc.classList.add('otwarta'); k.ruchOkno(true); app.inert = true; wyc.inert = false;
      $('.wyc-karta', wyc).focus({ preventScroll: true }); pokaz(0);
    }
    function koniec() {
      if (!trwa) return; trwa = false; k.ruchOkno(false); pamiec.set('wycieczka', '1'); app.inert = false; wyc.classList.remove('otwarta'); wyc.classList.add('zamyka');
      setTimeout(() => { if (!trwa && wyc) wyc.hidden = true; }, 360); if (telefon() && wtorna) k.ustawZakladke('dzis', false);
    }
    addEventListener('keydown', e => {
      if (!trwa) return;
      if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); koniec(); }
      else if (e.key === 'ArrowRight' || e.key === 'Enter') { if (e.key === 'Enter' && e.target.closest && e.target.closest('button')) return; e.preventDefault(); e.stopImmediatePropagation(); idz2(krok + 1); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); e.stopImmediatePropagation(); idz2(krok - 1); }
      else if (e.key === 'Tab') { const b = $$('button:not([hidden])', wyc); if (!b.length) return; const i = b.indexOf(doc.activeElement); e.preventDefault(); b[(i + (e.shiftKey ? -1 : 1) + b.length) % b.length].focus(); e.stopImmediatePropagation(); }
    }, true);
    addEventListener('resize', () => { if (trwa) pokaz(krok); });
    /* pierwsze uruchomienie: po zapisaniu własnych danych i uspokojeniu ekranu */
    const oferuj = () => {
      const { PROFIL, arkuszOtwarty, M } = S(); if (pamiec.get('wycieczka') || trwa || (!PROFIL && !(M && M.demo))) return;
      if (arkuszOtwarty || app.classList.contains('wejscie') || app.classList.contains('czeka')) { setTimeout(oferuj, 900); return; }
      setTimeout(() => { if (!pamiec.get('wycieczka') && !S().arkuszOtwarty && !palOtw) start(false); }, 1100);
    };
    slucha('profil', () => setTimeout(oferuj, 600));
    setTimeout(oferuj, 6500);
    return { start, trwa: () => trwa };
  })();

  /* ============================================================ PRZESUWANIE ZAKŁADEK (telefon) ============================================================ */
  {
    const kolej = ['dzis', 'miesiac', 'dokumenty']; let s = null;
    const WYLACZ = 'input, select, textarea, .tuner, .podroz, .w-tor, .tabela-w';
    bento.addEventListener('pointerdown', e => {
      if (e.pointerType !== 'touch' || !telefon() || (e.target.closest && e.target.closest(WYLACZ))) { s = null; return; }
      s = { x: e.clientX, y: e.clientY, dx: 0, poz: false };
    });
    bento.addEventListener('pointermove', e => {
      if (!s || e.pointerType !== 'touch') return; const dx = e.clientX - s.x, dy = e.clientY - s.y;
      if (!s.poz && Math.abs(dx) > 14 && Math.abs(dx) > Math.abs(dy) * 1.6) s.poz = true;
      if (s.poz) { s.dx = dx; bento.style.translate = `${(dx * .32).toFixed(1)}px 0`; bento.style.opacity = String((1 - Math.min(.35, Math.abs(dx) / 700)).toFixed(2)); }
    }, { passive: true });
    const koniec = () => {
      if (!s) return; const { dx, poz } = s; s = null;
      if (bento.style.translate) { bento.style.transition = 'translate .35s var(--e-spr), opacity .35s'; bento.style.translate = ''; bento.style.opacity = ''; setTimeout(() => { bento.style.transition = ''; }, 380); }
      if (!poz || Math.abs(dx) < 70) return;
      const i = kolej.indexOf(app.dataset.tab), j = ogr(i + (dx < 0 ? 1 : -1), 0, kolej.length - 1);
      if (j !== i) { wibruj(6); k.ustawZakladke(kolej[j]); }
    };
    bento.addEventListener('pointerup', koniec); bento.addEventListener('pointercancel', koniec);
  }

  return { blysk, wycieczka: wycieczka.start };
}
