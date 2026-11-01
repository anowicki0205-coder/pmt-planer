// Pulpit na komputerze: mozaika (kafle pionowe i poziome, jak we wzorze) ma być w KAŻDYM zwykłym oknie przeglądarki, nie tylko w wysokim monitorze —
// właściciel zobaczył „poziome bloki”, bo okno przeglądarki laptopa (1366×650, 1280×590…) miało mniej niż 700 px wysokości; kafel „Na telefon” z kodem QR znikał poniżej 780 px.
// Poniżej progu (okno węższe niż 1100 px albo niższe niż 520 px) zostaje dotychczasowy układ trzech rzędów.
// NODE_PATH=/opt/node22/lib/node_modules node mozaika_app.js
const { otworz } = require('./wspolne');
const OKNA = [[1920, 1080], [1920, 950], [1536, 864], [1536, 730], [1440, 760], [1366, 768], [1366, 650], [1280, 720], [1280, 590], [1180, 600], [1100, 640], [1100, 520]];
const PONIZEJ = [[1024, 768], [1280, 500], [1099, 700]];
const uklad = () => Object.fromEntries([...document.querySelectorAll('.bento>.kafel')].filter(k => getComputedStyle(k).display !== 'none').map(k => {
  const b = k.getBoundingClientRect(); return [([...k.classList].find(c => /^k-/.test(c)) || '?'), { l: Math.round(b.left), t: Math.round(b.top), w: Math.round(b.width), h: Math.round(b.height), r: Math.round(b.right), d: Math.round(b.bottom) }];
}));
const nachodza = u => { const k = Object.entries(u), z = []; for (let i = 0; i < k.length; i++) for (let j = i + 1; j < k.length; j++) { const a = k[i][1], b = k[j][1]; if (a.l < b.r - 1 && b.l < a.r - 1 && a.t < b.d - 1 && b.t < a.d - 1) z.push(k[i][0] + '×' + k[j][0]); } return z; };
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const t = await otworz({ w: 1440, h: 900, przyklad: true }); const p = t.p;
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#siatka .dz.trasa', { timeout: 120000 });
  for (const [w, h] of OKNA) {
    await p.setViewportSize({ width: w, height: h }); await p.waitForTimeout(900);
    const u = await p.evaluate(uklad), n = Object.keys(u).sort().join(',');
    const pion = k => u[k] && u[k].h > u[k].w * 1.1, poziom = k => u[k] && u[k].w > u[k].h * 1.5;
    ok(`${w}×${h}: mozaika — „Dziś” i „Dokumenty” są pionowe, kwota i „Dzień” poziome`, pion('k-dzis') && pion('k-dok') && poziom('k-bohater') && u['k-dzien'].w > u['k-dzien'].h, Object.entries(u).map(([k, v]) => `${k} ${v.w}×${v.h}`).join(', '));
    ok(`${w}×${h}: jest kafel „Na telefon” z kodem QR (nie znika w niskim oknie)`, !!u['k-qr'] && u['k-qr'].w >= 70 && u['k-qr'].h >= 120, u['k-qr'] ? `${u['k-qr'].w}×${u['k-qr'].h}` : 'brak');
    ok(`${w}×${h}: wszystkich 7 kafli, żaden nie nachodzi na inny ani nie wychodzi poza okno`, n === 'k-bohater,k-dok,k-dzien,k-dzis,k-kal,k-kontrola,k-qr' && !nachodza(u).length && Object.values(u).every(v => v.l >= 0 && v.t >= 0 && v.r <= w && v.d <= h), nachodza(u).join(' ') + ' ' + n);
    const strona = await p.evaluate(() => { const s = document.scrollingElement; return s.scrollHeight > innerHeight + 1 || s.scrollWidth > innerWidth + 1; });
    ok(`${w}×${h}: strona się nie przewija`, !strona);
  }
  for (const [w, h] of PONIZEJ) {
    await p.setViewportSize({ width: w, height: h }); await p.waitForTimeout(900);
    const u = await p.evaluate(uklad);
    ok(`${w}×${h}: poniżej progu mozaiki zostaje dotychczasowy układ trzech rzędów (kwota na całą szerokość u góry, „Dziś” obok, bez pionowego „Dziś”)`, u['k-bohater'] && u['k-dzis'] && u['k-bohater'].t === u['k-dzis'].t && !(u['k-dzis'].h > u['k-dzis'].w * 1.1 && u['k-dzis'].t === u['k-bohater'].t && u['k-kal'] && u['k-kal'].l > u['k-dzis'].l + u['k-dzis'].w), Object.entries(u).map(([k, v]) => `${k} ${v.l},${v.t} ${v.w}×${v.h}`).join(' | '));
    ok(`${w}×${h}: nic nie nachodzi na siebie i strona się nie przewija`, !nachodza(u).length && !(await p.evaluate(() => { const s = document.scrollingElement; return s.scrollHeight > innerHeight + 1 || s.scrollWidth > innerWidth + 1; })), nachodza(u).join(' '));
  }
  await p.setViewportSize({ width: 1366, height: 650 }); await p.waitForTimeout(1500); await p.screenshot({ path: '/tmp/mozaika_1366x650.png' });
  const bledy = t.bledy.filter(b => !/favicon|ERR_|net::|Failed to load/.test(b));
  ok('bez błędów w konsoli', bledy.length === 0, bledy.join(' | ').slice(0, 300));
  await t.zamknij(); console.log(kod ? 'KONIEC kod=1' : 'KONIEC kod=0'); process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
