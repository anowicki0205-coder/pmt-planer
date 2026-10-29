// Logowanie i dostęp: okno logowania, błędy, podpis zapytań, reset i ustawienie hasła, rozdzielone konta, wygasanie, praca bez sieci.
// Backend to zamiennik reguł Apps Script (testy/backend_mock.js). NODE_PATH=/opt/node22/lib/node_modules node testy/logowanie_app.js
const { otworz } = require('./wspolne'); const { BackendMock, hash } = require('./backend_mock');
(async () => {
  const B = new BackendMock(); const t = await otworz({ w: 1440, h: 900, zalogowany: false, backend: B }); const p = t.p; let kod = 0;
  const przeladuj = async () => { for (let i = 0; i < 4; i++) { try { await p.reload(); return; } catch (e) { if (!/ERR_ABORTED|detached/.test(String(e.message))) throw e; await p.waitForLoadState('load').catch(() => {}); await p.waitForTimeout(600); } } await p.reload(); };      // reload przerwany inną trwającą nawigacją (obciążona maszyna) powtarzamy po jej zakończeniu
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const wyj = '/tmp/logowanie_zrzuty'; require('fs').mkdirSync(wyj, { recursive: true });
  const info = () => p.locator('#dz-info').innerText();
  const czekajInfo = async re => { await p.waitForFunction(r => new RegExp(r).test((document.querySelector('#dz-info') || {}).textContent || ''), re.source, { timeout: 60000, polling: 150 }); return info(); };
  const wpisz = async (k, h) => { await p.fill('#dz-kod', k); await p.fill('#dz-haslo', h); await p.keyboard.press('Enter'); };
  const czekajLogowanie = () => p.waitForSelector('#dz-form', { state: 'attached', timeout: 60000 });
  const czekajAplikacje = () => p.waitForFunction(() => !document.querySelector('#aplikacja').classList.contains('zamknieta') && !document.querySelector('#ladowanie').classList.contains('widoczny'), null, { timeout: 180000, polling: 200 });
  const wyloguj = async () => { await p.waitForLoadState('load'); await p.waitForTimeout(800); const nawigacja = p.waitForEvent('framenavigated', { predicate: f => f === p.mainFrame(), timeout: 30000 }); await p.evaluate(() => document.querySelector('#wyloguj').click()); await nawigacja.catch(() => {}); await czekajLogowanie(); };      // bez czekania na „load” kolejnego przeładowania: przerwane przez nowe przeładowanie dawało sporadyczny ERR_ABORTED
  const stanDostepu = () => p.evaluate(() => JSON.parse(localStorage.getItem('pmt-web-dostep-v1') || '{}'));

  await p.goto(t.adres + '/index.html'); await czekajLogowanie(); await p.waitForTimeout(1200);
  ok('okno logowania zamiast aplikacji', await p.evaluate(() => getComputedStyle(document.querySelector('#aplikacja')).visibility === 'hidden') && (await p.locator('#dz-kod').count()) === 1);
  ok('przycisk Zaloguj czeka na login i hasło', await p.locator('#dz-ok').isDisabled());
  ok('okna logowania nie da się zamknąć Esc', await (async () => { await p.keyboard.press('Escape'); return (await p.locator('#dz-form').count()) === 1; })());
  await p.screenshot({ path: wyj + '/1_logowanie.png' });

  await wpisz('12345', 'zlehaslo'); let i = await czekajInfo(/Nieprawidlowe/);
  ok('złe hasło: komunikat z serwera', /Nieprawidlowe haslo/.test(i), i);
  await p.fill('#dz-haslo', '600100200'); await p.keyboard.press('Enter'); i = await czekajInfo(/ustawione haslo/);
  ok('konto z hasłem nie wpuszcza telefonem', /ustawione haslo/.test(i), i.slice(0, 80));
  ok('żadnej sesji po nieudanym logowaniu', !(await stanDostepu()).kod);

  await p.click('#dz-reset'); await p.waitForSelector('#dr-form'); await p.waitForTimeout(500);
  ok('reset hasła: kod przeniesiony z pola logowania', (await p.inputValue('#dr-kod')) === '12345');
  await p.screenshot({ path: wyj + '/2_reset.png' });
  await p.fill('#dr-tel', '111222333'); await p.fill('#dr-nowe', 'nowehaslo1'); await p.fill('#dr-pow', 'nowehaslo1'); await p.click('#dr-ok'); i = await czekajInfo(/nie zgadza/);
  ok('reset ze złym telefonem odrzucony', /Reset odrzucony.*nie zgadza/i.test(i), i);
  await p.fill('#dr-tel', '600 100 200'); await p.fill('#dr-pow', 'inne'); await p.click('#dr-ok'); i = await czekajInfo(/nie są takie same/);
  ok('różne hasła zatrzymane po stronie aplikacji', /nie są takie same/.test(i));
  await p.fill('#dr-pow', 'nowehaslo1'); await p.click('#dr-ok');
  await czekajAplikacje();
  ok('reset z właściwym telefonem ustawił hasło i od razu zalogował', B.uzytkownicy['12345'].hash === hash('12345', 'nowehaslo1') && (await stanDostepu()).kod === '12345');
  await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 60000 }); await p.waitForTimeout(1500);
  ok('pierwsze logowanie podpowiada imię z serwera w „Moje dane"', (await p.inputValue('#d-imie')) === 'Jan Testowy');
  ok('zapytania podpisane (backend nie zapisał „podpis_zly")', B.log.filter(l => l.zdarzenie === 'podpis_zly').length === 0 && B.log.some(l => l.zdarzenie === 'logowanie_www'));
  await p.waitForFunction(() => 1, null); await p.waitForTimeout(1500);
  ok('puls wysłany po zalogowaniu (uruchomienie liczone)', B.pulsy.length >= 1 && B.pulsy.some(x => x.kod === '12345' && x.uruchomienia >= 1 && x.system === 'Web'), JSON.stringify(B.pulsy.map(x => x.uruchomienia)));      // pierwszy puls to wczesna kontrola ważności dostępu (bez liczników), uruchomienie niesie kolejny
  ok('rejestr sesji dostał zalogowanie', B.sesje.some(s => s.rodzaj === 'logowanie' && s.kod === '12345'));
  ok('puls i sesja idą z podpisem hasłem (serwer nie odrzucił żadnego: ani pulsu, ani wpisu sesji)', !B.pulsyBezHasla && !B.sesjeOdrzucone && B.pulsy.length >= 1, JSON.stringify({ bezHasla: B.pulsyBezHasla || 0, odrzucone: B.sesjeOdrzucone || 0 }));
  await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa'); await p.click('#zapisz-dane');
  await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(1500);
  ok('menu konta: login i ważność dostępu', /Login 12345 · dostęp do 31\.12\.2099/.test(await p.locator('#konto-dostep').textContent()), await p.locator('#konto-dostep').textContent());

  await wyloguj();
  ok('po wylogowaniu login podpowiedziany, sesja zamknięta', (await p.inputValue('#dz-kod')) === '12345' && !(await stanDostepu()).kod);
  ok('rejestr sesji dostał wylogowanie', B.sesje.some(s => s.rodzaj === 'wylogowanie'));

  /* konto bez hasła: telefon wpuszcza i prosi o własne hasło */
  await wpisz('22222', '501502503'); await czekajAplikacje(); await p.waitForSelector('#zh-form', { timeout: 60000 });
  ok('logowanie telefonem proponuje ustawienie własnego hasła', /Ustaw własne hasło/.test(await p.locator('#ark-tyt').innerText()));
  await p.screenshot({ path: wyj + '/3_ustaw_haslo.png' });
  await p.fill('#zh-nowe', 'mojehaslo9'); await p.fill('#zh-pow', 'mojehaslo9'); await p.click('#zh-ok');
  await p.waitForFunction(() => !document.querySelector('#zh-form'), null, { timeout: 60000, polling: 200 });
  ok('własne hasło zapisane na serwerze', B.uzytkownicy['22222'].hash === hash('22222', 'mojehaslo9'));
  await p.waitForSelector('#d-imie', { timeout: 60000 }); await p.waitForTimeout(1200);
  ok('konto 22222 nie widzi danych konta 12345', (await p.inputValue('#d-pesel')) === '' && (await p.inputValue('#d-imie')) === 'Anna Nowa');
  await p.evaluate(() => document.querySelector('#wyloguj').click()); await p.waitForNavigation(); await czekajLogowanie();

  /* powrót na konto 12345: dane są, a okno „Moje dane" się nie otwiera */
  await wpisz('12345', 'nowehaslo1'); await czekajAplikacje(); await p.waitForTimeout(3500);
  ok('dane konta 12345 wróciły po ponownym logowaniu', (await p.locator('#imie-pasek').innerText()) === 'Jan Testowy' && (await p.locator('#arkusz-tlo.otwarty').count()) === 0);
  /* logowanie przy KAŻDYM uruchomieniu: odświeżenie tej samej karty nie pyta, nowa karta (jak ponowne otwarcie przeglądarki) pyta i podpowiada ostatni login */
  await przeladuj(); await czekajAplikacje(); await p.waitForTimeout(1500);
  ok('odświeżenie tej samej karty (F5) nie pyta ponownie o logowanie', (await p.locator('#dz-form').count()) === 0 && (await p.locator('#imie-pasek').innerText()) === 'Jan Testowy');
  const karta2 = await t.ctx.newPage(); await karta2.goto(t.adres + '/index.html'); await karta2.waitForSelector('#dz-form', { state: 'attached', timeout: 120000 }); await karta2.waitForTimeout(800);
  ok('nowa karta (nowe uruchomienie) prosi o logowanie, choć konto jest zapamiętane na urządzeniu', (await karta2.locator('#dz-kod').count()) === 1 && (await karta2.inputValue('#dz-kod')) === '12345' && await karta2.evaluate(() => getComputedStyle(document.querySelector('#aplikacja')).visibility === 'hidden'));
  await karta2.close(); await p.bringToFront();
  const par = await p.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('pmt-web-v1')).sort());
  ok('dane rozdzielone na konta w pamięci urządzenia', par.includes('pmt-web-v1:12345') && !par.includes('pmt-web-v1'), par.join(', '));

  /* zmiana hasła z menu konta */
  await p.evaluate(() => document.querySelector('#zmien-haslo').click()); await p.waitForSelector('#zh-stare');
  await p.fill('#zh-stare', 'zle'); await p.fill('#zh-nowe', 'jeszczeinne1'); await p.fill('#zh-pow', 'jeszczeinne1'); await p.click('#zh-ok'); i = await czekajInfo(/nie pasuje|nadal działa|dalej działa/);
  ok('zmiana ze złym dotychczasowym hasłem odrzucona', /nie pasuje/.test(i) && B.uzytkownicy['12345'].hash === hash('12345', 'nowehaslo1'), i);
  await p.fill('#zh-stare', 'nowehaslo1'); await p.click('#zh-ok');
  await p.waitForFunction(() => !document.querySelector('#zh-form'), null, { timeout: 60000, polling: 200 });
  ok('zmiana hasła z menu konta zapisana', B.uzytkownicy['12345'].hash === hash('12345', 'jeszczeinne1'));
  await wyloguj();

  /* konto wygasłe: wejście, puls „wygasla", blokada z komunikatem */
  await wpisz('33333', 'haslo123');
  await p.waitForFunction(() => /wygasł/.test((document.querySelector('#dz-info') || {}).textContent || ''), null, { timeout: 180000, polling: 300 });
  ok('konto bez ważnego dostępu zablokowane z komunikatem', /wygasł/.test(await info()) && !(await stanDostepu()).kod, await info());
  await p.screenshot({ path: wyj + '/4_wygaslo.png' });

  /* serwer osiągalny, ale odpowiedź zablokowana przez przeglądarkę (CORS) — inny komunikat niż brak internetu */
  B.cors = true; await wpisz('12345', 'zlehaslo'); i = await czekajInfo(/CORS|połączyć/);
  ok('zablokowana odpowiedź (CORS) rozpoznana osobno od braku internetu', /CORS/.test(i), i.slice(0, 100)); B.cors = false;

  /* bez sieci */
  await wpisz('12345', 'jeszczeinne1'); await czekajAplikacje(); await p.waitForTimeout(2500);
  B.martwy = true; await przeladuj(); await czekajAplikacje();
  ok('bez sieci zalogowane konto dalej pracuje', (await p.locator('#imie-pasek').innerText()) === 'Jan Testowy' && (await p.locator('#dz-form').count()) === 0);
  await wyloguj();
  await wpisz('12345', 'jeszczeinne1'); await czekajAplikacje();
  ok('bez sieci znane konto loguje się ze skrótu hasła', (await stanDostepu()).kod === '12345');
  await wyloguj();
  await wpisz('12345', 'zlehaslo'); i = await czekajInfo(/połączyć|serwer|internet/i);
  ok('bez sieci złe hasło nie wpuszcza (komunikat o sieci)', !(await stanDostepu()).kod && /połączyć|internet/i.test(i), i.slice(0, 90));
  await wpisz('44444', 'cokolwiek1'); i = await czekajInfo(/połączyć|serwer|internet/i);
  ok('bez sieci nieznane konto nie wchodzi', !(await stanDostepu()).kod);
  await wpisz('12345', 'jeszczeinne1'); await czekajAplikacje();
  await p.evaluate(() => { const d = JSON.parse(localStorage.getItem('pmt-web-dostep-v1')); d.konta['12345'].kontakt = Date.now() - 50 * 86400000; localStorage.setItem('pmt-web-dostep-v1', JSON.stringify(d)); });
  await przeladuj(); await czekajLogowanie();
  ok('po 45 dniach bez kontaktu z serwerem wymagane logowanie online', /45 dni/.test(await info()) && !(await p.evaluate(() => document.querySelector('#aplikacja').classList.contains('zamknieta') === false)), await info());
  B.martwy = false;
  await wpisz('12345', 'jeszczeinne1'); await czekajAplikacje();
  ok('po powrocie sieci logowanie online odnawia dostęp', (await stanDostepu()).kod === '12345' && (Date.now() - (await stanDostepu()).konta['12345'].kontakt) < 120000);
  ok('brak błędów konsoli poza celowo zerwanym połączeniem', t.bledy.filter(b => !/ERR_INTERNET_DISCONNECTED|Failed to load resource|net::ERR/.test(b)).length === 0, JSON.stringify(t.bledy.filter(b => !/ERR_INTERNET_DISCONNECTED|Failed to load resource|net::ERR/.test(b)).slice(0, 3)));
  await t.zamknij();

  /* podpis obowiązkowy: bez sekret.txt backend odmawia, z sekretem wpuszcza */
  const B2 = new BackendMock({ podpisObowiazkowy: true });
  let t2 = await otworz({ w: 1000, h: 800, zalogowany: false, backend: B2, opcjeSerwera: { sekret: '' } }); let q = t2.p;
  await q.goto(t2.adres + '/index.html'); await q.waitForSelector('#dz-form');
  await q.fill('#dz-kod', '12345'); await q.fill('#dz-haslo', 'haslo123'); await q.keyboard.press('Enter');
  await q.waitForFunction(() => /odmowa/.test((document.querySelector('#dz-info') || {}).textContent || ''), null, { timeout: 60000, polling: 150 });
  ok('przy obowiązkowym podpisie brak sekretu = odmowa', true);
  await t2.zamknij();
  t2 = await otworz({ w: 1000, h: 800, zalogowany: false, backend: B2 }); q = t2.p;
  await q.goto(t2.adres + '/index.html'); await q.waitForSelector('#dz-form');
  await q.fill('#dz-kod', '12345'); await q.fill('#dz-haslo', 'haslo123'); await q.keyboard.press('Enter');
  await q.waitForFunction(() => !document.querySelector('#dz-form'), null, { timeout: 60000, polling: 200 });
  ok('przy obowiązkowym podpisie z sekretem logowanie przechodzi', B2.log.some(l => l.zdarzenie === 'logowanie_www'));
  await t2.zamknij();
  process.exit(kod);
})().catch(e => { console.error('BŁĄD TESTU', e); process.exit(2); });
