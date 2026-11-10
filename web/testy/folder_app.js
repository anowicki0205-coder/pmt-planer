// Folder roboczy na pulpicie (js/folder.js + podpis.js): dokumenty zapisują się w folderze, a aplikacja SAMA zauważa podpisane pliki, które pojawią się w tym folderze, wczytuje je i sprawdza w tle —
// zamiast ręcznego „Wybierz pliki”. Okna systemowego „Wybierz folder” nie da się obsłużyć w przeglądarce bez interfejsu, więc w teście showDirectoryPicker zwraca folder z prywatnej pamięci przeglądarki (OPFS):
// ten sam interfejs uchwytów. „Podpisanie na gov.pl” to testowe podpisy z dane/podpisz_pliki.py zapisywane do folderu tak, jak zrobiłby to użytkownik.
// NODE_PATH=/opt/node22/lib/node_modules node folder_app.js
const { wpiszAdres, otworz, generuj } = require('./wspolne'); const fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
(async () => {
  const PY = process.env.PYTHON_PODPISY || '/tmp/phvenv/bin/python', DANE = path.join(__dirname, 'dane');
  const t = await otworz({ w: 1440, h: 900, folder: true, pocztaDomyslna: null }); const p = t.p; let kod = 0; p.on('crash', () => console.log('!! strona padła (crash)')); p.on('close', () => console.log('!! strona zamknięta')); p.context().browser().on('disconnected', () => console.log('!! przeglądarka rozłączona'));
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
  const zapiszDoKorzenia = (nazwa, bajty) => p.evaluate(async ([nazwa, b64]) => { const k = await navigator.storage.getDirectory(), f = await (await k.getDirectoryHandle('pmt-folder-testowy')).getDirectoryHandle('delegacje'), w = await (await f.getFileHandle(nazwa, { create: true })).createWritable(); await w.write(Uint8Array.from(atob(b64), c => c.charCodeAt(0))); await w.close(); }, [nazwa, Buffer.from(bajty).toString('base64')]);      // folder główny „delegacje” (tu trafiają pobrane pliki, gdy w przeglądarce ustawiono „Pobrane → Lokalizacja” na ten folder)
  const zrzut = async n => { if (process.env.PMT_ZRZUTY) { fs.mkdirSync(process.env.PMT_ZRZUTY, { recursive: true }); await p.screenshot({ path: path.join(process.env.PMT_ZRZUTY, n + '.png') }); } };      // PMT_ZRZUTY=katalog: zrzuty ekranu kluczowych stanów asystenta (do oglądania)
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
  ok('w przeglądarce z dostępem do folderów okno to ASYSTENT: pasek „Folder · Podpis · Wysyłka”, tytuł „Wskaż folder na dokumenty”, trzy krótkie kroki i JEDEN duży przycisk „Wskaż folder”', (await p.locator('#asystent .as-kroki li').count()) === 3 && /Wskaż folder na dokumenty/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent .as-lista li').count()) === 3 && (await p.locator('#asystent .przycisk.glowny').count()) === 1 && (await p.locator('#asystent [data-akcja="folder-wskaz"]').count()) === 1 && (await p.locator('.kroki4').count()) === 0);
  ok('przed wskazaniem folderu nie ma „Otwórz gov.pl”, a krok pierwszy mówi wprost, co kliknąć w oknie wyboru („Nowy folder”, nazwa delegacje, „Wybierz folder”)', (await p.locator('#otworz-gov').count()) === 0 && /Nowy folder/.test(await tekst('#asystent')) && /delegacje/.test(await tekst('#asystent')) && /Wybierz folder/.test(await tekst('#asystent')));
  const chipy = () => p.evaluate(() => [...document.querySelectorAll('#asystent .as-kroki li')].map(e => e.className + ':' + e.textContent.trim())), tc = sel => p.locator(sel).textContent();
  ok('pasek postępu: „Folder” jest teraz, „Podpis” i „Wysyłka” czekają', JSON.stringify(await chipy()) === '["teraz:1Folder",":2Podpis",":3Wysyłka"]', JSON.stringify(await chipy()));
  ok('„Inne sposoby i szczegóły” są zwinięte i kryją: podpis odręczny, ręczne wgrywanie (przycisk „Wybierz pliki”, strefa przeciągania), pobieranie osobno, wysyłkę i zmianę folderu', !(await p.locator('details.asyst-inne').evaluate(d => d.open)) && (await p.locator('details.asyst-inne section').count()) === 5 && (await p.locator('#plik-wgraj').count()) === 1 && (await p.locator('details.asyst-inne [data-akcja="folder-zmien"]').count()) === 1 && (await p.locator('details.asyst-inne [data-akcja="drukuj"]').count()) === 1);
  await p.click('details.asyst-inne > summary'); ok('po otwarciu „Inne sposoby” widać ręczne wgrywanie z przyciskiem „Wybierz pliki” i strefą przeciągania', (await p.locator('details.asyst-inne .podp-wgraj').isVisible()) && (await p.locator('details.asyst-inne .podp-strefa').isVisible())); await p.click('details.asyst-inne > summary');
  /* przeglądarka może odmówić (sam Pulpit, Dokumenty i Pobrane są zablokowane): czytelny komunikat („Nowy folder” → „delegacje”), nic się nie psuje, można spróbować ponownie */
  await p.evaluate(() => { window.__pickerOrig = window.showDirectoryPicker; window.showDirectoryPicker = async () => { throw new DOMException('Can\'t open this folder because it contains system files.', 'SecurityError'); }; });
  await p.click('#asystent [data-akcja="folder-wskaz"]'); await p.waitForSelector('#asystent .as-blad', { timeout: 10000 });
  ok('folder zablokowany przez przeglądarkę → komunikat „kliknij „Nowy folder”, nazwij go „delegacje” i wskaż go”, przycisk zostaje', /Nowy folder.*delegacje/.test(await tekst('#asystent .as-blad')) && (await p.locator('#asystent [data-akcja="folder-wskaz"]').count()) === 1, await tekst('#asystent .as-blad'));
  await p.evaluate(() => { window.showDirectoryPicker = window.__pickerOrig; });
  /* ---------- wskazanie miejsca: aplikacja SAMA tworzy „delegacje” i podfolder miesiąca i od razu zapisuje dokumenty ---------- */
  await p.click('#asystent [data-akcja="folder-wskaz"]'); await p.waitForSelector('#kk-folder-stan', { timeout: 40000 }).catch(async e => { console.log('STAN ASYSTENTA:', (await tekst('#asystent')).replace(/\n/g, ' | '), JSON.stringify(t.bledy)); throw e; }); await p.waitForTimeout(1500);
  ok('po wskazaniu folderu asystent sam przechodzi do kroku „Podpisz”: tytuł „Podpisz dokumenty na gov.pl”, gdzie leżą dokumenty („delegacje” › „wrzesień 2026”), które pliki wybrać i JEDEN duży przycisk „Otwórz gov.pl” — bez dodatkowego klikania', /Podpisz dokumenty na gov\.pl/.test(await tekst('#asystent .as-tytul')) && /„delegacje” › „wrzesień 2026”/.test(await tekst('#asystent')) && /delegacja_01, 02, 03, 04, 05/.test(await tekst('#asystent')) && (await p.locator('#asystent a#otworz-gov[href*="gov.pl"]').count()) === 1 && (await p.locator('#asystent [data-akcja="folder-wskaz"]').count()) === 0 && JSON.stringify(await chipy()) === '["zrobione:✓Folder","teraz:2Podpis",":3Wysyłka"]', (await tekst('#asystent')).replace(/\n/g, ' | ').slice(0, 400));
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
  ok('asystent pokazuje postęp na żywo (pasek „0 z 6”) i że folder jest obserwowany', (await p.locator('#asystent .as-pasek').count()) === 1 && /Czekam na podpisane pliki · 0 z 6/.test(await tekst('#asystent .as-status')) && /Obserwuję folder/.test(await tekst('#kk-folder-stan')));
  ok('w kroku „Podpisz” nie ma niczego zbędnego: żadnego „Zapisz ponownie”, „Pobierz wszystkie”, listy pobierania ani drugiego dużego przycisku obok „Otwórz gov.pl”', (await p.locator('#asystent [data-akcja="folder-zapisz"], #asystent [data-akcja="osobno"], #asystent .kk-plik').count()) === 0 && (await p.locator('#asystent .as-akcja .przycisk').count()) === 1, (await tekst('#asystent')).replace(/\n/g, ' | ').slice(0, 300));
  ok('rozliczenie wydatków (nie wymaga podpisu) weszło do aplikacji od razu jako przyjęte; polecenia czekają na podpis', JSON.stringify(await stany()) === '["czeka","czeka","czeka","czeka","czeka","czeka","ok"]' && /nie jest na nim wymagany/.test(await tekst('.dok-k[data-i="6"] .dok-kom')), JSON.stringify(await stany()));
  await p.waitForTimeout(6500);
  ok('oryginały zapisane przez aplikację NIE są wczytywane z powrotem jako „nowe pliki” (po kilku obrotach obserwacji nic nie wykryto)', !/wczytane pliki/.test(await tekst('#kk-folder-stan')) && JSON.stringify(await stany()) === '["czeka","czeka","czeka","czeka","czeka","czeka","ok"]', await tekst('#kk-folder-stan'));

  ok('w asystencie jest jednolinijkowa, zwinięta podpowiedź „Pobrane → Lokalizacja”', (await p.locator('#kk-pobrane-rada').count()) === 1 && /Lokalizacja/.test(await tekst('#kk-pobrane-rada')) && !(await p.locator('#kk-pobrane-rada details').evaluate(d => d.open)));
  await p.click('#kk-pobrane-rada summary');
  ok('„Jak to zrobić?” pokazuje adres ustawień pobierania przeglądarki z przyciskiem „Kopiuj” i uwagą o blokadzie przez firmę', /settings\/downloads/.test(await tekst('#kk-pobrane-rada')) && (await p.locator('[data-akcja="pobrane-kopiuj"]').count()) === 1 && /Firma może to blokować/.test(await tekst('#kk-pobrane-rada')));
  await p.click('[data-akcja="pobrane-rada-ok"]');
  ok('„Ukryj” chowa podpowiedź i pamięta wybór na urządzeniu', (await p.locator('#kk-pobrane-rada').count()) === 0 && (await p.evaluate(() => localStorage.getItem('pmt-ui-pobrane-rada'))) === '1');
  await p.evaluate(() => localStorage.removeItem('pmt-ui-pobrane-rada')); await zamknijOkno(); await otworzOkno(); await p.waitForSelector('#kk-folder-stan', { timeout: 20000 });      // podpowiedź ma wrócić, dopóki pliki nie zaczną docierać (znikła tylko przez „Ukryj”, które właśnie cofnęliśmy)
  ok('po cofnięciu „Ukryj” podpowiedź znów jest (znika dopiero po pierwszym wczytanym pliku)', (await p.locator('#kk-pobrane-rada').count()) === 1);

  /* ---------- „podpis na gov.pl”: podpisane pliki pojawiają się w folderze, aplikacja sama je wczytuje i sprawdza ---------- */
  fs.writeFileSync(path.join(tmp, 'plan1.json'), JSON.stringify({ [pdfy[0]]: 'jan', [pdfy[1]]: 'jan' }));
  const tylko01 = path.join(tmp, 'tylko01'); fs.mkdirSync(tylko01); for (const f of [pdfy[0], pdfy[1]]) fs.copyFileSync(path.join(roz, f), path.join(tylko01, f));
  py('podpisz_pliki.py', tylko01, path.join(tmp, 'e1'), path.join(tmp, 'plan1.json'));
  await zapiszDoFolderu(nazwaPod, 'Podpisany dokument (1).pdf', fs.readFileSync(path.join(tmp, 'e1', pdfy[0])));      // gov.pl oddaje pliki pod przypadkowymi nazwami
  /* powrót na kartę aplikacji (zdarzenie focus): plik starszy niż 4 s jest brany od razu, bez czekania na drugi obrót obserwacji (2,5 s) — czas przesuwamy sztucznie, bo plik testowy jest świeży */
  await p.waitForTimeout(300);
  await p.evaluate(() => { const n = Date.now.bind(Date); window.__n = n; Date.now = () => n() + 6000; window.dispatchEvent(new Event('focus')); });
  const szybko = await p.waitForFunction(() => /Wykryto 1|wczytane pliki: 1/.test((document.querySelector('#kk-folder-stan') || {}).textContent || ''), null, { timeout: 2000, polling: 100 }).then(() => true).catch(() => false);
  await p.evaluate(() => { Date.now = window.__n; });
  ok('po powrocie na kartę plik starszy niż 4 s jest wczytywany od razu (w ciągu 2 s, zanim zdążyłby drugi obrót obserwacji)', szybko, await tekst('#kk-folder-stan'));
  await zapiszDoFolderu(nazwaPod, pdfy[1], fs.readFileSync(path.join(tmp, 'e1', pdfy[1])));      // albo podpisany plik zastępuje oryginał o tej samej nazwie
  const s1 = await czekajStany(['ok', 'ok', 'czeka', 'czeka', 'czeka', 'czeka', 'ok'], 90000);
  ok('dwa podpisane pliki zapisane w folderze (jeden pod obcą nazwą, drugi w miejsce oryginału) zostały SAME wczytane, rozpoznane i sprawdzone — bez „Wybierz pliki”', JSON.stringify(s1) === '["ok","ok","czeka","czeka","czeka","czeka","ok"]', JSON.stringify(s1));
  ok('po pierwszym wczytanym pliku podpowiedź o lokalizacji pobierania znika (podpisane pliki już docierają)', (await p.locator('#kk-pobrane-rada').count()) === 0);
  ok('okno mówi, ile plików wczytano z folderu', /wczytane pliki: 2/.test(await tekst('#kk-folder-stan')), await tekst('#kk-folder-stan'));
  await zrzut('3_postep');
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
  ok('po zamknięciu i ponownym otwarciu okna folder jest pamiętany i dalej obserwowany (bez ponownego wskazywania)', (await p.locator('#asystent [data-akcja="folder-wskaz"]').count()) === 0 && /Obserwuję folder/.test(await tekst('#kk-folder-stan')) && /delegacje/.test(await tekst('#asystent')));
  await p.waitForTimeout(8000);
  const z2 = await zapisane();
  ok('po ponownym otwarciu pliki z poprzedniej wizyty nie wczytują się drugi raz (te same pliki, te same stany)', JSON.stringify(await stany()) === '["ok","ok","zle","czeka","czeka","czeka","ok"]' && z2.pliki[0].length === 1 && z2.pliki[1].length === 1 && !/wczytane pliki/.test(await tekst('#kk-folder-stan')), JSON.stringify(z2.pliki));

  /* przeglądarka bywa, że prosi o ponowną zgodę (nowa sesja): jedno kliknięcie „Pozwól” i obserwacja rusza dalej */
  await zamknijOkno();
  await p.evaluate(() => { const H = FileSystemHandle.prototype; window.__qp = H.queryPermission; window.__rp = H.requestPermission; H.queryPermission = async () => 'prompt'; H.requestPermission = async () => { H.queryPermission = window.__qp; H.requestPermission = window.__rp; return 'granted'; }; });
  await otworzOkno(); await p.waitForSelector('[data-akcja="folder-wznow"]', { timeout: 20000 });
  ok('gdy przeglądarka prosi o zgodę: „Pozwól” (bez ponownego wskazywania folderu), obserwacji jeszcze nie ma', /pyta o zgodę na folder/.test(await tekst('#asystent')) && (await p.locator('#kk-folder-stan').count()) === 0, (await tekst('#asystent')).slice(0, 160));
  await p.click('[data-akcja="folder-wznow"]'); await p.waitForSelector('#kk-folder-stan', { timeout: 20000 });
  ok('po „Pozwól” folder jest znów obserwowany', /Obserwuję folder/.test(await tekst('#kk-folder-stan')));

  /* ---------- reszta poleceń: wszystkie podpisane → „Wyślij” się zapala ---------- */
  const reszta = path.join(tmp, 'reszta'); fs.mkdirSync(reszta); for (const f of pdfy.slice(2, 6)) fs.copyFileSync(path.join(roz, f), path.join(reszta, f));
  fs.writeFileSync(path.join(tmp, 'plan3.json'), '{}'); py('podpisz_pliki.py', reszta, path.join(tmp, 'e3'), path.join(tmp, 'plan3.json'));      // domyślnie „jan”: poprawny podpis
  for (const f of pdfy.slice(2, 6)) await zapiszDoKorzenia('gov_' + f, fs.readFileSync(path.join(tmp, 'e3', f)));      // tym razem do folderu GŁÓWNEGO (nie do podfolderu miesiąca), jak przy pobieraniu ustawionym na „delegacje”
  const s3 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok'], 120000);
  ok('pozostałe cztery podpisane pliki zapisane w folderze GŁÓWNYM „delegacje” (jak przy pobieraniu ustawionym na ten folder) też weszły same (podpis innej osoby zastąpiony poprawnym) — wszystkie 7 dokumentów sprawdzone', JSON.stringify(s3) === '["ok","ok","ok","ok","ok","ok","ok"]', JSON.stringify(s3));
  await p.waitForSelector('#asystent [data-akcja="wyslij"]', { timeout: 30000 });
  await zrzut('4_wyslij');
  ok('po wczytaniu wszystkich podpisów asystent pokazuje krok „Wysyłka”: „Wszystko podpisane i sprawdzone ✔”, pasek z dwoma zaliczonymi etapami i JEDEN przycisk „Wyślij”', /Wszystko podpisane i sprawdzone/.test(await tekst('#asystent .as-tytul')) && JSON.stringify(await chipy()) === '["zrobione:✓Folder","zrobione:✓Podpis","teraz:3Wysyłka"]' && (await p.locator('#asystent .as-akcja .przycisk').count()) === 1 && (await p.locator('#asystent [data-akcja="wyslij"]').count()) === 1, JSON.stringify(await chipy()));
  /* „zmień”: ponowne wskazanie miejsca (tu to samo) — dokumenty zapisują się od nowa, a już wczytane podpisane pliki nie wczytują się drugi raz */
  const przed = JSON.stringify((await zapisane()).pliki);
  await p.click('details.asyst-inne > summary'); await p.click('details.asyst-inne [data-akcja="folder-zmien"]'); await p.waitForTimeout(8000);
  ok('po „zmień” (ponowne wskazanie folderu) stany i wczytane pliki dokumentów się nie zmieniły (nic nie wczytało się drugi raz), a asystent nadal pokazuje „Wyślij”', /Wszystko podpisane i sprawdzone/.test(await tekst('#asystent .as-tytul')) && JSON.stringify(await stany()) === '["ok","ok","ok","ok","ok","ok","ok"]' && JSON.stringify((await zapisane()).pliki) === przed && /„delegacje”/.test(await tc('details.asyst-inne')), JSON.stringify(await stany()));
  /* wysyłka: z działającym folderem DOMYŚLNY sposób to „folder” — wiadomość .eml trafia wprost do „delegacje”, bez pobierania (Chromium oznacza POBRANY .eml jako „potencjalnie niebezpieczny”) */
  let pobrano = 0; p.on('download', () => pobrano++);
  await p.waitForSelector('#asystent [data-akcja="wyslij"][data-metoda="folder"]', { timeout: 20000 });
  ok('z folderem domyślnym sposobem wysyłki jest „wiadomość w folderze „delegacje””; „Zmień sposób” siedzi pod „Inne sposoby”, nie obok przycisku', /wiadomość w folderze „delegacje”/.test(await tc('#asyst-sposob')) && (await p.locator('#asystent [data-akcja="zmien-poczte"]').count()) === 0 && (await p.locator('details.asyst-inne [data-akcja="zmien-poczte"]').count()) === 1, await tc('#asyst-sposob'));
  await p.click('#asystent [data-akcja="wyslij"]');
  await p.waitForFunction(() => /Wiadomość gotowa w folderze/.test((document.querySelector('#podp-wyslij-stan') || {}).innerText || ''), null, { timeout: 60000, polling: 250 }).catch(async () => console.log('STAN WYSYŁKI:', await tekst('#podp-wyslij-stan')));
  const stanW = await tekst('#podp-wyslij-stan');
  const eml = await p.evaluate(async () => { const k = await navigator.storage.getDirectory(), d = await (await k.getDirectoryHandle('pmt-folder-testowy')).getDirectoryHandle('delegacje'); try { return await (await (await d.getFileHandle('PMT_wiadomosc_do_wyslania.eml')).getFile()).text(); } catch (e) { return ''; } });
  ok('„Wyślij” zapisało w folderze „delegacje” plik PMT_wiadomosc_do_wyslania.eml: nagłówki szkicu (X-Unsent, Subject, To) i zahasłowana paczka ZIP jako załącznik', /X-Unsent: 1/.test(eml) && /^To: .+@/m.test(eml) && /^Subject: /m.test(eml) && /filename="[^"]+\.zip"/.test(eml) && /Content-Transfer-Encoding: base64\r?\n\r?\nUEsDB/.test(eml.split('Content-Disposition: attachment')[1] ? 'Content-Transfer-Encoding: base64\r\n\r\n' + eml.split('Content-Disposition: attachment')[1].split('\r\n\r\n')[1] : ''), eml.length + ' znaków');
  ok('nic nie zostało POBRANE (przeglądarka nie ma okazji ostrzegać o „niebezpiecznym pliku”), a komunikat mówi, gdzie kliknąć dwukrotnie — bez adresu odbiorcy', pobrano === 0 && /kliknij dwukrotnie/.test(stanW) && !/@/.test(stanW), stanW.replace(/\n/g, ' | '));
  await zrzut('5_po_wyslaniu');
  ok('po wysyłce asystent mówi „Wysyłka przygotowana ✔” i pokazuje, gdzie kliknąć dwukrotnie; plik wiadomości nie wchodzi do obserwacji folderu (nie jest wczytywany jak podpisany dokument)', /Wysyłka przygotowana/.test(await tekst('#asystent .as-tytul')) && /kliknij dwukrotnie/.test(await tekst('#asystent')) && (await p.locator('#asystent [data-akcja="wyslij"]').count()) === 0 && JSON.stringify(await stany()) === '["ok","ok","ok","ok","ok","ok","ok"]');
  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
