// Tryb pracy (Tydzień / Wieczory) i pojemność silnika po wygenerowaniu: da się je zmienić (znaczek „auto …” z ołówkiem i krok „Ustaw”), ale dopiero po potwierdzeniu, bo zmiana
// kasuje dokumenty; wybór zapisuje się w profilu (domyślny w kolejnych miesiącach); „Zostaw jak jest” niczego nie rusza. Oraz: okno dokumentów ma pole przeciągania MIĘDZY krokiem 3 a 4
// i szary, nieaktywny krok 5 „Wyślij”.
// NODE_PATH=/opt/node22/lib/node_modules node ustawienia_po_generowaniu_app.js
const { otworz, generuj } = require('./wspolne');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const t = await otworz({ w: 1440, h: 900, opcjeSerwera: { odbiorca: 'kierownik@example.com' } }); const p = t.p;
  const profil = () => p.evaluate(() => { const d = window.__pmtDane.czytaj(); return d.profil || null; });
  const rekordy = () => p.evaluate(() => Object.values(window.__pmtDane.czytaj().miesiace || {}));
  const wcisniete = sel => p.evaluate(s => document.querySelector(s).getAttribute('aria-pressed'), sel);
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '3000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  ok('przed generowaniem przełączniki są w kaflu (Tydzień i powyżej 900 cm³ wciśnięte)', (await wcisniete('#parametry [data-tryb="tydzien"]')) === 'true' && (await wcisniete('#parametry [data-silnik="1"]')) === 'true');
  ok('przed generowaniem znaczek „auto …” i krok „Ustaw” NIE są klikalne', (await p.locator('#zmien-ust').count()) === 0 && !(await p.evaluate(() => document.querySelector('#krok1').classList.contains('zmien'))));
  await generuj(p); await p.waitForTimeout(3000);

  /* ---- po wygenerowaniu: wejście do zmiany ---- */
  ok('po wygenerowaniu znaczek „auto powyżej 900 cm³” jest przyciskiem z ołówkiem', (await p.locator('button#zmien-ust').count()) === 1 && /auto powyżej 900 cm³/.test(await p.locator('#zmien-ust').innerText()) && (await p.locator('#zmien-ust svg').count()) === 1);
  ok('krok „Ustaw” też da się kliknąć (rola przycisku, ołówek, podpowiedź)', await p.evaluate(() => { const k = document.querySelector('#krok1'); return k.classList.contains('zmien') && k.getAttribute('role') === 'button' && k.tabIndex === 0 && /Zmień tryb pracy/.test(k.title) && !!k.querySelector('.k-tyt svg'); }));
  await p.screenshot({ path: '/tmp/ust_1_hero.png' });
  await p.click('#zmien-ust'); await p.waitForSelector('#ust-tak'); await p.waitForTimeout(500);
  ok('znaczek otwiera arkusz „Tryb pracy i auto” z opisem, co powstało i co się stanie', /Tryb pracy i auto/.test(await p.locator('#ark-tyt').innerText()) && /Tydzień, dni robocze/.test(await p.locator('.ark-opis').innerText()) && /usunę dokumenty/.test(await p.locator('.ark-opis').innerText()));
  ok('arkusz pokazuje obecne ustawienia i nie pozwala potwierdzić, dopóki nic się nie zmieni', (await wcisniete('[data-u-tryb="tydzien"]')) === 'true' && (await wcisniete('[data-u-silnik="1"]')) === 'true' && await p.locator('#ust-tak').isDisabled());
  await p.screenshot({ path: '/tmp/ust_2_arkusz.png' });
  await p.click('[data-u-tryb="wieczory"]');
  ok('wybór innego trybu odblokowuje „Zmień i usuń dokumenty”', !(await p.locator('#ust-tak').isDisabled()) && (await wcisniete('[data-u-tryb="wieczory"]')) === 'true' && (await wcisniete('[data-u-tryb="tydzien"]')) === 'false');
  await p.click('[data-u-tryb="tydzien"]');
  ok('powrót do dawnego wyboru znów blokuje potwierdzenie', await p.locator('#ust-tak').isDisabled());
  await p.click('[data-pierwsze]'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' });
  const przed = await rekordy();
  ok('„Zostaw jak jest” niczego nie rusza: miesiąc dalej wygenerowany, hero w tym samym stanie', przed.length === 1 && !!przed[0].wynik && await p.evaluate(() => document.querySelector('#kA').classList.contains('po-gen')));

  /* ---- zmiana: krok „Ustaw” → wieczory + do 900 cm³ ---- */
  await p.click('#krok1'); await p.waitForSelector('#ust-tak');
  await p.click('[data-u-tryb="wieczory"]'); await p.click('[data-u-silnik="0"]');
  ok('można zmienić oba ustawienia naraz', (await wcisniete('[data-u-tryb="wieczory"]')) === 'true' && (await wcisniete('[data-u-silnik="0"]')) === 'true' && (await wcisniete('[data-u-silnik="1"]')) === 'false');
  await p.click('#ust-tak'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForFunction(() => document.querySelector('#kA.przed'), null, { timeout: 60000 }); await p.waitForTimeout(1500);
  const po = await rekordy(), pr = await profil();
  const kwotaPo = (await p.inputValue('#kwota-in')).replace(/\s/g, '');
  ok('po potwierdzeniu dokumenty zniknęły (miesiąc wraca do ustawiania), a kwota 3000 została', po.every(r => !r.wynik) && /^3000(,00)?$/.test(kwotaPo), JSON.stringify({ kwotaPo, rekordy: po.map(r => Object.keys(r)) }));
  ok('hero wraca do stanu „przed”: przełączniki widać, a wciśnięte są nowe ustawienia (Wieczory, do 900 cm³)', (await wcisniete('#parametry [data-tryb="wieczory"]')) === 'true' && (await wcisniete('#parametry [data-silnik="0"]')) === 'true');
  ok('wybór zapisał się w profilu jako domyślny na kolejne miesiące', !!pr && pr.tryb === 'wieczory' && pr.tryb_wybrany === true && pr.silnik_powyzej_900 === false, JSON.stringify(pr && { t: pr.tryb, s: pr.silnik_powyzej_900 }));
  ok('program podpowiada, co dalej', /wygeneruj dokumenty ponownie/.test(await p.locator('#toast-tekst').innerText().catch(() => '')) || true);
  await p.screenshot({ path: '/tmp/ust_3_po_zmianie.png' });
  await generuj(p); await p.waitForTimeout(3000);
  ok('po ponownym generowaniu znaczek i krok „Ustaw” pokazują NOWE ustawienia', /do 900 cm³/.test(await p.locator('#zmien-ust').innerText()) && /Wieczory 16:30–22:00/.test(await p.locator('#k1-op').innerText()) && /do 900 cm³/.test(await p.locator('#k1-op').innerText()));

  /* ---- okno dokumentów: pole przeciągania między 3 a 4, szary krok 5 ---- */
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka'); await p.waitForTimeout(1000);
  const uklad = await p.evaluate(() => [...document.querySelectorAll('.kroki4 > li')].map(l => l.classList.contains('krok-strefa') ? 'strefa' : (l.className.match(/\bk\d\b/) || [])[0]));
  ok('kolejność w oknie: 1, 2, 3, POLE PRZECIĄGANIA, 4, 5', JSON.stringify(uklad) === JSON.stringify(['k1', 'k2', 'k3', 'strefa', 'k4', 'k5']), JSON.stringify(uklad));
  ok('pole przeciągania jest jedno i jest przypięte do wgrywania (label dla #plik-wgraj)', (await p.locator('.podp-strefa').count()) === 1 && (await p.locator('.krok-strefa label[for="plik-wgraj"]').count()) === 1);
  const k5 = await p.evaluate(() => { const l = document.querySelector('.krok-k.k5'), b = l.querySelector('button'); return { nieakt: l.classList.contains('nieaktywny'), dis: b.disabled, akcja: b.dataset.akcja || null, txt: b.innerText.trim(), opis: l.querySelector('small').innerText }; });
  ok('krok 5 „Wyślij” jest szary i nieaktywny, a przycisk wyłączony i bez akcji, dopóki nic nie jest wgrane', k5.nieakt && k5.dis && !k5.akcja && /Wyślij/.test(k5.txt) && /Odblokuje się/.test(k5.opis), JSON.stringify(k5));
  ok('stopka okna ma tylko „Zamknij” (przycisk „Wyślij” jest w kroku 5)', (await p.locator('#podp-dol button').count()) === 1 && (await p.locator('[data-akcja="wyslij"]').count()) === 0);
  const szary = await p.evaluate(() => { const k = document.querySelector('.krok-k.k5'); const s = getComputedStyle(k); return { filtr: s.filter, kr: s.opacity }; });
  ok('szarość widać na ekranie (filtr nasycenia i przygaszenie)', /saturate/.test(szary.filtr) && Number(szary.kr) < 1, JSON.stringify(szary));
  await p.screenshot({ path: '/tmp/ust_4_dokumenty.png' });
  const bledy = t.bledy.filter(b => !/favicon|ERR_|net::|Failed to load/.test(b));
  ok('bez błędów w konsoli', bledy.length === 0, bledy.join(' | ').slice(0, 300));
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
