// Szybki podgląd: uruchamia aplikację, czeka na silnik, robi zrzut. NODE_PATH=/opt/node22/lib/node_modules node podglad.js [wyjscie.png] [szer] [wys] [dsf]
const { otworz } = require('./wspolne');
(async () => {
  const [wyj = '/tmp/podglad.png', w = 1440, h = 900, dsf = 1] = process.argv.slice(2);
  const t = await otworz({ w: +w, h: +h, dsf: +dsf });
  await t.p.goto(t.adres + '/index.html');
  await t.p.waitForFunction(() => !document.querySelector('#ladowanie.widoczny') && !document.querySelector('#aplikacja.czeka'), null, { timeout: 120000 }).catch(e => console.log('LIMIT CZASU ładowania'));
  await t.p.waitForTimeout(5000);
  await t.p.screenshot({ path: wyj });
  console.log('zrzut', wyj, 'błędy:', JSON.stringify(t.bledy.slice(0, 8)));
  await t.zamknij();
})();
