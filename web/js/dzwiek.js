// PMT Planer (web) — dźwięki: krótkie efekty i spokojny podkład muzyczny.
// WSZYSTKO jest wytwarzane w przeglądarce (Web Audio API): żadnych plików dźwiękowych, żadnych licencji, działa offline i nie dokłada nic do pobierania.
// Przeglądarki odtwarzają dźwięk dopiero po geście użytkownika (kliknięcie, klawisz), dlatego kontekst audio powstaje przy pierwszym takim geście.
//
// Dwie części:
//   1) czysta synteza — zbudujEfekt(), zbudujMuzyke(): przyjmują dowolny kontekst (także OfflineAudioContext), dzięki czemu testy renderują dźwięk do liczb i sprawdzają ciszę/przesterowanie;
//   2) sterowanie — obiekt „dzwiek”: ustawienia na urządzeniu (pmt-ui-dzwiek: efekty, domyślnie włączone; pmt-ui-muzyka: podkład, domyślnie wyłączony), przyciski w nagłówku i w menu konta.
// Moduł nie robi nic przy samym imporcie (bezpieczny w teście w Node): wszystko startuje w dzwiek.init().

const mid = n => 440 * Math.pow(2, (n - 69) / 12);      // numer nuty MIDI → częstotliwość
const SZUM = new WeakMap();
function szumBufor(c) {
  let b = SZUM.get(c);
  if (!b) { const n = Math.floor(c.sampleRate * 1.2); b = c.createBuffer(1, n, c.sampleRate); const d = b.getChannelData(0); for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1; SZUM.set(c, b); }
  return b;
}

/** Jeden ton: obwiednia (szybki narost, wykładniczy zanik), opcjonalny przesuw wysokości i filtr. */
function ton(c, wyj, { t, f, f2, d, g = .1, a = .005, typ = 'sine', filtr, vib }) {
  const o = c.createOscillator(), v = c.createGain();
  o.type = typ; o.frequency.setValueAtTime(f, t); if (f2) o.frequency.exponentialRampToValueAtTime(f2, t + d);
  if (vib) { const l = c.createOscillator(), lg = c.createGain(); l.frequency.value = vib.hz; lg.gain.value = vib.cent; l.connect(lg); lg.connect(o.detune); l.start(t); l.stop(t + d + .03); }      // delikatne vibrato (w centach)
  v.gain.setValueAtTime(0.0001, t); v.gain.exponentialRampToValueAtTime(g, t + a); v.gain.exponentialRampToValueAtTime(0.0001, t + d);
  o.connect(v); let out = v;
  if (filtr) { const bq = c.createBiquadFilter(); bq.type = filtr.typ || 'lowpass'; bq.frequency.setValueAtTime(filtr.f, t); if (filtr.f2) bq.frequency.exponentialRampToValueAtTime(filtr.f2, t + d); bq.Q.value = filtr.q || .7; v.connect(bq); out = bq; }
  out.connect(wyj); o.start(t); o.stop(t + d + .03);
}
/** Szum przepuszczony przez filtr (świst, uderzenie werbla, talerz). */
function szum(c, wyj, { t, d, g = .05, f = 2000, f2, q = 1, typ = 'bandpass', a = .004 }) {
  const s = c.createBufferSource(), bq = c.createBiquadFilter(), v = c.createGain();
  s.buffer = szumBufor(c); bq.type = typ; bq.frequency.setValueAtTime(f, t); if (f2) bq.frequency.exponentialRampToValueAtTime(f2, t + d); bq.Q.value = q;
  v.gain.setValueAtTime(0.0001, t); v.gain.exponentialRampToValueAtTime(g, t + a); v.gain.exponentialRampToValueAtTime(0.0001, t + d);
  s.connect(bq); bq.connect(v); v.connect(wyj); s.start(t, Math.random() * .1); s.stop(t + d + .03);
}
/** Dzwonek: dźwięk zasadniczy plus dwa nieharmoniczne alikwoty, które zanikają szybciej — jak szklane uderzenie. */
function dzwonek(c, wyj, t, n, { g = .08, d = .6 } = {}) {
  const f = mid(n);
  [[1, 1, 1], [2.756, .26, .5], [5.4, .09, .28]].forEach(([m, a, k]) => ton(c, wyj, { t, f: f * m, d: d * k + .05, g: g * a, a: .004 }));
}
const arpeg = (c, w, t, nuty, krok, g, d) => nuty.forEach((n, i) => dzwonek(c, w, t + i * krok, n, { g, d }));

