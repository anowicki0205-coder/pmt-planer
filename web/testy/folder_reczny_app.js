// Podpis ODRĘCZNY w asystencie (js/podpis.js, tryb z folderem): wybór sposobu podpisu (gov.pl albo wydruk i skan) zapamiętany na urządzeniu; ścieżka odręczna — wydruk, podpis długopisem, skan zapisany
// w folderze „delegacje” — ma wyglądać i działać tak samo jak ścieżka gov.pl: jeden duży przycisk, strefa na skany i postęp na żywo, a skany z folderu aplikacja SAMA wczytuje i sprawdza (podpis odręczny
// w miejscu „podpis pracownika”). Okno wyboru folderu zastępuje prywatna pamięć przeglądarki (OPFS), skany to sztuczne skany z dane/skanuj_pliki.py.
// NODE_PATH=/opt/node22/lib/node_modules node folder_reczny_app.js
const { wpiszAdres, otworz, generuj } = require('./wspolne'); const fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
(async () => {
  const PY = process.env.PYTHON_PODPISY || '/tmp/phvenv/bin/python', DANE = path.join(__dirname, 'dane');
  const t = await otworz({ w: 1440, h: 900, folder: true, pocztaDomyslna: null }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'reczny-'));
  t.backend.paczka = { haslo: 'Admin-Haslo-Paczki#2026', wazne_do: '2099-12-31', adres: 'odbiorca@example.com' };
  const norm = x => x.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l');
  const stany = () => p.evaluate(() => [...document.querySelectorAll('.dok-k')].map(k => (k.className.match(/st-(\w+)/) || [])[1]));
  const czekajStany = async (oczekiwane, ms = 60000) => { await p.waitForFunction(o => { const s = [...document.querySelectorAll('.dok-k')].map(k => (k.className.match(/st-(\w+)/) || [])[1]); return !s.includes('trwa') && JSON.stringify(s) === JSON.stringify(o); }, oczekiwane, { timeout: ms, polling: 250 }).catch(() => {}); return stany(); };
  const tekst = s => p.locator(s).innerText();
  const chipy = () => p.evaluate(() => [...document.querySelectorAll('#asystent .as-kroki li')].map(e => e.className + ':' + e.textContent.trim()));
  const zapiszDoFolderu = (pod, nazwa, bajty) => p.evaluate(async ([pod, nazwa, b64]) => { const k = await navigator.storage.getDirectory(), f = await (await (await k.getDirectoryHandle('pmt-folder-testowy')).getDirectoryHandle('delegacje')).getDirectoryHandle(pod), w = await (await f.getFileHandle(nazwa, { create: true })).createWritable(); await w.write(Uint8Array.from(atob(b64), c => c.charCodeAt(0))); await w.close(); }, [pod, nazwa, Buffer.from(bajty).toString('base64')]);
  const wFolderze = () => p.evaluate(async () => { const k = await navigator.storage.getDirectory(), f = await (await k.getDirectoryHandle('pmt-folder-testowy')).getDirectoryHandle('delegacje'); const wyn = {}; for await (const [n, u] of f.entries()) { if (u.kind !== 'directory') continue; wyn[n] = []; for await (const [m, v] of u.entries()) wyn[n].push(m); } return wyn; });
  const czytaj = (pod, nazwa) => p.evaluate(async ([pod, nazwa]) => { const k = await navigator.storage.getDirectory(), f = await (await (await k.getDirectoryHandle('pmt-folder-testowy')).getDirectoryHandle('delegacje')).getDirectoryHandle(pod), pl = await (await f.getFileHandle(nazwa)).getFile(), b = new Uint8Array(await pl.arrayBuffer()); let s = ''; for (let i = 0; i < b.length; i += 8192) s += String.fromCharCode(...b.subarray(i, i + 8192)); return btoa(s); }, [pod, nazwa]);
  const otworzOkno = async () => { await p.click('#podpisz'); await p.waitForSelector('#asystent', { timeout: 20000 }); await p.waitForTimeout(900); };
  const zamknijOkno = async () => { await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); await p.waitForTimeout(400); };

  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await wpiszAdres(p, 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await generuj(p); await p.waitForTimeout(3500);
  await otworzOkno();
  await p.click('#asystent [data-akcja="folder-wskaz"]'); await p.waitForSelector('#asystent .as-wybor', { timeout: 60000 }); await p.waitForTimeout(1500);

  /* ---------- wybór sposobu podpisu ---------- */
  ok('po wskazaniu folderu asystent pyta JEDNYM ekranem, jak podpisać: karty „Elektronicznie — gov.pl” i „Odręcznie — wydruk i skan” (bez kont w drugiej)', /Jak chcesz podpisać dokumenty/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent .as-wybor').count()) === 2 && /Nie potrzeba żadnych kont/.test(await tekst('#asystent .as-wybor >> nth=1')), (await tekst('#asystent')).replace(/\n/g, ' | ').slice(0, 300));
  await p.click('#asystent [data-sposob="reczny"]');

  /* ---------- ścieżka odręczna wygląda i działa jak ścieżka gov.pl ---------- */
  ok('wybrano „Odręcznie”: tytuł „Podpisz odręcznie”, trzy kroki (wydruk, podpis długopisem w miejscu „podpis pracownika”, skan do folderu), rozliczenie bez podpisu', /Podpisz odręcznie/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent .as-lista li').count()) === 3 && /podpis pracownika/.test(await tekst('#asystent')) && /rozliczenia wydatków nie podpisujesz/.test(await tekst('#asystent')) && /zapisz skany w folderze/.test(await tekst('#asystent')), (await tekst('#asystent')).replace(/\n/g, ' | ').slice(0, 420));
  ok('jest JEDEN duży przycisk „Wydrukuj dokumenty” (plus odnośnik „pobierz PDF do wydruku”), strefa na skany i pasek postępu „Czekam na skany podpisanych poleceń · 0 z 6”; bez przycisków gov.pl', (await p.locator('#asystent .as-akcja .przycisk').count()) === 1 && /Wydrukuj dokumenty/.test(await tekst('#asystent .as-akcja .przycisk')) && (await p.locator('#asystent [data-akcja="pdf-wydruk"]').count()) === 1 && (await p.locator('#asystent .as-strefa').count()) === 1 && /Czekam na skany podpisanych poleceń · 0 z 6/.test(await tekst('#asystent .as-status')) && (await p.locator('#otworz-gov').count()) === 0 && JSON.stringify(await chipy()) === '["zrobione:✓Folder","teraz:2Podpis",":3Wysyłka"]');
  ok('odnośnik „Wolę podpisać elektronicznie (gov.pl)” przełącza z powrotem, a „Wolę podpisać odręcznie” wraca — wybór nie ginie po zamknięciu okna (zapamiętany na urządzeniu)', (await p.locator('#asystent .as-przelacz').count()) === 1);
  await p.click('#asystent .as-przelacz'); const naGov = /Podpisz dokumenty na gov\.pl/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent a#otworz-gov').count()) === 1 && /Wolę podpisać odręcznie/.test(await tekst('#asystent .as-przelacz'));
  await p.click('#asystent .as-przelacz'); await zamknijOkno(); await otworzOkno(); await p.waitForSelector('#kk-folder-stan', { timeout: 20000 });
  ok('przełączanie działa w obie strony, a po zamknięciu i ponownym otwarciu okna asystent od razu pokazuje wybraną ścieżkę odręczną (bez ponownego pytania)', naGov && /Podpisz odręcznie/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent .as-wybor').count()) === 0);

  /* ---------- wydruk ---------- */
  await p.evaluate(() => { window.__otwarte = []; window.open = (u, ...r) => { window.__otwarte.push(String(u)); return {}; }; });      // przeglądarka bez okna wydruku: sprawdzamy, CO aplikacja otwiera
  await p.click('#asystent [data-akcja="drukuj"]'); await p.waitForFunction(() => window.__otwarte.length > 0, null, { timeout: 15000 }).catch(() => {});
  const otwarte = await p.evaluate(() => window.__otwarte);
  ok('„Wydrukuj dokumenty” otwiera PDF do wydruku (jeden plik ze wszystkimi dokumentami, adres blob:)', otwarte.length === 1 && /^blob:/.test(otwarte[0]), JSON.stringify(otwarte).slice(0, 80));

  /* ---------- skany zapisane w folderze „delegacje” → aplikacja sama je wczytuje i sprawdza ---------- */
  const f1 = await wFolderze(), pod = Object.keys(f1)[0], roz = path.join(tmp, 'pdf'); fs.mkdirSync(roz, { recursive: true });
  for (const n of f1[pod]) fs.writeFileSync(path.join(roz, n), Buffer.from(await czytaj(pod, n), 'base64'));
  const pdfy = fs.readdirSync(roz).sort();
  const miejsca = await p.evaluate(() => Object.values(window.__pmtDane.czytaj().miesiace)[0].wynik.miejsca_podpisu);
  fs.writeFileSync(path.join(tmp, 'miejsca.json'), JSON.stringify(Object.fromEntries(Object.entries(miejsca).map(([k, v]) => [norm(k), v]))));
  const plan = Object.fromEntries(pdfy.map(f => [f, 'pominiety'])); plan[pdfy[0]] = 'z'; plan[pdfy[1]] = 'z';      // skany dwóch pierwszych poleceń, z podpisem długopisem
  fs.writeFileSync(path.join(tmp, 'plan.json'), JSON.stringify(plan));
  const r = cp.spawnSync(PY, [path.join(DANE, 'skanuj_pliki.py'), roz, path.join(tmp, 'miejsca.json'), path.join(tmp, 'skany'), path.join(tmp, 'plan.json')], { encoding: 'utf8' }); if (r.status) { console.log(r.stdout, r.stderr); throw new Error('skanuj_pliki.py nie powiódł się'); }
  const skany = fs.readdirSync(path.join(tmp, 'skany')).filter(f => /\.jpg$/.test(f)).sort();
  for (const f of skany) await zapiszDoFolderu(pod, f, fs.readFileSync(path.join(tmp, 'skany', f)));
  const s1 = await czekajStany(['ok', 'ok', 'czeka', 'czeka', 'czeka', 'czeka', 'ok'], 120000);
  ok('dwa skany z podpisem odręcznym zapisane w folderze zostały SAME wczytane i sprawdzone („Widzę podpis w miejscu podpis pracownika”) — bez „Wybierz pliki”', JSON.stringify(s1) === '["ok","ok","czeka","czeka","czeka","czeka","ok"]' && /Widzę podpis w miejscu/.test(await p.locator('.dok-k[data-i="0"]').innerText()), JSON.stringify(s1));
  ok('pasek postępu pokazuje „Wczytano 2 z 6 podpisanych poleceń”, a asystent zostaje na ścieżce odręcznej', /Wczytano 2 z 6 podpisanych poleceń/.test(await tekst('#asystent .as-status')) && /Podpisz odręcznie/.test(await tekst('#asystent .as-tytul')), (await tekst('#asystent .as-status')).replace(/\n/g, ' | '));

  /* ---------- pozostałe cztery polecenia: skany z podpisem → „Wyślij” ---------- */
  const plan2 = Object.fromEntries(pdfy.map(f => [f, 'pominiety'])); for (const f of pdfy.slice(2, 6)) plan2[f] = 'z';
  fs.writeFileSync(path.join(tmp, 'plan2.json'), JSON.stringify(plan2));
  const r2 = cp.spawnSync(PY, [path.join(DANE, 'skanuj_pliki.py'), roz, path.join(tmp, 'miejsca.json'), path.join(tmp, 'skany2'), path.join(tmp, 'plan2.json')], { encoding: 'utf8' }); if (r2.status) { console.log(r2.stdout, r2.stderr); throw new Error('skanuj_pliki.py (2) nie powiódł się'); }
  for (const f of fs.readdirSync(path.join(tmp, 'skany2')).filter(f => /\.jpg$/.test(f)).sort()) await zapiszDoFolderu(pod, f, fs.readFileSync(path.join(tmp, 'skany2', f)));
  const s2 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok'], 150000);
  await p.waitForSelector('#asystent [data-akcja="wyslij"]', { timeout: 30000 });
  ok('po wczytaniu wszystkich skanów asystent pokazuje krok „Wysyłka” z JEDNYM przyciskiem „Wyślij” — tak samo jak po podpisie na gov.pl', JSON.stringify(s2) === '["ok","ok","ok","ok","ok","ok","ok"]' && /Wszystko podpisane i sprawdzone/.test(await tekst('#asystent .as-tytul')) && JSON.stringify(await chipy()) === '["zrobione:✓Folder","zrobione:✓Podpis","teraz:3Wysyłka"]' && (await p.locator('#asystent .as-akcja .przycisk').count()) === 1, JSON.stringify(s2));
  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
