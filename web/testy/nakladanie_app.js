// Wykrywanie nakładającego się i wystającego tekstu w wielu rozmiarach okna (m.in. typowe laptopowe okna przeglądarki ze scalingiem 125%/150%).
// Tryb jak Firefox: bez View Transitions. NODE_PATH=/opt/node22/lib/node_modules node testy/nakladanie_app.js [motyw]
const { otworz } = require('./wspolne'); const path = require('path'); const fs = require('fs');
const ROZMIARY = process.env.ROZMIARY ? JSON.parse(process.env.ROZMIARY) : [[1920, 1080], [1536, 730], [1536, 864], [1440, 760], [1366, 650], [1280, 590], [1100, 640], [1024, 768], [960, 560], [900, 700], [820, 1100], [390, 844], [360, 640]];
const WYKRYJ = () => {
  const wyn = [], opis = e => e ? (e.id ? '#' + e.id : (e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : ''))) : '?';
  const widoczny = e => { for (let x = e; x && x !== document.documentElement; x = x.parentElement) { const c = getComputedStyle(x); if (c.display === 'none' || c.visibility === 'hidden' || Number(c.opacity) < 0.05) return false; if (x.hasAttribute && x.hasAttribute('hidden')) return false; } return true; };
  const przytnij = (r, e) => { let a = { l: r.left, t: r.top, r: r.right, b: r.bottom }; for (let x = e; x && x !== document.documentElement; x = x.parentElement) { const c = getComputedStyle(x); if (c.overflowX !== 'visible' || c.overflowY !== 'visible') { const b = x.getBoundingClientRect(); a = { l: Math.max(a.l, b.left), t: Math.max(a.t, b.top), r: Math.min(a.r, b.right), b: Math.min(a.b, b.bottom) }; } } return a.r - a.l > 1 && a.b - a.t > 1 ? a : null; };
  const tek = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = w.nextNode());) {
    const t = n.textContent.replace(/\s+/g, ' ').trim(); if (!t) continue; const e = n.parentElement; if (!e || e.closest('script,style,noscript,option,.cien-tekstu,.tr-et-halo,#toast,.podp,#ladowanie,.sr-only,.cyfry,.t-dni') || !widoczny(e)) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    for (const r of rg.getClientRects()) { if (r.width < 3 || r.height < 4) continue; const k = przytnij(r, e); if (k) tek.push({ e, t: t.slice(0, 28), k, r }); }
  }
  const pole = (a, b) => Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t));
  for (let i = 0; i < tek.length; i++) for (let j = i + 1; j < tek.length; j++) {
    const a = tek[i], b = tek[j]; if (a.e === b.e || a.e.contains(b.e) || b.e.contains(a.e)) { if (a.e !== b.e) { /* zagnieżdżone: też sprawdzamy */ } else continue; }
    const p = pole(a.k, b.k); const mn = Math.min((a.k.r - a.k.l) * (a.k.b - a.k.t), (b.k.r - b.k.l) * (b.k.b - b.k.t));
    if (p > 6 && p / mn > 0.12) wyn.push({ rodzaj: 'NAKŁADA', a: `${opis(a.e)}„${a.t}"`, b: `${opis(b.e)}„${b.t}"`, p: Math.round(p) });
  }
  const przyciski = [...document.querySelectorAll('button,input,select,img,.dz')].filter(widoczny);
  for (const a of tek) for (const o of przyciski) {
    if (o === a.e || o.contains(a.e) || a.e.contains(o)) continue; const r = o.getBoundingClientRect(); const k = przytnij(r, o); if (!k) continue;
    const p = pole(a.k, k); if (p > 30 && p / ((a.k.r - a.k.l) * (a.k.b - a.k.t)) > 0.2) wyn.push({ rodzaj: 'NA OBIEKCIE', a: `${opis(a.e)}„${a.t}"`, b: opis(o), p: Math.round(p) });
  }
  for (const a of tek) {
    const k = a.e.closest('.kafel,.arkusz,.dymek,.pigulka,.zakladki'); if (!k) continue; const b = k.getBoundingClientRect();
    if (a.r.left < b.left - 1.5 || a.r.right > b.right + 1.5 || a.r.top < b.top - 1.5 || a.r.bottom > b.bottom + 1.5) { if (!a.e.closest('.przystanki,.dzien-tresc,.tabela-w,.ark-pola')) wyn.push({ rodzaj: 'WYSTAJE', a: `${opis(a.e)}„${a.t}"`, b: opis(k), p: Math.round(Math.max(b.left - a.r.left, a.r.right - b.right, b.top - a.r.top, a.r.bottom - b.bottom)) }); }
    if (a.r.right > innerWidth + 1 || a.r.left < -1) wyn.push({ rodzaj: 'POZA EKRANEM', a: `${opis(a.e)}„${a.t}"`, b: '', p: 0 });
  }
  const uniq = new Map(); for (const x of wyn) { const k = x.rodzaj + x.a + x.b; if (!uniq.has(k)) uniq.set(k, x); } return [...uniq.values()];
};
(async () => {
  const motyw = process.argv[2] || 'dark', wyj = process.env.WYJ || '/tmp/nakladanie_zrzuty'; fs.mkdirSync(wyj, { recursive: true });
  const t = await otworz({ w: 1440, h: 900, motyw, bezVT: !process.env.Z_VT, przyklad: !!process.env.PRZYKLAD });      // PRZYKLAD=1: sprawdzamy wyłącznie przykładowy miesiąc z pierwszego uruchomienia
  const SZYBKO = !!process.env.SZYBKO; const p = t.p; let kod = 0;
  await p.goto(t.adres + '/index.html');
  if (process.env.PRZYKLAD) await p.waitForFunction(() => document.documentElement.classList.contains('przyklad'), null, { timeout: 120000, polling: 300 }); else await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  if (process.env.STRES) await p.addStyleTag({ content: '*{letter-spacing:.02em!important;word-spacing:.04em!important}' });   // szersze pismo niż w Chromium (Firefox bywa szerszy)
  if (process.env.PRZYKLAD) await p.waitForTimeout(6000);
  else {
    await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
    await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 60000 }); await p.waitForTimeout(3000);
  }
  const stan = async nazwa => {
    for (const [w, h] of ROZMIARY) {
      await p.setViewportSize({ width: w, height: h }); await p.waitForTimeout(SZYBKO ? 900 : 1800);
      const zakl = w < 1024 ? ['dzis', 'miesiac', 'dokumenty'] : [null];
      for (const z of zakl) {
        if (z) { await p.evaluate(zz => document.querySelector(`.zakladka[data-tab="${zz}"]`).click(), z); await p.waitForTimeout(1200); }
        await p.waitForFunction(() => !document.getAnimations().some(x => x.playState === 'running' && isFinite(x.effect.getComputedTiming().endTime)), null, { timeout: 30000, polling: 200 }).catch(() => {});      // mierzymy po skończeniu wejścia (przy wolnej grafice animacja ma jeszcze kilka ostatnich klatek)
        const w1 = await p.evaluate(WYKRYJ); const id = `${nazwa}_${w}x${h}${z ? '_' + z : ''}`;
        if (!SZYBKO || w1.length) await p.screenshot({ path: `${wyj}/${id}_${motyw}.png` });
        if (w1.length) { kod = 1; console.log(`  PROBLEMY ${id}: ${w1.length}`); for (const x of w1.slice(0, 14)) console.log(`     ${x.rodzaj}: ${x.a} ↔ ${x.b} (${x.p})`); } else console.log(`  OK   ${id}`);
      }
    }
  };
  if (process.env.PRZYKLAD) { await stan('przyklad'); console.log('błędy konsoli:', JSON.stringify(t.bledy.slice(0, 5))); await t.zamknij(); process.exit(kod); }
  await p.setViewportSize({ width: 1440, height: 900 });
  await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1500);
  await stan('przed');
  await p.setViewportSize({ width: 1440, height: 900 }); await p.waitForTimeout(1200);
  await p.evaluate(() => document.querySelector('#podpisz').click()); await p.waitForSelector('#potwierdz-gen', { timeout: 60000 }); await p.evaluate(() => document.querySelector('#potwierdz-gen').click()); await p.waitForFunction(() => document.querySelector('#kA.po-gen'), null, { timeout: 240000, polling: 300 }); await p.waitForTimeout(5000);
  await stan('gotowe');
  await p.setViewportSize({ width: 1440, height: 900 }); await p.waitForTimeout(1200);
  await p.evaluate(() => document.querySelector('#plan-btn').click()); await p.waitForSelector('#plan-plik', { state: 'attached' });
  await p.setInputFiles('#plan-plik', path.join(__dirname, 'dane/sklepy.xlsx'));
  await p.waitForFunction(() => /Wczytano/.test(document.querySelector('#plan-plik-info').textContent), null, { timeout: 60000, polling: 200 });
  await p.evaluate(() => document.querySelector('#plan-uloz').click()); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 240000 }); await p.waitForFunction(() => document.querySelector('#przystanki .przystanek'), null, { timeout: 120000, polling: 200 }); await p.waitForTimeout(3000);
  await stan('plan');
  console.log('błędy konsoli:', JSON.stringify(t.bledy.slice(0, 5)));
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('BŁĄD TESTU', e); process.exit(2); });
