// PMT Planer (web) — karuzela 3D: karty stoją na okręgu, cały czas zwrócone do widza (lekko odchylone do środka), przednia jest największa, tylne mniejsze, wyżej i przyciemnione —
// dzięki temu widać wszystkie, a nie tylko te z przodu. Obrót: przeciąganie myszą/palcem (z bezwładnością i zatrzaśnięciem na karcie), strzałki, kółko myszy, kliknięcie karty z boku.
// Bez „życia” (testy, tryb spokojny, „Ogranicz ruch”) wszystko dzieje się natychmiast, bez płynnego dojeżdżania i bez automatycznego obrotu. Czysty DOM — niczego nie wie o dokumentach.

const stopnie = r => r * Math.PI / 180;
const roznicaKata = (a, b) => (((a - b) % 360) + 540) % 360 - 180;

/** scena: element z perspektywą, pier: kontener kart (dzieci = karty o rozmiarze W×H). opcje: { W, H, zycie, start (numer karty z przodu na początku), auto: () => bool, onWybor(i) (klik w przednią kartę), onZmiana(i) (zmiana przedniej karty) }. */
export function karuzela(scena, pier, opcje) {
  const { W, H } = opcje, zycie = !!opcje.zycie;
  let n = 0, krok = 360, R = 300, Rx = 300, zoom = 1, kat = 0, cel = null, v = 0, przeciaganie = false, przesunieto = false, startX = 0, ostatniX = 0, spokoj = 0, raf = 0, ostatniaPrzod = -1, zywa = true;

  function przelicz() {
    n = pier.children.length; krok = n ? 360 / n : 360;
    R = n < 3 ? W * 0.75 : Math.max(W * 1.15, (W / 2 + 64) / Math.tan(Math.PI / n));
    const cw = scena.clientWidth || 800, ch = scena.clientHeight || 520;
    zoom = Math.max(.4, Math.min(1, ch / (H + 128)));      // 128 = zapas na tylne karty, uniesione nad przednią
    Rx = Math.max(W * 0.62, Math.min(R, (cw / zoom - W) / 2 - 8));      // w wąskim oknie pierścień się spłaszcza z boków (głębia zostaje)
    rysuj();
  }
  function rysuj() {
    pier.style.transform = `scale(${zoom})`;
    let naj = 0, najA = 999;
    [...pier.children].forEach((k, i) => {
      const a = roznicaKata(i * krok + kat, 0), r = stopnie(a), c = Math.cos(r), blisko = (c + 1) / 2;
      const x = Rx * Math.sin(r), z = R * c - R, y = -(1 - c) * 44, odchyl = Math.max(-58, Math.min(58, -a * 0.5));
      k.style.transform = `translate3d(${x.toFixed(1)}px,${y.toFixed(1)}px,${z.toFixed(1)}px) rotateY(${odchyl.toFixed(1)}deg)`;
      k.style.opacity = (0.42 + 0.58 * Math.pow(blisko, 1.1)).toFixed(3);
      k.style.filter = blisko < .6 ? `saturate(${(0.6 + blisko * 0.6).toFixed(2)}) blur(${((0.6 - blisko) * 2.4).toFixed(1)}px)` : 'none';
      k.style.zIndex = String(Math.round(blisko * 100));
      k.classList.toggle('przod', false);
      if (Math.abs(a) < najA) { najA = Math.abs(a); naj = i; }
    });
    const k = pier.children[naj]; if (k) { k.classList.add('przod'); k.setAttribute('aria-current', 'true'); }
    [...pier.children].forEach((x, i) => { if (i !== naj) x.removeAttribute('aria-current'); });
    if (naj !== ostatniaPrzod) { ostatniaPrzod = naj; opcje.onZmiana && opcje.onZmiana(naj); }
  }
  const przod = () => ostatniaPrzod < 0 ? 0 : ostatniaPrzod;
  const naNajblizszy = () => Math.round(kat / krok) * krok;
  const docelowyKat = i => { const d = roznicaKata(-i * krok, kat); return kat + d; };
  function start() { if (!raf && zywa) raf = requestAnimationFrame(klatka); }
  function klatka() {
    raf = 0; if (!scena.isConnected) { zywa = false; document.removeEventListener('visibilitychange', naWidocznosc); return; }
    if (!przeciaganie) {
      if (Math.abs(v) > 0.02) { kat += v; v *= 0.94; if (Math.abs(v) <= 0.02) { v = 0; cel = naNajblizszy(); } }
      else if (cel !== null) { const d = cel - kat; if (Math.abs(d) < 0.05) { kat = cel; cel = null; } else kat += d * 0.14; }
      else if (opcje.auto && opcje.auto() && spokoj > 150) kat += 0.13;
      spokoj++;
    }
    rysuj();
    if (przeciaganie || cel !== null || Math.abs(v) > 0.02 || (opcje.auto && opcje.auto())) raf = requestAnimationFrame(klatka);
  }
  function ustawCel(c) { v = 0; spokoj = 0; if (zycie) { cel = c; start(); } else { kat = c; cel = null; rysuj(); } }
  const doKarty = i => ustawCel(docelowyKat(i));
  const kroki = s => ustawCel((cel === null ? naNajblizszy() : cel) + s * krok);

  scena.addEventListener('pointerdown', e => {
    if (e.button !== undefined && e.button !== 0) return; przeciaganie = true; przesunieto = false; startX = ostatniX = e.clientX; v = 0; cel = null; spokoj = 0; scena.classList.add('chwyt');
    start();      // przechwyt wskaźnika dopiero po przesunięciu: przechwycony wskaźnik kieruje „click” na scenę i kliknięcie karty by nie zadziałało
  });
  scena.addEventListener('pointermove', e => {
    if (!przeciaganie) return; const dx = e.clientX - ostatniX; if (!przesunieto && Math.abs(e.clientX - startX) > 6) { przesunieto = true; try { scena.setPointerCapture(e.pointerId); } catch (x) { /* brak przechwytu: obrót nadal działa w obrębie sceny */ } }
    kat += dx * 0.32; v = zycie ? dx * 0.32 * 0.9 + v * 0.1 : 0; ostatniX = e.clientX; spokoj = 0; if (!zycie) rysuj();
  });
  const koniec = () => {
    if (!przeciaganie) return; przeciaganie = false; scena.classList.remove('chwyt');
    if (!zycie || Math.abs(v) < 0.4) { v = 0; ustawCel(naNajblizszy()); } start(); setTimeout(() => { przesunieto = false; }, 0);
  };
  scena.addEventListener('pointerup', koniec); scena.addEventListener('pointercancel', koniec);
  // pętla klatek kończy się, gdy auto() mówi „stój” (kursor lub fokus na scenie, ukryta karta) — wznawiam ją, gdy ten powód mija
  const naWidocznosc = () => { if (!document.hidden) start(); };
  scena.addEventListener('pointerleave', start); scena.addEventListener('focusout', start); document.addEventListener('visibilitychange', naWidocznosc);
  scena.addEventListener('wheel', e => { if (Math.abs(e.deltaY) + Math.abs(e.deltaX) < 4) return; e.preventDefault(); kroki((e.deltaY + e.deltaX) > 0 ? -1 : 1); }, { passive: false });
  scena.addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft') { e.preventDefault(); kroki(1); } else if (e.key === 'ArrowRight') { e.preventDefault(); kroki(-1); }
    else if (e.key === 'Home') { e.preventDefault(); doKarty(0); } else if (e.key === 'End') { e.preventDefault(); doKarty(n - 1); }
    else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); opcje.onWybor && opcje.onWybor(przod()); }
  });
  pier.addEventListener('click', e => {
    if (przesunieto) return; const k = e.target.closest('.karta3d'); if (!k || !pier.contains(k)) return;
    const i = [...pier.children].indexOf(k); if (i < 0) return;
    if (i === przod()) { if (!e.target.closest('button')) opcje.onWybor && opcje.onWybor(i); } else doKarty(i);
  });
  const naRozmiar = () => przelicz(), obserwator = typeof ResizeObserver === 'function' ? new ResizeObserver(naRozmiar) : null;      // rozmiar sceny zmienia się też bez zmiany okna (układ okna dokumentów, czcionki)
  if (obserwator) obserwator.observe(scena); else addEventListener('resize', naRozmiar);
  if (opcje.start > 0 && opcje.start < pier.children.length) kat = -opcje.start * (360 / pier.children.length);      // wracamy do karuzeli z oglądanym dokumentem z przodu
  przelicz(); start();
  return { przelicz, doKarty, kroki, przod, odswiez: rysuj, zniszcz() { zywa = false; if (raf) cancelAnimationFrame(raf); raf = 0; document.removeEventListener('visibilitychange', naWidocznosc); if (obserwator) obserwator.disconnect(); else removeEventListener('resize', naRozmiar); } };
}
