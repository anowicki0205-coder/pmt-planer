// Pulpit pod otwartym oknem (np. „Dokumenty do podpisu”) blaknie i rozmywa się, żeby nie zwracał na siebie uwagi;
// po zamknięciu okna wraca do normy, a okno logowania (które samo jest tłem) tego nie uruchamia.
// NODE_PATH=/opt/node22/lib/node_modules node okno_tlo_app.js           (MOTYW=light — motyw Dzień; WYJ=/ścieżka.png — zrzut okna)
const { otworz, generuj } = require('./wspolne'); const { BackendMock } = require('./backend_mock');
(async () => {
  const motyw = process.env.MOTYW || 'dark';
  const t = await otworz({ w: 1440, h: 900, motyw }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const czytaj = () => { const a = document.querySelector('#aplikacja'), cs = getComputedStyle(a); return { okno: document.documentElement.classList.contains('okno'), filtr: cs.filter, kryje: +cs.opacity }; };
  const tlo = async () => { await p.waitForFunction(() => { const a = document.querySelector('#aplikacja'); return !a.getAnimations().some(x => x.playState === 'running'); }, null, { timeout: 20000, polling: 200 }).catch(() => {}); return p.evaluate(czytaj); };      // przejście .4 s kończy się zanim odczytamy wartości (na grafice programowej klatki są rzadkie)
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.waitForTimeout(900); let s = await tlo();
  ok('okno „Moje dane” rozmywa i wycisza pulpit pod spodem', s.okno && /blur\(8px\)/.test(s.filtr) && s.kryje < .6, JSON.stringify(s));
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(1500);
  s = await tlo();
  ok('po zamknięciu okna pulpit wraca do normy (ostry, w pełni kryjący)', !s.okno && s.filtr === 'none' && s.kryje === 1, JSON.stringify(s));
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await generuj(p); await p.waitForTimeout(3000);
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka'); await p.waitForTimeout(1500);
  s = await tlo();
  ok('okno „Dokumenty do podpisu” rozmywa i wycisza pulpit pod spodem', s.okno && /blur\(8px\)/.test(s.filtr) && s.kryje < .6, JSON.stringify(s));
  const okno = await p.evaluate(() => { const o = document.querySelector('#arkusz'), cs = getComputedStyle(o); return { filtr: cs.filter, kryje: +cs.opacity, szer: o.getBoundingClientRect().width }; });
  ok('samo okno pozostaje ostre i w pełni widoczne', okno.filtr === 'none' && okno.kryje === 1 && okno.szer > 300, JSON.stringify(okno));
  await p.screenshot({ path: process.env.WYJ || '/tmp/okno_tlo.png' });
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(1200);
  s = await tlo();
  ok('po zamknięciu „Dokumentów do podpisu” pulpit znów jest ostry', !s.okno && s.filtr === 'none' && s.kryje === 1, JSON.stringify(s));
  console.log('  błędy konsoli:', JSON.stringify(t.bledy.slice(0, 6))); if (t.bledy.length) kod = 1;
  await t.zamknij();

  /* okno logowania jest samo tłem — pulpitu nie rozmywamy dodatkowo (i tak jest schowany) */
  const B = new BackendMock(); const t2 = await otworz({ w: 1440, h: 900, motyw, zalogowany: false, backend: B }); const q = t2.p;
  await q.goto(t2.adres + '/index.html'); await q.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await q.waitForTimeout(1200);
  const l = await q.evaluate(() => ({ okno: document.documentElement.classList.contains('okno') }));
  ok('okno logowania nie uruchamia rozmycia pulpitu', !l.okno, JSON.stringify(l));
  await t2.zamknij();
  process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
