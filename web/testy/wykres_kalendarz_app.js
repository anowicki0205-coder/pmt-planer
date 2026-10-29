// Kalendarz (kolorowe karty dni zamiast fiolek) i wykres dni w kaflu kwoty (płaskie słupki w kontrastowym panelu, bez WebGL):
// ta sama skala kolorów n1…n5 (kolor = kwota dnia wobec limitu), klik i najechanie na słupek, zaznaczony dzień, kontrast panelu do kafla.
// NODE_PATH=/opt/node22/lib/node_modules node wykres_kalendarz_app.js            (MOTYW=light — motyw Dzień; W=390 H=844 MOB=1 — telefon)
const { otworz, generuj } = require('./wspolne');
(async () => {
  const motyw = process.env.MOTYW || 'dark', mob = process.env.MOB === '1';
  const t = await otworz({ w: +(process.env.W || 1440), h: +(process.env.H || 900), motyw, mobile: mob }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await generuj(p); await p.waitForTimeout(3500);
  if (mob) { await p.click('[data-tab="miesiac"]'); await p.waitForTimeout(800); }

  const dane = await p.evaluate(() => {
    const kom = [...document.querySelectorAll('#siatka button.dz.trasa')].map(e => ({ d: +e.dataset.d, n: (e.className.match(/\bn[1-5]\b/) || [])[0], poziom: parseFloat(e.style.getPropertyValue('--poziom')), bg: getComputedStyle(e).backgroundImage, kol: getComputedStyle(e).color, pl: getComputedStyle(e.querySelector('.pl-w')).display }));
    const sl = [...document.querySelectorAll('#ku-zapas i.tr')].map(e => ({ d: +e.dataset.d, n: (e.className.match(/\bn[1-5]\b/) || [])[0], h: parseFloat(e.style.getPropertyValue('--h')) }));
    return { kom, sl, gl: !!document.querySelector('#kurtyna-gl'), wszystkie: document.querySelectorAll('#ku-zapas i').length, N: document.querySelectorAll('#siatka .dz[data-d]').length };
  });
  const klasaOczek = h => h < .3 ? 'n1' : h < .5 ? 'n2' : h < .68 ? 'n3' : h < .86 ? 'n4' : 'n5';
  if (!mob) {
    ok('wykres dni nie używa WebGL (nie ma płótna #kurtyna-gl), jest po jednym słupku na dzień miesiąca', !dane.gl && dane.wszystkie === 30, `${dane.wszystkie} słupków`);
    ok('słupek jest dla każdego dnia z trasą (tyle, ile kart w kalendarzu)', dane.sl.length === dane.kom.length && dane.kom.length >= 10, `${dane.sl.length} / ${dane.kom.length}`);
    ok('ta sama skala: klasa koloru (n1…n5) i wysokość słupka zgadzają się z kartą dnia w kalendarzu', dane.kom.every(k => { const s = dane.sl.find(x => x.d === k.d); return s && s.n === k.n && Math.abs(s.h - k.poziom) < .002; }));
  } else ok('na telefonie wykres dni jest ukryty (zakładka „Miesiąc” pokazuje kalendarz i dzień)', await p.evaluate(() => getComputedStyle(document.querySelector('#kurtyna')).display === 'none'));
  ok('klasa koloru wynika z poziomu kwoty wobec limitu dnia (progi .30/.50/.68/.86)', dane.kom.every(k => k.n === klasaOczek(k.poziom)), JSON.stringify(dane.kom.slice(0, 3).map(k => [k.poziom, k.n])));
  ok('w kalendarzu są co najmniej dwa różne kolory (kolor niesie informację o kwocie)', new Set(dane.kom.map(k => k.n)).size >= 2, [...new Set(dane.kom.map(k => k.n))].join(','));
  ok('karta dnia jest płaską, kolorową kartą z ciemnym tekstem (bez wypełnienia cieczą)', dane.kom.every(k => /gradient/.test(k.bg) && k.kol === 'rgb(26, 20, 64)' && k.pl === 'none'), `${dane.kom[0].kol} ${dane.kom[0].pl}`);

  if (!mob) {
  /* kontrast panelu wykresu do kafla */
  const kolory = await p.evaluate(() => {
    const k = document.querySelector('#kurtyna'), kafel = document.querySelector('#kA'), cs = getComputedStyle(k), tl = getComputedStyle(kafel);
    const rgb = s => (s.match(/rgba?\(([^)]+)\)/) || [])[1];
    const probka = el => { const m = getComputedStyle(el).backgroundImage.match(/rgba?\([^)]+\)/); return m ? m[0] : ''; };
    return { panel: probka(k), kafel: probka(kafel), tekst: cs.color, bar: getComputedStyle(document.querySelector('#ku-zapas i.tr:not(.wyb)'), '::before').backgroundColor, rb: k.getBoundingClientRect().toJSON(), rl: document.querySelector('.b-lewa').getBoundingClientRect().toJSON() };
  });
  const ton = s => { const m = (s.match(/(\d+)[, ]+(\d+)[, ]+(\d+)/) || []).slice(1).map(Number); return m; };
  const [pr, pg, pb] = ton(kolory.panel), [kr, kg, kb] = ton(kolory.kafel);
  ok('panel wykresu jest w innym, ciepłym kolorze niż niebieski kafel (kontrast: czerwień panelu > niebieski, odwrotnie niż kafel)', pr > pb + 80 && kb > kr + 60, `panel ${kolory.panel}  kafel ${kolory.kafel}`);
  ok('panel wykresu i pole kwoty są rozdzielone (panel nie nachodzi na pole kwoty)', kolory.rb.left >= kolory.rl.right - 1, `panel od ${Math.round(kolory.rb.left)}, kwota do ${Math.round(kolory.rl.right)}`);
  ok('słupki wykresu są białe, tekst panelu biały', kolory.bar === 'rgb(255, 255, 255)' || /255, 255, 255/.test(kolory.bar), kolory.bar + ' / ' + kolory.tekst);

  /* klik i najechanie na słupek */
  const dz = dane.kom[3].d, r = await p.evaluate(d => { const e = document.querySelector(`#ku-zapas i[data-d="${d}"]`).getBoundingClientRect(), pole = document.querySelector('#ku-pole').getBoundingClientRect(); return { x: e.left + e.width / 2, y: pole.top + pole.height * .75 }; }, dz);
  if (!mob) {
    await p.mouse.move(r.x, r.y); await p.waitForTimeout(300);
    const tip = await p.evaluate(() => { const e = document.querySelector('.podp'); return e ? { t: e.innerText, wid: getComputedStyle(e).opacity } : null; });
    ok('najechanie na słupek pokazuje dymek z dniem i kwotą oraz podświetla słupek', !!tip && /\d/.test(tip.t) && await p.locator(`#ku-zapas i[data-d="${dz}"].hov`).count() === 1, tip && tip.t.replace(/\n/g, ' | '));
  }
  await p.mouse.click(r.x, r.y); await p.waitForTimeout(900);
  const wyb = await p.evaluate(() => ({ komorka: +(document.querySelector('#siatka .dz.wybrany') || {}).dataset?.d, slup: +(document.querySelector('#ku-zapas i.wyb') || {}).dataset?.d, os: document.querySelectorAll('#ku-os span.wyb').length, tytul: document.querySelector('#d-tyt, #de-tyt')?.innerText || '' }));
  ok('klik w słupek wybiera ten dzień: karta w kalendarzu, słupek i panel dnia zgodne', wyb.komorka === dz && wyb.slup === dz, JSON.stringify(wyb));
  await p.mouse.move(3, 3); await p.waitForTimeout(900);      // kursor poza słupkiem: bez podświetlenia najechania
  const wybKolor = await p.waitForFunction(() => { const c = getComputedStyle(document.querySelector('#ku-zapas i.wyb'), '::before').backgroundColor; return /31, 91, 255/.test(c) ? c : false; }, null, { timeout: 10000, polling: 200 }).then(h => h.jsonValue()).catch(async () => p.evaluate(() => getComputedStyle(document.querySelector('#ku-zapas i.wyb'), '::before').backgroundColor));      // przejście koloru na wolnej grafice programowej potrafi trwać dłużej
  ok('wybrany słupek wyróżnia się niebieskim kolorem (jak wyróżnienie we wzorze)', /31, 91, 255/.test(wybKolor), wybKolor);
  await p.locator(`#siatka button.dz.trasa[data-d="${dane.kom[6].d}"]`).click({ force: true }); await p.waitForTimeout(900);
  ok('klik w kartę dnia przenosi wyróżnienie na właściwy słupek', (await p.evaluate(() => +document.querySelector('#ku-zapas i.wyb').dataset.d)) === dane.kom[6].d);

  }
  /* legenda i dni specjalne */
  const leg = await p.evaluate(() => ({ l1: getComputedStyle(document.querySelector('.kal-leg .l1')).backgroundImage }));
  ok('legenda kalendarza pokazuje skalę kolorów (gradient)', /gradient/.test(leg.l1));
  await p.screenshot({ path: process.env.WYJ || '/tmp/wykres_kalendarz.png' });
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 6))); if (t.bledy.length) kod = 1;
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
