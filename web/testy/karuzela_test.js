// Jednostkowy test js/karuzela.js na atrapie DOM i requestAnimationFrame: automatyczny obrót staje, gdy kursor albo fokus jest na scenie lub karta przeglądarki jest ukryta,
// i WRACA, gdy ten powód minie (zejście kursora, utrata fokusu, powrót do karty) — bez klikania. Uruchom: node karuzela_test.js
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  let kolejka = [];
  globalThis.requestAnimationFrame = f => { kolejka.push(f); return kolejka.length; };
  globalThis.cancelAnimationFrame = () => { kolejka = []; };
  globalThis.ResizeObserver = class { observe() {} disconnect() {} };
  const zdarzenia = () => ({ h: {}, addEventListener(t, f) { (this.h[t] = this.h[t] || []).push(f); }, removeEventListener(t, f) { this.h[t] = (this.h[t] || []).filter(x => x !== f); }, wyslij(t) { (this.h[t] || []).forEach(f => f({ type: t })); } });
  globalThis.document = Object.assign(zdarzenia(), { hidden: false });
  const el = () => Object.assign(zdarzenia(), { style: {}, classList: { toggle() {}, add() {}, remove() {} }, setAttribute() {}, removeAttribute() {}, isConnected: true, clientWidth: 800, clientHeight: 520 });
  const scena = el(), pier = el(); pier.children = [el(), el(), el(), el(), el()];
  const { karuzela } = await import('../js/karuzela.js');
  let kursor = false, fokus = false;
  const k = karuzela(scena, pier, { W: 232, H: 372, zycie: true, auto: () => !document.hidden && !kursor && !fokus });
  const krec = n => { for (let i = 0; i < n; i++) { const q = kolejka; kolejka = []; q.forEach(f => f()); } };
  const obraca = () => { const t0 = pier.children[0].style.transform; krec(30); return kolejka.length > 0 && pier.children[0].style.transform !== t0; };

  krec(200); ok('na starcie karuzela kręci się sama (pętla klatek trwa, karty się przesuwają)', obraca());
  kursor = true; krec(3); ok('kursor nad sceną: obrót staje (żadna klatka nie czeka)', kolejka.length === 0, String(kolejka.length));
  kursor = false; scena.wyslij('pointerleave'); krec(160); ok('kursor zszedł ze sceny: obrót wraca bez klikania', obraca());
  fokus = true; krec(3); ok('fokus na scenie: obrót staje', kolejka.length === 0);
  fokus = false; scena.wyslij('focusout'); krec(160); ok('fokus opuścił scenę: obrót wraca', obraca());
  document.hidden = true; krec(3); ok('ukryta karta przeglądarki: obrót staje', kolejka.length === 0);
  document.wyslij('visibilitychange'); ok('  …zdarzenie przy ukrywaniu karty nie budzi pętli', kolejka.length === 0);
  document.hidden = false; document.wyslij('visibilitychange'); krec(160); ok('powrót do karty: obrót wraca', obraca());
  k.zniszcz(); ok('zniszcz(): pętla zatrzymana i zdjęte nasłuchiwanie widoczności dokumentu', kolejka.length === 0 && (document.h.visibilitychange || []).length === 0);
  document.wyslij('visibilitychange'); scena.wyslij('pointerleave'); ok('  …po zniszczeniu nic jej już nie budzi', kolejka.length === 0);
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