/* ------------------------------ efekty ------------------------------ */
export const EFEKTY = {
  klik: (c, w, t) => { ton(c, w, { t, f: 2100, f2: 1500, d: .035, g: .03, a: .002, typ: 'triangle' }); return .06; },
  okno: (c, w, t) => { ton(c, w, { t, f: 420, f2: 840, d: .16, g: .05, a: .01 }); dzwonek(c, w, t + .07, 84, { g: .04, d: .3 }); return .45; },
  'okno-zam': (c, w, t) => { ton(c, w, { t, f: 760, f2: 380, d: .13, g: .045, a: .006 }); return .2; },
  motyw: (c, w, t) => { szum(c, w, { t, d: .3, g: .07, f: 500, f2: 3200, q: 1.4 }); dzwonek(c, w, t + .12, 88, { g: .035, d: .35 }); return .55; },
  ok: (c, w, t) => { dzwonek(c, w, t, 76, { g: .1, d: .55 }); dzwonek(c, w, t + .09, 83, { g: .09, d: .7 }); return .9; },      // E5 → H5: „sprawdzone”
  zle: (c, w, t) => { ton(c, w, { t, f: 233, f2: 175, d: .26, g: .1, a: .01, typ: 'triangle', filtr: { typ: 'lowpass', f: 900 } }); return .35; },
  wszystkie: (c, w, t) => { arpeg(c, w, t, [69, 72, 76, 81, 84, 88], .075, .08, .7); dzwonek(c, w, t + .5, 93, { g: .035, d: .9 }); return 1.5; },      // wszystkie dokumenty podpisane
  wyslano: (c, w, t) => { szum(c, w, { t, d: .26, g: .06, f: 700, f2: 4200, q: 1.2 }); dzwonek(c, w, t + .17, 79, { g: .09, d: .6 }); dzwonek(c, w, t + .28, 86, { g: .09, d: .85 }); return 1.2; },
  'gen-start': (c, w, t) => {
    ton(c, w, { t, f: 98, f2: 392, d: .55, g: .05, a: .04, typ: 'sawtooth', filtr: { typ: 'lowpass', f: 300, f2: 2600, q: 2 } });
    ton(c, w, { t, f: 49, f2: 196, d: .55, g: .09, a: .04 }); szum(c, w, { t: t + .1, d: .45, g: .025, f: 1500, f2: 7000, q: .8, typ: 'highpass' }); return .65;
  },
  'gen-koniec': (c, w, t) => { arpeg(c, w, t, [72, 76, 79, 84, 88, 91, 96], .09, .065, .8); [72, 79, 84].forEach(n => dzwonek(c, w, t + .75, n, { g: .045, d: 1.2 })); return 2.1; },
  odhacz: (c, w, t) => { ton(c, w, { t, f: 784, d: .15, g: .09, a: .003 }); ton(c, w, { t, f: 1568, d: .07, g: .03, a: .002 }); return .22; },
  'odhacz-wyl': (c, w, t) => { ton(c, w, { t, f: 523, f2: 392, d: .11, g: .05, a: .004, typ: 'triangle' }); return .16; }
};
/** Planuje efekt na kontekście c, w węźle wyj, od chwili t. Zwraca czas trwania w sekundach (0 = nieznany efekt). */
export function zbudujEfekt(c, wyj, nazwa, t) { const f = EFEKTY[nazwa]; return f ? f(c, wyj, t) : 0; }

