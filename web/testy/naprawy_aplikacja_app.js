// Poprawki z przeglądu aplikacji (pakiet „web-aplikacja”): okna trzymają fokus (pulpit pod spodem jest inert), komunikaty są widoczne w trybie spokojnym,
// tryb pracy i auto wybrane przed „Moimi danymi” zostają, „Wieczory” bez profilu liczą soboty, dni wolne przetrwają zmianę miesiąca, szybkie strzałki liczą od miesiąca, który się wczytuje,
// etykieta kalendarza mówi, który to miesiąc, błąd zapisu po generowaniu nie zostawia aplikacji w „generowaniu”, zmiana miesiąca w trakcie generowania nie przenosi dokumentów do innego miesiąca,
// nazwy miejscowości nie wchodzą do strony jako znaczniki, „Zmień kwotę” zostawia tryb i auto miesiąca, a kafel „Dziś” przechodzi na nowy dzień po północy.
// NODE_PATH=/opt/node22/lib/node_modules node naprawy_aplikacja_app.js
const { wpiszAdres, otworz } = require('./wspolne');
(async () => {
  const t = await otworz({ w: 1440, h: 900 }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const wcisniete = s => p.evaluate(s => document.querySelector(s).getAttribute('aria-pressed') === 'true', s);
  const klasy = d => p.evaluate(d => (document.querySelector(`#siatka [data-d="${d}"]`) || {}).className || '', d);
  const miesiac = () => p.locator('#m-nazwa').innerText();
  const czekajMiesiac = (re, ms = 30000) => p.waitForFunction(r => new RegExp(r, 'i').test(document.querySelector('#m-nazwa').textContent), re, { timeout: ms, polling: 100 }).then(() => p.waitForTimeout(900)).then(() => true, () => false);
  const dane = () => p.evaluate(() => window.__pmtDane.czytaj());
  const tabWychodzi = async n => { for (let i = 0; i < n; i++) { await p.keyboard.press('Tab'); if (await p.evaluate(() => document.querySelector('#aplikacja').contains(document.activeElement))) return true; } return false; };

  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 120000 }); await p.waitForTimeout(1500);

  /* ---- okno z aria-modal: pulpit pod spodem jest nieaktywny ---- */
  ok('otwarte okno „Moje dane”: pulpit pod spodem jest inert', await p.evaluate(() => document.querySelector('#aplikacja').inert === true));
  ok('Tab (40 razy) nie wychodzi z okna do pulpitu pod spodem', !(await tabWychodzi(40)));
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(600);
  ok('po zamknięciu okna pulpit znów jest aktywny', await p.evaluate(() => document.querySelector('#aplikacja').inert === false));

  /* ---- bez Moich danych: Wieczory, do 900 cm³, kwota, dzień wolny ---- */
  await p.click('#parametry [data-tryb="wieczory"]'); await p.waitForFunction(() => document.querySelector('#parametry [data-tryb="wieczory"]').getAttribute('aria-pressed') === 'true', null, { timeout: 30000 }); await p.waitForTimeout(1500);
  ok('bez Moich danych „Wieczory” liczą soboty jako dni robocze (sobota 5 września da się oznaczyć, 26 dni roboczych)', /przelacz/.test(await klasy(5)) && /26 dni roboczych/.test(await p.locator('#c-tyt').innerText()), `${await klasy(5)} · ${await p.locator('#c-tyt').innerText()}`);
  await p.click('#parametry [data-silnik="0"]'); await p.waitForTimeout(500);
  await p.fill('#kwota-in', '3000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await p.click('#siatka [data-d="8"]', { force: true }); await p.waitForTimeout(600);
  ok('dzień wolny 8 września zaznaczony', /urlop/.test(await klasy(8)));

  /* ---- „Generuj” bez danych → Moje dane → Zapisz: wybór z pulpitu zostaje, komunikat widać ---- */
  await p.click('#podpisz'); await p.waitForSelector('#arkusz-tlo.otwarty #d-imie', { timeout: 30000 }); await p.waitForTimeout(500);
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await wpiszAdres(p, 'ul. Testowa 1, 00-001 Warszawa');
  await p.evaluate(() => { window.__toast = { od: 0, do: 0 }; const el = document.querySelector('#toast'), t0 = performance.now(); const z = setInterval(() => { const t = performance.now() - t0; if (el.classList.contains('widoczny')) { if (!window.__toast.od) window.__toast.od = t; window.__toast.do = t; } if (t > 9000) clearInterval(z); }, 40); });      // klasa, nie nieprzezroczystość: na grafice programowej klatki są zbyt rzadkie, żeby mierzyć przejście
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 30000 }); await p.waitForTimeout(3000);
  await p.waitForTimeout(2000); const czasToastu = await p.evaluate(() => window.__toast.do - window.__toast.od);
  ok('komunikat „Zapisano Twoje dane” zostaje na ekranie ok. 2,8 s także w trybie spokojnym (nie znika, zanim się narysuje)', czasToastu >= 2000 && czasToastu < 4000 && /Zapisano/.test(await p.locator('#toast-tekst').innerText()), Math.round(czasToastu) + ' ms');
  const pr = (await dane()).profil || {};
  ok('pierwszy zapis Moich danych przejmuje tryb i auto z pulpitu (Wieczory, do 900 cm³)', pr.tryb === 'wieczory' && pr.tryb_wybrany === true && pr.silnik_powyzej_900 === false, JSON.stringify({ t: pr.tryb, w: pr.tryb_wybrany, s: pr.silnik_powyzej_900 }));
  ok('po zapisie pulpit dalej ma Wieczory i do 900 cm³, a dzień wolny został', await wcisniete('#parametry [data-tryb="wieczory"]') && await wcisniete('#parametry [data-silnik="0"]') && /urlop/.test(await klasy(8)));

  /* ---- dni wolne przetrwają zmianę miesiąca; szybkie strzałki; etykieta kalendarza ---- */
  await p.click('#m-dalej'); await czekajMiesiac('październik');
  await p.click('#m-wstecz'); await czekajMiesiac('wrzesień');
  ok('po wizycie w październiku dzień wolny 8 września dalej jest wolny (jak kwota)', /urlop/.test(await klasy(8)) && /^3\s?000/.test(await p.inputValue('#kwota-in')), `${await klasy(8)} · ${await p.inputValue('#kwota-in')}`);
  await p.evaluate(() => { const b = document.querySelector('#m-dalej'); b.click(); b.click(); });
  ok('dwa szybkie kliknięcia „dalej” z września prowadzą do listopada', await czekajMiesiac('listopad', 15000), await miesiac());
  ok('etykieta kalendarza dla czytnika ekranu mówi o bieżącym miesiącu', /^Dni listopada 2026 — poziom cieczy/.test(await p.getAttribute('#siatka', 'aria-label')), await p.getAttribute('#siatka', 'aria-label'));
  await p.evaluate(() => { const b = document.querySelector('#m-wstecz'); b.click(); b.click(); });
  ok('dwa szybkie kliknięcia „wstecz” wracają do września', await czekajMiesiac('wrzesień', 15000), await miesiac());

  /* ---- błąd zapisu po generowaniu (pełna pamięć): aplikacja nie zostaje w „generowaniu” ---- */
  await p.evaluate(() => { window.__putOrig = IDBObjectStore.prototype.put; IDBObjectStore.prototype.put = function () { throw new DOMException('Brak miejsca (test)', 'QuotaExceededError'); }; });
  await p.click('#podpisz'); await p.waitForSelector('#potwierdz-gen', { timeout: 60000 }); await p.waitForTimeout(400);
  ok('okno „Sprawdź, zanim wygeneruję”: Tab nie wychodzi do strzałek miesiąca pod spodem', !(await tabWychodzi(15)));
  await p.click('#potwierdz-gen');
  const blad = await p.waitForFunction(() => /Nie udało się zapisać/.test((document.querySelector('#arkusz-tresc') || {}).textContent || ''), null, { timeout: 240000, polling: 300 }).then(() => true, () => false);
  const stanBledu = await p.evaluate(() => ({ zbiera: document.querySelector('#podpisz').classList.contains('zbiera'), busy: document.querySelector('#podpisz').hasAttribute('aria-busy'), strzalki: document.querySelector('#m-wstecz').disabled, rekord: !!(window.__pmtDane.czytaj().miesiace || {})['2026-09'] }));
  ok('błąd zapisu PDF: okno z wyjaśnieniem, przycisk nie wisi w „Przerwij generowanie”, strzałki działają', blad && !stanBledu.zbiera && !stanBledu.busy && !stanBledu.strzalki, JSON.stringify(stanBledu));
  ok('błąd zapisu PDF: miesiąc nie udaje wygenerowanego (brak rekordu bez plików)', !stanBledu.rekord);
  await p.evaluate(() => { IDBObjectStore.prototype.put = window.__putOrig; }); await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(600);

  /* ---- zmiana miesiąca w trakcie generowania ---- */
  await p.evaluate(() => {
    const b = document.querySelector('#podpisz'); window.__wyscig = null;
    const o = new MutationObserver(() => { if (!b.classList.contains('zbiera') || window.__wyscig) return; o.disconnect();
      window.__wyscig = { wylaczone: ['#m-wstecz', '#m-dalej', '#m-nazwa'].every(s => document.querySelector(s).disabled) };
      const w = document.querySelector('#m-wstecz'); w.click(); setTimeout(() => w.click(), 60); document.querySelector('#parametry [data-tryb="tydzien"]').click(); document.querySelector('#parametry [data-silnik="1"]').click(); });
    o.observe(b, { attributes: true, attributeFilter: ['class'] });
  });
  await p.click('#podpisz'); await p.waitForSelector('#potwierdz-gen', { timeout: 60000 }); await p.click('#potwierdz-gen');
  await p.waitForFunction(() => document.querySelector('#kA.po-gen'), null, { timeout: 240000, polling: 300 }); await p.waitForTimeout(3000);
  const wys = await p.evaluate(() => window.__wyscig), mies = (await dane()).miesiace || {};
  ok('w trakcie generowania strzałki i okno roku są wyłączone', !!wys && wys.wylaczone, JSON.stringify(wys));
  ok('klik „wstecz” w trakcie generowania nie przenosi dokumentów: zapisany jest tylko wrzesień, z parametrami września', Object.keys(mies).join(',') === '2026-09' && mies['2026-09'].params.miesiac === 9 && !!mies['2026-09'].wynik, Object.keys(mies).join(','));
  ok('po generowaniu na ekranie wrzesień, strzałki znów działają', /wrzesień/i.test(await miesiac()) && !(await p.evaluate(() => document.querySelector('#m-wstecz').disabled)), await miesiac());
  const par = (mies['2026-09'] || {}).params || {};
  ok('dokumenty powstały dla wyboru z pulpitu: Wieczory, do 900 cm³, wolne 8 września', par.tryb === 'wieczory' && par.silnik_powyzej_900 === false && JSON.stringify(par.wolne) === '[8]', JSON.stringify({ t: par.tryb, s: par.silnik_powyzej_900, w: par.wolne }));
  ok('klik „Tydzień” w trakcie generowania nie zmienia trybu (profil dalej Wieczory, pulpit pokazuje tryb dokumentów)', ((await dane()).profil || {}).tryb === 'wieczory' && await wcisniete('#parametry [data-tryb="wieczory"]'), ((await dane()).profil || {}).tryb);
  ok('klik „powyżej 900 cm³” w trakcie generowania nie zmienia auta (profil dalej do 900 cm³)', ((await dane()).profil || {}).silnik_powyzej_900 === false && await wcisniete('#parametry [data-silnik="0"]'), String(((await dane()).profil || {}).silnik_powyzej_900));
  ok('po udanym generowaniu zapamiętane dni wolne miesiąca są wyczyszczone (są w rekordzie)', ((await dane()).ustawienia || {})['wolne-2026-09'] == null);

  /* ---- nazwy miejscowości ze znacznikami (np. z adresu w Moich danych) ---- */
  const PAY = 'Nowe<style id="xss-styl">#xss-nic{color:red}</style>" data-xss="1';
  await p.evaluate(P => { const d = window.__pmtDane.czytaj(); for (const dz of d.miesiace['2026-09'].wynik.dni) { dz.etapy[0].skad = P; for (const e of dz.etapy) e.dokad = P; (dz.punkty || []).forEach(q => { q.m = P; }); } window.__pmtDane.zapisz(d); }, PAY);
  await p.click('#m-dalej'); await czekajMiesiac('październik'); await p.click('#m-wstecz'); await czekajMiesiac('wrzesień');
  await p.click('#siatka button.dz.trasa >> nth=1', { force: true }); await p.waitForTimeout(2000);
  const xss = await p.evaluate(() => ({ styl: !!document.querySelector('#xss-styl'), atr: !!document.querySelector('[data-xss]'), tabela: (document.querySelector('.odcinki') || {}).textContent || '', tytul: (document.querySelector('.podroz li.pr:not(.dom)') || { title: '' }).title, mapa: [...document.querySelectorAll('.mapka text.tr-et')].map(x => x.textContent).join('|') }));
  ok('nazwa miejscowości ze znacznikami: żaden <style> ani atrybut nie wszedł do strony', !xss.styl && !xss.atr, JSON.stringify({ styl: xss.styl, atr: xss.atr }));
  ok('nazwa pokazana jako tekst w tabeli odcinków, na osi podróży (title) i na mapce', xss.tabela.includes('<style id="xss-styl">') && xss.tytul === PAY && xss.mapa.includes('<style'), JSON.stringify({ t: xss.tabela.slice(0, 60), ty: xss.tytul.slice(0, 40), m: xss.mapa.slice(0, 40) }));

  /* ---- „Zmień kwotę” zostawia tryb i auto miesiąca (profil w międzyczasie zmieniony w innym miesiącu) ---- */
  await p.click('#m-dalej'); await czekajMiesiac('październik');
  await p.click('#parametry [data-tryb="tydzien"]'); await p.waitForTimeout(1200); await p.click('#parametry [data-silnik="1"]'); await p.waitForTimeout(600);
  const pr2 = (await dane()).profil || {};
  ok('w październiku profil przełączony na Tydzień i powyżej 900 cm³', pr2.tryb === 'tydzien' && pr2.silnik_powyzej_900 === true);
  await p.click('#m-wstecz'); await czekajMiesiac('wrzesień');
  await p.click('#b-kwota-w'); await p.waitForSelector('#od-nowa-tak', { timeout: 30000 }); await p.click('#od-nowa-tak');
  await p.waitForFunction(() => document.querySelector('#kA.przed'), null, { timeout: 60000, polling: 200 }); await p.waitForTimeout(1500);
  ok('po „Usuń i wpisz nową kwotę” wrzesień dalej ma Wieczory i do 900 cm³ (nie ustawienia z profilu)', await wcisniete('#parametry [data-tryb="wieczory"]') && await wcisniete('#parametry [data-silnik="0"]'));
  ok('… dni robocze są dla Wieczorów (sobota 5 roboczy), a dzień wolny 8 i kwota zostały', /przelacz/.test(await klasy(5)) && /urlop/.test(await klasy(8)) && /^3\s?000/.test(await p.inputValue('#kwota-in')), `${await klasy(5)} · ${await klasy(8)} · ${await p.inputValue('#kwota-in')}`);
  ok('… tryb i auto miesiąca są zapamiętane na urządzeniu (jak kwota i dni wolne)', JSON.stringify(((await dane()).ustawienia || {})['ust-2026-09']) === JSON.stringify({ tryb: 'wieczory', silnik: false }), JSON.stringify(((await dane()).ustawienia || {})['ust-2026-09']));
  await p.click('#m-dalej'); await czekajMiesiac('październik'); await p.click('#m-wstecz'); await czekajMiesiac('wrzesień');
  ok('po wizycie w październiku wrzesień „od nowa” dalej ma Wieczory, do 900 cm³, sobotę 5 roboczą i wolny 8 (nie wraca do profilu)', await wcisniete('#parametry [data-tryb="wieczory"]') && await wcisniete('#parametry [data-silnik="0"]') && /przelacz/.test(await klasy(5)) && /urlop/.test(await klasy(8)), `${await klasy(5)} · ${await klasy(8)}`);
  ok('… a październik nadal idzie za profilem (Tydzień, powyżej 900 cm³)', ((await dane()).ustawienia || {})['ust-2026-10'] == null);

  /* ---- kafel „Dziś” po północy (aplikacja wraca z tła następnego dnia) ---- */
  const dzien0 = await p.evaluate(() => document.querySelector('#kD .blask').dataset.d);
  await p.evaluate(() => { const R = Date; globalThis.Date = class extends R { constructor(...a) { if (a.length === 0) super(new R().getTime() + 864e5); else super(...a); } }; window.dispatchEvent(new Event('focus')); });
  await p.waitForTimeout(1200);
  const dzien1 = await p.evaluate(() => document.querySelector('#kD .blask').dataset.d);
  ok('po powrocie do aplikacji następnego dnia kafel „Dziś” rysuje się na nowo (15 → 16)', dzien0 === '15' && dzien1 === '16', `${dzien0} → ${dzien1}`);

  const bledy = t.bledy.filter(b => !/DNI-BLAD|net::ERR|Failed to load resource/.test(b));
  ok('bez błędów strony', bledy.length === 0, JSON.stringify(bledy.slice(0, 4)));
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
