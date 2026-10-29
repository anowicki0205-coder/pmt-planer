// „Życie” kalendarza i fiolek dokumentów (prośba właściciela: wybrane dni pulsują, ciecz w fiolkach się kołysze, „coś się dzieje”): lekki, ciągły ruch CSS tylko w tych dwóch kaflach,
// mimo trybu spokojnego dla reszty aplikacji; znika przy „Ogranicz ruch” w systemie; nie wychodzi poza kafle i nie psuje klikania.
// NODE_PATH=/opt/node22/lib/node_modules node zycie_app.js
const { otworz } = require('./wspolne');
const animacje = p => p.evaluate(() => document.getAnimations().filter(a => a.playState === 'running' && !(a instanceof CSSTransition)).map(a => ({
  nazwa: a.animationName, poza: (a.effect && a.effect.pseudoElement) || '',
  kafel: (() => { const e = a.effect && a.effect.target; const k = e && e.closest && e.closest('.kafel'); return k ? k.id : (e && e.id) || '?'; })(),
  cel: (() => { const e = a.effect && a.effect.target; return e && e.className ? String(e.className.baseVal ?? e.className).trim().split(/\s+/).slice(0, 3).join('.') : (e && e.tagName) || '?'; })()
})));
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const t = await otworz({ w: 1440, h: 900, przyklad: true, bezZycia: false }); const p = t.p;
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#siatka .dz.trasa', { timeout: 120000 }); await p.waitForTimeout(3500);
  ok('aplikacja nadal jest w trybie spokojnym, a „życie” jest włączone osobno (html.spokojne + html.zyje)', await p.evaluate(() => document.documentElement.classList.contains('spokojne') && document.documentElement.classList.contains('zyje')));
  const a = await animacje(p);
  const obce = a.filter(x => !/^zycie-/.test(x.nazwa));
  ok('działają WYŁĄCZNIE animacje „zycie-…” — reszta aplikacji stoi', a.length > 0 && obce.length === 0, JSON.stringify(obce.slice(0, 5)));
  const poza = a.filter(x => !['kC', 'kF'].includes(x.kafel) && x.cel.indexOf('pierscien') < 0);
  ok('i tylko w dwóch kaflach: kalendarz (#kC) i dokumenty (#kF)', poza.length === 0, JSON.stringify(poza.slice(0, 5)));
  const ile = n => a.filter(x => x.nazwa === n).length;

  /* ---- kalendarz ---- */
  const dniT = await p.locator('#siatka .dz.trasa').count();
  ok(`każdy dzień z trasą (${dniT}) unosi się, oddycha światłem, a co jakiś czas przebiega po nim błysk`, ile('zycie-plyn') === dniT && ile('zycie-blysk') === dniT && ile('zycie-oddech') === dniT, `plyn=${ile('zycie-plyn')} blysk=${ile('zycie-blysk')} oddech=${ile('zycie-oddech')}`);
  ok('wybrany dzień pulsuje: fala (sonar) i pierścień', (await p.locator('#siatka .dz.trasa.wybrany').count()) === 1 && ile('zycie-sonar') === 1 && ile('zycie-puls') >= 1, `sonar=${ile('zycie-sonar')} puls=${ile('zycie-puls')}`);
  ok('dni bez trasy i wolne stoją (kreskowane kontury się nie ruszają)', (await p.evaluate(() => [...document.querySelectorAll('#siatka .dz:not(.trasa)')].filter(e => e.getAnimations().length).length)) === 0);
  const faz = await p.evaluate(() => [...document.querySelectorAll('#siatka .dz.trasa')].map(e => Math.round(e.getAnimations()[0].effect.getComputedTiming().progress * 100)));
  ok('dni są w różnych fazach (nie poruszają się jednym ciałem)', new Set(faz).size > Math.min(3, dniT - 1), faz.join(','));
  const sw = async () => p.evaluate(() => getComputedStyle(document.querySelector('.fiolki .f-ciecz')).clipPath);

  /* ---- fiolki ---- */
  const fiolek = await p.locator('#fiolki .fiolka').count();
  ok(`w każdej z ${fiolek} fiolek ciecz się chlupie, fiolka buja, połysk faluje`, ile('zycie-chlup') === fiolek && ile('zycie-kolys') === fiolek && ile('zycie-polysk') === fiolek, `chlup=${ile('zycie-chlup')} kolys=${ile('zycie-kolys')} polysk=${ile('zycie-polysk')}`);
  ok('bąbelki się unoszą', ile('zycie-babel') >= fiolek, 'bąbelków: ' + ile('zycie-babel'));
  const c1 = await sw(); await p.waitForTimeout(900); const c2 = await sw(); await p.waitForTimeout(900); const c3 = await sw();
  ok('powierzchnia cieczy naprawdę zmienia nachylenie w czasie', new Set([c1, c2, c3]).size === 3, [c1, c2, c3].join(' | '));
  const wychyl = await p.evaluate(() => { const o = []; for (let i = 0; i < 12; i++) o.push(Math.abs(parseFloat(getComputedStyle(document.querySelector('.fiolki .f-rurka')).rotate) || 0)); return Math.max(...o); });
  ok('kołysanie fiolki jest subtelne (poniżej 1,5°)', wychyl <= 1.5, wychyl + '°');

  /* ---- ruch nie psuje układu ani klikania ---- */
  const wKaflu = () => p.evaluate(() => { const g = document.querySelector('#siatka').getBoundingClientRect(); return [...document.querySelectorAll('#siatka .dz.trasa')].filter(e => { const r = e.getBoundingClientRect(); return r.left < g.left - 4 || r.right > g.right + 4 || r.top < g.top - 8 || r.bottom > g.bottom + 8; }).length; });
  let wyszlo = 0; for (let i = 0; i < 6; i++) { wyszlo += await wKaflu(); await p.waitForTimeout(400); }
  ok('dni nie wychodzą poza siatkę podczas unoszenia', wyszlo === 0, 'poza siatką: ' + wyszlo);
  const przed = await p.evaluate(() => document.querySelector('#siatka .dz.trasa.wybrany').dataset.d);
  const inny = await p.evaluate(() => [...document.querySelectorAll('#siatka .dz.trasa')].map(e => e.dataset.d).find(d => d !== document.querySelector('#siatka .dz.trasa.wybrany').dataset.d));
  await p.click(`#siatka .dz.trasa[data-d="${inny}"]`, { force: true }); await p.waitForTimeout(900);
  const po = await p.evaluate(() => document.querySelector('#siatka .dz.trasa.wybrany').dataset.d);
  ok('dni (mimo unoszenia) dają się klikać: wybór przechodzi na kliknięty dzień', po === inny && po !== przed, przed + ' → ' + po);
  const a2 = await animacje(p), sonary = a2.filter(x => x.nazwa === 'zycie-sonar').length;
  ok('fala pulsu przeszła razem z wyborem (jeden pulsujący dzień)', sonary === 1, 'sonar=' + sonary);

  /* ---- zrzuty do oceny wzrokowej ---- */
  const kal = p.locator('#kC'), dok = p.locator('#kF');
  for (let i = 0; i < 3; i++) { await kal.screenshot({ path: `/tmp/zycie_kal_${i}.png` }); await dok.screenshot({ path: `/tmp/zycie_dok_${i}.png` }); await p.waitForTimeout(700); }

  /* ---- jasny motyw działa tak samo ---- */
  await p.evaluate(() => { document.documentElement.dataset.theme = 'light'; }); await p.waitForTimeout(800);
  const aj = await animacje(p); ok('w jasnym motywie ruch działa tak samo', aj.filter(x => /^zycie-/.test(x.nazwa)).length >= a.length - 2 && aj.every(x => /^zycie-/.test(x.nazwa)), aj.length + ' animacji');
  const bledy = t.bledy.filter(b => !/favicon|ERR_|net::|Failed to load/.test(b));
  ok('bez błędów w konsoli', bledy.length === 0, bledy.join(' | ').slice(0, 300));
  await t.zamknij();

  /* ---- „Ogranicz ruch” w systemie: nic się nie rusza ---- */
  const r = await otworz({ w: 1440, h: 900, przyklad: true, ruch: 'reduce', bezZycia: false });
  await r.p.goto(r.adres + '/index.html'); await r.p.waitForSelector('#siatka .dz.trasa', { timeout: 120000 }); await r.p.waitForTimeout(3000);
  const ar = await animacje(r.p); ok('przy „Ogranicz ruch” w systemie nie działa żadna animacja', ar.length === 0, JSON.stringify(ar.slice(0, 4)));
  await r.zamknij();
  console.log(kod ? 'KONIEC kod=1' : 'KONIEC kod=0'); process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
