// Telefon: kontekst mobilny od początku (390x844 / 360x740), wszystkie zakładki. NODE_PATH=/opt/node22/lib/node_modules node telefon_app.js [w] [h] [motyw]
const { otworz, generuj, wieczory } = require('./wspolne'); const fs = require('fs');
(async () => {
  const [w = 390, h = 844, motyw = 'dark'] = process.argv.slice(2); const wyj = '/tmp/telefon_zrzuty'; fs.mkdirSync(wyj, { recursive: true });
  const t = await otworz({ w: +w, h: +h, dsf: 2, mobile: true, motyw }); const p = t.p;
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.waitForTimeout(2500); await p.screenshot({ path: `${wyj}/${motyw}_${w}_0_dane.png` });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.tap('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3500);
  await p.screenshot({ path: `${wyj}/${motyw}_${w}_1_plan.png` });
  await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await wieczory(p, { tap: true });
  await p.tap('.zakladka[data-tab="miesiac"]'); await p.waitForTimeout(2500);
  for (const d of [21, 22, 23, 24, 25, 26]) { await p.tap(`#siatka button.dz[data-d="${d}"]`); await p.waitForTimeout(250); }
  await p.screenshot({ path: `${wyj}/${motyw}_${w}_2_plan_miesiac.png` });
  await p.tap('.zakladka[data-tab="dzis"]'); await p.waitForTimeout(2000);
  await generuj(p, { tap: true }); await p.waitForTimeout(4000);
  for (const z of ['dzis', 'miesiac', 'dokumenty']) { await p.tap(`.zakladka[data-tab="${z}"]`); await p.waitForTimeout(2800); await p.screenshot({ path: `${wyj}/${motyw}_${w}_3_${z}.png` }); }
  await p.tap('.zakladka[data-tab="dokumenty"]'); await p.waitForTimeout(1000); await p.tap('#podpisz'); await p.waitForSelector('#arkusz-tlo.otwarty'); await p.waitForTimeout(2500); await p.screenshot({ path: `${wyj}/${motyw}_${w}_4_podpis.png` });
  console.log('gotowe; błędy:', JSON.stringify(t.bledy.slice(0, 6))); await t.zamknij();
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
