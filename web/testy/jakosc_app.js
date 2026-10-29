// Jedna, stała jakość tła: wyjście w natywnej rozdzielczości ekranu i brak jakiegokolwiek automatycznego obniżania (nawet gdy klatek jest mało).
// NODE_PATH=/opt/node22/lib/node_modules node jakosc_app.js
const { otworz } = require('./wspolne');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const scenariusze = [{ w: 1440, h: 900, dsf: 2, nazwa: '1440×900 przy skalowaniu 200%' }, { w: 2560, h: 1440, dsf: 1, nazwa: '2560×1440 przy skalowaniu 100%' }];
  for (const s of scenariusze) {
    const t = await otworz({ w: s.w, h: s.h, dsf: s.dsf, pelnaZorza: true }); const p = t.p;
    await p.goto(t.adres + '/index.html');
    await p.waitForFunction(() => window.__zorzaWyjscie && (window.__zorzaKlatki || 0) >= 1, null, { timeout: 120000, polling: 250 });
    const W = s.w + 48, H = s.h + 48, sk = Math.min(Math.min(2, s.dsf), Math.sqrt(8.4e6 / (W * H))), cel = `${Math.round(W * sk)}×${Math.round(H * sk)} px`;
    const a = await p.evaluate(() => ({ wyj: window.__zorzaWyjscie, cw: document.querySelector('#zorza').width, poziom: window.__zorzaPoziom, kl: window.__zorzaKlatki }));
    ok(`${s.nazwa}: tło liczone w natywnej rozdzielczości (${cel})`, a.wyj === cel && a.cw === Math.round(W * sk), `${a.wyj}, płótno ${a.cw}`);
    await p.waitForTimeout(16000);          // na grafice programowej to kilka klatek na sekundę — dawniej wystarczało, by tło „schodziło” na niższy poziom
    const b = await p.evaluate(() => ({ wyj: window.__zorzaWyjscie, cw: document.querySelector('#zorza').width, poziom: window.__zorzaPoziom, kl: window.__zorzaKlatki }));
    ok(`${s.nazwa}: po 16 s przy małej liczbie klatek jakość się NIE zmienia`, b.wyj === a.wyj && b.cw === a.cw && b.poziom === undefined, `${a.wyj} → ${b.wyj}, klatek ${a.kl} → ${b.kl}`);
    ok(`${s.nazwa}: tło dalej się odświeża`, b.kl > a.kl);
    ok(`${s.nazwa}: bez błędów w konsoli`, t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
    await t.zamknij();
  }
  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