/* ------------------------------ tor wyjściowy: pogłos, kompresor ------------------------------ */
/** Syntetyczna odpowiedź impulsowa małej sali (stereo, ok. 1,9 s): szum, który zanika wykładniczo i z czasem ciemnieje (powietrze tłumi wysokie tony). */
function odpowiedzImpulsowa(c, sek = 1.9) {
  const sr = c.sampleRate, n = Math.floor(sr * sek), b = c.createBuffer(2, n, sr), wstep = Math.floor(sr * .012);
  for (let ch = 0; ch < 2; ch++) {
    const d = b.getChannelData(ch); let lp = 0;
    for (let i = wstep; i < n; i++) { const t = (i - wstep) / sr, a = .22 + .78 * Math.exp(-t / .45); lp += a * ((Math.random() * 2 - 1) * Math.exp(-t / .42) - lp); d[i] = lp; }
  }
  return b;
}
/** Wspólny tor wyjściowy (używa go aplikacja i renderowanie próbek do testów oraz odsłuchu — dzięki temu brzmią tak samo):
 *  efekty (ef — bez pogłosu, efR — z pogłosem) i podkład (pogMuzyki — wysyłka do pogłosu) → wzmocnienie 0,8 → kompresor → cel. */
export function zbudujTor(c, cel) {
  const master = c.createGain(); master.gain.value = .8;
  const k = c.createDynamicsCompressor(); k.threshold.value = -20; k.knee.value = 12; k.ratio.value = 4; k.attack.value = .004; k.release.value = .2;
  const lim = c.createDynamicsCompressor(); lim.threshold.value = -3; lim.knee.value = 0; lim.ratio.value = 20; lim.attack.value = .002; lim.release.value = .09;      // zabezpieczenie przed przesterowaniem (limiter)
  master.connect(k); k.connect(lim); lim.connect(cel);
  const ef = c.createGain(); ef.connect(master);
  const conv = c.createConvolver(); conv.buffer = odpowiedzImpulsowa(c); const pogWyj = c.createGain(); pogWyj.gain.value = 3; conv.connect(pogWyj); pogWyj.connect(master);      // splot z odpowiedzią impulsową jest znormalizowany, więc sam z siebie wychodzi bardzo cicho — stąd duże wzmocnienie powrotu
  const efR = c.createGain(); efR.connect(master); const efWysylka = c.createGain(); efWysylka.gain.value = 1; efR.connect(efWysylka); efWysylka.connect(conv);
  const pogMuzyki = c.createGain(); pogMuzyki.gain.value = 1; pogMuzyki.connect(conv);
  return { master, ef, efR, pogMuzyki };
}
/** Muzyka na chwilę cichnie, gdy gra efekt (efekt zawsze wyraźnie słychać), potem wraca. duck — węzeł wzmocnienia z zbudujMuzyke(). */
export function przygluszMuzyke(duck, t, dl) {
  duck.gain.cancelScheduledValues(t); duck.gain.setTargetAtTime(.6, t, .025); duck.gain.setTargetAtTime(1, t + Math.min(dl, 1.3) * .6, .28);
}
const Z_POGLOSEM = new Set(['okno', 'okno-zam', 'motyw', 'ok', 'wszystkie', 'wyslano', 'gen-start', 'gen-koniec']);      // dzwonki i „ruchy okien”; klik, odhaczenie i błąd zostają suche
/** Do której magistrali tora trafia efekt: z pogłosem (dzwonki, okna) albo suchej (klik, odhaczenie, błąd). */
export const magistralaEfektu = (tor, nazwa) => (Z_POGLOSEM.has(nazwa) ? tor.efR : tor.ef);

