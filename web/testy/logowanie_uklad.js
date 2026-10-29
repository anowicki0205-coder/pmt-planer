// Układ okna logowania i resetu hasła: telefony i komputer, motyw Noc i Dzień — karta mieści się w ekranie, nic nie wystaje poziomo.
const { otworz } = require('./wspolne');
(async () => {
  let kod = 0; const wyj = '/tmp/logowanie_uklad'; require('fs').mkdirSync(wyj, { recursive: true });
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  for (const [w, h, mob] of [[390, 844, true], [360, 640, true], [1440, 900, false]]) for (const motyw of ['dark', 'light']) {
    const t = await otworz({ w, h, dsf: 2, mobile: mob, motyw, zalogowany: false }); const p = t.p;
    await p.goto(t.adres + '/index.html'); await p.waitForSelector('#dz-form'); await p.waitForTimeout(1200);
    const mierz = () => p.evaluate(() => { const a = document.querySelector('#arkusz').getBoundingClientRect(); const s = document.querySelector('#arkusz'); return { gora: a.top, dol: a.bottom, l: a.left, r: a.right, W: innerWidth, H: innerHeight, przewija: s.scrollHeight > s.clientHeight + 1, poziomo: document.documentElement.scrollWidth > innerWidth }; });
    let m = await mierz(); const nazwa = `${w}x${h}_${motyw}`;
    await p.screenshot({ path: `${wyj}/${nazwa}_logowanie.png` });
    ok(`${nazwa} logowanie: karta w ekranie`, m.gora >= 0 && m.dol <= m.H && m.l >= 0 && m.r <= m.W && !m.poziomo, JSON.stringify(m));
    await p.click('#dz-reset'); await p.waitForSelector('#dr-form'); await p.waitForTimeout(600);
    m = await mierz(); await p.screenshot({ path: `${wyj}/${nazwa}_reset.png` });
    ok(`${nazwa} reset: karta w ekranie albo przewijana wewnątrz`, m.gora >= 0 && m.dol <= m.H && m.l >= 0 && m.r <= m.W && !m.poziomo, JSON.stringify(m));
    await p.fill('#dr-kod', '12345'); await p.fill('#dr-tel', '1'); await p.fill('#dr-nowe', 'a'); await p.fill('#dr-pow', 'b'); await p.click('#dr-ok'); await p.waitForTimeout(800);
    m = await mierz(); ok(`${nazwa} reset z komunikatem: nic nie wypada`, m.gora >= 0 && m.dol <= m.H && !m.poziomo, JSON.stringify(m));
    await t.zamknij();
  }
  process.exit(kod);
})().catch(e => { console.error('BŁĄD TESTU', e); process.exit(2); });
