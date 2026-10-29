// Jedna pełna wersja: ruch i efekty zawsze włączone (także gdy system prosi o „ogranicz animacje”), użytkownik niczego nie wybiera.
// Do testów właściciela zostaje tylko ?diag (nakładka z klatkami/s). NODE_PATH=/opt/node22/lib/node_modules node testy/ruch_app.js
const { otworz } = require('./wspolne');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const t = await otworz({ w: 1440, h: 900, ruch: 'reduce', zalogowany: false, pelnaZorza: true }); const p = t.p;
  const klatki = async () => { const a = await p.evaluate(() => window.__zorzaKlatki || 0); await p.waitForTimeout(3000); const b = await p.evaluate(() => window.__zorzaKlatki || 0); return b - a; };
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#dz-form'); await p.waitForTimeout(1500);
  ok('nie ma żadnego wyboru trybu animacji (logowanie)', (await p.locator('[data-ruch],.ruch-opis,.dz-ruch').count()) === 0 && !(await p.locator('#diag').isVisible()));
  ok('system z „ogranicz animacje” NIE wyłącza ruchu — jedna pełna wersja', (await p.evaluate(() => [...document.documentElement.classList].filter(c => ['lekki', 'spokoj', 'bez-blur'].includes(c)))).length === 0);
  const kl = await klatki(); ok('zorza (WebGL) pływa na żywo', kl >= 1, `${kl} klatek / 3 s (grafika programowa testu jest wolna)`);
  ok('zorza liczona na żywo, bez wypieczonych/CSS-owych zamienników', (await p.locator('#zorza-css,#zorza-pieczona').count()) === 0 && (await p.evaluate(() => getComputedStyle(document.querySelector('#zorza')).display)) !== 'none');
  for (let i = 0; i < 14; i++) await p.mouse.move(300 + i * 40, 200 + (i % 3) * 30);
  const pylek = await p.waitForFunction(() => { const c = document.querySelector('#pylek'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; for (let i = 3; i < d.length; i += 4) if (d[i] > 8) return true; return false; }, null, { timeout: 15000, polling: 100 }).then(() => true).catch(() => false);
  ok('pył gwiezdny rysuje się za kursorem', pylek);
  const b = await p.locator('.dz-oko').boundingBox(); await p.mouse.move(b.x + b.width * .9, b.y + b.height * .5);
  ok('przyciski garną się do kursora (magnes)', (await p.evaluate(() => document.querySelector('.dz-oko').style.translate)) !== '');
  await p.goto(t.adres + '/index.html?ruch=brak&diag'); await p.waitForSelector('#dz-form'); await p.waitForTimeout(2500);
  ok('?ruch= nic nie zmienia (nie ma trybów), ?diag pokazuje klatki/s i grafikę', (await p.evaluate(() => [...document.documentElement.classList].includes('spokoj'))) === false && /kl\.\/s/.test(await p.locator('#diag').textContent()), await p.locator('#diag').textContent());
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#dz-form');
  await p.fill('#dz-kod', '12345'); await p.fill('#dz-haslo', 'haslo123');
  await p.waitForFunction(() => !document.querySelector('#aplikacja').classList.contains('zamknieta') && !document.querySelector('#ladowanie').classList.contains('widoczny'), null, { timeout: 180000, polling: 200 });
  ok('w menu konta nie ma wyboru animacji', (await p.locator('#konto-menu [data-ruch]').count()) === 0);
  ok('brak błędów konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('BŁĄD TESTU', e); process.exit(2); });
