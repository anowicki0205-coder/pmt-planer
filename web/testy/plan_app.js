// Plan wizyt: import .xlsx/.csv → układanie → kafel „Dziś" → odhaczanie → trwałość. NODE_PATH=/opt/node22/lib/node_modules node plan_app.js
const { otworz } = require('./wspolne'); const path = require('path');
(async () => {
  const W = Number(process.env.W || 1440), H = Number(process.env.H || 900), MOB = !!process.env.MOB; const t = await otworz({ w: W, h: H, mobile: MOB }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const wyj = process.env.WYJ || '/tmp/plan_zrzuty'; require('fs').mkdirSync(wyj, { recursive: true });
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3500);
  ok('bez planu kafel „Dziś" proponuje wczytanie', (await p.locator('#plan-otworz').count()) === 1);
  await p.click('#plan-otworz'); await p.waitForSelector('#plan-plik', { state: 'attached' });
  await p.setInputFiles('#plan-plik', path.join(__dirname, 'dane/sklepy.xlsx'));
  await p.waitForFunction(() => /Wczytano/.test(document.querySelector('#plan-plik-info').textContent), null, { timeout: 60000, polling: 200 });
  ok('xlsx wczytany, kolumny rozpoznane', /20<\/b> adresów/.test(await p.locator('#plan-plik-info').innerHTML()) && /miasto/.test(await p.locator('#plan-plik-info').innerText()), (await p.locator('#plan-plik-info').innerText()).slice(0, 120));
  await p.setInputFiles('#plan-plik', path.join(__dirname, 'dane/sklepy.csv'));
  await p.waitForFunction(() => /sklepy\.csv/.test(document.querySelector('#plan-plik-info').textContent), null, { timeout: 60000, polling: 200 });
  ok('csv (średniki, UTF-8 z BOM) też wczytany', /20<\/b> adresów/.test(await p.locator('#plan-plik-info').innerHTML()));
  await p.click('[data-cykl="1"]'); await p.waitForTimeout(300);
  ok('wybór cyklicznego pokazuje parametry', await p.locator('#plan-cykl-pola').isVisible());
  await p.screenshot({ path: wyj + '/1_arkusz_planu.png' });
  await p.click('#plan-uloz'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 180000 }); await p.waitForFunction(() => document.querySelector('#przystanki .przystanek'), null, { timeout: 120000, polling: 200 }); await p.waitForTimeout(2500);
  const wiersze = await p.locator('#przystanki .przystanek').count(); ok('kafel „Dziś" pokazuje wizyty z planu', wiersze >= 3, String(wiersze));
  ok('godziny szacunkowe rosnąco', await p.evaluate(() => { const g = [...document.querySelectorAll('#przystanki .p-godz')].map(e => e.textContent.trim()); return g.length > 1 && g.every(x => /^\d\d:\d\d$/.test(x)) && g.every((x, i) => i === 0 || x >= g[i - 1]); }));
  ok('następny sklep ma przycisk Nawiguj', (await p.locator('#nawiguj').count()) === 1);
  ok('meta kafla: wizyty, km i liczba sklepów', /wizy/.test(await p.locator('#d-meta').innerText()) && (MOB || (/km/.test(await p.locator('#d-meta').innerText()) && /20 sklepów/.test(await p.locator('#d-meta').textContent()))), await p.locator('#d-meta').innerText());
  await p.screenshot({ path: wyj + '/2_dzis.png' });
  const pierwszy = (await p.locator('#przystanki .p-nazwa').first().innerText());
  await p.click('#przystanki .p-znak >> nth=0', { force: true });
  await p.waitForFunction(() => /^1\//.test(document.querySelector('#d-pier-t').textContent), null, { timeout: 60000, polling: 200 }).catch(() => {});
  ok('odhaczenie zmienia licznik', /^1\//.test(await p.locator('#d-pier-t').innerText()), await p.locator('#d-pier-t').innerText());
  await p.evaluate(() => { window.__otw = []; window.open = (u) => { window.__otw.push(u); return null; }; });
  await p.waitForSelector('#nawiguj', { state: 'attached', timeout: 60000 });
  await p.waitForFunction(() => { const b = document.querySelector('#nawiguj'); return b && b.dataset.i === '1'; }, null, { timeout: 60000, polling: 200 }); await p.evaluate(() => document.querySelector('#nawiguj').click());
  await p.waitForFunction(() => window.__otw.length, null, { timeout: 30000, polling: 200 }).catch(() => {});
  const otw = await p.evaluate(() => window.__otw);
  ok('„Nawiguj" otwiera trasę w mapach do następnego sklepu', otw.length === 1 && /google\.com\/maps\/dir\/\?api=1&travelmode=driving&destination=/.test(otw[0]), otw[0] ? otw[0].slice(0, 100) : 'brak wywołania');
  await p.reload(); await p.waitForFunction(() => document.querySelector('#przystanki .przystanek'), null, { timeout: 120000, polling: 300 }); await p.waitForTimeout(2500);
  ok('plan i odhaczenia przetrwały odświeżenie', /^1\//.test(await p.locator('#d-pier-t').innerText()) && (await p.locator('#przystanki .p-nazwa').first().innerText()) === pierwszy);
  // ten sam sklep (ten sam adres) bywa odwiedzany kilka razy w ciągu dnia: każda wizyta ma się odhaczać osobno (dawniej klik zaznaczał wszystkie naraz)
  const powt = await p.evaluate(() => {
    const d = window.__pmtDane.czytaj(); d.wizyty = {};
    const dzien = d.plan.miesiace.flatMap(m => m.dni).sort((a, b) => a.data.localeCompare(b.data)).find(x => x.data >= new Date().toISOString().slice(0, 10)) || d.plan.miesiace[0].dni[0];
    for (let i = 1; i < Math.min(5, dzien.wizyty.length); i++) dzien.wizyty[i] = { ...dzien.wizyty[0] };      // pięć wizyt pod jednym adresem
    window.__pmtDane.zapisz(d); return dzien.wizyty.length;
  });
  await p.reload(); await p.waitForFunction(() => document.querySelector('#przystanki .przystanek'), null, { timeout: 120000, polling: 300 }); await p.waitForTimeout(2500);
  await p.click('#przystanki .p-znak[data-i="2"]', { force: true }); await p.waitForTimeout(1200);
  const ilePo = await p.evaluate(() => ({ ok: document.querySelectorAll('#przystanki .p-znak[aria-pressed="true"]').length, ktora: (document.querySelector('#przystanki .p-znak[aria-pressed="true"]') || { dataset: {} }).dataset.i, licznik: document.querySelector('#d-pier-t').textContent }));
  ok('wizyty w tym samym sklepie odhaczane osobno: klik w jedną zaznacza dokładnie tę jedną (a nie sąsiednią)', ilePo.ok === 1 && ilePo.ktora === '2' && /^1\//.test(ilePo.licznik), JSON.stringify({ ...ilePo, wizyt: powt }));
  const przedCofnieciem = await p.evaluate(() => { const e = document.querySelector('#przystanki .p-znak[aria-pressed="true"]'), r = e.getBoundingClientRect(), g = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return { i: e.dataset.i, r: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], trafia: g === e || e.contains(g) || (g && g.closest && g.closest('.p-znak') === e) ? 'w znak' : (g && (g.id || g.className)) }; });
  await p.click('#przystanki .p-znak[aria-pressed="true"]', { force: true }); await p.waitForTimeout(1200);
  const poCofnieciu = await p.locator('#przystanki .p-znak[aria-pressed="true"]').count(), naciśnięte = await p.evaluate(() => [...document.querySelectorAll('#przystanki .p-znak')].map(e => e.dataset.i + (e.getAttribute('aria-pressed') === 'true' ? '*' : '')).join(','));
  ok('i cofnięcie dotyczy tylko tej jednej wizyty', poCofnieciu === 0, JSON.stringify({ przedCofnieciem, poCofnieciu, naciśnięte }));
  await p.evaluate(() => { const d = window.__pmtDane.czytaj(); d.wizyty = {}; window.__pmtDane.zapisz(d); });
  await p.reload(); await p.waitForFunction(() => document.querySelector('#przystanki .przystanek'), null, { timeout: 120000, polling: 300 }); await p.waitForTimeout(2500);
  // przejście przy odhaczaniu: nazwane (a więc rysowane osobno) są tylko wiersze w pełni widoczne w liście — reszta nie ma prawa „wypłynąć” poza kafel
  const vtWiersze = await p.evaluate(() => { const l = document.querySelector('#przystanki'), c = l.getBoundingClientRect(); l.querySelector('.p-znak[aria-pressed="false"]').click();
    const w = [...l.querySelectorAll('.przystanek')]; return { n: w.length, vt: w.filter(e => e.classList.contains('vt')).length, zle: w.filter(e => { const r = e.getBoundingClientRect(), wid = r.height > 0 && r.top >= c.top - 1 && r.bottom <= c.bottom + 1; return e.classList.contains('vt') !== wid; }).length }; });
  ok('przejście: nazwane są wyłącznie w pełni widoczne wiersze listy', vtWiersze.zle === 0 && vtWiersze.vt > 0, JSON.stringify(vtWiersze));
  await p.waitForTimeout(1500);
  // fanfary: po odhaczeniu WSZYSTKICH wizyt dnia
  ok('przed ostatnią wizytą nie ma fanfar', (await p.locator('.fanfary').count()) === 0 && (await p.locator('#kD.komplet').count()) === 0);
  for (let g = 0; g < 80; g++) {
    const reszta = await p.locator('#przystanki .p-znak[aria-pressed="false"]').count();
    if (!reszta) break;
    await p.evaluate(() => { const b = document.querySelector('#przystanki .p-znak[aria-pressed="false"]'); b && b.click(); });
    await p.waitForTimeout(700);
  }
  await p.waitForSelector('#kD.komplet', { timeout: 60000 }).catch(() => {});
  ok('wszystkie wizyty odhaczone: kafel Dziś w stanie „komplet”', (await p.locator('#kD.komplet').count()) === 1, await p.locator('#d-pier-t').innerText());
  const spokojnie = await p.evaluate(() => document.documentElement.classList.contains('spokojne'));      // animacje wyłączone: zamiast fanfar krótka informacja
  if (spokojnie) {
    await p.waitForSelector('.fanfary', { timeout: 30000 }).catch(() => {});
    ok('tryb spokojny: gratulacje to baner „Gratulacje! Dzień zrobiony” (widoczny, bez konfetti i ruchu)', /Gratulacje/.test(await p.locator('.fanfary').first().innerText().catch(() => '')) && await p.locator('.fanfary').first().isVisible() && (await p.locator('canvas.konfetti').count()) === 0, await p.locator('.fanfary').first().innerText().catch(() => 'brak'));
  } else {
    await p.waitForSelector('.fanfary', { timeout: 30000 }).catch(() => {});
    ok('fanfary: baner „Gratulacje! Dzień zrobiony”', /Gratulacje/.test(await p.locator('.fanfary').first().innerText().catch(() => '')), await p.locator('.fanfary').first().innerText().catch(() => 'brak'));
    ok('fanfary: konfetti na jednym płótnie', (await p.locator('canvas.konfetti').count()) === 1);
  }
  await p.screenshot({ path: wyj + '/4_fanfary.png' });
  await p.click('#plan-btn'); await p.waitForSelector('#plan-usun'); await p.waitForTimeout(600); await p.screenshot({ path: wyj + '/3_plan_istniejacy.png' });
  ok('arkusz planu pokazuje stan istniejącego planu', /Plan ułożony/.test(await p.locator('#plan-stan').innerText()), (await p.locator('#plan-stan').innerText()).slice(0, 90));
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 6))); if (t.bledy.length) kod = 1;
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