/* ------------------------------ podkład (synth-wave) ------------------------------ */
export const TEMPO = 96;
export const KROK = 60 / TEMPO / 4;      // szesnastka
export const GLOSNOSC_MUZYKI = 1.2;      // docelowe wzmocnienie podkładu (tło: wyraźnie ciszej niż efekty)
export const TAKT = KROK * 16;
const AKORDY = [
  { baz: 45, ton: [57, 60, 64], lead: [[0, 76], [6, 72], [10, 69]] },       // Am
  { baz: 41, ton: [53, 57, 60], lead: [[0, 77], [6, 72], [12, 69]] },       // F
  { baz: 48, ton: [55, 60, 64], lead: [[0, 79], [6, 76], [10, 72]] },       // C
  { baz: 43, ton: [55, 59, 62], lead: [[0, 74], [6, 79], [12, 71]] }        // G
];
const WZOR_ARP = [0, 1, 2, 3, 2, 1, 2, 3];
/** Buduje tor podkładu i zwraca { bus, duck, planTakt(numerTaktu, czasPoczatku) }. pog (opcjonalnie): węzeł wysyłki do pogłosu (zbudujTor().pogMuzyki).
 *  Pętla 8 taktów: akordy Am–F–C–G dwa razy; w drugiej czwórce melodia z vibrato. Brzmienie: szeroki pad (każda nuta w innym miejscu panoramy), arpeggio z echem „ping-pong”,
 *  bas, cicha perkusja, „pompowanie” padu i arpeggia w rytm stopy (jak sidechain w muzyce klubowej), filtr, który otwiera się w ciągu pętli, krótkie wypełnienie przed powrotem. */
