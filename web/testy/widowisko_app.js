// Widowisko generowania (js/widowisko.js): punkty GPS → trasa → stos → wachlarz dokumentów z prawdziwymi kwotami.
// Część 1: sam moduł sterowany z testu (fazy, dopełzanie postępu, wachlarz, pominięcie kliknięciem i Esc — kliknięcie nie trafia w pulpit, sprzątanie).
// Część 2: prawdziwe generowanie z „życiem” — pokaz pojawia się, przechodzi wszystkie fazy, pokazuje kwoty z silnika i znika; pulpit działa normalnie.
// Część 3: przy „Ogranicz ruch” w systemie pokazu nie ma wcale. (Domyślnie testy mają „życie” wyłączone — wtedy też go nie ma; sprawdzają to pozostałe testy przeglądarkowe.)
// NODE_PATH=/opt/node22/lib/node_modules node widowisko_app.js
const { otworz, generuj } = require('./wspolne');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const bezSp = s => String(s).replace(/\s/g, '');
  const dane = async p => {
    await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
    await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
    await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
    await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  };
  let t = await otworz({ w: 1440, h: 900, bezZycia: false }); let p = t.p;
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });

  /* ---- część 1: sam moduł ---- */
  const w1 = await p.evaluate(async () => {
    const { widowisko } = await import('/js/widowisko.js'); window.__w = widowisko({ fmt: x => x.toFixed(2) }); window.__klik = 0; document.body.addEventListener('click', () => { window.__klik++; });
    const stan = () => { const s = document.querySelector('#gen-scena'); return s && { klasy: s.className, on: s.querySelectorAll('.gen-punkty circle.on').length, kropek: s.querySelectorAll('.gen-punkty circle').length, off: Number(s.querySelector('.gen-sciezka').style.strokeDashoffset), faza: s.querySelector('.gen-faza').textContent, proc: s.querySelector('.gen-proc').textContent, nakladka: getComputedStyle(s).pointerEvents }; };
    const czekaj = ms => new Promise(r => setTimeout(r, ms)); const o = {};
    window.__w.start(); o.start = stan();
    window.__w.postep('Pobieranie współrzędnych GPS...', 0.10); await czekaj(1600); o.gps = stan();
    window.__w.postep('Generowanie tras...', 0.40); await czekaj(1600); o.trasa = stan();
    window.__w.postep('Rysowanie dokumentów PDF...', 0.85); await czekaj(900); o.druk = stan();
    return o;
  });
  ok('start: scena jest na stronie, faza „GPS”, 7 punktów, żaden jeszcze nie świeci, napis „Start…”, 0%; nie blokuje kliknięć pod spodem (pointer-events: none)', w1.start.klasy.includes('faza-gps') && w1.start.kropek === 7 && w1.start.on === 0 && w1.start.faza === 'Start…' && w1.start.proc === '0%' && w1.start.nakladka === 'none', JSON.stringify(w1.start));
  ok('krok silnika „GPS 10 %”: tekst z silnika (kropki zamiast trzech kropek), postęp sam dopełza do progu następnego kroku, ale go nie przekracza (<40 %)', w1.gps.faza === 'Pobieranie współrzędnych GPS…' && w1.gps.on >= 1 && w1.gps.on <= 7 && parseInt(w1.gps.proc) > 10 && parseInt(w1.gps.proc) < 40, `${w1.gps.on}/7, ${w1.gps.proc}`);
  ok('krok „trasy 40 %”: faza trasy, wszystkie 7 punktów świeci, ścieżka zaczyna się rysować (dashoffset < 1)', w1.trasa.klasy.includes('faza-trasa') && !w1.trasa.klasy.includes('faza-gps') && w1.trasa.on === 7 && w1.trasa.off < 1 && w1.trasa.off > 0, JSON.stringify(w1.trasa));
  ok('krok „PDF 85 %”: faza druku (stos kartek), ścieżka prawie cała, postęp poniżej 100 % aż do wyniku', w1.druk.klasy.includes('faza-druk') && w1.druk.off < 0.2 && parseInt(w1.druk.proc) >= 85 && parseInt(w1.druk.proc) < 100, JSON.stringify(w1.druk));
  const wynik1 = p.evaluate(() => window.__w.zakoncz({ polecenia: [{ nr: 1, kw: 805.7 }, { nr: 2, kw: 798.95 }], suma: 1604.65 }).then(() => 'koniec'));
  await p.waitForTimeout(500);
  const kaf = await p.evaluate(() => { const s = document.querySelector('#gen-scena'); return s && { klasy: s.className, znaki: [...s.querySelectorAll('.gen-kafel b')].map(x => x.textContent), faza: s.querySelector('.gen-faza').textContent, proc: s.querySelector('.gen-proc').textContent }; });
  ok('wynik: faza „wynik”, wachlarz z 3 kafli (P1, P2, R), „Gotowe”, 100%', kaf && kaf.klasy.includes('faza-wynik') && kaf.znaki.join() === 'P1,P2,R' && kaf.faza === 'Gotowe' && kaf.proc === '100%', JSON.stringify(kaf));
  await p.waitForTimeout(1100);
  const kw = await p.evaluate(() => { const s = document.querySelector('#gen-scena'); return s && { kwoty: [...s.querySelectorAll('.gen-kafel .num')].map(x => x.textContent), razem: s.querySelector('.gen-razem').textContent }; });
  ok('kwoty na kaflach i suma „Razem” liczą się w górę do prawdziwych wartości (805.70, 798.95, 1604.65; „2 polecenia i rozliczenie”)', kw && kw.kwoty.join() === '805.70,798.95,1604.65' && kw.razem === 'Razem 1604.65 zł · 2 polecenia i rozliczenie', JSON.stringify(kw));
  ok('pokaz kończy się sam, scena znika ze strony, a obietnica się rozwiązuje', (await wynik1) === 'koniec' && (await p.locator('#gen-scena').count()) === 0);
  await p.mouse.click(40, 40); await p.waitForTimeout(100);
  const klikPo = await p.evaluate(() => window.__klik);
  ok('po pokazie kliknięcia działają normalnie (nasłuch pominięcia zdjęty)', klikPo === 1, String(klikPo));

  /* pominięcie kliknięciem: pokaz kończy się od razu, a kliknięcie NIE trafia w pulpit */
  const skok = async (jak) => {
    await p.evaluate(() => { window.__klik = 0; window.__w = null; window.__tk = 0; const znacznik = () => { window.__tk = window.__tk || performance.now(); }; document.addEventListener('click', znacznik, true); document.addEventListener('keydown', znacznik, true); window.__znacznik = znacznik;
      return import('/js/widowisko.js').then(({ widowisko }) => { window.__w = widowisko({ fmt: x => x.toFixed(2) }); window.__w.start(); window.__w.postep('Rysowanie dokumentów PDF...', 0.85); window.__t0 = performance.now(); window.__sk = window.__w.zakoncz({ polecenia: [{ nr: 1, kw: 100 }], suma: 100 }).then(() => ({ po: performance.now() - window.__tk, kiedy: window.__tk - window.__t0 })); }); });
    await p.waitForTimeout(450);
    if (jak === 'klik') await p.mouse.click(300, 500); else await p.keyboard.press('Escape');
    const r = await p.evaluate(() => window.__sk); await p.waitForTimeout(100);
    await p.evaluate(() => { document.removeEventListener('click', window.__znacznik, true); document.removeEventListener('keydown', window.__znacznik, true); });
    return { ...r, klik: await p.evaluate(() => window.__klik), scena: await p.locator('#gen-scena').count() };
  };
  const sk1 = await skok('klik');
  ok('kliknięcie w czasie pokazu wyników pomija go (kończy się w < 400 ms od kliknięcia, kliknięcie padło przed naturalnym końcem ~2,2 s), scena znika, a kliknięcie jest połknięte — nie trafia w pulpit pod spodem', sk1.po < 400 && sk1.kiedy < 2000 && sk1.scena === 0 && sk1.klik === 0, JSON.stringify(sk1));
  const sk2 = await skok('esc');
  ok('Esc też pomija pokaz', sk2.po < 400 && sk2.kiedy < 2000 && sk2.scena === 0, JSON.stringify(sk2));
  const przerw = await p.evaluate(() => { return import('/js/widowisko.js').then(({ widowisko }) => { const w = widowisko(); w.start(); const byla = !!document.querySelector('#gen-scena'); w.przerwij(); w.postep('x', .5); return { byla, jest: !!document.querySelector('#gen-scena') }; }); });
  ok('przerwij() natychmiast sprząta scenę (błąd lub przerwanie generowania), a późny postęp niczego nie psuje', przerw.byla && !przerw.jest);
  const wisi = await p.evaluate(() => import('/js/widowisko.js').then(async ({ widowisko }) => { const w = widowisko(); w.start(); const pr = w.zakoncz({ polecenia: [{ nr: 1, kw: 1 }], suma: 1 }); await new Promise(r => setTimeout(r, 200)); w.przerwij(); return Promise.race([pr.then(() => 'koniec'), new Promise(r => setTimeout(() => r('wisi'), 800))]); }));
  ok('przerwij() w trakcie pokazu wyników rozwiązuje obietnicę zakoncz() (nic nie wisi) i sprząta scenę', wisi === 'koniec' && (await p.locator('#gen-scena').count()) === 0, wisi);
  ok('bez błędów w konsoli (część 1)', t.bledy.length === 0, t.bledy.slice(0, 2).join(' | '));

  /* ---- część 2: prawdziwe generowanie z „życiem” ---- */
  await dane(p);
  await p.evaluate(() => {      // rejestrator: MutationObserver łapie KAŻDĄ zmianę napisu i fazy (próbkowanie co 100 ms gubiło krótkie napisy przy obciążonej stronie)
    window.__gen = { fazy: [], maxOn: 0, kafle: [], kwoty: [], teksty: new Set(), anim: new Set() };
    const zapisz = () => { const s = document.querySelector('#gen-scena'); if (!s) return; const g = window.__gen; for (const f of ['gps', 'trasa', 'druk', 'wynik']) if (s.classList.contains('faza-' + f) && !g.fazy.includes(f)) g.fazy.push(f); g.maxOn = Math.max(g.maxOn, s.querySelectorAll('.gen-punkty circle.on').length); g.teksty.add(s.querySelector('.gen-faza').textContent); document.getAnimations().forEach(x => { if (x.animationName) g.anim.add(x.animationName); }); const k = [...s.querySelectorAll('.gen-kafel b')].map(x => x.textContent); if (k.length) { g.kafle = k; g.kwoty = [...s.querySelectorAll('.gen-kafel .num')].map(x => x.textContent); g.razem = s.querySelector('.gen-razem').textContent; } };
    new MutationObserver(zapisz).observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true }); setInterval(zapisz, 100);
  });
  const pojawil = p.waitForSelector('#gen-scena', { state: 'attached', timeout: 240000 });
  await generuj(p); await pojawil;
  const g = await p.evaluate(() => ({ ...window.__gen, teksty: [...window.__gen.teksty], anim: [...window.__gen.anim] }));
  const W = await p.evaluate(() => Object.values(window.__pmtDane.czytaj().miesiace)[0].wynik);
  ok('podczas generowania pojawia się pokaz i przechodzi wszystkie fazy: GPS → trasy → druk → wynik', ['gps', 'trasa', 'druk', 'wynik'].every(f => g.fazy.includes(f)), g.fazy.join('→'));
  ok('ruch widowiska naprawdę działa mimo trybu spokojnego (`.spokojne *{animation:none}`): wejście sceny, błysk punktów, kartki stosu, wachlarz — wszystko jako animacje „zycie-…”', ['zycie-gen-wejscie', 'zycie-gen-punkt', 'zycie-gen-kartka', 'zycie-gen-wachlarz'].every(n => g.anim.includes(n)), g.anim.join(' '));
  ok('punkty GPS zapaliły się wszystkie 7, prawdziwe napisy silnika były widoczne („Klastrowanie GPS (Dzień n/m)…”, „Renderowanie pliku PDF (n/6)…”)', g.maxOn === 7 && g.teksty.includes('Generowanie tras…') && g.teksty.some(x => /^Klastrowanie GPS \(Dzień \d+\/\d+\)…$/.test(x)) && g.teksty.some(x => /^Renderowanie pliku PDF \(\d+\/\d+\)…$/.test(x)), g.maxOn + ' | ' + g.teksty.join(' / '));
  const nr = W.dokumenty.map(x => 'P' + x.nr).concat('R'), suma = W.dokumenty.reduce((s, x) => s + x.kw, 0);
  ok('wachlarz pokazał dokładnie dokumenty z wyniku silnika (P1…P6 i R) z ich kwotami; suma „Razem” = suma poleceń', g.kafle.join() === nr.join() && g.kwoty.slice(0, -1).every((k, i) => Math.abs(parseFloat(bezSp(k).replace(',', '.')) - W.dokumenty[i].kw) < 0.005) && Math.abs(parseFloat(bezSp(g.kwoty[g.kwoty.length - 1]).replace(',', '.')) - suma) < 0.005 && bezSp(g.razem).includes(bezSp(suma.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, ' '))), `${g.kafle.join()} | ${g.kwoty.join(' ')} | ${g.razem}`);
  await p.waitForTimeout(600);
  ok('po pokazie scena zniknęła, pulpit jest w stanie „po generowaniu” (7 probówek) i działa', (await p.locator('#gen-scena').count()) === 0 && (await p.locator('#kA.po-gen').count()) === 1 && (await p.locator('#fiolki .fiolka').count()) === 7);
  ok('bez błędów w konsoli (część 2)', t.bledy.length === 0, t.bledy.slice(0, 2).join(' | '));
  await t.zamknij();

  /* ---- część 3: „Ogranicz ruch” w systemie → bez pokazu ---- */
  t = await otworz({ w: 1440, h: 900, bezZycia: false, ruch: 'reduce' }); p = t.p; await dane(p);
  await p.evaluate(() => { window.__byla = false; new MutationObserver(() => { if (document.querySelector('#gen-scena')) window.__byla = true; }).observe(document.body, { childList: true, subtree: true }); });
  await generuj(p); await p.waitForTimeout(800);
  ok('przy „Ogranicz ruch” pokazu nie ma wcale, a generowanie kończy się normalnie', (await p.evaluate(() => window.__byla)) === false && (await p.locator('#kA.po-gen').count()) === 1 && (await p.locator('#fiolki .fiolka').count()) === 7);
  ok('bez błędów w konsoli (część 3)', t.bledy.length === 0, t.bledy.slice(0, 2).join(' | '));
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('BŁĄD TESTU', e); process.exit(2); });
