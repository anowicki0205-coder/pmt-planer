// Dźwięki w aplikacji (js/dzwiek.js podpięte w aplikacja.js, podpis.js, zywe.js): przyciski w nagłówku i w menu konta, ustawienia pamiętane na urządzeniu, momenty, w których gra efekt
// (okna, motyw, generowanie), oraz to, że dźwięk niczego nie psuje (brak błędów w konsoli, wyciszenie działa). Sama synteza: dzwiek_test.js; podpisy/wysyłka: podpis_offline_app.js; odhaczanie: plan_app.js.
// NODE_PATH=/opt/node22/lib/node_modules node dzwiek_app.js
const { otworz, generuj } = require('./wspolne');
(async () => {
  const t = await otworz({ w: 1440, h: 900, bezZycia: true }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const log = () => p.evaluate(() => [...window.__pmtDzwiek.log]), czysc = () => p.evaluate(() => { window.__pmtDzwiek.log.length = 0; });
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3500);

  /* ---------- przyciski i ustawienia ---------- */
  const st = () => p.evaluate(() => ({ efekty: document.querySelector('#dzwiek').getAttribute('aria-pressed'), muzyka: document.querySelector('#muzyka').getAttribute('aria-pressed'),
    mEfekty: document.querySelector('[data-dzwiek="efekty"]').getAttribute('aria-pressed'), mMuzyka: document.querySelector('[data-dzwiek="muzyka"]').getAttribute('aria-pressed'), ikona: document.querySelector('#dzwiek use').getAttribute('href') }));
  const s0 = await st();
  ok('w nagłówku są dwa przyciski: głośnik (efekty) i nutka (podkład); domyślnie efekty włączone, podkład wyłączony', await p.locator('#dzwiek').isVisible() && await p.locator('#muzyka').isVisible() && s0.efekty === 'true' && s0.muzyka === 'false' && s0.ikona === '#i-glosnik', JSON.stringify(s0));
  ok('te same ustawienia są w menu konta (sekcja „Dźwięk”: Efekty i Muzyka) i pokazują ten sam stan', s0.mEfekty === 'true' && s0.mMuzyka === 'false' && (await p.locator('#konto-menu h3', { hasText: 'Dźwięk' }).count()) === 1);
  ok('przyciski mają opisy dla czytników ekranu (aria-label) i stan (aria-pressed)', /włączone/.test(await p.locator('#dzwiek').getAttribute('aria-label')) && /wyłączona/.test(await p.locator('#muzyka').getAttribute('aria-label')));
  await p.screenshot({ path: '/tmp/dzwiek_naglowek.png', clip: { x: 900, y: 0, width: 540, height: 90 } });

  /* ---------- efekty w ważnych momentach ---------- */
  await czysc(); await p.click('#moje-dane', { force: true }).catch(() => {}); await p.click('#konto'); await p.waitForTimeout(300); await p.click('#moje-dane'); await p.waitForSelector('#arkusz-tlo.otwarty'); await p.waitForTimeout(300);
  ok('otwarcie okna gra „okno” (raz, nie przy zmianie treści tego samego okna)', (await log()).filter(x => x === 'okno').length === 1, JSON.stringify(await log()));
  await czysc(); await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(200);
  ok('zamknięcie okna gra „okno-zam”', (await log()).includes('okno-zam'), JSON.stringify(await log()));
  await czysc(); await p.click('#motyw'); await p.waitForTimeout(900);
  ok('przełączenie Noc/Dzień gra „motyw”', (await log()).includes('motyw'), JSON.stringify(await log()));
  await p.click('#motyw'); await p.waitForTimeout(900);
  ok('zwykłe kliknięcie przycisku gra „klik”, ale nie przy samych przyciskach dźwięku (te nie dublują dźwięków)', await (async () => { await czysc(); await p.click('#m-dalej'); await p.waitForTimeout(150); const l1 = await log(); await czysc(); await p.click('#dzwiek'); await p.waitForTimeout(150); const l2 = await log(); await p.click('#dzwiek'); await p.waitForTimeout(150); return l1.includes('klik') && !l2.includes('klik'); })());
  await p.click('#m-wstecz'); await p.waitForTimeout(500);

  /* ---------- wyciszenie z nagłówka i z menu, podkład ---------- */
  await czysc(); await p.click('#dzwiek'); await p.waitForTimeout(150);
  const s1 = await st();
  ok('wyciszenie głośnikiem: przycisk w nagłówku i w menu pokazują wyciszenie (aria-pressed=false), ikona „głośnik przekreślony”, zapis na urządzeniu', s1.efekty === 'false' && s1.mEfekty === 'false' && s1.ikona === '#i-glosnik-wyl' && await p.evaluate(() => localStorage.getItem('pmt-ui-dzwiek')) === '0', JSON.stringify(s1));
  await czysc(); await p.click('#motyw'); await p.waitForTimeout(900); await p.click('#motyw'); await p.waitForTimeout(900);
  ok('po wyciszeniu żaden efekt nie jest odtwarzany (motyw, kliknięcia)', (await log()).length === 0, JSON.stringify(await log()));
  await p.click('#konto'); await p.waitForTimeout(400); await p.click('[data-dzwiek="efekty"]'); await p.waitForTimeout(200);
  const s2 = await st();
  ok('włączenie z menu konta przywraca efekty i synchronizuje przycisk w nagłówku', s2.efekty === 'true' && s2.mEfekty === 'true' && s2.ikona === '#i-glosnik', JSON.stringify(s2));
  await p.click('[data-dzwiek="muzyka"]'); await p.waitForTimeout(1500);
  const s3 = await st(), gra = await p.evaluate(() => window.__pmtDzwiek.muzykaGra());
  ok('włączenie muzyki z menu: podkład gra, przycisk „nutka” w nagłówku też jest wciśnięty, wybór zapamiętany', gra && s3.muzyka === 'true' && s3.mMuzyka === 'true' && await p.evaluate(() => localStorage.getItem('pmt-ui-muzyka')) === '1', JSON.stringify(s3));
  await p.keyboard.press('Escape'); await p.click('#muzyka'); await p.waitForTimeout(300);
  const s4 = await st();
  ok('wyłączenie nutką z nagłówka zatrzymuje podkład; menu pokazuje to samo', !(await p.evaluate(() => window.__pmtDzwiek.muzykaGra())) && s4.muzyka === 'false' && s4.mMuzyka === 'false', JSON.stringify(s4));

  /* ---------- głośność w menu konta ---------- */
  await p.click('#konto'); await p.waitForTimeout(400);
  const sg0 = await p.evaluate(() => ({ wart: document.querySelector('#glosnosc').value, out: document.querySelector('#glosnosc').parentElement.querySelector('output').textContent, widoczny: !!document.querySelector('#glosnosc').offsetParent, gl: window.__pmtDzwiek.glosnosc() }));
  ok('w menu konta (sekcja „Dźwięk”) jest suwak „Głośność” ze stanem 70% i napisem obok', sg0.widoczny && sg0.wart === '70' && sg0.out === '70%' && sg0.gl === 70, JSON.stringify(sg0));
  await p.evaluate(() => { const r = document.querySelector('#glosnosc'); r.value = '35'; r.dispatchEvent(new Event('input', { bubbles: true })); r.dispatchEvent(new Event('change', { bubbles: true })); }); await p.waitForTimeout(400);
  const sg1 = await p.evaluate(() => ({ gl: window.__pmtDzwiek.glosnosc(), out: document.querySelector('#glosnosc').parentElement.querySelector('output').textContent, wz: window.__pmtDzwiek.wzmocnienie(), mag: localStorage.getItem('pmt-ui-glosnosc') }));
  ok('zmiana suwaka na 35%: napis „35%”, zapis na urządzeniu, wzmocnienie główne spada do ≈ 0,40 (0,8 × 35/70)', sg1.gl === 35 && sg1.out === '35%' && sg1.mag === '35' && (sg1.wz === null || Math.abs(sg1.wz - .4) < .02), JSON.stringify(sg1));
  await p.evaluate(() => { const r = document.querySelector('#glosnosc'); r.value = '70'; r.dispatchEvent(new Event('input', { bubbles: true })); r.dispatchEvent(new Event('change', { bubbles: true })); localStorage.removeItem('pmt-ui-glosnosc'); }); await p.keyboard.press('Escape'); await p.waitForTimeout(200);

  /* ---------- generowanie ---------- */
  // jak użytkownik: najpierw kwota do rozliczenia (bez niej „Generuj” prosi o potwierdzenie z kwotą), jednorazowe okna informacji zamknięte
  if (await p.locator('#arkusz-tlo.otwarty').count()) { await p.keyboard.press('Escape'); await p.waitForFunction(() => !document.querySelector('#arkusz-tlo.otwarty'), null, { timeout: 5000, polling: 100 }).catch(() => {}); }
  await p.fill('#kwota-in', '3095,26'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await czysc(); await generuj(p); await p.waitForTimeout(500);
  const lg = await log(), ig = lg.indexOf('gen-start'), ik = lg.indexOf('gen-koniec');
  ok('generowanie: najpierw „gen-start”, potem „gen-koniec” (raz każdy)', ig >= 0 && ik > ig && lg.filter(x => x === 'gen-start').length === 1 && lg.filter(x => x === 'gen-koniec').length === 1, JSON.stringify(lg));
  const bledy = t.bledy.filter(b => !/net::ERR_INTERNET_DISCONNECTED/.test(b));
  ok('w konsoli nie było błędów ani ostrzeżeń związanych z dźwiękiem (m.in. „AudioContext was not allowed to start”)', !bledy.some(b => /audio|dźwi/i.test(b)), JSON.stringify(bledy.filter(b => /audio|dźwi/i.test(b))));
  ok('żadnych błędów konsoli', bledy.length === 0, JSON.stringify(bledy.slice(0, 3)));
  await t.b.close(); t.sv && t.sv.close && t.sv.close();
  console.log(kod ? 'KONIEC kod=1' : 'KONIEC kod=0'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