export function zbudujMuzyke(c, cel, pog) {
  const bus = c.createGain(); bus.gain.value = 0.0001; const duck = c.createGain(); duck.gain.value = 1; bus.connect(duck); duck.connect(cel);
  const sucho = c.createGain(); sucho.connect(bus);
  const pompa = c.createGain(); pompa.gain.setValueAtTime(1, 0); pompa.connect(sucho);      // pad, arpeggio i melodia przechodzą tędy: gain opada na każdej stopie i wraca
  const wysylka = (zrodlo, ile) => { if (!pog) return; const g = c.createGain(); g.gain.value = ile; zrodlo.connect(g); g.connect(pog); };
  // echo „ping-pong”: powtórki na przemian w lewym i prawym kanale, coraz ciemniejsze
  const dL = c.createDelay(1.5), dR = c.createDelay(1.5); dL.delayTime.value = dR.delayTime.value = 60 / TEMPO * .75;
  const lpE = c.createBiquadFilter(); lpE.type = 'lowpass'; lpE.frequency.value = 2400; const fb = c.createGain(); fb.gain.value = .36;
  const pL = c.createStereoPanner(), pR = c.createStereoPanner(); pL.pan.value = -.65; pR.pan.value = .65; const wet = c.createGain(); wet.gain.value = .34;
  const doEcha = c.createGain(); doEcha.connect(dL); dL.connect(pL); pL.connect(wet); dL.connect(lpE); lpE.connect(dR); dR.connect(pR); pR.connect(wet); dR.connect(fb); fb.connect(dL); wet.connect(bus);
  const arpWyj = c.createGain(); arpWyj.connect(pompa); arpWyj.connect(doEcha); wysylka(arpWyj, .14);
  const leadWyj = c.createGain(); leadWyj.connect(pompa); const leadEcho = c.createGain(); leadEcho.gain.value = 1.6; leadWyj.connect(leadEcho); leadEcho.connect(doEcha); wysylka(leadWyj, .5);
  const padWyj = c.createGain(); padWyj.connect(pompa); wysylka(padWyj, .3);
  function planTakt(takt, t0) {
    const ak = AKORDY[takt % 4], faza = takt % 8, druga = faza >= 4, ostatni = takt % 4 === 3;
    // pompowanie: na każdej stopie (kroki 0, 4, 8, 12) pad/arpeggio schodzą do 40% i w ćwierć sekundy wracają
    [0, 4, 8, 12].forEach(st => { const t = t0 + st * KROK; pompa.gain.setValueAtTime(.4, t); pompa.gain.linearRampToValueAtTime(1, t + .26); });
    // pad: nuty akordu rozstawione w panoramie, filtr powoli się otwiera w ciągu ośmiu taktów
    const padF = c.createBiquadFilter(); padF.type = 'lowpass'; padF.frequency.value = 800 + 1100 * (faza / 7); padF.Q.value = .5;
    const padG = c.createGain(); padG.gain.setValueAtTime(0.0001, t0); padG.gain.exponentialRampToValueAtTime(.09, t0 + .7); padG.gain.setValueAtTime(.09, t0 + TAKT - .5); padG.gain.exponentialRampToValueAtTime(0.0001, t0 + TAKT + .25);
    padF.connect(padG); padG.connect(padWyj);
    ak.ton.forEach((n, i) => { const pn = c.createStereoPanner(); pn.pan.value = [-.5, 0, .5][i]; pn.connect(padF);
      [-7, 7].forEach(det => { const o = c.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mid(n); o.detune.value = det; const og = c.createGain(); og.gain.value = .3; o.connect(og); og.connect(pn); o.start(t0); o.stop(t0 + TAKT + .3); }); });
    // arpeggio szesnastkowe z echem; im dalej w pętli, tym jaśniejsze
    const nutyArp = [ak.ton[0] + 12, ak.ton[1] + 12, ak.ton[2] + 12, ak.ton[0] + 24];
    for (let s = 0; s < 16; s++) {
      const n = nutyArp[WZOR_ARP[s % 8]] + (druga && s % 8 === 7 ? 12 : 0);
      ton(c, arpWyj, { t: t0 + s * KROK, f: mid(n), d: KROK * 1.9, g: s % 4 === 0 ? .072 : .054, a: .004, typ: 'sawtooth', filtr: { typ: 'lowpass', f: 3000 + 450 * faza, f2: 600, q: 2.2 } });
    }
    // bas: sinus z piłą pod spodem, synkopowy rytm
    [0, 3, 6, 8, 11, 14].forEach(s => {
      const t = t0 + s * KROK, f = mid(ak.baz);
      ton(c, sucho, { t, f, d: KROK * 2.6, g: .055, a: .006 });
      ton(c, sucho, { t, f, d: KROK * 2.6, g: .066, a: .006, typ: 'sawtooth', filtr: { typ: 'lowpass', f: 480, q: .8 } });      // piła z harmonicznymi: bas słychać też na małych głośnikach
    });
    // perkusja bardzo cicha: stopa na „raz”, klaśnięcie na „dwa” i „cztery”, hi-hat na ósemkach
    [0, 4, 8, 12].forEach(s => ton(c, sucho, { t: t0 + s * KROK, f: 140, f2: 42, d: .2, g: .09, a: .002 }));
    [4, 12].forEach(s => { szum(c, sucho, { t: t0 + s * KROK, d: .15, g: .05, f: 1700, q: .9 }); szum(c, sucho, { t: t0 + s * KROK + .018, d: .1, g: .03, f: 2100, q: .9 }); });
    for (let s = 0; s < 16; s += 2) szum(c, sucho, { t: t0 + s * KROK, d: s % 4 === 2 ? .07 : .035, g: s % 4 === 2 ? .018 : .01, f: 7500, q: .6, typ: 'highpass' });
    // melodia z vibrato (druga połowa pętli); dzwoneczek na pierwszej dobie pętli
    if (druga) ak.lead.forEach(([s, n]) => ton(c, leadWyj, { t: t0 + s * KROK, f: mid(n), d: KROK * 5, g: .075, a: .02, typ: 'triangle', vib: { hz: 5.2, cent: 7 } }));
    if (faza === 0) dzwonek(c, leadWyj, t0, 93, { g: .03, d: 1.3 });
    // zakończenie frazy: „przelot” przed powrotem do początku, a przed końcem pętli krótkie wypełnienie werblami
    if (ostatni) szum(c, sucho, { t: t0 + TAKT - KROK * 3, d: KROK * 3, g: .03, f: 600, f2: 5000, q: 1.2 });
    if (faza === 7) [12, 13, 14, 15].forEach((s, i) => szum(c, sucho, { t: t0 + s * KROK, d: .09, g: .03 + .014 * i, f: 1900, q: .9 }));
  }
  return { bus, duck, planTakt };
}

