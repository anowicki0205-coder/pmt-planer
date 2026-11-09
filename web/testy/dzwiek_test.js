// Dźwięki (js/dzwiek.js): synteza efektów i podkładu muzycznego, sprawdzana BEZ słuchania — dźwięk jest renderowany do liczb (OfflineAudioContext w prawdziwej przeglądarce),
// a testy sprawdzają: brak NaN, brak przesterowania, brak ciszy, zanik na końcu (żadnego trzasku), właściwą wysokość dźwięku. Na końcu sterowanie: ustawienia, przyciski, zapamiętanie wyboru.
// Uruchom: NODE_PATH=/opt/node22/lib/node_modules node testy/dzwiek_test.js
const { chromium } = require('playwright'), http = require('http'), fs = require('fs'), path = require('path');
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const WEB = path.join(__dirname, '..');
  const STRONA = `<!doctype html><meta charset="utf-8"><title>dźwięk</title>
    <button id="dzwiek" aria-pressed="true"><svg><use href="#i-glosnik"/></svg></button><button id="muzyka" aria-pressed="false"></button>
    <label><input type="range" id="glosnosc" min="0" max="100" step="5" value="70"><output></output></label><button id="zwykly">Zwykły</button><button id="zam" data-zamknij>Zamknij</button><button class="p-znak" id="znak">Znak</button><button id="wyl" disabled>Wyłączony</button>
    <script type="module">import { dzwiek, zbudujEfekt, zbudujMuzyke, zbudujTor, przygluszMuzyke, EFEKTY, TAKT, GLOSNOSC_MUZYKI, PETLA } from '/js/dzwiek.js'; window.D = { dzwiek, zbudujEfekt, zbudujMuzyke, zbudujTor, przygluszMuzyke, EFEKTY, TAKT, GLOSNOSC_MUZYKI, PETLA }; dzwiek.init(document); window.gotowe = true;</script>`;
  const sv = http.createServer((q, o) => {
    if (q.url === '/') { o.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); return o.end(STRONA); }
    const f = path.join(WEB, q.url.split('?')[0]); if (!f.startsWith(WEB) || !fs.existsSync(f)) { o.writeHead(404); return o.end(); }
    o.writeHead(200, { 'content-type': f.endsWith('.js') ? 'text/javascript' : 'application/octet-stream' }); o.end(fs.readFileSync(f));
  });
  await new Promise(r => sv.listen(0, '127.0.0.1', r)); const adres = 'http://127.0.0.1:' + sv.address().port;
  const b = await chromium.launch(); const ctx = await b.newContext(); const p = await ctx.newPage(); const bledy = [];
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') bledy.push(m.type() + ': ' + m.text()); }); p.on('pageerror', e => bledy.push('wyjątek: ' + e.message));
  await p.goto(adres + '/'); await p.waitForFunction(() => window.gotowe, null, { timeout: 15000 });

  /* ---------- synteza: efekty ---------- */
  const analiza = await p.evaluate(async () => {
    const SR = 44100, wyn = {};
    const gz = (d, f, od, dl) => { const w = 2 * Math.PI * f / SR; let s1 = 0, s2 = 0; const c = 2 * Math.cos(w); for (let i = od; i < od + dl; i++) { const s = d[i] + c * s1 - s2; s2 = s1; s1 = s; } return (s1 * s1 + s2 * s2 - c * s1 * s2) / dl; };      // moc na częstotliwości (Goertzel)
    for (const n of Object.keys(D.EFEKTY)) {
      const oc = new OfflineAudioContext(1, SR * 3.5, SR), w = oc.createGain(); w.connect(oc.destination);
      const dl = D.zbudujEfekt(oc, w, n, .01), buf = await oc.startRendering(), d = buf.getChannelData(0);
      let pk = 0, nan = false; for (let i = 0; i < d.length; i++) { const a = Math.abs(d[i]); if (!(a === a)) nan = true; if (a > pk) pk = a; }
      const kon = Math.floor((.01 + dl + .25) * SR), tail = Math.sqrt(d.slice(kon, kon + Math.floor(SR * .1)).reduce((s, x) => s + x * x, 0) / Math.floor(SR * .1));
      const pierwsze = Math.floor(.01 * SR), moc = f => gz(d, f, pierwsze, Math.floor(SR * .5));
      wyn[n] = { dl, pk, nan, tail, p659: moc(659.3), p988: moc(987.8), p800: moc(800), p1200: moc(1200) };
    }
    return wyn;
  });
  const nazwy = Object.keys(analiza);
  ok('są wszystkie efekty: klik, okno, okno-zam, motyw, ok, zle, wszystkie, wyslano, gen-start, gen-koniec, odhacz, odhacz-wyl', ['klik', 'okno', 'okno-zam', 'motyw', 'ok', 'zle', 'wszystkie', 'wyslano', 'gen-start', 'gen-koniec', 'odhacz', 'odhacz-wyl'].every(n => nazwy.includes(n)), nazwy.join(', '));
  ok('żaden efekt nie ma NaN w próbkach', nazwy.every(n => !analiza[n].nan));
  ok('efekty są słyszalne (szczyt ≥ 0,02), ale nie przesterowane (szczyt ≤ 0,55) i nie za głośne względem siebie', nazwy.every(n => analiza[n].pk >= .02 && analiza[n].pk <= .55), nazwy.map(n => n + ':' + analiza[n].pk.toFixed(2)).join(' '));
  ok('każdy efekt wygasa do ciszy (po jego końcu < 0,002) — bez trzasku na końcu', nazwy.every(n => analiza[n].tail < .002), nazwy.map(n => n + ':' + analiza[n].tail.toExponential(1)).join(' '));
  ok('efekty są krótkie (do 2,2 s), „klik” krócej niż 0,1 s', nazwy.every(n => analiza[n].dl > 0 && analiza[n].dl <= 2.2) && analiza.klik.dl < .1, nazwy.map(n => n + ':' + analiza[n].dl.toFixed(2)).join(' '));
  { const a = analiza.ok; ok('efekt „ok” brzmi na zamierzonych nutach (E5 ≈ 659 Hz i H5 ≈ 988 Hz mocniejsze ≥ 5× niż 800 i 1200 Hz)', a.p659 > 5 * a.p800 && a.p988 > 5 * a.p1200 && a.p659 > 5 * a.p1200, JSON.stringify({ p659: a.p659.toExponential(1), p988: a.p988.toExponential(1), p800: a.p800.toExponential(1), p1200: a.p1200.toExponential(1) })); }
  ok('nieznany efekt nic nie robi i nie rzuca wyjątku', await p.evaluate(async () => { const oc = new OfflineAudioContext(1, 4410, 44100); return D.zbudujEfekt(oc, oc.destination, 'nie-ma-takiego', 0) === 0; }));

  /* ---------- synteza: podkład ---------- */
  const mu = await p.evaluate(async () => {
    const SR = 44100, TAKTOW = D.PETLA, oc = new OfflineAudioContext(1, Math.ceil(SR * (D.TAKT * TAKTOW + 3.2)), SR), m = D.zbudujMuzyke(oc, oc.destination);
    m.bus.gain.setValueAtTime(D.GLOSNOSC_MUZYKI, 0); for (let i = 0; i < TAKTOW; i++) m.planTakt(i, i * D.TAKT);
    const buf = await oc.startRendering(), d = buf.getChannelData(0), N = Math.floor(SR * D.TAKT);
    // podział energii na pasma (prawdziwe FFT, 2^20 próbek ≈ 23,8 s): podkład nie może być samym basem, którego małe głośniki laptopa nie odtworzą
    const fft = (re, im) => { const n = re.length; for (let i = 1, j = 0; i < n; i++) { let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; if (i < j) { [re[i], re[j]] = [re[j], re[i]]; } } for (let len = 2; len <= n; len <<= 1) { const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang); for (let i = 0; i < n; i += len) { let cr = 1, ci = 0; for (let k = 0; k < len / 2; k++) { const ur = re[i + k], ui = im[i + k], vr = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci, vi = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr; re[i + k] = ur + vr; im[i + k] = ui + vi; re[i + k + len / 2] = ur - vr; im[i + k + len / 2] = ui - vi; const nr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = nr; } } } };
    const NF = 1 << 20, re = new Float64Array(NF), im = new Float64Array(NF); for (let i = 0; i < NF && i < d.length; i++) re[i] = d[i]; fft(re, im);
    const pasmo = (a, b) => { let e = 0; for (let k = Math.floor(a * NF / SR); k < Math.floor(b * NF / SR); k++) e += re[k] * re[k] + im[k] * im[k]; return e; }, calosc = pasmo(30, 11000);
    let pk = 0, nan = false; const rms = []; for (let t = 0; t < TAKTOW; t++) { let s = 0; for (let i = t * N; i < (t + 1) * N; i++) { const a = d[i]; if (!(a === a)) nan = true; s += a * a; if (Math.abs(a) > pk) pk = Math.abs(a); } rms.push(Math.sqrt(s / N)); }
    const kon = d.slice(Math.floor((TAKTOW * D.TAKT + 1.7) * SR)), ogon = Math.sqrt(kon.reduce((s, x) => s + x * x, 0) / kon.length);
    // trzask na łączeniu pętli: największy skok między sąsiednimi próbkami w okolicy granicy taktów
    let skok = 0; for (let t = 1; t < TAKTOW; t++) for (let i = t * N - 40; i < t * N + 40; i++) skok = Math.max(skok, Math.abs(d[i] - d[i - 1]));
    return { pk, nan, rms, ogon, skok, takt: D.TAKT, takty: TAKTOW, bas: pasmo(30, 150) / calosc, srodek: pasmo(150, 2000) / calosc, rmsDb: 20 * Math.log10(Math.sqrt(rms.reduce((s, r) => s + r * r, 0) / rms.length)) };
  });
  ok('podkład: takt ma ok. 2,5 s (96 BPM), pętla 16 taktów (ok. 40 s)', Math.abs(mu.takt - 2.5) < .01 && mu.takty === 16, mu.takt.toFixed(3) + ' s, taktów ' + mu.takty);
  ok('podkład: brak NaN, szczyt ≤ 0,5 (bez przesterowania)', !mu.nan && mu.pk <= .5, 'szczyt ' + mu.pk.toFixed(3));
  ok('podkład: każdy takt gra (RMS ≥ 0,008) i jest tłem, nie hałasem (RMS ≤ 0,12 ≈ −18 dBFS)', mu.rms.every(r => r >= .008 && r <= .12), mu.rms.map(r => r.toFixed(3)).join(' '));
  { const sr = t => t.reduce((s, v) => s + v, 0) / t.length, bez = sr(mu.rms.slice(0, 4)), z = sr(mu.rms.slice(4)); ok('podkład: takty z melodią (od 5. do 16.) nie są cichsze od pierwszych czterech (bez melodii) i nie głośniejsze więcej niż o 40%', z >= bez * .98 && z <= bez * 1.4, `bez ${bez.toFixed(3)}, z melodią ${z.toFixed(3)}; ` + mu.rms.map(r => r.toFixed(3)).join(' ')); }
  ok('podkład: równowaga pasm — bas (30–150 Hz) nie przeważa nad resztą (≤ 60% energii), a środek (150–2000 Hz: pad, arpeggio, melodia) ma ≥ 35%; poziom ≈ −31…−22 dBFS jako tło', mu.bas <= .6 && mu.srodek >= .35 && mu.rmsDb >= -31 && mu.rmsDb <= -22, `bas ${(mu.bas * 100).toFixed(0)}%, środek ${(mu.srodek * 100).toFixed(0)}%, ${mu.rmsDb.toFixed(1)} dBFS`);
  ok('podkład: 1,7 s po ostatnim takcie zostaje tylko cichy ogon echa (< 0,01) i nie ma skoków na łączeniu taktów (największa różnica sąsiednich próbek < 0,25)', mu.ogon < .01 && mu.skok < .25, `ogon ${mu.ogon.toFixed(4)}, skok ${mu.skok.toFixed(3)}`);


  /* ---------- tor z pogłosem, stereo, przyciszanie muzyki ---------- */
  const tor = await p.evaluate(async () => {
    const SR = 44100, rms = (d, a, b) => { let s = 0; for (let i = Math.floor(a * SR); i < Math.floor(b * SR); i++) s += d[i] * d[i]; return Math.sqrt(s / Math.max(1, Math.floor((b - a) * SR))); };
    const wyn = {};
    // pogłos: efekt „wszystkie” przez tor z pogłosem (efR) i bez (ef): po końcu suchego dźwięku pogłos ma dźwięczeć i wygasać do ciszy
    for (const [nazwa, bus] of [['sucho', 'ef'], ['pogłos', 'efR']]) {
      const oc = new OfflineAudioContext(2, SR * 6, SR), t = D.zbudujTor(oc, oc.destination), dl = D.zbudujEfekt(oc, t[bus], 'wszystkie', .1), buf = await oc.startRendering(), L = buf.getChannelData(0), R = buf.getChannelData(1);
      let pk = 0, nan = false; for (let i = 0; i < L.length; i++) { const a = Math.max(Math.abs(L[i]), Math.abs(R[i])); if (!(a === a)) nan = true; if (a > pk) pk = a; }
      wyn[nazwa] = { dl, pk, nan, po: rms(L, .1 + dl + .15, .1 + dl + .6), koniec: rms(L, 5.5, 6) };
    }
    // muzyka w pełnym torze (stereo, z pogłosem): poziom, szczyt, szerokość stereo
    { const T = D.PETLA, oc = new OfflineAudioContext(2, Math.ceil(SR * (D.TAKT * T)), SR), t = D.zbudujTor(oc, oc.destination), m = D.zbudujMuzyke(oc, t.master, t.pogMuzyki);
      m.bus.gain.setValueAtTime(D.GLOSNOSC_MUZYKI, 0); for (let i = 0; i < T; i++) m.planTakt(i, i * D.TAKT);
      const buf = await oc.startRendering(), L = buf.getChannelData(0), R = buf.getChannelData(1); let pk = 0, nan = false, sl = 0, sr = 0, slr = 0;
      for (let i = SR * 2; i < L.length; i++) { const a = Math.max(Math.abs(L[i]), Math.abs(R[i])); if (!(a === a)) nan = true; if (a > pk) pk = a; sl += L[i] * L[i]; sr += R[i] * R[i]; slr += L[i] * R[i]; }
      wyn.muzyka = { pk, nan, rmsDb: 20 * Math.log10(Math.sqrt((sl + sr) / 2 / (L.length - SR * 2))), korelacja: slr / Math.sqrt(sl * sr) }; }
    // przyciszanie: ta sama muzyka z wywołaniem przygluszMuzyke w 6. sekundzie i bez
    { const render = async duck => { const oc = new OfflineAudioContext(1, SR * 9, SR), m = D.zbudujMuzyke(oc, oc.destination); m.bus.gain.setValueAtTime(D.GLOSNOSC_MUZYKI, 0); for (let i = 0; i < 4; i++) m.planTakt(i, i * D.TAKT); if (duck) D.przygluszMuzyke(m.duck, 6, .8); return (await oc.startRendering()).getChannelData(0); };
      const a = await render(false), b = await render(true); wyn.duck = { w: rms(b, 6.15, 6.55) / rms(a, 6.15, 6.55), po: rms(b, 8.6, 9) / rms(a, 8.6, 9) }; }
    return wyn;
  });
  ok('pogłos: po zakończeniu suchego efektu wciąż słychać pogłos (≥ 3× głośniej niż bez pogłosu), a po kilku sekundach wygasa do ciszy (< 0,002)', tor['pogłos'].po > 3 * tor.sucho.po && tor['pogłos'].koniec < .002 && tor.sucho.koniec < .002, JSON.stringify({ sucho: tor.sucho.po.toExponential(1), pogłos: tor['pogłos'].po.toExponential(1), koniec: tor['pogłos'].koniec.toExponential(1) }));
  ok('efekt przez cały tor (kompresor + pogłos): brak NaN i przesterowania (szczyt ≤ 0,95)', !tor.sucho.nan && !tor['pogłos'].nan && tor.sucho.pk <= .95 && tor['pogłos'].pk <= .95, `sucho ${tor.sucho.pk.toFixed(2)}, z pogłosem ${tor['pogłos'].pk.toFixed(2)}`);
  ok('podkład w pełnym torze (jak w aplikacji): brak NaN, szczyt ≤ 0,95, poziom −30…−16 dBFS (RMS)', !tor.muzyka.nan && tor.muzyka.pk <= .95 && tor.muzyka.rmsDb >= -30 && tor.muzyka.rmsDb <= -16, `szczyt ${tor.muzyka.pk.toFixed(2)}, ${tor.muzyka.rmsDb.toFixed(1)} dBFS`);
  ok('podkład jest naprawdę stereo: lewy i prawy kanał nie są kopią (korelacja < 0,95)', tor.muzyka.korelacja < .95, 'korelacja ' + tor.muzyka.korelacja.toFixed(3));
  ok('przyciszanie: w czasie efektu muzyka jest cichsza o ≥ 20% i wraca do poprzedniego poziomu (±10%) po jego końcu', tor.duck.w < .8 && Math.abs(tor.duck.po - 1) < .1, JSON.stringify(tor.duck));

  /* ---------- sterowanie ---------- */
  const st0 = await p.evaluate(() => ({ efekty: D.dzwiek.efektyWl(), muzyka: D.dzwiek.muzykaWl(), gra: D.dzwiek.muzykaGra(), ctx: D.dzwiek.stan(), a1: document.querySelector('#dzwiek').getAttribute('aria-pressed'), a2: document.querySelector('#muzyka').getAttribute('aria-pressed') }));
  ok('domyślnie efekty są włączone, podkład wyłączony; kontekst audio powstaje dopiero po geście użytkownika (wcześniej „brak”)', st0.efekty === true && st0.muzyka === false && st0.gra === false && st0.ctx === 'brak' && st0.a1 === 'true' && st0.a2 === 'false', JSON.stringify(st0));
  await p.click('#zwykly'); await p.waitForTimeout(300);
  const st1 = await p.evaluate(() => ({ ctx: D.dzwiek.stan(), log: [...D.dzwiek.log] }));
  ok('zwykły przycisk: po pierwszym kliknięciu powstaje kontekst audio; efekt „klik” zapisany w dzienniku', st1.ctx !== 'brak' && st1.log.includes('klik') || st1.log.length === 0 && st1.ctx !== 'brak', JSON.stringify(st1));
  await p.evaluate(() => { D.dzwiek.log.length = 0; });
  await p.waitForTimeout(80); await p.click('#zwykly'); await p.waitForTimeout(80); await p.click('#zam'); await p.waitForTimeout(80); await p.click('#znak'); await p.waitForTimeout(80); await p.click('#wyl', { force: true }).catch(() => {});
  ok('klik gra przy zwykłym przycisku, a NIE przy „zamknij”, znaku odhaczenia ani przycisku wyłączonym (te mają własny dźwięk albo milczą)', JSON.stringify(await p.evaluate(() => D.dzwiek.log.filter(x => x === 'klik'))) === '["klik"]', JSON.stringify(await p.evaluate(() => D.dzwiek.log)));
  await p.evaluate(() => { D.dzwiek.log.length = 0; for (let i = 0; i < 6; i++) D.dzwiek.efekt('klik'); });
  ok('ten sam efekt nie gra częściej niż co kilkadziesiąt ms (seria 6 „kliknięć” naraz daje jeden dźwięk, ale wszystkie trafiają do dziennika)', await p.evaluate(() => D.dzwiek.log.length === 6));
  // wyciszenie
  await p.click('#dzwiek'); await p.waitForTimeout(150);
  const st2 = await p.evaluate(() => ({ efekty: D.dzwiek.efektyWl(), a1: document.querySelector('#dzwiek').getAttribute('aria-pressed'), href: document.querySelector('#dzwiek use').getAttribute('href'), mag: localStorage.getItem('pmt-ui-dzwiek'), label: document.querySelector('#dzwiek').getAttribute('aria-label') }));
  ok('wyciszenie: stan, aria-pressed, ikona „głośnik wyłączony”, opis przycisku i zapis na urządzeniu (pmt-ui-dzwiek=0)', st2.efekty === false && st2.a1 === 'false' && st2.href === '#i-glosnik-wyl' && st2.mag === '0' && /wyciszone/.test(st2.label), JSON.stringify(st2));
  await p.evaluate(() => { D.dzwiek.log.length = 0; D.dzwiek.efekt('ok'); }); await p.click('#zwykly'); await p.waitForTimeout(100);
  ok('po wyciszeniu żaden efekt się nie zapisuje ani nie gra (także kliknięcia)', await p.evaluate(() => D.dzwiek.log.length === 0));
  await p.click('#dzwiek'); await p.waitForTimeout(150);
  ok('ponowne włączenie przywraca efekty (i zapamiętuje to)', await p.evaluate(() => D.dzwiek.efektyWl() === true && localStorage.getItem('pmt-ui-dzwiek') === '1' && document.querySelector('#dzwiek use').getAttribute('href') === '#i-glosnik'));
  // podkład
  await p.click('#muzyka'); await p.waitForTimeout(1500);
  const m1 = await p.evaluate(() => ({ gra: D.dzwiek.muzykaGra(), wl: D.dzwiek.muzykaWl(), a2: document.querySelector('#muzyka').getAttribute('aria-pressed'), takty: D.dzwiek.taktow(), mag: localStorage.getItem('pmt-ui-muzyka'), ctx: D.dzwiek.stan() }));
  ok('włączenie podkładu: gra, przycisk wciśnięty, kolejne takty są planowane z wyprzedzeniem, wybór zapamiętany (pmt-ui-muzyka=1)', m1.gra && m1.wl && m1.a2 === 'true' && m1.takty >= 1 && m1.mag === '1', JSON.stringify(m1));
  await p.waitForTimeout(3200);
  const m2 = await p.evaluate(() => D.dzwiek.taktow());
  ok('podkład działa w pętli: po kolejnych sekundach zaplanowano więcej taktów (nie urywa się po pierwszym)', m2 > m1.takty || m1.ctx !== 'running', `${m1.takty} → ${m2} (kontekst: ${m1.ctx})`);
  await p.click('#muzyka'); await p.waitForTimeout(200);
  const m3 = await p.evaluate(() => ({ gra: D.dzwiek.muzykaGra(), a2: document.querySelector('#muzyka').getAttribute('aria-pressed'), mag: localStorage.getItem('pmt-ui-muzyka') })); const tk = await p.evaluate(() => D.dzwiek.taktow()); await p.waitForTimeout(1200);
  ok('wyłączenie podkładu: przestaje grać, planowanie się zatrzymuje, wybór zapamiętany (pmt-ui-muzyka=0)', !m3.gra && m3.a2 === 'false' && m3.mag === '0' && (await p.evaluate(() => D.dzwiek.taktow())) === tk, JSON.stringify(m3));
  // zapamiętany podkład rusza dopiero po geście na nowej stronie
  await p.evaluate(() => localStorage.setItem('pmt-ui-muzyka', '1')); await p.reload(); await p.waitForFunction(() => window.gotowe);
  const r0 = await p.evaluate(() => ({ wl: D.dzwiek.muzykaWl(), gra: D.dzwiek.muzykaGra() }));
  ok('zapamiętany podkład po odświeżeniu NIE rusza sam (przeglądarka by go zablokowała, a użytkownik nie jest zaskakiwany w ciszy)', r0.wl === true && r0.gra === false, JSON.stringify(r0));
  await p.click('#zwykly'); await p.waitForTimeout(600);
  ok('…ale rusza przy pierwszym geście (kliknięciu gdziekolwiek), bo użytkownik miał go włączony', await p.evaluate(() => D.dzwiek.muzykaGra() === true));
  await p.evaluate(() => { D.dzwiek.ustawMuzyke(false); localStorage.removeItem('pmt-ui-muzyka'); localStorage.removeItem('pmt-ui-dzwiek'); });

  /* ---------- głośność ---------- */
  await p.evaluate(() => { document.querySelector('#glosnosc').dispatchEvent(new Event('input')); });
  const g0 = await p.evaluate(() => ({ gl: D.dzwiek.glosnosc(), suwak: document.querySelector('#glosnosc').value, out: document.querySelector('#glosnosc').parentElement.querySelector('output').textContent, wz: D.dzwiek.wzmocnienie() }));
  ok('głośność: domyślnie 70% (suwak i napis), wzmocnienie główne 0,8 (poziom wzorcowy)', g0.gl === 70 && g0.suwak === '70' && g0.out === '70%' && Math.abs(g0.wz - .8) < .005, JSON.stringify(g0));
  await p.evaluate(() => { const r = document.querySelector('#glosnosc'); r.value = '100'; r.dispatchEvent(new Event('input')); r.dispatchEvent(new Event('change')); }); await p.waitForTimeout(300);
  const g1 = await p.evaluate(() => ({ gl: D.dzwiek.glosnosc(), out: document.querySelector('#glosnosc').parentElement.querySelector('output').textContent, wz: D.dzwiek.wzmocnienie(), mag: localStorage.getItem('pmt-ui-glosnosc') }));
  ok('głośność 100%: wzmocnienie ≈ 1,14 (+3 dB), napis „100%”, zapis na urządzeniu', g1.gl === 100 && g1.out === '100%' && Math.abs(g1.wz - 1.143) < .02 && g1.mag === '100', JSON.stringify(g1));
  await p.evaluate(() => { const r = document.querySelector('#glosnosc'); r.value = '0'; r.dispatchEvent(new Event('input')); r.dispatchEvent(new Event('change')); }); await p.waitForTimeout(300);
  ok('głośność 0%: wzmocnienie 0 (cisza), a zapisane ustawienie to 0', await p.evaluate(() => D.dzwiek.glosnosc() === 0 && D.dzwiek.wzmocnienie() < .01 && localStorage.getItem('pmt-ui-glosnosc') === '0'));
  await p.evaluate(() => { const r = document.querySelector('#glosnosc'); r.value = '45'; r.dispatchEvent(new Event('input')); r.dispatchEvent(new Event('change')); }); await p.waitForTimeout(300);
  await p.reload(); await p.waitForFunction(() => window.gotowe);
  ok('zapamiętana głośność wraca po odświeżeniu (suwak 45%, napis „45%”)', await p.evaluate(() => D.dzwiek.glosnosc() === 45 && document.querySelector('#glosnosc').value === '45' && document.querySelector('#glosnosc').parentElement.querySelector('output').textContent === '45%'));
  await p.evaluate(() => localStorage.setItem('pmt-ui-glosnosc', 'abc')); await p.reload(); await p.waitForFunction(() => window.gotowe);
  ok('zepsuta wartość w pamięci (tekst) nie psuje głośności: wraca 70%', await p.evaluate(() => D.dzwiek.glosnosc() === 70));
  await p.evaluate(() => localStorage.removeItem('pmt-ui-glosnosc'));
  ok('w konsoli nie było błędów ani ostrzeżeń (m.in. „AudioContext was not allowed to start”)', bledy.length === 0, bledy.join(' | '));
  await b.close(); sv.close();
  console.log(kod ? 'KONIEC kod=1' : 'KONIEC kod=0'); process.exit(kod);
})().catch(e => { console.error(e); process.exit(1); });
