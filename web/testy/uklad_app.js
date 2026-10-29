// Układ aplikacji w wielu rozdzielczościach i obu motywach: przewijanie strony, przycięte teksty, elementy poza ekranem, błędy.
// NODE_PATH=/opt/node22/lib/node_modules node uklad_app.js [katalog-zrzutow]
const { otworz, generuj, wieczory } = require('./wspolne'); const fs = require('fs');
const WIDOKI = [['1920x1080', 1920, 1080], ['1440x900', 1440, 900], ['1366x768', 1366, 768], ['1280x720', 1280, 720], ['1024x768', 1024, 768], ['390x844', 390, 844], ['360x740', 360, 740], ['412x915', 412, 915]];
const BADAJ = () => {
  const se = document.scrollingElement, przyciete = [], poza = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('.arkusz-tlo:not(.otwarty), #ladowanie:not(.widoczny), canvas, svg, [aria-hidden="true"]')) continue;
    const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const tekst = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (tekst && ((el.scrollWidth > el.clientWidth + 1 && cs.overflowX !== 'visible' && cs.textOverflow !== 'ellipsis') || (el.scrollHeight > el.clientHeight + 2 && cs.overflowY === 'hidden' && !el.closest('.przystanki,.dzien-tresc,.tabela-w,.arkusz'))))
      przyciete.push((el.className || el.tagName).toString().slice(0, 36) + ' «' + el.textContent.trim().slice(0, 30) + '»');
    if ((r.right > innerWidth + 1 || r.left < -1) && cs.position !== 'fixed' && !el.closest('.scena,.dymek,.podp,.toast,.lot')) poza.push((el.className || el.tagName).toString().slice(0, 36));
  }
  return { przewijanie: se.scrollHeight > innerHeight + 1 || se.scrollWidth > innerWidth + 1, sh: se.scrollHeight, ih: innerHeight, przyciete: przyciete.slice(0, 8), poza: poza.slice(0, 8) };
};
(async () => {
  const wyj = process.argv[2] || '/tmp/uklad_zrzuty'; fs.mkdirSync(wyj, { recursive: true });
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p; let kod = 0;
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 30000 });
  await p.waitForTimeout(3500);
  await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await wieczory(p);
  for (const d of [21, 22, 23, 24, 25, 26]) { await p.click(`#siatka button.dz[data-d="${d}"]`, { force: true }); await p.waitForTimeout(300); }
  await generuj(p);
  await p.waitForTimeout(4500);
  for (const motyw of ['dark', 'light']) {
    await p.emulateMedia({ colorScheme: motyw }); await p.waitForTimeout(1500);
    for (const [nazwa, w, h] of WIDOKI) {
      await p.setViewportSize({ width: w, height: h }); await p.waitForTimeout(2200);
      const telefon = w < 761, zakladki = telefon ? ['dzis', 'miesiac', 'dokumenty'] : [null];
      for (const z of zakladki) {
        if (z) { await p.click(`.zakladka[data-tab="${z}"]`); await p.waitForTimeout(2500); }
        const b = await p.evaluate(BADAJ);
        const plik = `${wyj}/${motyw}_${nazwa}${z ? '_' + z : ''}.png`; await p.screenshot({ path: plik });
        const zle = b.przewijanie || b.przyciete.length || b.poza.length;
        console.log((zle ? '  UWAGA ' : '  OK    ') + `${motyw} ${nazwa}${z ? ' ' + z : ''}` + (zle ? ' ' + JSON.stringify(b) : ''));
        if (zle) kod = 1;
      }
    }
  }
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 6))); if (t.bledy.length) kod = 1;
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