/* ------------------------------ sterowanie ------------------------------ */
const KLUCZ_EFEKTY = 'pmt-ui-dzwiek', KLUCZ_MUZYKA = 'pmt-ui-muzyka';
const BEZ_KLIKU = '.p-znak,[data-zamknij],.ark-zam,#motyw,[data-motyw],#dzwiek,#muzyka,[data-dzwiek]';      // te elementy mają własny dźwięk albo działają cicho
const KLIKALNE = 'button,[role="button"],a.przycisk,label.przycisk,[data-akcja]';
const ODSTEP_MS = { klik: 45, okno: 120, 'okno-zam': 120, odhacz: 60, 'odhacz-wyl': 60, ok: 220, zle: 220 };      // ten sam efekt nie częściej niż co tyle ms (kilka naraz brzmi jak szum)
const odczyt = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const zapis = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* bez pamięci przeglądarki ustawienie obowiązuje do zamknięcia karty */ } };

function utworz() {
  let doc = null, c = null, tor = null, mus = null, timer = 0, takt = 0, nastepny = 0, init = false;
  let efektyWl = odczyt(KLUCZ_EFEKTY) !== '0', muzykaWl = odczyt(KLUCZ_MUZYKA) === '1';
  const log = [], licznik = {}, ostatnio = {}, sluchacze = [];
  const AC = typeof window !== 'undefined' ? (window.AudioContext || window.webkitAudioContext) : null;
  const powiadom = () => sluchacze.forEach(f => { try { f(); } catch (e) { /* słuchacz nie psuje dźwięku */ } });

  function kontekst(zGestu) {
    if (!AC) return null;
    if (!c) {
      if (!zGestu) return null;      // bez gestu użytkownika przeglądarka i tak nie pozwoli grać (i wypisze ostrzeżenie w konsoli)
      try { c = new AC({ latencyHint: 'interactive' }); } catch (e) { return null; }
      tor = zbudujTor(c, c.destination);
    }
    if (c.state === 'suspended') { try { c.resume().catch(() => {}); } catch (e) { /* kontekst zamknięty */ } }
    return c;
  }
  function efekt(nazwa, opcje = {}) {
    if (!efektyWl && !opcje.wymus) return false;
    log.push(nazwa); if (log.length > 80) log.shift(); licznik[nazwa] = (licznik[nazwa] || 0) + 1;
    if (!c || c.state !== 'running' || (doc && doc.hidden)) return false;
    const teraz = Date.now(), min = ODSTEP_MS[nazwa] || 0; if (min && ostatnio[nazwa] && teraz - ostatnio[nazwa] < min) return false; ostatnio[nazwa] = teraz;
    try { const t = c.currentTime + .005, dl = zbudujEfekt(c, magistralaEfektu(tor, nazwa), nazwa, t); if (dl > 0 && mus && nazwa !== 'klik') przygluszMuzyke(mus.duck, t, dl); return dl > 0; } catch (e) { return false; }
  }
  function tik() {
    if (!mus || !c) return;
    while (nastepny < c.currentTime + .7) { mus.planTakt(takt, nastepny); takt++; nastepny += TAKT; }
  }
  function startMuzyki() {
    if (mus) return true;
    const k = kontekst(true); if (!k) return false;
    mus = zbudujMuzyke(k, tor.master, tor.pogMuzyki); const t = k.currentTime;
    mus.bus.gain.cancelScheduledValues(t); mus.bus.gain.setValueAtTime(0.0001, t); mus.bus.gain.exponentialRampToValueAtTime(GLOSNOSC_MUZYKI, t + 1.6);
    takt = 0; nastepny = t + .12; tik(); timer = setInterval(tik, 90); return true;
  }
  function stopMuzyki() {
    if (!mus) return; const m = mus; mus = null; clearInterval(timer); timer = 0;
    if (c) { const t = c.currentTime; m.bus.gain.cancelScheduledValues(t); m.bus.gain.setValueAtTime(Math.max(m.bus.gain.value, .0001), t); m.bus.gain.exponentialRampToValueAtTime(.0001, t + .35); setTimeout(() => { try { m.bus.disconnect(); } catch (e) { /* już odłączony */ } }, 600); }
  }
  function odswiezPrzyciski() {
    if (!doc) return;
    doc.querySelectorAll('#dzwiek,[data-dzwiek="efekty"]').forEach(b => { b.setAttribute('aria-pressed', String(efektyWl)); });
    doc.querySelectorAll('#muzyka,[data-dzwiek="muzyka"]').forEach(b => { b.setAttribute('aria-pressed', String(muzykaWl && !!mus)); });
    const g = doc.querySelector('#dzwiek use'); if (g) g.setAttribute('href', efektyWl ? '#i-glosnik' : '#i-glosnik-wyl');
    const e = doc.querySelector('#dzwiek'); if (e) e.setAttribute('aria-label', efektyWl ? 'Dźwięki: włączone — kliknij, żeby wyciszyć' : 'Dźwięki: wyciszone — kliknij, żeby włączyć');
    const m = doc.querySelector('#muzyka'); if (m) m.setAttribute('aria-label', muzykaWl && mus ? 'Muzyka w tle: gra — kliknij, żeby wyłączyć' : 'Muzyka w tle: wyłączona — kliknij, żeby włączyć');
  }
  function ustawEfekty(w, zGestu = true) {
    efektyWl = !!w; zapis(KLUCZ_EFEKTY, efektyWl ? '1' : '0');
    if (efektyWl && zGestu) { kontekst(true); efekt('klik', { wymus: true }); }
    odswiezPrzyciski(); powiadom();
  }
  function ustawMuzyke(w, zGestu = true) {
    if (w) { if (zGestu && !startMuzyki()) { muzykaWl = false; zapis(KLUCZ_MUZYKA, '0'); odswiezPrzyciski(); powiadom(); return false; } muzykaWl = true; }
    else { muzykaWl = false; stopMuzyki(); }
    zapis(KLUCZ_MUZYKA, muzykaWl ? '1' : '0'); odswiezPrzyciski(); powiadom(); return muzykaWl;
  }
  /** Pierwszy prawdziwy gest użytkownika: powstaje kontekst audio; zapamiętany podkład rusza dopiero teraz (wcześniej przeglądarka by go zablokowała). */
  function odblokuj(e) {
    if (!e.isTrusted) return; const k = kontekst(true); if (!k) return;
    if (muzykaWl && !mus) { startMuzyki(); odswiezPrzyciski(); powiadom(); }
  }
  function podepnij(d) {
    doc = d;
    ['pointerdown', 'keydown', 'touchend'].forEach(z => doc.addEventListener(z, odblokuj, { capture: true, passive: true }));
    doc.addEventListener('click', e => {
      if (!e.isTrusted || !efektyWl) return;
      const el = e.target && e.target.closest ? e.target.closest(KLIKALNE) : null;
      if (!el || el.disabled || el.getAttribute('aria-disabled') === 'true' || el.matches(BEZ_KLIKU)) return;
      efekt('klik');
    }, true);
    const sw = (sel, f) => doc.querySelectorAll(sel).forEach(b => b.addEventListener('click', e => { if (e.isTrusted) f(); }));
    sw('#dzwiek,[data-dzwiek="efekty"]', () => ustawEfekty(!efektyWl));
    sw('#muzyka,[data-dzwiek="muzyka"]', () => ustawMuzyke(!(muzykaWl && !!mus)));
    doc.addEventListener('visibilitychange', () => {
      if (!c) return;
      if (doc.hidden) { try { c.suspend().catch(() => {}); } catch (e) { /* kontekst zamknięty */ } }      // karta w tle nie gra i nie zjada baterii
      else if (efektyWl || (muzykaWl && mus)) { try { c.resume().catch(() => {}); } catch (e) { /* kontekst zamknięty */ } }
    });
    odswiezPrzyciski();
  }
  return {
    init(d) { if (init || !d) return; init = true; podepnij(d); },
    efekt, ustawEfekty, ustawMuzyke, odswiezPrzyciski,
    efektyWl: () => efektyWl, muzykaWl: () => muzykaWl, muzykaGra: () => !!mus, stan: () => (c ? c.state : 'brak'),
    naZmiane: f => sluchacze.push(f), log, licznik,      // dziennik ostatnich efektów i liczniki od początku (dla testów)
    // tylko do testów: ile taktów podkładu już zaplanowano
    taktow: () => takt
  };
}
export const dzwiek = utworz();
if (globalThis.__testy) globalThis.__pmtDzwiek = dzwiek;      // tylko dla testów (strona z ustawionym window.__testy)
