// Samouczek (js/zywe.js, css .wyc-*): karta z opisem i przyciski „Pomiń / Wstecz / Dalej” muszą mieścić się na ekranie na KAŻDYM kroku — także na niskim oknie przeglądarki i na wąskim telefonie
// (zgłoszenie: „przycisk Dalej potrafi wyjść poza ekran” — trzynaście kropek obok trzech przycisków nie mieściło się w karcie). NODE_PATH=/opt/node22/lib/node_modules node wycieczka_uklad_app.js
const { wpiszAdres, otworz } = require('./wspolne');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const UKLADY = [{ n: 'komputer 1440×900', w: 1440, h: 900, mobile: false }, { n: 'niskie okno 1100×470', w: 1100, h: 470, mobile: false }, { n: 'telefon 390×700', w: 390, h: 700, mobile: true }, { n: 'wąski telefon 360×560', w: 360, h: 560, mobile: true }];
  for (const u of UKLADY) {
    const t = await otworz({ w: u.w, h: u.h, mobile: u.mobile, wycieczka: true }); const p = t.p;
    await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
    await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await wpiszAdres(p, 'ul. Testowa 1, 00-001 Warszawa');
    await (u.mobile ? p.tap('#zapisz-dane') : p.click('#zapisz-dane')); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 30000 });
    await p.waitForSelector('.wyc.otwarta', { timeout: 60000 });
    const licz = () => p.evaluate(() => document.querySelector('.wyc-licz').textContent);
    await p.waitForFunction(() => /^1 z \d+$/.test(document.querySelector('.wyc-licz').textContent), null, { timeout: 60000 }); await p.waitForTimeout(900);
    const N = Number((await licz()).split(' z ')[1]); const zle = [];
    for (let i = 1; i <= N; i++) {
      await p.waitForFunction(a => document.querySelector('.wyc-licz').textContent === a[0] + ' z ' + a[1], [i, N], { timeout: 30000 }); await p.waitForFunction(() => { const r = document.querySelector('.wyc-karta').getBoundingClientRect(), k = [r.left, r.top].join(); const poprz = window.__wycPoprz; window.__wycPoprz = k; return poprz === k; }, null, { timeout: 15000, polling: 300 });      // karta jedzie na miejsce 0,65 s: mierzymy, gdy stoi
      const m = await p.evaluate(() => {
        const W = innerWidth, H = innerHeight, poza = e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.left < -0.5 || r.top < -0.5 || r.right > W + 0.5 || r.bottom > H + 0.5); };
        const karta = document.querySelector('.wyc-karta'), przyciski = [...document.querySelectorAll('.wyc-dol button')].filter(b => !b.hidden && b.getBoundingClientRect().width > 0);
        return { karta: poza(karta), przyciski: przyciski.filter(poza).map(b => b.textContent.trim()), dalej: !!przyciski.find(b => b.dataset.w === 'dalej'), kartaWKarcie: przyciski.filter(b => { const k = karta.getBoundingClientRect(), r = b.getBoundingClientRect(); return r.right > k.right + 0.5 || r.left < k.left - 0.5; }).map(b => b.textContent.trim()) };
      });
      if (m.karta || m.przyciski.length || !m.dalej || m.kartaWKarcie.length) zle.push(`krok ${i}: ${JSON.stringify(m)}`);
      if (i < N) await p.click('[data-w="dalej"]');
    }
    ok(`${u.n}: na wszystkich ${N} krokach karta i przyciski (Pomiń, Wstecz, Dalej) są w całości na ekranie i w obrębie karty`, zle.length === 0, zle.slice(0, 2).join(' | '));
    await t.zamknij();
  }
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
