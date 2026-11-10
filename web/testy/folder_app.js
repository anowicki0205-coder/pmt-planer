// Folder roboczy na pulpicie (js/folder.js + podpis.js): dokumenty zapisują się w folderze, a aplikacja SAMA zauważa podpisane pliki, które pojawią się w tym folderze, wczytuje je i sprawdza w tle —
// zamiast ręcznego „Wybierz pliki”. Okna systemowego „Wybierz folder” nie da się obsłużyć w przeglądarce bez interfejsu, więc w teście showDirectoryPicker zwraca folder z prywatnej pamięci przeglądarki (OPFS):
// ten sam interfejs uchwytów. „Podpisanie na gov.pl” to testowe podpisy z dane/podpisz_pliki.py zapisywane do folderu tak, jak zrobiłby to użytkownik.
// NODE_PATH=/opt/node22/lib/node_modules node folder_app.js
const { wpiszAdres, otworz, generuj } = require('./wspolne'); const fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
(async () => {
  const PY = process.env.PYTHON_PODPISY || '/tmp/phvenv/bin/python', DANE = path.join(__dirname, 'dane');
  const t = await otworz({ w: 1440, h: 900, folder: true }); const p = t.p; let kod = 0; p.on('crash', () => console.log('!! strona padła (crash)')); p.on('close', () => console.log('!! strona zamknięta')); p.context().browser().on('disconnected', () => console.log('!! przeglądarka rozłączona'));
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'folder-'));
  t.backend.paczka = { haslo: 'Admin-Haslo-Paczki#2026', wazne_do: '2099-12-31', adres: 'odbiorca@example.com' };
  const stany = () => p.evaluate(() => [...document.querySelectorAll('.dok-k')].map(k => (k.className.match(/st-(\w+)/) || [])[1]));
  const czekajStany = async (oczekiwane, ms = 60000) => { await p.waitForFunction(o => { const s = [...document.querySelectorAll('.dok-k')].map(k => (k.className.match(/st-(\w+)/) || [])[1]); return !s.includes('trwa') && JSON.stringify(s) === JSON.stringify(o); }, oczekiwane, { timeout: ms, polling: 250 }).catch(() => {}); return stany(); };
  const py = (skrypt, ...args) => { const r = cp.spawnSync(PY, [path.join(DANE, skrypt), ...args], { encoding: 'utf8' }); if (r.status) { console.log(r.stdout, r.stderr); throw new Error(skrypt + ' nie powiódł się'); } return r.stdout; };
  const tekst = s => p.locator(s).innerText();
  /* folder testowy (OPFS) widziany z testu: lista plików i zapis „podpisanych” plików tak, jak zrobiłby to użytkownik */
  const wFolderze = () => p.evaluate(async () => { const k = await navigator.storage.getDirectory(), f = await (await k.getDirectoryHandle('pmt-folder-testowy', { create: true })).getDirectoryHandle('delegacje'); const wyn = {}; for await (const [n, u] of f.entries()) { if (u.kind !== 'directory') continue; wyn[n] = []; for await (const [m, v] of u.entries()) { const pl = await v.getFile(); wyn[n].push({ nazwa: m, rozmiar: pl.size }); } } return wyn; });
  const czytajZFolderu = (pod, nazwa) => p.evaluate(async ([pod, nazwa]) => { const k = await navigator.storage.getDirectory(), f = await (await (await k.getDirectoryHandle('pmt-folder-testowy')).getDirectoryHandle('delegacje')).getDirectoryHandle(pod), pl = await (await f.getFileHandle(nazwa)).getFile(), b = new Uint8Array(await pl.arrayBuffer()); let s = ''; for (let i = 0; i < b.length; i += 8192) s += String.fromCharCode(...b.subarray(i, i + 8192)); return btoa(s); }, [pod, nazwa]);
  const zapiszDoFolderu = (pod, nazwa, bajty) => p.evaluate(async ([pod, nazwa, b64]) => { const k = await navigator.storage.getDirectory(), f = await (await (await k.getDirectoryHandle('pmt-folder-testowy')).getDirectoryHandle('delegacje')).getDirectoryHandle(pod), w = await (await f.getFileHandle(nazwa, { create: true })).createWritable(); await w.write(Uint8Array.from(atob(b64), c => c.charCodeAt(0))); await w.close(); }, [pod, nazwa, Buffer.from(bajty).toString('base64')]);
  const zapisane = () => p.evaluate(() => { const r = Object.values(window.__pmtDane.czytaj().miesiace)[0]; return { pliki: r.podpisaniPliki || {}, weryfikacje: r.weryfikacje || {} }; });
  const otworzOkno = async () => { await p.click('#podpisz'); await p.waitForSelector('#dok-siatka', { timeout: 20000 }); await p.waitForTimeout(900); };
  const zamknijOkno = async () => { await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); await p.waitForTimeout(400); };

  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await wpiszAdres(p, 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await generuj(p); await p.waitForTimeout(3500);

  /* ---------- pierwsze otwarcie: trzeba wskazać folder ---------- */
  await otworzOkno();
  ok('w przeglądarce z dostępem do folderów krok „Podpisz” oferuje folder „delegacje”: „Wskaż miejsce”; pobieranie osobnych PDF-ów jest schowane („Albo pobierz dokumenty osobno”)', (await p.locator('#kk-folder [data-akcja="folder-wskaz"]').count()) === 1 && (await p.locator('details.kk-osobno').count()) === 1 && !(await p.locator('details.kk-osobno').evaluate(d => d.open)));
  ok('przed zapisaniem dokumentów „Otwórz gov.pl” jest wyszarzone', await p.locator('#otworz-gov').isDisabled());
  /* przeglądarka może odmówić (sam Pulpit, Dokumenty i Pobrane są zablokowane): czytelny komunikat („Nowy folder” → „delegacje”), nic się nie psuje, można spróbować ponownie */
  await p.evaluate(() => { window.__pickerOrig = window.showDirectoryPicker; window.showDirectoryPicker = async () => { throw new DOMException('Can\'t open this folder because it contains system files.', 'SecurityError'); }; });
  await p.click('[data-akcja="folder-wskaz"]'); await p.waitForSelector('.kk-folder-blad', { timeout: 10000 });
  ok('folder zablokowany przez przeglądarkę → komunikat „kliknij „Nowy folder”, nazwij go „delegacje” i wskaż go”, przycisk zostaje', /Nowy folder.*delegacje/.test(await tekst('.kk-folder-blad')) && (await p.locator('[data-akcja="folder-wskaz"]').count()) === 1, await tekst('.kk-folder-blad'));
  await p.evaluate(() => { window.showDirectoryPicker = window.__pickerOrig; });
  /* ---------- wskazanie miejsca: aplikacja SAMA tworzy „delegacje” i podfolder miesiąca i od razu zapisuje dokumenty ---------- */
  await p.click('[data-akcja="folder-wskaz"]'); await p.waitForSelector('#kk-folder-stan', { timeout: 40000 }).catch(async e => { console.log('STAN FOLDERU:', (await tekst('#kk-folder')).replace(/\n/g, ' | '), JSON.stringify(t.bledy)); throw e; }); await p.waitForTimeout(1500);
  ok('po wskazaniu miejsca blok jest niski i mówi, gdzie leżą dokumenty: „Folder „delegacje” › „wrzesień 2026””; bez dodatkowego klikania („Zapisz dokumenty” nie jest potrzebne)', /Folder „delegacje” › „wrzesień 2026”/.test(await tekst('#kk-folder')) && (await p.locator('#kk-folder [data-akcja="folder-wskaz"]').count()) === 0 && (await p.locator('#kk-folder').evaluate(e => e.getBoundingClientRect().height)) < 75, (await tekst('#kk-folder')).replace(/\n/g, ' | ') + ' · wysokość ' + Math.round(await p.locator('#kk-folder').evaluate(e => e.getBoundingClientRect().height)));
  const topFolder = await p.evaluate(async () => { const k = await navigator.storage.getDirectory(), f = await k.getDirectoryHandle('pmt-folder-testowy'), w = []; for await (const [n, u] of f.entries()) w.push(n + ':' + u.kind); return w; });
  ok('we wskazanym miejscu powstał jeden folder „delegacje” (nic więcej)', JSON.stringify(topFolder) === '["delegacje:directory"]', JSON.stringify(topFolder));
  const f1 = await wFolderze(), nazwaPod = Object.keys(f1)[0];
  ok('w „delegacje” powstał podfolder miesiąca „wrzesień 2026” z 7 plikami PDF (6 poleceń i rozliczenie)', Object.keys(f1).length === 1 && nazwaPod === 'wrzesien 2026' && f1[nazwaPod].length === 7 && f1[nazwaPod].every(x => /\.pdf$/.test(x.nazwa) && x.rozmiar > 1000), JSON.stringify(f1));
  const roz = path.join(tmp, 'pdf'); fs.mkdirSync(roz, { recursive: true });
  for (const x of f1[nazwaPod]) fs.writeFileSync(path.join(roz, x.nazwa), Buffer.from(await czytajZFolderu(nazwaPod, x.nazwa), 'base64'));
  const pdfy = fs.readdirSync(roz).sort();
  ok('zapisane pliki to prawdziwe PDF-y o nazwach dokumentów', pdfy.every(f => fs.readFileSync(path.join(roz, f)).subarray(0, 5).toString() === '%PDF-') && /^delegacja_01_/.test(pdfy[0]), pdfy[0]);
  /* nagłówek polecenia: pieczątka podpisu zaufanego z gov.pl wchodzi w prawy górny róg pierwszej strony (do ok. 28 mm od góry, x od ok. 165 mm) — numer centrum kosztów i napis „Centrum” nie mogą pod nią wchodzić */
  const bbox = cp.spawnSync('pdftotext', ['-bbox', '-f', '1', '-l', '1', path.join(roz, pdfy[0]), '-'], { encoding: 'utf8' });
  if (bbox.status === 0) {
    const mm = pt => pt * 25.4 / 72, slowa = [...bbox.stdout.matchAll(/<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)<\/word>/g)].map(m => ({ x: mm(+m[1]), y: mm(+m[2]), t: m[5] }));
    const prawe = slowa.filter(w => w.x > 150), centrum = prawe.find(w => w.t === 'Centrum'), numer = prawe.find(w => w.t === '6');
    ok('numer centrum kosztów i napis „Centrum” zaczynają się poniżej pieczątki podpisu zaufanego (ponad 28 mm od góry strony), a w prawym górnym rogu nad nimi nic nie ma', !!centrum && !!numer && numer.y >= 28 && centrum.y >= 28 && prawe.every(w => w === numer || w === centrum || w.y >= 28), JSON.stringify({ numer, centrum }));
  } else console.log('  (pominięto kontrolę układu nagłówka: brak pdftotext)');
  ok('po zapisie „Otwórz gov.pl” jest odblokowane (link), a okno mówi, że folder jest obserwowany i gdzie zapisać podpisane pliki', (await p.locator('a#otworz-gov[href*="gov.pl"]').count()) === 1 && /Obserwuję folder/.test(await tekst('#kk-folder-stan')) && /zapisz w folderze poniżej/.test(await tekst('.kk-gov')));
  ok('gdy folder działa, nie ma zbędnych elementów: żadnego „Zapisz ponownie”, „Pobierz wszystkie”, rozwijanej listy pobierania ani podpowiedzi — w bloku zostaje ścieżka, stan i odnośnik „zmień”; w kroku „Podpisz” jedyny przycisk to „Otwórz gov.pl”', (await p.locator('details.kk-osobno, [data-akcja="folder-zapisz"], [data-akcja="osobno"], #kk-gov-podp, .kk-plik').count()) === 0 && (await p.locator('#kk-folder [data-akcja="folder-zmien"]').count()) === 1 && (await p.locator('#kk-gov-akcje button, #kk-gov-akcje a').count()) === 1, (await tekst('.kk-gov')).replace(/\n/g, ' | '));
  ok('rozliczenie wydatków (nie wymaga podpisu) weszło do aplikacji od razu jako przyjęte; polecenia czekają na podpis', JSON.stringify(await stany()) === '["czeka","czeka","czeka","czeka","czeka","czeka","ok"]' && /nie jest na nim wymagany/.test(await tekst('.dok-k[data-i="6"] .dok-kom')), JSON.stringify(await stany()));
  await p.waitForTimeout(6500);
  ok('oryginały zapisane przez aplikację NIE są wczytywane z powrotem jako „nowe pliki” (po kilku obrotach obserwacji nic nie wykryto)', !/wczytane pliki/.test(await tekst('#kk-folder-stan')) && JSON.stringify(await stany()) === '["czeka","czeka","czeka","czeka","czeka","czeka","ok"]', await tekst('#kk-folder-stan'));

  /* ---------- „podpis na gov.pl”: podpisane pliki pojawiają się w folderze, aplikacja sama je wczytuje i sprawdza ---------- */
  fs.writeFileSync(path.join(tmp, 'plan1.json'), JSON.stringify({ [pdfy[0]]: 'jan', [pdfy[1]]: 'jan' }));
  const tylko01 = path.join(tmp, 'tylko01'); fs.mkdirSync(tylko01); for (const f of [pdfy[0], pdfy[1]]) fs.copyFileSync(path.join(roz, f), path.join(tylko01, f));
  py('podpisz_pliki.py', tylko01, path.join(tmp, 'e1'), path.join(tmp, 'plan1.json'));
  await zapiszDoFolderu(nazwaPod, 'Podpisany dokument (1).pdf', fs.readFileSync(path.join(tmp, 'e1', pdfy[0])));      // gov.pl oddaje pliki pod przypadkowymi nazwami
  await zapiszDoFolderu(nazwaPod, pdfy[1], fs.readFileSync(path.join(tmp, 'e1', pdfy[1])));      // albo podpisany plik zastępuje oryginał o tej samej nazwie
  const s1 = await czekajStany(['ok', 'ok', 'czeka', 'czeka', 'czeka', 'czeka', 'ok'], 90000);
  ok('dwa podpisane pliki zapisane w folderze (jeden pod obcą nazwą, drugi w miejsce oryginału) zostały SAME wczytane, rozpoznane i sprawdzone — bez „Wybierz pliki”', JSON.stringify(s1) === '["ok","ok","czeka","czeka","czeka","czeka","ok"]', JSON.stringify(s1));
  ok('okno mówi, ile plików wczytano z folderu', /wczytane pliki: 2/.test(await tekst('#kk-folder-stan')), await tekst('#kk-folder-stan'));
  const z1 = await zapisane();
  ok('każdy z dwóch dokumentów ma dokładnie JEDEN wczytany plik (nic nie wczytało się dwa razy)', z1.pliki[0].length === 1 && z1.pliki[1].length === 1 && z1.weryfikacje[0].stan === 'ok' && z1.weryfikacje[1].stan === 'ok' && z1.weryfikacje[0].rodzaj !== 'odreczny', JSON.stringify(z1.pliki) + ' ' + JSON.stringify([z1.weryfikacje[0].rodzaj, z1.weryfikacje[0].stan, z1.weryfikacje[1].rodzaj, z1.weryfikacje[1].stan]));

  /* plik bez podpisu zapisany w folderze: aplikacja go zauważa i mówi, czego brakuje; podpis innej osoby → błąd dokumentu */
  await zapiszDoFolderu(nazwaPod, 'kopia_bez_podpisu.pdf', fs.readFileSync(path.join(roz, pdfy[3])));
  await p.waitForFunction(() => /nie ma podpisu elektronicznego/.test((document.querySelector('#podp-odrzucone') || {}).innerText || ''), null, { timeout: 40000 });
  ok('niepodpisany PDF polecenia zapisany w folderze: aplikacja go zauważyła i pokazuje powód odrzucenia („nie ma podpisu elektronicznego”); stan dokumentów bez zmian', JSON.stringify(await stany()) === '["ok","ok","czeka","czeka","czeka","czeka","ok"]');
  fs.writeFileSync(path.join(tmp, 'plan2.json'), JSON.stringify({ [pdfy[2]]: 'anna' })); const tylko2 = path.join(tmp, 'tylko2'); fs.mkdirSync(tylko2); fs.copyFileSync(path.join(roz, pdfy[2]), path.join(tylko2, pdfy[2]));
  py('podpisz_pliki.py', tylko2, path.join(tmp, 'e2'), path.join(tmp, 'plan2.json'));
  await zapiszDoFolderu(nazwaPod, 'podpis_innej_osoby.pdf', fs.readFileSync(path.join(tmp, 'e2', pdfy[2])));
  const s2 = await czekajStany(['ok', 'ok', 'zle', 'czeka', 'czeka', 'czeka', 'ok'], 90000);
  ok('podpis INNEJ osoby zapisany w folderze: dokument jest odrzucony (czerwony), jak przy ręcznym wgraniu', JSON.stringify(s2) === '["ok","ok","zle","czeka","czeka","czeka","ok"]', JSON.stringify(s2));

  /* ---------- ponowne otwarcie okna: folder pamiętany, nic nie wczytuje się drugi raz ---------- */
  console.log('-- zamykam okno'); await zamknijOkno(); console.log('-- otwieram okno'); await otworzOkno(); console.log('-- czekam na stan folderu'); await p.waitForSelector('#kk-folder-stan', { timeout: 20000 });
  ok('po zamknięciu i ponownym otwarciu okna folder jest pamiętany i dalej obserwowany (bez ponownego wskazywania)', (await p.locator('[data-akcja="folder-wskaz"]').count()) === 0 && /Obserwuję folder/.test(await tekst('#kk-folder-stan')) && /delegacje/.test(await tekst('#kk-folder')));
  await p.waitForTimeout(8000);
  const z2 = await zapisane();
  ok('po ponownym otwarciu pliki z poprzedniej wizyty nie wczytują się drugi raz (te same pliki, te same stany)', JSON.stringify(await stany()) === '["ok","ok","zle","czeka","czeka","czeka","ok"]' && z2.pliki[0].length === 1 && z2.pliki[1].length === 1 && !/wczytane pliki/.test(await tekst('#kk-folder-stan')), JSON.stringify(z2.pliki));

  /* przeglądarka bywa, że prosi o ponowną zgodę (nowa sesja): jedno kliknięcie „Pozwól” i obserwacja rusza dalej */
  await zamknijOkno();
  await p.evaluate(() => { const H = FileSystemHandle.prototype; window.__qp = H.queryPermission; window.__rp = H.requestPermission; H.queryPermission = async () => 'prompt'; H.requestPermission = async () => { H.queryPermission = window.__qp; H.requestPermission = window.__rp; return 'granted'; }; });
  await otworzOkno(); await p.waitForSelector('[data-akcja="folder-wznow"]', { timeout: 20000 });
  ok('gdy przeglądarka prosi o zgodę: „Pozwól” (bez ponownego wskazywania folderu), obserwacji jeszcze nie ma', /prosi o zgodę na dostęp/.test(await tekst('#kk-folder')) && (await p.locator('#kk-folder-stan').count()) === 0, (await tekst('#kk-folder')).slice(0, 160));
  await p.click('[data-akcja="folder-wznow"]'); await p.waitForSelector('#kk-folder-stan', { timeout: 20000 });
  ok('po „Pozwól” folder jest znów obserwowany', /Obserwuję folder/.test(await tekst('#kk-folder-stan')));

  /* ---------- reszta poleceń: wszystkie podpisane → „Wyślij” się zapala ---------- */
  const reszta = path.join(tmp, 'reszta'); fs.mkdirSync(reszta); for (const f of pdfy.slice(2, 6)) fs.copyFileSync(path.join(roz, f), path.join(reszta, f));
  fs.writeFileSync(path.join(tmp, 'plan3.json'), '{}'); py('podpisz_pliki.py', reszta, path.join(tmp, 'e3'), path.join(tmp, 'plan3.json'));      // domyślnie „jan”: poprawny podpis
  for (const f of pdfy.slice(2, 6)) await zapiszDoFolderu(nazwaPod, 'gov_' + f, fs.readFileSync(path.join(tmp, 'e3', f)));
  const s3 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok'], 120000);
  ok('pozostałe cztery podpisane pliki też weszły same (podpis innej osoby zastąpiony poprawnym) — wszystkie 7 dokumentów sprawdzone', JSON.stringify(s3) === '["ok","ok","ok","ok","ok","ok","ok"]', JSON.stringify(s3));
  await p.waitForSelector('.krok-k.k5.aktywny [data-akcja="wyslij"]', { timeout: 30000 });
  ok('„Wyślij” (krok 4) zapalił się — można wysłać zahasłowaną paczkę z podpisanymi PDF-ami', (await p.locator('.krok-k.k5.aktywny [data-akcja="wyslij"]').count()) === 1);
  /* „zmień”: ponowne wskazanie miejsca (tu to samo) — dokumenty zapisują się od nowa, a już wczytane podpisane pliki nie wczytują się drugi raz */
  const przed = JSON.stringify((await zapisane()).pliki);
  await p.click('#kk-folder [data-akcja="folder-zmien"]'); await p.waitForSelector('#kk-folder-stan', { timeout: 40000 }); await p.waitForTimeout(8000);
  ok('po „zmień” blok znów pokazuje folder, a stany i wczytane pliki dokumentów się nie zmieniły (nic nie wczytało się drugi raz)', /Folder „delegacje” › „wrzesień 2026”/.test(await tekst('#kk-folder')) && JSON.stringify(await stany()) === '["ok","ok","ok","ok","ok","ok","ok"]' && JSON.stringify((await zapisane()).pliki) === przed, JSON.stringify(await stany()));
  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
