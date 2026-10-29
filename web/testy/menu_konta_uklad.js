// Menu konta (login, ważność dostępu, zmiana hasła, wylogowanie) mieści się w ekranie telefonu i komputera. NODE_PATH=/opt/node22/lib/node_modules node testy/menu_konta_uklad.js
const { otworz } = require('./wspolne');
(async () => {
  let kod = 0; const wyj = '/tmp/menu_konta'; require('fs').mkdirSync(wyj, { recursive: true });
  for (const [w, h, mob] of [[390, 844, true], [360, 640, true], [1440, 900, false]]) {
    const t = await otworz({ w, h, dsf: 2, mobile: mob }); const p = t.p;
    await p.goto(t.adres + '/index.html');
    await p.waitForFunction(() => !document.querySelector('#aplikacja').classList.contains('zamknieta') && !document.querySelector('#ladowanie').classList.contains('widoczny'), null, { timeout: 180000, polling: 200 });
    await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 60000 }); await p.evaluate(() => document.querySelector('#d-imie').closest('#arkusz-tresc') && (document.querySelector('#arkusz-tlo').classList.remove('otwarty')));
    await p.waitForTimeout(8000);
    await p.evaluate(() => document.querySelector('#konto').click()); await p.waitForTimeout(1500);
    const m = await p.evaluate(() => { const d = document.querySelector('#konto-menu').getBoundingClientRect(); return { g: d.top, d: d.bottom, l: d.left, r: d.right, W: innerWidth, H: innerHeight, tekst: document.querySelector('#konto-dostep').textContent }; });
    await p.screenshot({ path: `${wyj}/${w}x${h}.png` });
    const ok = m.g >= 0 && m.d <= m.H && m.l >= 0 && m.r <= m.W && /Login 12345/.test(m.tekst);
    console.log((ok ? '  OK   ' : '  BŁĄD ') + `${w}x${h} menu konta w ekranie — ${JSON.stringify(m)}`); if (!ok) kod = 1;
    await t.zamknij();
  }
  process.exit(kod);
})().catch(e => { console.error('BŁĄD TESTU', e); process.exit(2); });
