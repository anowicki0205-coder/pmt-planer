
(() => {
'use strict';
/* ====================== czas, pomocnicze ====================== */
const czas = () => performance.now() * (window.__tempo ?? 1);
/* animacje CSS i WAAPI (.animate) biegną w zegarze dokumentu — narzędzie wideo zwalnia je osobno (CDP Animation.setPlaybackRate),
   więc ich czasów NIE dzielimy przez __tempo (inaczej w nagraniu byłyby zwolnione podwójnie) */
const doc = document, root = doc.documentElement;
const $ = (s, r = doc) => r.querySelector(s);
const $$ = (s, r = doc) => [...r.querySelectorAll(s)];
const mq = q => { try { return matchMedia(q); } catch (e) { return { matches: false, addEventListener() {} }; } };
const RM = mq('(prefers-reduced-motion: reduce)');
const JASNY = mq('(prefers-color-scheme: light)');
let spokoj = RM.matches;
const NBSP = ' ';
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
  get(k) { try { return localStorage.getItem('pmt-final-' + k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem('pmt-final-' + k, v); } catch (e) {} }
};
/* przejście widoku; rodzaj trafia do html[data-vt], by CSS zostawił tylko potrzebne nazwy przejść;
   na czas przejścia zorza stoi (tło szkła się nie zmienia — tańsze przechwycenie i płynniejszy ruch) */
let vtTrwa = null;
function przejscie(zmiana, potem, rodzaj = 'zwykle') {
  if (vtTrwa) { try { vtTrwa.skipTransition(); } catch (e) {} }
  if (!doc.startViewTransition || spokoj) { zmiana(); potem && potem(); return null; }
  root.dataset.vt = rodzaj;
  wstrzymajRuch(true);
  let vt;
  const koniec = () => { if (vtTrwa === vt) vtTrwa = null; if (!vtTrwa) { delete root.dataset.vt; wstrzymajRuch(false); } potem && potem(); };
  try { vt = doc.startViewTransition(zmiana); } catch (e) { zmiana(); delete root.dataset.vt; wstrzymajRuch(false); potem && potem(); return null; }
  vtTrwa = vt;
  vt.ready.catch(() => {}); vt.updateCallbackDone.catch(() => {});
  vt.finished.then(koniec, koniec);
  return vt;
}
function wstrzymajRuch(v) { zorza && zorza.wstrzymaj(v); kurtyna && kurtyna.wstrzymaj(v); }

/* ====================== dane demo ====================== */
const TRASY = { 1: [215.6, 247.91], 2: [132.0, 151.79], 3: [122.2, 140.54], 4: [217.7, 250.35], 5: [220.2, 253.27], 7: [260.0, 299.09], 10: [288.4, 331.61],
  11: [238.3, 274.10], 12: [212.2, 244.18], 15: [94.3, 108.42], 16: [154.1, 177.15], 18: [184.3, 212.00], 19: [217.7, 250.35], 30: [134.4, 154.50] };
const DNI_T = Object.keys(TRASY).map(Number).sort((a, b) => a - b);
const URLOP = new Set([21, 22, 23, 24, 25, 26]);
const BEZ_TRASY = new Set([8, 9, 14, 17, 28, 29]);
const LIMIT_DZIEN = 587.19, LIMIT_POL = 986.34;
const POLECENIA = [{ nr: 1, od: 1, do: 4, kw: 790.59 }, { nr: 2, od: 5, do: 10, kw: 883.97 }, { nr: 3, od: 11, do: 15, kw: 626.70 }, { nr: 4, od: 16, do: 30, kw: 794.00 }];
const DN = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela'];
const DK = ['pn', 'wt', 'śr', 'cz', 'pt', 'sb', 'nd'];
const dzienTyg = d => d % 7; // 0 = pn (1.09.2026 to wtorek)
const polDla = d => POLECENIA.find(p => d >= p.od && d <= p.do);
const typDnia = d => TRASY[d] ? 'trasa' : URLOP.has(d) ? 'urlop' : dzienTyg(d) === 6 ? 'nd' : 'bez';
const ODC3 = [
  { przyj: '', m: 'Warszawa (dom)', odj: '16:24', dom: true },
  { przyj: '16:58', m: 'Józefów', odj: '17:16', km: 37.5, zl: 43.16 },
  { przyj: '17:25', m: 'Karczew', odj: '17:44', km: 9.7, zl: 11.14 },
  { przyj: '17:58', m: 'Wiązowna', odj: '18:15', km: 15.5, zl: 17.83 },
  { przyj: '18:25', m: 'Halinów', odj: '18:43', km: 10.1, zl: 11.65 },
  { przyj: '18:50', m: 'Sulejówek', odj: '19:06', km: 8.4, zl: 9.62 },
  { przyj: '19:20', m: 'Wołomin', odj: '19:39', km: 14.5, zl: 16.70 },
  { przyj: '20:03', m: 'Warszawa (dom)', odj: '', km: 26.5, zl: 30.44, dom: true }
];
/* przybliżone położenie miejscowości (schemat w rzucie geograficznym, nie mapa drogowa) */
const GEO = { 'Warszawa (dom)': [21.05, 52.235], 'Józefów': [21.233, 52.137], 'Karczew': [21.250, 52.083], 'Wiązowna': [21.297, 52.168],
  'Halinów': [21.358, 52.226], 'Sulejówek': [21.280, 52.246], 'Wołomin': [21.242, 52.344] };
const DZIS = [
  { g: '16:40', s: 'Żabka', m: 'Józefów', a: 'ul. Piłsudskiego 6', c: '--s-zabka', ok: true },
  { g: '17:25', s: 'Biedronka', m: 'Karczew', a: 'ul. Wojska Polskiego 53', c: '--s-biedronka', ok: true },
  { g: '18:20', s: 'Lidl', m: 'Otwock', a: 'ul. Rynek 16', c: '--s-lidl', ok: false },
  { g: '19:05', s: 'Stokrotka', m: 'Wiązowna', a: 'ul. Partyzantów 33', c: '--s-stokrotka', ok: false },
  { g: '19:50', s: 'Dino', m: 'Halinów', a: 'ul. Kwiatowa 66', c: '--s-dino', ok: false },
  { g: '20:35', s: 'Lewiatan', m: 'Sulejówek', a: 'ul. Polna 86', c: '--s-lewiatan', ok: false }
];
const ik = (id, kl = 'ik') => `<svg class="${kl}" aria-hidden="true"><use href="#${id}"/></svg>`;
const opisDnia = d => {
  const t = typDnia(d), k = `${DK[dzienTyg(d)]} ${d}.09`;
  if (t === 'trasa') return `${k} · <b>${fmt(TRASY[d][1])} zł</b> · <span>${fmt(TRASY[d][0], 1)} km</span>`;
  if (t === 'bez') return `${k} · <span>dzień pracy bez trasy</span>`;
  if (t === 'urlop') return `${k} · <span>bez pracy (urlop)</span>`;
  return `${k} · <span>niedziela, wolne</span>`;
};

const app = $('#aplikacja'), bento = $('#bento');
let zorza = null, kurtyna = null;
/* bezczynność: po 15 s bez ruchu zorza i kurtyna odświeżają się 20 zamiast 30 razy na sekundę */
let ostatniRuch = 0;
const odstepKlatki = () => oszczedny ? 5000 : (czas() - ostatniRuch > 15000 ? 50 : 33);
for (const ev of ['pointermove', 'pointerdown', 'keydown', 'wheel']) addEventListener(ev, () => { ostatniRuch = czas(); }, { passive: true, capture: true });

/* ====================== motyw: Noc / Dzień ====================== */
const motywTeraz = () => { const d = root.dataset.theme; return d === 'light' || d === 'dark' ? d : (JASNY.matches ? 'light' : 'dark'); };
function poMotywie() {
  const m = motywTeraz();
  $$('.przel button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.motyw === m)));
  $('#motyw').setAttribute('aria-label', m === 'light' ? 'Motyw: Dzień — przełącz na Noc' : 'Motyw: Noc — przełącz na Dzień');
  zorza && zorza.kolory();
  kurtyna && kurtyna.kolory();
  szkla.forEach(budujSoczewke); /* stan zawiera motyw → filtr przebudowany, stary usunięty */
  rysujGwiazdy();
}
function ustawMotyw(m, zrodlo) {
  if (m === motywTeraz() && root.dataset.theme) return;
  const zm = () => { root.dataset.theme = m; pamiec.set('motyw', m); poMotywie(); };
  if (!doc.startViewTransition || spokoj) { zm(); return; }
  const r = zrodlo && zrodlo.getClientRects().length ? zrodlo.getBoundingClientRect() : { left: innerWidth - 40, top: 28, width: 0, height: 0 };
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  const R = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
  const vt = przejscie(zm, null, 'motyw');
  if (!vt) return;
  vt.ready.then(() => {
    root.animate({ clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${R.toFixed(0)}px at ${x}px ${y}px)`] },
      { duration: 950, easing: 'cubic-bezier(.65,0,.35,1)', pseudoElement: '::view-transition-new(root)' });
  }).catch(() => {});
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

/* ====================== kalendarz ====================== */
let wybrany = 3;
function budujKalendarz() {
  let h = '<div class="dz pusty" aria-hidden="true"></div>';
  for (let d = 1, k = 0; d <= 30; d++, k++) {
    const t = TRASY[d], wd = dzienTyg(d);
    if (t) {
      /* poziom cieczy = kwota dnia / limit dnia (15.09 ≈ 18 %, 10.09 ≈ 56 %) */
      h += `<button type="button" class="dz trasa" data-d="${d}" style="--poziom:${(t[1] / LIMIT_DZIEN).toFixed(3)};--k:${k}" aria-pressed="false" aria-label="${DN[wd]} ${d} września: ${fmt(t[0], 1)} km, ${fmt(t[1])} zł, ${Math.round(t[1] / LIMIT_DZIEN * 100)} % limitu dnia">` +
        `<span class="pl-w" aria-hidden="true"><span class="pl"></span></span><span class="nr">${d}</span><span class="dane num"><span class="km">${fmt(t[0], 1)} km</span><span class="zl">${fmt(t[1])}</span></span></button>`;
    } else if (URLOP.has(d)) {
      if (d === 21) h += `<div class="urlop-pas" role="img" aria-label="21–26 września: bez pracy (urlop)" style="--k:${k}"><span class="u-dni" aria-hidden="true">${[21, 22, 23, 24, 25, 26].map(x => `<span>${x}</span>`).join('')}</span><span class="u-et" aria-hidden="true">bez pracy · 21–26.09</span></div>`;
    }
    else if (wd === 6) h += `<div class="dz nd" data-d="${d}"><span class="nr">${d}</span></div>`;
    else h += `<div class="dz bez" data-d="${d}" aria-label="${DN[wd]} ${d} września: dzień pracy bez wyjazdu"><span class="nr">${d}</span><span class="etyk">bez trasy</span></div>`;
  }
  for (let i = 0; i < 4; i++) h += '<div class="dz pusty" aria-hidden="true"></div>';
  $('#siatka').innerHTML = h;
  zaznaczKomorke();
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
}

/* ====================== kurtyna września (WebGL, promienie danych) ====================== */
function budujKurtyneDOM() {
  const pc = d => ((d - .5) / 30 * 100).toFixed(2) + '%';
  const os = [1, 5, 10, 15, 19, 30];
  let h = os.map(d => `<span data-d="${d}" style="left:${pc(d)}">${d}</span>`).join('');
  h += `<span class="urlop" style="left:${(20 / 30 * 100).toFixed(2)}%;width:${(6 / 30 * 100).toFixed(2)}%">bez pracy</span>`;
  $('#ku-os').innerHTML = h;
  $('#ku-pol').innerHTML = POLECENIA.map(p => `<span data-pol="${p.nr}" style="grid-column:${p.od}/${p.do + 1}" title="Polecenie ${p.nr}: ${dwa(p.od)}–${dwa(p.do)}.09, ${fmt(p.kw)} zł"><b>P${p.nr}</b><span class="dl">${fmt(p.kw)}</span><span class="kr">${Math.round(p.kw / LIMIT_POL * 100)}&nbsp;%</span></span>`).join('');
  $('#ku-zapas').innerHTML = Array.from({ length: 30 }, (_, i) => { const d = i + 1; return `<i style="--h:${TRASY[d] ? (TRASY[d][1] / LIMIT_DZIEN).toFixed(3) : 0}"></i>`; }).join('');
}
const FS_KUR = `precision highp float;
uniform vec2 uR;uniform float uT,uS,uHv,uWz,uFl,uSw,uDzien,uB;uniform sampler2D uD;uniform vec3 c1,c2,c3;
float h11(float p){p=fract(p*.1031);p*=p+33.33;p*=p+p;return fract(p);}
float n2(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);float a=h11(i.x+i.y*57.),b=h11(i.x+1.+i.y*57.),c=h11(i.x+(i.y+1.)*57.),d=h11(i.x+1.+(i.y+1.)*57.);return mix(mix(a,b,f.x),mix(c,d,f.x),f.y);}
void main(){
 vec2 px=gl_FragCoord.xy;float H=uR.y-uB;float q=(px.y-uB)/H;float colW=uR.x/30.;
 float cx=px.x/colW;float i0=floor(cx);vec3 col=vec3(0.);
 for(int k=-1;k<=1;k++){
  float fi=i0+float(k);
  if(fi<0.||fi>29.)continue;
  vec4 dd=texture2D(uD,vec2((fi+.5)/32.,.5));
  float h=dd.r;float rodz=dd.g;float dx=cx-(fi+.5);
  float wsch=clamp(uWz*1.7-fi*.022,0.,1.);wsch=1.-pow(1.-wsch,3.);
  float sel=1.-step(.5,abs(fi-uS));float hov=1.-step(.5,abs(fi-uHv));
  if(rodz>.8){
   float top=h*wsch;
   float x=dx-.05*sin(uT*.7+fi*1.3)*q;
   float wew=smoothstep(top+.012,top-.05,q)*smoothstep(-.03,0.,q);
   float rdzen=exp(-x*x*15.);
   float nit=exp(-x*x*160.);
   float wl=n2(vec2(fi*3.7,q*2.-uT*.5));
   nit+=.55*exp(-pow(x-.2,2.)*260.)*smoothstep(.3,.8,wl)+.45*exp(-pow(x+.18,2.)*260.)*smoothstep(.35,.85,1.-wl);
   float posw=exp(-x*x*2.2)*(.16+.22*sel+.16*hov);
   float smugi=.6+.5*n2(vec2(x*2.5+fi*7.3,q*7.-uT*1.1));
   float pion=.42+.78*clamp(q/max(top,.04),0.,1.);
   float I=wew*(rdzen*(.85+.55*sel+.4*hov)+nit*(.5+.8*sel)+posw)*smugi*pion;
   float og=exp(-x*x*5.)*smoothstep(top+.62,top,q)*step(top,q)*(.24+.2*sel+.12*hov)*wsch*(.7+.3*n2(vec2(fi*5.1,q*4.-uT*.8)));
   col+=mix(c2,c3,smoothstep(top,top+.4,q))*og;
   vec2 e=vec2(x*colW,(q-top)*H)/(colW*.2);
   I+=exp(-dot(e,e))*(1.1+.8*sel+.5*hov)*wsch;
   I*=1.+uFl*sel*1.6+uSw*(1.1+.6*sin(fi*.9-uT*6.));
   I+=uFl*sel*exp(-x*x*1.2)*smoothstep(top+.55,0.,q)*.35;
   vec3 c=mix(c1,c2,smoothstep(0.,.42,q));
   c=mix(c,c3,smoothstep(.36,.95,q));
   c=mix(c,vec3(1.),sel*(rdzen*.3+nit*.45)*(1.-uDzien));
   col+=c*I;
  }else if(rodz>.5){
   vec2 e=vec2(dx*3.2,(q-.02)*H/(colW*.32));
   col+=c2*exp(-dot(e,e))*.55*wsch;
  }
 }
 float lb=exp(-pow((px.y-uB)/(1.6*uR.y/120.),2.));
 col+=c1*lb*.3*uWz;
 float a=clamp(max(col.r,max(col.g,col.b)),0.,1.);
 vec4 noc=vec4(min(col,vec3(1.)),a*.55);
 vec3 cd=col/max(a,.001);
 float ad=clamp(a*1.7,0.,.95);
 vec4 dzien=vec4(cd*ad,ad);
 gl_FragColor=mix(noc,dzien,uDzien);
}`;
function startKurtyna() {
  const fig = $('#kurtyna'), pole = $('#ku-pole'), cv = $('#kurtyna-gl');
  let gl = null;
  try { gl = cv.getContext('webgl', { antialias: false, depth: false, stencil: false, alpha: true, premultipliedAlpha: true, powerPreference: 'low-power' }); } catch (e) { gl = null; }
  if (!gl || window.__bezZorzy) { fig.classList.add('bez-gl'); return null; }
  let prog = null, U = {}, raf = 0, ost = -1e9, zgubiony = false, t0 = czas(), pauza = false;
  const st = { s: wybrany - 1, hv: -1, fl: 0, sw: 0, wz: oszczedny ? 1 : 0, startWz: czas() + 900 };
  const sh = (typ, src) => { const o = gl.createShader(typ); gl.shaderSource(o, src); gl.compileShader(o); return gl.getShaderParameter(o, gl.COMPILE_STATUS) ? o : null; };
  function init() {
    const vs = sh(gl.VERTEX_SHADER, 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}'), fs = sh(gl.FRAGMENT_SHADER, FS_KUR);
    if (!vs || !fs) return false;
    prog = gl.createProgram(); gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return false;
    gl.useProgram(prog);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const a = gl.getAttribLocation(prog, 'p'); gl.enableVertexAttribArray(a); gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0);
    for (const n of ['uR', 'uT', 'uS', 'uHv', 'uWz', 'uFl', 'uSw', 'uDzien', 'uB', 'uD', 'c1', 'c2', 'c3']) U[n] = gl.getUniformLocation(prog, n);
    const dane = new Uint8Array(32 * 4);
    for (let d = 1; d <= 30; d++) {
      const t = typDnia(d), o = (d - 1) * 4;
      dane[o] = t === 'trasa' ? Math.round(TRASY[d][1] / LIMIT_DZIEN * 255) : 0;
      dane[o + 1] = t === 'trasa' ? 255 : t === 'bez' ? 170 : 0; dane[o + 3] = 255;
    }
    const tex = gl.createTexture(); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 32, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, dane);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.uniform1i(U.uD, 0);
    gl.clearColor(0, 0, 0, 0);
    kolory(); rozmiar();
    return true;
  }
  function kolory() {
    if (zgubiony || !prog) return;
    gl.uniform3fv(U.c1, tokenRGB('--kur-1')); gl.uniform3fv(U.c2, tokenRGB('--kur-2')); gl.uniform3fv(U.c3, tokenRGB('--kur-3'));
    gl.uniform1f(U.uDzien, motywTeraz() === 'light' ? 1 : 0);
  }
  function rozmiar() {
    if (zgubiony || !prog) return;
    const dpr = Math.min(2, devicePixelRatio || 1), r = cv.getBoundingClientRect();
    const w = Math.max(2, Math.round(r.width * dpr)), h = Math.max(2, Math.round(r.height * dpr));
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    gl.viewport(0, 0, w, h); gl.uniform2f(U.uR, w, h);
    const b = (r.height - pole.clientHeight) * dpr;
    gl.uniform1f(U.uB, Math.max(2, b));
  }
  function rysuj() {
    if (zgubiony || !prog) return;
    const t = czas();
    if (!oszczedny && !spokoj) st.wz = Math.min(1, Math.max(0, (t - st.startWz) / 1700));
    else st.wz = 1;
    gl.uniform1f(U.uT, (t - t0) / 1000); gl.uniform1f(U.uS, st.s); gl.uniform1f(U.uHv, st.hv);
    gl.uniform1f(U.uWz, st.wz); gl.uniform1f(U.uFl, st.fl); gl.uniform1f(U.uSw, st.sw);
    gl.clear(gl.COLOR_BUFFER_BIT); gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  function klatka() {
    raf = requestAnimationFrame(klatka);
    const t = czas();
    if (t - ost < odstepKlatki()) return;
    const dt = oszczedny ? 5 : Math.min(.1, (t - ost) / 1000); ost = t;
    st.fl *= Math.exp(-dt * 1.6); if (st.fl < .002) st.fl = 0;
    st.sw *= Math.exp(-dt * 1.2); if (st.sw < .002) st.sw = 0;
    rysuj();
  }
  function stop() { cancelAnimationFrame(raf); raf = 0; }
  function tryb() {
    stop();
    if (spokoj) { st.fl = 0; rysuj(); return; }
    if (!doc.hidden && !pauza) { ost = -1e9; raf = requestAnimationFrame(klatka); }
  }
  if (!init()) { fig.classList.add('bez-gl'); return null; }
  cv.addEventListener('webglcontextlost', e => { e.preventDefault(); zgubiony = true; stop(); });
  cv.addEventListener('webglcontextrestored', () => { zgubiony = false; if (init()) tryb(); });
  doc.addEventListener('visibilitychange', () => { if (doc.hidden) stop(); else tryb(); });
  /* najechanie, dotyk i klik: dzień z kolumny */
  const dzienZ = e => { const r = pole.getBoundingClientRect(); return Math.min(30, Math.max(1, Math.floor((e.clientX - r.left) / r.width * 30) + 1)); };
  pole.addEventListener('pointermove', e => {
    const d = dzienZ(e), t = typDnia(d), r = pole.getBoundingClientRect();
    st.hv = t === 'trasa' ? d - 1 : -1;
    const h = t === 'trasa' ? TRASY[d][1] / LIMIT_DZIEN : 0;
    pokazPodp(opisDnia(d), r.left + (d - .5) / 30 * r.width, r.top + r.height * (1 - h) - 4);
    pole.style.cursor = t === 'trasa' ? 'pointer' : 'default';
    podswietlPolecenie(polDla(d) ? polDla(d).nr : 0, true, true);
    if (oszczedny || spokoj) rysuj();
  });
  pole.addEventListener('pointerleave', () => { st.hv = -1; ukryjPodp(); podswietlPolecenie(0, false); if (oszczedny || spokoj) rysuj(); });
  pole.addEventListener('click', e => { const d = dzienZ(e); if (TRASY[d]) wybierzDzien(d); });
  let dotyk = 0;
  pole.addEventListener('pointerup', e => { if (e.pointerType !== 'mouse') { clearTimeout(dotyk); dotyk = setTimeout(() => { st.hv = -1; ukryjPodp(); podswietlPolecenie(0, false); }, 1600); } });
  tryb();
  return {
    tryb, kolory() { kolory(); rysuj(); }, rozmiar() { rozmiar(); rysuj(); },
    wstrzymaj(v) { pauza = v; if (v) stop(); else tryb(); },
    wybierz(d) { st.s = d - 1; st.fl = spokoj ? 0 : 1; rysuj(); },
    restart() { st.startWz = czas() + 900; t0 = czas(); },
    swieto() { if (spokoj) return; st.sw = 1; if (oszczedny) rysuj(); },
    rysuj
  };
}

/* ====================== wybrany dzień: podróż ====================== */
function mapkaSVG() {
  const kolej = ODC3.map(o => o.m);
  const P = kolej.map(n => { const [lon, lat] = GEO[n]; return [(lon - 21) * 0.613, -(lat - 52)]; });
  const xs = P.map(p => p[0]), ys = P.map(p => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const W = 170, H = 112, pad = 15, sk = Math.min((W - 2 * pad) / (x1 - x0), (H - 2 * pad) / (y1 - y0));
  const ox = (W - (x1 - x0) * sk) / 2, oy = (H - (y1 - y0) * sk) / 2;
  const Q = P.map(([x, y]) => [ox + (x - x0) * sk, oy + (y - y0) * sk]);
  const N = Q.length - 1; const g = i => Q[(i + N) % N];
  let d = `M${Q[0][0].toFixed(2)} ${Q[0][1].toFixed(2)}`;
  for (let i = 0; i < N; i++) {
    const p0 = g(i - 1), p1 = g(i), p2 = g(i + 1), p3 = g(i + 2), k = 0.2;
    d += ` C${(p1[0] + (p2[0] - p0[0]) * k).toFixed(2)} ${(p1[1] + (p2[1] - p0[1]) * k).toFixed(2)} ${(p2[0] - (p3[0] - p1[0]) * k).toFixed(2)} ${(p2[1] - (p3[1] - p1[1]) * k).toFixed(2)} ${p2[0].toFixed(2)} ${p2[1].toFixed(2)}`;
  }
  /* okręgi odległości od domu w tym samym rzucie (1° szer. ≈ 111 km) */
  const [hx, hy] = Q[0];
  const kregi = [10, 20].map(km => { const r = km / 111 * sk; return `<circle class="tr-krag" cx="${hx.toFixed(2)}" cy="${hy.toFixed(2)}" r="${r.toFixed(2)}"/><text class="tr-krag-et" x="${(hx - r * .7071 - .8).toFixed(2)}" y="${(hy - r * .7071 - .8).toFixed(2)}" text-anchor="end">${km} km</text>`; }).join('');
  const strony = { 'Warszawa (dom)': [-6.5, 0, 'end'], 'Józefów': [-6, 0, 'end'], 'Karczew': [0, 8.5, 'middle'], 'Wiązowna': [6, 2, 'start'], 'Halinów': [6, 0, 'start'], 'Sulejówek': [-5.5, .5, 'end'], 'Wołomin': [6, 0, 'start'] };
  let pk = '';
  for (let i = 0; i < N; i++) {
    const [x, y] = Q[i], nazwa = kolej[i], s = strony[nazwa];
    const et = `<text class="tr-et" x="${(x + s[0]).toFixed(1)}" y="${(y + s[1]).toFixed(1)}" text-anchor="${s[2]}" dominant-baseline="central">${nazwa === 'Warszawa (dom)' ? 'Warszawa' : nazwa}</text>`;
    pk += i === 0
      ? `<g class="tr-pkt tr-dom" style="--p:0"><circle class="tr-halo" cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="7"/><circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="4"/><path class="tr-dach" d="M${(x - 2.1).toFixed(2)} ${(y + .3).toFixed(2)} L${x.toFixed(2)} ${(y - 1.9).toFixed(2)} L${(x + 2.1).toFixed(2)} ${(y + .3).toFixed(2)} M${(x - 1.4).toFixed(2)} ${(y - .2).toFixed(2)} V${(y + 1.9).toFixed(2)} H${(x + 1.4).toFixed(2)} V${(y - .2).toFixed(2)}"/></g>${et}`
      : `<g class="tr-pkt" style="--p:${i}"><circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="3.4"/><text x="${x.toFixed(2)}" y="${(y + .2).toFixed(2)}">${i}</text></g>${et}`;
  }
  return `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">${kregi}<path class="tr-cien" d="${d}" filter="url(#poswiata)"/><path class="tr-baza" d="${d}"/><path class="tr-linia" pathLength="1" d="${d}"/><path class="tr-pakiet" pathLength="1" d="${d}"/>${pk}</svg>` +
    `<figcaption class="mapka-pod" title="Schemat w rzucie geograficznym (bez dróg); okręgi 10 i 20 km od domu"><i aria-hidden="true"></i><span class="rz">rzut geograficzny · </span>okręgi <span class="kr-km">10 i 20 km </span>od domu</figcaption>`;
}
const minuty = s => { const [h, m] = s.split(':').map(Number); return h * 60 + m; };
function podrozHTML(op) {
  /* kolumny: dom .6fr, przystanki 1fr → szerokość odcinka = połowa własnej + połowa następnej kolumny */
  const sz = i => (i === 0 || i === ODC3.length - 1) ? .6 : 1;
  let h = '';
  ODC3.forEach((o, i) => {
    const nast = ODC3[i + 1];
    const nazwa = o.dom ? 'Dom' : o.m;
    const czasT = o.dom ? (i === 0 ? o.odj : o.przyj) : `${o.przyj}–${o.odj}`;
    const wezel = o.dom ? `<span class="pr-wezel">${ik('i-dom')}</span>` : `<span class="pr-wezel"><span class="pr-nr">${i}</span></span>`;
    const sw = nast ? ((sz(i) / 2 + sz(i + 1) / 2) / sz(i) * 100).toFixed(1) + '%' : '0%';
    const wy = nast ? `<span class="pr-odc"><i></i></span><span class="pr-km wy num"><b>${fmt(nast.km, 1)} km</b><span>${fmt(nast.zl)} zł</span></span>` : '';
    const we = o.km != null ? `<span class="pr-km we num"><b>${fmt(o.km, 1)} km</b><span>${fmt(o.zl)} zł</span></span>` : '<span class="pr-km we num"><span>start</span></span>';
    h += `<li class="pr${o.dom ? ' dom' : ''}" style="--s:${i};--sw:${sw}" title="${o.dom ? 'Warszawa (dom)' : o.m}"><span class="pr-nazwa">${nazwa}</span><span class="pr-czas num">${czasT}</span>` +
      `<span class="pr-os">${wezel}${wy}</span>${we}</li>`;
  });
  return `<ol class="podroz rysuj" style="--op:${op}ms" aria-label="Trasa: Warszawa (dom), 6 miejscowości, powrót; 7 odcinków, 122,2 km, 140,54 zł">${h}<span class="pr-kometa" aria-hidden="true"></span></ol>`;
}
function wstegaHTML(op) {
  const A = 16 * 60, Z = 22 * 60, L = Z - A;
  const pc = v => ((v - A) / L * 100).toFixed(3) + '%';
  let seg = '', k = 0;
  for (let i = 0; i < ODC3.length - 1; i++) {
    const a = minuty(ODC3[i].odj), b = minuty(ODC3[i + 1].przyj);
    seg += `<span class="w-seg j" style="left:${pc(a)};width:calc(${pc(b)} - ${pc(a)});--s:${k++}"></span>`;
    if (ODC3[i + 1].odj) { const c = minuty(ODC3[i + 1].odj); seg += `<span class="w-seg s" style="left:${pc(b)};width:calc(${pc(c)} - ${pc(b)});--s:${k++}"></span>`; }
  }
  return `<div class="wstega rysuj" style="--op:${op}ms"><div class="w-tor"><span class="w-okno" style="left:${pc(16 * 60 + 30)};right:0"></span>${seg}</div>` +
    `<div class="w-dol num" aria-hidden="true"><span>16:00</span><span>17:00</span><span>18:00</span><span>19:00</span><span>20:00</span><span>21:00</span><span>22:00</span></div></div>`;
}
function tabelaHTML() {
  let w = '', nr = 0;
  const maxKm = 37.5;
  for (const o of ODC3) {
    const znak = o.dom ? `<i class="dom">${ik('i-dom')}</i>` : `<i>${++nr}</i>`;
    const km = o.km != null ? `<span class="kmp"><i style="--p:${(o.km / maxKm).toFixed(3)}" aria-hidden="true"></i>${fmt(o.km, 1)}</span>` : '';
    w += `<tr><td class="s">${o.przyj}</td><td><span class="m">${znak}${o.m}</span></td><td class="odj">${o.odj}</td><td class="r s">${km}</td><td class="r">${o.zl != null ? fmt(o.zl) : ''}</td></tr>`;
  }
  return `<div class="tabela-w"><table class="odcinki"><thead><tr><th>Przyj.</th><th>Miejscowość</th><th class="odj">Odj.</th><th class="r">km</th><th class="r">zł</th></tr></thead><tbody>${w}</tbody>` +
    `<tfoot><tr><td colspan="2" class="s">Razem · 7 odcinków</td><td class="odj"></td><td class="r">122,2</td><td class="r">140,54</td></tr></tfoot></table></div>`;
}
function trescDnia(d, op) {
  const t = TRASY[d], p = polDla(d);
  if (d === 3) {
    return `<div class="de-top z-mapa"><div class="de-glowna plyta" style="--pl-in:-14% -18% -10% -14%;--pl-o:.7"><p class="de-kwota num">140,54<small>zł</small></p><p class="de-podkwota num">kwota dnia · 122,2 km × 1,15 zł/km</p>` +
      `<p class="de-tel de-podkwota num">122,2 km × 1,15 zł/km · 16:24–20:03 · 6 wizyt</p>` +
      `<dl class="de-staty num"><div><dt>Wyjazd–powrót</dt><dd>16:24–20:03</dd></div><div><dt>Wizyty</dt><dd>6</dd></div><div><dt><i class="lg j"></i>Jazda</dt><dd>1 h 52 min</dd></div><div><dt><i class="lg s"></i>W sklepach</dt><dd>1 h 47 min</dd></div></dl></div>` +
      `<figure class="mapka rysuj" style="--op:${op}ms">${mapkaSVG()}</figure></div>` +
      podrozHTML(op) + wstegaHTML(op + 500) +
      `<div class="de-szczeg">${tabelaHTML()}</div>`;
  }
  const udzialLimit = t[1] / LIMIT_DZIEN, udzialPol = t[1] / p.kw;
  const dniP = DNI_T.filter(x => x >= p.od && x <= p.do);
  const sk = dniP.map((x, i) => `<div class="sk${x === d ? ' ten' : ''}" style="--s:${i}"><span class="sk-nazwa num">${DK[dzienTyg(x)]} ${dwa(x)}.09</span><span class="sk-pas"><i style="--p:${(TRASY[x][1] / LIMIT_DZIEN).toFixed(4)};--s:${i}"></i></span><span class="sk-kw num">${fmt(TRASY[x][1])} zł</span></div>`).join('');
  return `<div class="de-top"><div class="de-glowna"><p class="de-kwota num">${fmt(t[1])}<small>zł</small></p><p class="de-podkwota num">kwota dnia · ${fmt(t[0], 1)} km × 1,15 zł/km</p></div>` +
    `<dl class="de-staty num"><div><dt>Polecenie</dt><dd>${p.nr} <small>· ${dwa(p.od)}–${dwa(p.do)}.09</small></dd></div><div><dt>Udział w poleceniu</dt><dd>${Math.round(udzialPol * 100)}&nbsp;%</dd></div></dl></div>` +
    `<div class="de-pas"><h3><span>Kwota dnia a limit dnia</span><b class="num">${Math.round(udzialLimit * 100)}&nbsp;%</b></h3><div class="miernik" style="--p:${udzialLimit.toFixed(4)}"><i></i></div><div class="miernik-op num"><span><b>${fmt(t[1])} zł</b> z ${fmt(LIMIT_DZIEN)} zł</span><span>limit dnia</span></div></div>` +
    `<div class="de-pas"><h3><span>Dni z trasą w poleceniu ${p.nr}</span><b class="num">${fmt(p.kw)} zł</b></h3><div class="sklad">${sk}</div></div>` +
    `<div class="de-dol"><button class="wroc" type="button" data-d="3">${ik('i-lewo')}Trasa 3 września</button><p class="de-nota">${ik('i-info')}<span>Przystanki i odcinki w makiecie pokazane dla 3 września.</span></p></div>`;
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
  const d = wybrany, p = polDla(d);
  $('#e-tyt').textContent = `${cap(DN[dzienTyg(d)])}, ${d} września`;
  $('#e-pol').textContent = `Polecenie ${p.nr}`;
  const tr = $('#dzien-tresc');
  const op = start ? 1100 : 120;
  tr.innerHTML = trescDnia(d, op);
  tr.className = 'dzien-tresc ' + (d === 3 ? 'pelny' : 'skrot');
  const i = DNI_T.indexOf(d);
  $('#e-wstecz').disabled = i <= 0; $('#e-dalej').disabled = i >= DNI_T.length - 1;
  kometa(op);
  requestAnimationFrame(skalaMapki);
}
/* schemat trasy skaluje się z kaflem: gdy cyfry węzłów / opisy okręgów wyszłyby poniżej ~7,5 px, chowamy je
   (numery są też na osi podróży pod schematem, a w trybie skupienia schemat jest duży i ma nazwy) */
function skalaMapki() {
  const f = $('.mapka'), m = f && $('svg', f); if (!m) return;
  const r = m.getBoundingClientRect(); if (!r.width) return;
  const s = Math.min(r.width / 170, r.height / 112);
  f.classList.toggle('bez-nr', s * 4.6 < 7.5);
  f.classList.toggle('bez-kregow-et', s * 6.6 < 8.5);
}
function wybierzDzien(d, kier) {
  if (!TRASY[d] || d === wybrany) return;
  root.style.setProperty('--kier', String(kier ?? (d > wybrany ? 1 : -1)));
  zorza && zorza.przesun(d > wybrany ? 1 : -1);
  przejscie(() => { wybrany = d; rysujDzien(); zaznaczKomorke(); }, () => { kurtyna && kurtyna.wybierz(d); });
}

/* ====================== dziś: oś dnia ====================== */
let nawigacja = -1;
function rysujDzis() {
  const ile = DZIS.filter(s => s.ok).length, n = DZIS.findIndex(s => !s.ok);
  $('#d-ile').textContent = `${ile} z 6`; $('#d-pier-t').textContent = `${ile}/6`;
  $('#d-pier').style.setProperty('--p', (ile / 6).toFixed(4));
  if (nawigacja !== n) nawigacja = -1;
  let h = DZIS.map((s, i) => {
    const teraz = i === n, pr = nawigacja === i;
    return `<li class="przystanek${s.ok ? ' ok' : ''}${teraz ? ' teraz' : ''}" style="view-transition-name:p${i}">` +
      `<span class="p-godz num">${s.g}</span>` +
      `<button class="p-znak" type="button" data-i="${i}" aria-pressed="${s.ok}" aria-label="${s.ok ? 'Cofnij odhaczenie' : 'Odhacz wizytę'}: ${s.s}, ${s.m}">${ik('i-ok')}</button>` +
      (teraz ? `<p class="p-etyk brew">Następny · jedziesz teraz</p>` : '') +
      `<p class="p-nazwa"><i style="--c:var(${s.c})"></i>${s.s} <span>· ${s.m}</span></p><p class="p-adres">${s.a}</p>` +
      (teraz ? `<button class="nawiguj${pr ? ' prowadzi' : ''}" type="button" id="nawiguj" data-i="${i}" aria-pressed="${pr}">${ik('i-nawi')}<span>${pr ? 'Prowadzę' : 'Nawiguj'}</span></button>` : '') +
      `</li>`;
  }).join('');
  $('#przystanki').innerHTML = h;
  rysujPlanDnia(ile, n);
  requestAnimationFrame(sprawdzListe);
}
/* tryb skupienia kafla Dziś: plan wieczoru (liczby) + oś godzin 16:00–21:00 z wizytami */
const wizyt = k => k === 1 ? 'wizyta' : (k % 10 >= 2 && k % 10 <= 4 && (k % 100 < 10 || k % 100 >= 20)) ? 'wizyty' : 'wizyt';
function rysujPlanDnia(ile, n) {
  const zost = 6 - ile, prawie = '<svg class="zn" aria-hidden="true"><use href="#i-prawie"/></svg>';
  $('#d-plan').innerHTML =
    `<div class="dp-k dp-glowny"><span class="dp-et">Przed Tobą</span><b class="num">${zost}</b><span class="dp-op">${zost ? `${wizyt(zost)} · następna ${DZIS[n].g}` : 'komplet — trasa zakończona'}</span></div>` +
    `<div class="dp-k"><span class="dp-et">Trasa dnia</span><b class="num" aria-label="około 74 km">${prawie}74<small>km</small></b><span class="dp-op">baza 52 sklepy</span></div>` +
    `<div class="dp-k"><span class="dp-et">Kilometrówka dziś</span><b class="num" aria-label="około 85 zł">${prawie}85<small>zł</small></b><span class="dp-op">74 km × 1,15 zł/km</span></div>` +
    `<div class="dp-k"><span class="dp-et">Ostatnia wizyta</span><b class="num">20:35</b><span class="dp-op">Lewiatan · Sulejówek</span></div>`;
  const A = 16 * 60, Z = 21 * 60, pc = v => ((v - A) / (Z - A) * 100).toFixed(2) + '%';
  const t = i => minuty(DZIS[i].g), ost = DZIS.reduce((m, x, i) => x.ok ? i : m, -1);
  let h = `<div class="dos-tor">`;
  if (ost >= 0) h += `<span class="dos-zrob" style="left:${pc(t(0))};width:calc(${pc(t(ost))} - ${pc(t(0))})"></span>`;
  if (n >= 0) { const a = n > 0 ? t(n - 1) : A + 24; h += `<span class="dos-jazda" style="left:${pc(a)};width:calc(${pc(t(n))} - ${pc(a)})"></span>`; }
  h += DZIS.map((x, i) => `<span class="dos-p${x.ok ? ' ok' : ''}${i === n ? ' teraz' : ''}" style="left:${pc(t(i))}"><i></i><b>${x.s}</b><small class="num">${x.g}</small></span>`).join('');
  h += `</div><div class="dos-skala num"><span>16:00</span><span>21:00</span></div>`;
  $('#d-os').innerHTML = h;
}
function sprawdzListe() {
  const l = $('#przystanki'); if (!l) return;
  l.classList.toggle('przewijana', l.scrollHeight > l.clientHeight + 2 && l.scrollTop + l.clientHeight < l.scrollHeight - 2);
}

/* ====================== dokumenty: fiolki ====================== */
function budujFiolki() {
  const h = POLECENIA.map((p, i) => {
    const u = p.kw / LIMIT_POL, pr = Math.round(u * 100);
    return `<div class="fiolka${u >= .85 ? ' blisko' : ''}" data-pol="${p.nr}" data-dok="${i}" style="--p:${u.toFixed(4)};--s:${i}" aria-label="Polecenie ${p.nr}, ${dwa(p.od)}–${dwa(p.do)}.09: ${fmt(p.kw)} zł, ${pr} % limitu ${fmt(LIMIT_POL)} zł">` +
      `<div class="f-rurka"><span class="f-limit" aria-hidden="true"></span><span class="f-ciecz" aria-hidden="true"></span>` +
      `<span class="f-pieczec" data-dok="${i}" role="img" aria-label="Polecenie ${p.nr}: niepodpisane">${ik('i-ok')}</span></div>` +
      `<p class="f-op num" aria-hidden="true"><b>P${p.nr}<em>${pr}&nbsp;%</em></b><span>${fmt(p.kw)}</span><small>${dwa(p.od)}–${dwa(p.do)}.09</small></p></div>`;
  }).join('');
  const r = `<div class="fiolka rozl" data-dok="4" style="--p:1;--s:4" aria-label="Rozliczenie: 3 095,26 zł, 4 polecenia">` +
    `<div class="f-rurka"><span class="f-ciecz" aria-hidden="true"></span><span class="f-pieczec" data-dok="4" role="img" aria-label="Rozliczenie: niepodpisane">${ik('i-ok')}</span></div>` +
    `<p class="f-op num" aria-hidden="true"><b>R</b><span>3&nbsp;095,26</span><small>4 polecenia</small></p></div>`;
  $('#fiolki').innerHTML = h + r;
}
function podswietlPolecenie(nr, on, tylkoKurtyna) {
  $$('#siatka .swiec, .fiolka.swiec, #ku-pol .swiec').forEach(c => c.classList.remove('swiec'));
  if (!on || !nr) return;
  const p = POLECENIA.find(x => x.nr === nr); if (!p) return;
  const s = $(`#ku-pol [data-pol="${nr}"]`); s && s.classList.add('swiec');
  const w = $(`.fiolka[data-pol="${nr}"]`); w && w.classList.add('swiec');
  if (!tylkoKurtyna) $$('#siatka .dz.trasa').forEach(c => { const d = Number(c.dataset.d); if (d >= p.od && d <= p.do) c.classList.add('swiec'); });
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
const oszczedny = (() => {
  try {
    const c = doc.createElement('canvas'), g = c.getContext('webgl');
    if (!g) return true;
    const e = g.getExtension('WEBGL_debug_renderer_info');
    const r = e ? String(g.getParameter(e.UNMASKED_RENDERER_WEBGL)) : '';
    const wynik = /SwiftShader|llvmpipe|Software|softpipe/i.test(r);
    const l = g.getExtension('WEBGL_lose_context'); l && l.loseContext();
    return wynik;
  } catch (e) { return false; }
})();
function startZorza() {
  const cv = $('#zorza'), gw = $('#gw');
  if (window.__bezZorzy) { cv.classList.add('brak'); return null; }
  let gl = null;
  try { gl = cv.getContext('webgl', { antialias: false, depth: false, stencil: false, alpha: false, premultipliedAlpha: false, preserveDrawingBuffer: false, powerPreference: 'low-power' }); } catch (e) { gl = null; }
  if (!gl) { cv.classList.add('brak'); return null; }
  let prog = null, U = {}, raf = 0, ostatnia = -1e9, t0 = czas(), zgubiony = false, pauza = false;
  const st = { flara: 0, flaraCel: 0, cieplo: 0, cieploCel: 0, faza: 0, fazaCel: 0, mx: 0, my: 0, mxCel: 0, myCel: 0, jasn: 0, cx: .55, cy: .5 };
  function init() {
    const sh = (typ, src) => { const o = gl.createShader(typ); gl.shaderSource(o, src); gl.compileShader(o); return gl.getShaderParameter(o, gl.COMPILE_STATUS) ? o : null; };
    const vs = sh(gl.VERTEX_SHADER, 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}');
    const fs = sh(gl.FRAGMENT_SHADER, '#define KROKI 28\n' + FS);
    if (!vs || !fs) return false;
    prog = gl.createProgram(); gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return false;
    gl.useProgram(prog);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const a = gl.getAttribLocation(prog, 'p'); gl.enableVertexAttribArray(a); gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0);
    for (const n of ['uR', 'uT', 'uM', 'uFlara', 'uCieplo', 'uFaza', 'uJasn', 'uDzien', 'uCel', 'cZ', 'cC', 'cF', 'cR', 'cB', 'cS0', 'cS1', 'cS2']) U[n] = gl.getUniformLocation(prog, n);
    kolory(); rozmiar();
    return true;
  }
  function kolory() {
    if (zgubiony || !prog) return;
    const k = (u, n) => gl.uniform3fv(U[u], tokenRGB(n));
    k('cZ', '--zorza-z'); k('cC', '--zorza-c'); k('cF', '--zorza-f'); k('cR', '--zorza-r'); k('cB', '--burs'); k('cS0', '--niebo-0'); k('cS1', '--niebo-1'); k('cS2', '--niebo-2');
    gl.uniform1f(U.uDzien, motywTeraz() === 'light' ? 1 : 0);
  }
  /* rozdzielczość: połowa pikseli CSS (0,42 na bardzo dużych ekranach), potem rozmycie CSS 2 px */
  function rozmiar() {
    const W = innerWidth + 48, H = innerHeight + 48;
    const sk = W * H > 2.4e6 ? 0.42 : 0.5;
    const w = Math.max(2, Math.round(W * sk)), h = Math.max(2, Math.round(H * sk));
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    gl.viewport(0, 0, w, h); gl.uniform2f(U.uR, w, h);
  }
  function rysuj(T) {
    if (zgubiony || !prog) return;
    gl.uniform1f(U.uT, T); gl.uniform2f(U.uM, st.mx, st.my);
    gl.uniform1f(U.uFlara, st.flara); gl.uniform1f(U.uCieplo, st.cieplo); gl.uniform1f(U.uFaza, st.faza); gl.uniform1f(U.uJasn, st.jasn);
    gl.uniform2f(U.uCel, st.cx, st.cy);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    /* paralaksa: zorza dalej (większy ruch), gwiazdy bliżej horyzontu nieba (mniejszy) */
    cv.style.transform = `translate3d(${(-st.mx * 16).toFixed(2)}px,${(st.my * 10).toFixed(2)}px,0)`;
    gw.style.transform = `translate3d(${(-st.mx * 6).toFixed(2)}px,${(st.my * 4).toFixed(2)}px,0)`;
  }
  function klatka() {
    raf = requestAnimationFrame(klatka);
    const t = czas();
    if (t - ostatnia < odstepKlatki()) return;
    /* przy rzadkim odświeżaniu stan dociąga się do tego, jaki byłby po 5 s na GPU */
    const dt = oszczedny ? 5 : Math.min(0.12, (t - ostatnia) / 1000); ostatnia = t;
    const k = 1 - Math.exp(-dt * 2.6);
    st.flaraCel *= Math.exp(-dt * 1.1); st.cieploCel *= Math.exp(-dt * .7);
    st.flara += (st.flaraCel - st.flara) * k; st.cieplo += (st.cieploCel - st.cieplo) * k;
    st.faza += (st.fazaCel - st.faza) * (1 - Math.exp(-dt * 1.6));
    st.mx += (st.mxCel - st.mx) * (1 - Math.exp(-dt * 2.2)); st.my += (st.myCel - st.my) * (1 - Math.exp(-dt * 2.2));
    /* wschód zorzy 1,4 s; przy rzadkim odświeżaniu (SwiftShader) od razu pełna jasność, jak na GPU po starcie */
    const p = oszczedny ? 1 : Math.min(1, (t - t0) / 1400); st.jasn = 1 - Math.pow(1 - p, 3);
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
    flara(v) { st.flaraCel = Math.max(st.flaraCel, v); if (oszczedny) { st.flara = st.flaraCel; ostatnia = -1e9; } },
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
function ustawSwiatlo() {
  for (const el of szkla) {
    const r = rects.get(el); if (!r) continue;
    el.style.setProperty('--lx', (sw.x - r.left).toFixed(1) + 'px');
    el.style.setProperty('--ly', (sw.y - r.top).toFixed(1) + 'px');
  }
}
function krokPetli() {
  petla = 0;
  const t = czas(), dt = Math.min(0.05, Math.max(0.001, (t - ostP) / 1000)); ostP = t;
  const k = 1 - Math.exp(-dt * 14);
  sw.x += (sw.cx - sw.x) * k; sw.y += (sw.cy - sw.y) * k;
  ustawSwiatlo();
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
  if (e.pointerType === 'touch') return;
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
  }, () => { el.style.viewTransitionName = ''; setTimeout(() => { szkla.forEach(budujSoczewke); mierz(); ustawSwiatlo(); sprawdzListe(); }, 30); }, 'skupienie');
}

/* ====================== podpis: kropla ciekłego szkła ====================== */
let etap = 'podpisz', podpisane = 0;
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
  const r = btn.getBoundingClientRect();
  const x = Math.max(16, Math.min(r.width - 16, e.clientX - r.left));
  const yRel = (e.clientY - r.top) / r.height;
  const y = yRel < .5 ? 4 : r.height - 4;
  btn.style.setProperty('--bx', (x + 16) + 'px'); btn.style.setProperty('--by', (y + 16) + 'px');
  btn.style.setProperty('--mx2', ((e.clientX - r.left - r.width / 2) / r.width * 6).toFixed(2) + 'px');
  btn.style.setProperty('--my2', ((e.clientY - r.top - r.height / 2) / r.height * 4).toFixed(2) + 'px');
});
function ustawLicznik() {
  $('#podp-ile').textContent = podpisane;
  $('#k3-ile').textContent = `${podpisane} z 5`;
  $$('#dok-kolka i').forEach((k, i) => k.classList.toggle('ok', i < podpisane));
  btn.style.setProperty('--pk', String(podpisane * 20));
}
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
function podpiszDok(i) {
  const st = $(`.f-pieczec[data-dok="${i}"]`);
  if (st) { st.classList.add('ok'); st.setAttribute('aria-label', (i < 4 ? `Polecenie ${i + 1}` : 'Rozliczenie') + ': podpisane'); }
  const f = $(`.fiolka[data-dok="${i}"]`); f && f.classList.add('podp-ok');
  podpisane++; ustawLicznik();
  zorza && zorza.flara(0.22);
}
function ustawStatus(t, kl) {
  for (const s of [$('#status'), $('#status-tel')]) { s.classList.toggle('podpisane', !!kl); $('span', s).textContent = t; }
}
async function podpisz() {
  if (etap === 'wyslij') return wyslij();
  if (etap !== 'podpisz') return;
  etap = 'trwa';
  btn.style.setProperty('--hh', (btn.offsetHeight / 2) + 'px');
  btn.setAttribute('aria-busy', 'true');
  btn.classList.add('zbiera');
  zorza && zorza.flara(.35);
  await zegar(520);
  const r = btn.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const kr = $$('.kropla-kr', btn);
  const ang = i => (-90 + (i - 2) * 30) * Math.PI / 180;
  if (!spokoj) kr.forEach((k, i) => k.animate([{ transform: 'translate(0,0) scale(.3)' }, { transform: `translate(${(Math.cos(ang(i)) * 30).toFixed(1)}px,${(Math.sin(ang(i)) * 30).toFixed(1)}px) scale(1)` }],
    { duration: 420, easing: 'cubic-bezier(.3,1.4,.5,1)', fill: 'forwards' }));
  await zegar(380);
  /* dokumenty podpisują się kolejno: 1 … 5 (każda kropla ląduje po poprzedniej) */
  const loty = [];
  for (let i = 0; i < 5; i++) {
    const cel = $(`.f-pieczec[data-dok="${i}"]`);
    const k = kr[i]; k && k.getAnimations().forEach(a => a.cancel());
    loty.push(lot(i, cx + Math.cos(ang(i)) * 30, cy + Math.sin(ang(i)) * 30, cel).then(() => podpiszDok(i)));
    await zegar(360);
  }
  await Promise.all(loty);
  await zegar(300);
  $('#krok3').className = 'krok zrobiony'; $('#krok3').style.setProperty('--k', '0');
  $('#krok3 .wezel').innerHTML = ik('i-ok');
  $('#krok4').className = 'krok aktywny';
  ustawStatus('Podpisane', true);
  btn.classList.remove('zbiera'); btn.classList.add('wyslij'); btn.removeAttribute('aria-busy');
  zmienNapis('Wyślij do Kierownika regionu', 'i-nawi');
  $('#kA').classList.add('po');
  zorza && zorza.flara(1);
  kurtyna && kurtyna.swieto();
  etap = 'wyslij';
  pokazToast('Podpisano 5 dokumentów Profilem Zaufanym (demo)');
}
function wyslij() {
  etap = 'wyslane';
  $('#krok4').className = 'krok zrobiony'; $('#krok4 .wezel').innerHTML = ik('i-ok');
  btn.classList.remove('wyslij'); btn.classList.add('gotowe');
  zmienNapis('Wysłano do Kierownika regionu', 'i-ok');
  ustawStatus('Wysłane', true);
  zorza && zorza.flara(.7);
  pokazToast('Wysłano 5 dokumentów do Kierownika regionu (demo)');
}
function cofnij() {
  etap = 'podpisz'; podpisane = 0; ustawLicznik();
  $$('.f-pieczec').forEach((st, i) => { st.classList.remove('ok'); st.setAttribute('aria-label', (i < 4 ? `Polecenie ${i + 1}` : 'Rozliczenie') + ': niepodpisane'); });
  $$('.fiolka.podp-ok').forEach(f => f.classList.remove('podp-ok'));
  $('#krok3').className = 'krok aktywny'; $('#krok3 .wezel').textContent = '3';
  $('#krok4').className = 'krok'; $('#krok4 .wezel').textContent = '4';
  ustawStatus('Wygenerowane', false);
  btn.classList.remove('wyslij', 'gotowe', 'zbiera');
  zmienNapis('Podpisz 5 dokumentów', 'i-pioro');
  $('#kA').classList.remove('po');
  pokazToast('Przywrócono stan przed podpisem');
  btn.focus({ preventScroll: true });
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
  if (animuj) przejscie(zm, () => { szkla.forEach(budujSoczewke); mierz(); }); else zm();
  pamiec.set('zakladka', t);
  requestAnimationFrame(() => { szkla.forEach(budujSoczewke); mierz(); sprawdzListe(); });
}
const dymki = [[$('#dzwonek'), $('#dymek')], [$('#konto'), $('#konto-menu')]];
function zamknijDymki(oprocz) {
  for (const [b, d] of dymki) if (d !== oprocz && d.classList.contains('otwarty')) { d.classList.remove('otwarty'); b.setAttribute('aria-expanded', 'false'); }
}

/* ====================== zdarzenia ====================== */
function zdarzenia() {
  const siatka = $('#siatka');
  siatka.addEventListener('click', e => { const b = e.target.closest('button.dz'); if (b) wybierzDzien(Number(b.dataset.d)); });
  siatka.addEventListener('pointerover', e => {
    const c = e.target.closest('.dz.trasa, .dz.bez');
    if (!c) { ukryjPodp(); podswietlPolecenie(0, false); return; }
    const d = Number(c.dataset.d), r = c.getBoundingClientRect();
    pokazPodp(opisDnia(d), r.left + r.width / 2, r.top - 2);
    const p = polDla(d); if (c.classList.contains('trasa') && p) { podswietlPolecenie(p.nr, true, true); }
  });
  siatka.addEventListener('pointerleave', () => { ukryjPodp(); podswietlPolecenie(0, false); });
  siatka.addEventListener('focusin', e => { const c = e.target.closest('.dz.trasa'); if (c) { const r = c.getBoundingClientRect(); pokazPodp(opisDnia(Number(c.dataset.d)), r.left + r.width / 2, r.top - 2); } });
  siatka.addEventListener('focusout', ukryjPodp);
  $('#fiolki').addEventListener('pointerover', e => { const w = e.target.closest('.fiolka[data-pol]'); if (w) podswietlPolecenie(Number(w.dataset.pol), true); else podswietlPolecenie(0, false); });
  $('#fiolki').addEventListener('pointerleave', () => podswietlPolecenie(0, false));
  $('#ku-pol').addEventListener('pointerover', e => { const s = e.target.closest('[data-pol]'); if (s) podswietlPolecenie(Number(s.dataset.pol), true); });
  $('#ku-pol').addEventListener('pointerleave', () => podswietlPolecenie(0, false));
  $('#e-wstecz').addEventListener('click', () => { const i = DNI_T.indexOf(wybrany); if (i > 0) wybierzDzien(DNI_T[i - 1], -1); });
  $('#e-dalej').addEventListener('click', () => { const i = DNI_T.indexOf(wybrany); if (i < DNI_T.length - 1) wybierzDzien(DNI_T[i + 1], 1); });
  $('#dzien-tresc').addEventListener('click', e => { const b = e.target.closest('.wroc'); if (b) wybierzDzien(Number(b.dataset.d), -1); });
  $$('.rozwin').forEach(b => { b.dataset.etykieta = b.getAttribute('aria-label'); b.setAttribute('aria-expanded', 'false'); b.addEventListener('click', e => { e.stopPropagation(); const k = b.closest('.kafel'); skupienie(k === skupiony ? null : k); }); });
  /* klik poza rozwiniętym kaflem (w cofniętą głąb) zamyka tryb skupienia */
  bento.addEventListener('click', e => { if (skupiony && !skupiony.contains(e.target)) skupienie(null); });
  btn.addEventListener('click', podpisz);
  $('#cofnij').addEventListener('click', cofnij);
  $('#przystanki').addEventListener('scroll', sprawdzListe, { passive: true });
  $('#przystanki').addEventListener('click', e => {
    const nav = e.target.closest('.nawiguj');
    if (nav) {
      const i = Number(nav.dataset.i), on = nawigacja !== i;
      nawigacja = on ? i : -1;
      nav.classList.toggle('prowadzi', on); nav.setAttribute('aria-pressed', String(on));
      $('span', nav).textContent = on ? 'Prowadzę' : 'Nawiguj';
      if (on) { zorza && zorza.flara(.18); pokazToast(`Nawigacja: ${DZIS[i].s} · ${DZIS[i].m}, ${DZIS[i].a} — w makiecie bez otwierania map`); }
      return;
    }
    const b = e.target.closest('.p-znak'); if (!b) return;
    const i = Number(b.dataset.i);
    /* stan zmieniamy od razu (View Transition wykonuje rysowanie asynchronicznie — toast i kolejne kliknięcia
       muszą widzieć już nowy stan); przejście tylko przerysowuje listę */
    DZIS[i].ok = !DZIS[i].ok;
    const ok = DZIS[i].ok, ile = DZIS.filter(x => x.ok).length, kto = `${DZIS[i].s} · ${DZIS[i].m}`;
    przejscie(rysujDzis, () => { const nb = $(`.p-znak[data-i="${i}"]`); nb && nb.focus({ preventScroll: true }); }, 'dzis');
    if (ok) { zorza && zorza.flara(.2); pokazToast(ile === 6 ? 'Komplet: 6 z 6 wizyt — trasa zakończona' : `Odhaczono: ${kto} (${ile} z 6)`); }
    else pokazToast(`Cofnięto odhaczenie: ${kto} (${ile} z 6)`);
  });
  for (const [b, d] of dymki) {
    b.addEventListener('click', e => {
      e.stopPropagation(); const o = !d.classList.contains('otwarty'); zamknijDymki(d);
      d.classList.toggle('otwarty', o); b.setAttribute('aria-expanded', String(o));
      if (o && b.id === 'dzwonek') { const x = $('b', b); x && x.remove(); b.setAttribute('aria-label', 'Powiadomienia'); }
    });
  }
  doc.addEventListener('click', e => { if (!e.target.closest('.dymek')) zamknijDymki(null); });
  $$('.przel button').forEach(b => b.addEventListener('click', () => { ustawMotyw(b.dataset.motyw, b); zegar(700).then(() => zamknijDymki(null)); }));
  $('#motyw').addEventListener('click', e => ustawMotyw(motywTeraz() === 'light' ? 'dark' : 'light', e.currentTarget));
  $('#m-wstecz').addEventListener('click', () => pokazToast('Makieta: dane demo tylko dla września 2026'));
  $('#m-dalej').addEventListener('click', () => pokazToast('Makieta: dane demo tylko dla września 2026'));
  $('#termin').addEventListener('pointerenter', () => { ustawCelCiepla(); zorza && zorza.cieplo(1); });
  $$('.zakladka').forEach(b => b.addEventListener('click', () => ustawZakladke(b.dataset.tab)));
  /* wzorzec ARIA tablist: strzałki / Home / End przełączają zakładki */
  $('#zakladki').addEventListener('keydown', e => {
    const z = $$('.zakladka'), i = z.indexOf(doc.activeElement); if (i < 0) return;
    const j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: z.length - 1 }[e.key]; if (j === undefined) return;
    e.preventDefault(); const c = z[(j + z.length) % z.length]; c.focus(); ustawZakladke(c.dataset.tab);
  });
  try { JASNY.addEventListener('change', () => { if (!root.dataset.theme) poMotywie(); }); } catch (e) {}
  try { RM.addEventListener('change', e => { spokoj = e.matches; zorza && zorza.tryb(); kurtyna && kurtyna.tryb(); }); } catch (e) {}
  addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    for (const [b, d] of dymki) if (d.classList.contains('otwarty')) { zamknijDymki(null); b.focus(); return; }
    if (skupiony) { const k = skupiony; skupienie(null); const b = $('.rozwin', k); b && b.focus({ preventScroll: true }); }
  });
  let rt = 0;
  addEventListener('resize', () => {
    clearTimeout(rt);
    rt = setTimeout(() => { zorza && zorza.rozmiar(); kurtyna && kurtyna.rozmiar(); rysujGwiazdy(); rysujHoryzont(); domyslne(); mierz(); ustawCelCiepla(); budz(); sprawdzListe(); }, 120);
  });
}

/* ====================== start ====================== */
const pierwszaKlatka = () => new Promise(res => {
  let gotowe = false; const ok = () => { if (!gotowe) { gotowe = true; res(); } };
  requestAnimationFrame(() => requestAnimationFrame(ok)); setTimeout(ok, 1200);
});
async function start() {
  app.classList.add('czeka');
  przygotujCyfry($('#kwota'), '3' + NBSP + '095,26');
  budujKalendarz(); budujKurtyneDOM(); budujFiolki(); rysujDzis(); rysujDzien(true);
  const zak = pamiec.get('zakladka');
  if (zak && ['dzis', 'miesiac', 'dokumenty'].includes(zak)) ustawZakladke(zak, false);
  rysujGwiazdy(); rysujHoryzont();
  zorza = startZorza();
  kurtyna = startKurtyna();
  szkla.forEach(el => { ro && ro.observe(el); });
  mierz(); ustawSwiatlo(); poMotywieUI();
  zdarzenia();
  /* pierwsza klatka bez filtrów soczewki (kafle i tak są jeszcze niewidoczne we mgle) — szybszy start;
     choreografia rusza od tej klatki (najpóźniej po 1,2 s) */
  await pierwszaKlatka();
  app.classList.remove('czeka');
  zorza && zorza.restart(); kurtyna && kurtyna.restart();
  if (czyChromium) { root.classList.add('soczewka'); szkla.forEach(budujSoczewke); }
  if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(() => { mierz(); ustawSwiatlo(); sprawdzListe(); kurtyna && kurtyna.rozmiar(); }).catch(() => {});
  /* sekwencja startowa na zegarze (nie na klatkach) — kompletna po ~3,4 s nawet przy wolnym renderowaniu */
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
  strazKlatek();
}
/* adaptacyjna jakość szkła: gdy prawdziwe GPU nie nadąża z soczewką (mediana klatki > 45 ms przez 2 s po wejściu),
   szkło przechodzi na zwykły blur + saturację + połysk (ten sam zapas co Safari/Firefox).
   Renderowania programowego (SwiftShader) nie mierzymy — tam wolno jest zawsze, a wygląd ma zostać jak na GPU. */
function strazKlatek() {
  if (oszczedny || spokoj || !root.classList.contains('soczewka')) return;
  const odst = []; let pop = 0, t0 = 0;
  const krok = ts => {
    if (doc.hidden) return;
    if (pop) odst.push(ts - pop);
    pop = ts; t0 = t0 || ts;
    if (ts - t0 < 2000) { requestAnimationFrame(krok); return; }
    odst.sort((a, b) => a - b);
    if ((odst[odst.length >> 1] || 0) > 45) {
      root.classList.remove('soczewka');
      szkla.forEach(el => { el.classList.remove('ma-soczewke'); el.style.removeProperty('--soczewka'); });
    }
  };
  requestAnimationFrame(krok);
}
function poMotywieUI() {
  const m = motywTeraz();
  $$('.przel button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.motyw === m)));
}
start();
})();
