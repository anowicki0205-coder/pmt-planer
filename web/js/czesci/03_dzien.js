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
  /* okręgi odległości od domu w tym samym rzucie (1° szer. ≈ 111 km) */
  const [hx, hy] = Q[0];
  const kregi = [10, 20].map(km => { const r = km / 111 * sk; return `<circle class="tr-krag" cx="${hx.toFixed(2)}" cy="${hy.toFixed(2)}" r="${r.toFixed(2)}"/><text class="tr-krag-et" x="${(hx - r * .7071 - .8).toFixed(2)}" y="${(hy - r * .7071 - .8).toFixed(2)}" text-anchor="end">${km} km</text>`; }).join('');
  const cx = (Math.min(...Q.map(q => q[0])) + Math.max(...Q.map(q => q[0]))) / 2;
  let pk = '';
  for (let i = 0; i < N; i++) {
    const [x, y] = Q[i], lewo = x < cx, nazwa = pt[i].m;
    const et = `<text class="tr-et" x="${(x + (lewo ? -6 : 6)).toFixed(1)}" y="${y.toFixed(1)}" text-anchor="${lewo ? 'end' : 'start'}" dominant-baseline="central">${nazwa}</text>`;
    pk += i === 0
      ? `<g class="tr-pkt tr-dom" style="--p:0"><circle class="tr-halo" cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="7"/><circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="4"/><path class="tr-dach" d="M${(x - 2.1).toFixed(2)} ${(y + .3).toFixed(2)} L${x.toFixed(2)} ${(y - 1.9).toFixed(2)} L${(x + 2.1).toFixed(2)} ${(y + .3).toFixed(2)} M${(x - 1.4).toFixed(2)} ${(y - .2).toFixed(2)} V${(y + 1.9).toFixed(2)} H${(x + 1.4).toFixed(2)} V${(y - .2).toFixed(2)}"/></g>${et}`
      : `<g class="tr-pkt" style="--p:${i}"><circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="3.4"/><text x="${x.toFixed(2)}" y="${(y + .2).toFixed(2)}">${i}</text></g>${et}`;
  }
  return `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">${kregi}<path class="tr-cien" d="${d}" filter="url(#poswiata)"/><path class="tr-baza" d="${d}"/><path class="tr-linia" pathLength="1" d="${d}"/><path class="tr-pakiet" pathLength="1" d="${d}"/>${pk}</svg>` +
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
  return `<div class="wstega rysuj" style="--op:${op}ms"><div class="w-tor">${okno}${seg}</div><div class="w-dol num" aria-hidden="true">${godz}</div></div>`;
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
  return `<div class="de-top z-mapa"><div class="de-glowna plyta" style="--pl-in:-14% -18% -10% -14%;--pl-o:.7"><p class="de-kwota num">${fmt(tr.suma)}<small>zł</small></p><p class="de-podkwota num">kwota dnia · ${fmt(tr.km, 1)} km × ${fmt(M.stawka)} zł/km</p>` +
    `<p class="de-tel de-podkwota num">${fmt(tr.km, 1)} km × ${fmt(M.stawka)} zł/km · ${odc[0].odj}–${odc[odc.length - 1].przyj} · ${wizyt} ${wizyt === 1 ? 'wizyta' : wizyt < 5 ? 'wizyty' : 'wizyt'}</p>` +
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
    return;
  }
  const d = wybrany, p = polDla(d);
  $('#e-tyt').textContent = `${cap(DN[dzienTyg(d)])}, ${d} ${MIES_D[M.mies - 1]}`;
  $('#e-pol').hidden = !p; if (p) $('#e-pol').textContent = `Polecenie ${p.nr}`;
  const op = start ? 1100 : 120;
  tr.innerHTML = trescDnia(d, op);
  tr.className = 'dzien-tresc pelny';
  const i = M.dniT.indexOf(d);
  $('#e-wstecz').disabled = i <= 0; $('#e-dalej').disabled = i >= M.dniT.length - 1;
  kometa(op);
  requestAnimationFrame(skalaMapki);
}
/* schemat trasy skaluje się z kaflem: gdy cyfry węzłów / opisy okręgów wyszłyby poniżej ~7,5 px, chowamy je */
function skalaMapki() {
  const f = $('.mapka'), m = f && $('svg', f); if (!m) return;
  const r = m.getBoundingClientRect(); if (!r.width) return;
  const s = Math.min(r.width / 170, r.height / 112);
  f.classList.toggle('bez-nr', s * 4.6 < 7.5);
  f.classList.toggle('bez-kregow-et', s * 6.6 < 8.5);
}
function wybierzDzien(d, kier) {
  if (!M || !M.trasy[d] || d === wybrany) return;
  root.style.setProperty('--kier', String(kier ?? (d > wybrany ? 1 : -1)));
  zorza && zorza.przesun(d > wybrany ? 1 : -1);
  przejscie(() => { wybrany = d; rysujDzien(); zaznaczKomorke(); }, () => { kurtyna && kurtyna.wybierz(d); });
}
