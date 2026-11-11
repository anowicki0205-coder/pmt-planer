// Asystent podpisu w przeglądarce BEZ dostępu do folderów (Firefox, Safari, telefon — tu: Chromium bez showDirectoryPicker i z UA Firefoksa). Ten sam asystent co w Chrome/Edge: wybór sposobu, jedna rzecz
// do zrobienia naraz, pasek postępu; pliki idą przez folder Pobrane: „Pobierz dokumenty” → gov.pl → przeciągnięcie albo wskazanie podpisanych plików (także całego folderu „Pobrane”, z automatycznym odsiewem
// cudzych plików). Rozliczenie wydatków przyjmuje się samo. Stary widok (cztery kroki naraz) zostaje pod przełącznikiem.
// NODE_PATH=/opt/node22/lib/node_modules node asystent_pobieranie_app.js
const { wpiszAdres, otworz, generuj } = require('./wspolne'); const fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
(async () => {
  const PY = process.env.PYTHON_PODPISY || '/tmp/phvenv/bin/python', DANE = path.join(__dirname, 'dane');
  const t = await otworz({ w: 1440, h: 900, widokPodpisu: null }); const p = t.p; let kod = 0; p.on('crash', () => console.log('!! strona padła (crash)'));
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'pobieranie-'));
  t.backend.paczka = { haslo: 'Admin-Haslo-Paczki#2026', wazne_do: '2099-12-31', adres: 'odbiorca@example.com' };
  const norm = x => x.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l');
  const stany = () => p.evaluate(() => [...document.querySelectorAll('.dok-k')].map(k => (k.className.match(/st-(\w+)/) || [])[1]));
  const czekajStany = async (oczekiwane, ms = 90000) => { await p.waitForFunction(o => { const s = [...document.querySelectorAll('.dok-k')].map(k => (k.className.match(/st-(\w+)/) || [])[1]); return !s.includes('trwa') && JSON.stringify(s) === JSON.stringify(o); }, oczekiwane, { timeout: ms, polling: 250 }).catch(() => {}); return stany(); };
  const py = (skrypt, ...args) => { const r = cp.spawnSync(PY, [path.join(DANE, skrypt), ...args], { encoding: 'utf8' }); if (r.status) { console.log(r.stdout, r.stderr); throw new Error(skrypt + ' nie powiódł się'); } return r.stdout; };
  const tekst = s => p.locator(s).innerText();
  const chipy = () => p.evaluate(() => [...document.querySelectorAll('#asystent .as-kroki li')].map(e => e.className + ':' + e.textContent.trim()));
  const otworzOkno = async () => { await p.click('#podpisz'); await p.waitForSelector('#asystent, .kroki4', { timeout: 20000 }); await p.waitForTimeout(900); };
  const zamknijOkno = async () => { await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); await p.waitForTimeout(400); };
  const zrzut = async n => { if (process.env.PMT_ZRZUTY) { fs.mkdirSync(process.env.PMT_ZRZUTY, { recursive: true }); await p.screenshot({ path: path.join(process.env.PMT_ZRZUTY, 'pobieranie_' + n + '.png') }); } };
  const pobrane = []; p.on('download', d => pobrane.push(d));
  const czekajNaPobrania = async (ile, ms = 30000) => { const start = Date.now(); while (pobrane.length < ile && Date.now() - start < ms) await p.waitForTimeout(150); };

  await p.context().addInitScript(() => { Object.defineProperty(navigator, 'userAgent', { get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0' }); });      // dla aplikacji to Firefox (bez showDirectoryPicker)
  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await wpiszAdres(p, 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await generuj(p); await p.waitForTimeout(3500);

  /* ---------- pierwsze otwarcie: asystent, nie cztery kroki; pytanie o sposób podpisu ---------- */
  await otworzOkno();
  ok('bez dostępu do folderów okno to ASYSTENT (pasek „Dokumenty · Podpis · Wysyłka”), a nie dawne cztery kroki naraz', (await p.locator('.kroki4').count()) === 0 && JSON.stringify(await chipy()) === '["teraz:1Dokumenty",":2Podpis",":3Wysyłka"]', JSON.stringify(await chipy()));
  ok('najpierw JEDEN ekran „Jak chcesz podpisać dokumenty?” z dwiema kartami; nic o folderze na pulpicie (tej przeglądarce nie jest potrzebny)', /Jak chcesz podpisać dokumenty/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent .as-wybor').count()) === 2 && !/Wskaż folder|Nowy folder/.test(await tekst('#asystent')));
  ok('rozliczenie wydatków (nie wymaga podpisu) zostało przyjęte SAMO, bez wgrywania i bez śladu na liście „dopasowanych plików”', JSON.stringify(await stany()) === '["czeka","czeka","czeka","czeka","czeka","czeka","ok"]' && (await p.locator('#podp-wyniki .wyniki-det').count()) === 0, JSON.stringify(await stany()));
  ok('podpowiedź o przeglądarce: Firefox nie zapisuje plików w folderze, a w Microsoft Edge albo Google Chrome aplikacja robi to sama — z przyciskiem „Rozumiem”', /Firefoksie/.test(await tekst('#as-rada-przegl')) && /Edge/.test(await tekst('#as-rada-przegl')) && /Chrome/.test(await tekst('#as-rada-przegl')) && (await p.locator('#as-rada-przegl [data-akcja="rada-przegladarki-ok"]').count()) === 1);
  await p.click('#as-rada-przegl [data-akcja="rada-przegladarki-ok"]'); const zniknela = (await p.locator('#as-rada-przegl').count()) === 0;
  await zamknijOkno(); await otworzOkno();
  ok('po „Rozumiem” podpowiedź znika i nie wraca po ponownym otwarciu okna', zniknela && (await p.locator('#as-rada-przegl').count()) === 0);

  await zrzut('1_wybor');
  /* ---------- gov.pl: najpierw pobranie dokumentów do podpisu ---------- */
  await p.click('#asystent [data-sposob="gov"]');
  ok('„Elektronicznie”: tytuł „Pobierz dokumenty do podpisu”, JEDEN duży przycisk „Pobierz dokumenty”, brak „Otwórz gov.pl” (strona gov.pl nie przyjmie plików z aplikacji); chipy: „Dokumenty” jest teraz', /Pobierz dokumenty do podpisu/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent [data-akcja="pobierz-do-podpisu"]').count()) === 1 && (await p.locator('#otworz-gov').count()) === 0 && JSON.stringify(await chipy()) === '["teraz:1Dokumenty",":2Podpis",":3Wysyłka"]', JSON.stringify(await chipy()));
  await p.click('#asystent [data-akcja="pobierz-do-podpisu"]'); await czekajNaPobrania(6); await p.waitForSelector('#asystent a#otworz-gov', { timeout: 20000 });
  const roz = path.join(tmp, 'pdf'); fs.mkdirSync(roz, { recursive: true }); for (const d of pobrane) await d.saveAs(path.join(roz, d.suggestedFilename()));
  const pdfy = fs.readdirSync(roz).sort();
  ok('kliknięcie pobiera 6 poleceń do podpisu (bez rozliczenia, które podpisu nie wymaga) jako prawdziwe PDF-y', pdfy.length === 6 && pdfy.every(n => /^delegacja_0[1-6]_.*\.pdf$/.test(n) && fs.readFileSync(path.join(roz, n)).subarray(0, 5).toString() === '%PDF-'), pdfy.join(', '));
  ok('potem asystent sam przechodzi do „Podpisz dokumenty na gov.pl”: link „Otwórz gov.pl” (nowa karta), pliki do wybrania na gov.pl (pierwsza tura: 01–05), „Pobierz je jeszcze raz”, duża strefa na podpisane pliki, odnośnik do wskazania folderu i pasek „0 z 6”; chipy: „Podpis” jest teraz', /Podpisz dokumenty na gov\.pl/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent a#otworz-gov[href*="gov.pl"][target="_blank"]').count()) === 1 && /delegacja_01, 02, 03, 04, 05/.test(await tekst('#asystent .as-lista')) && /Pobierz je jeszcze raz/.test(await tekst('#asystent')) && (await p.locator('#asystent .as-strefa-duza').count()) === 1 && (await p.locator('#asystent [data-akcja="wybierz-folder"]').count()) === 1 && /0 z 6/.test(await tekst('#asystent .as-status')) && JSON.stringify(await chipy()) === '["zrobione:✓Dokumenty","teraz:2Podpis",":3Wysyłka"]', JSON.stringify(await chipy()));

  await zrzut('2_podpisz');
  /* ---------- „Pobrane”: podpisane pliki z gov.pl razem z oryginałami i cudzymi plikami ---------- */
  const plan = Object.fromEntries(pdfy.map(f => [f, 'niepodpisany'])); for (const i of [2, 3, 4, 5]) plan[pdfy[i]] = 'jan';
  fs.writeFileSync(path.join(tmp, 'plan_p.json'), JSON.stringify(plan)); py('podpisz_pliki.py', roz, path.join(tmp, 'podpisane'), path.join(tmp, 'plan_p.json'));
  const podp = n => path.join(tmp, 'podpisane', n), stara = new Date(Date.now() - 90 * 86400000);
  const gov = path.join(tmp, 'Pobrane'); fs.mkdirSync(gov, { recursive: true });
  for (const f of pdfy) fs.copyFileSync(path.join(roz, f), path.join(gov, f));      // oryginały pobrane wcześniej (bez podpisu) — leżą w tym samym folderze
  for (const i of [2, 3]) fs.copyFileSync(podp(pdfy[i]), path.join(gov, pdfy[i].replace('.pdf', '_signed.pdf')));      // podpisane (gov.pl dopisuje do nazwy)
  fs.copyFileSync(podp(pdfy[2]), path.join(gov, 'stary_podpis.pdf')); fs.utimesSync(path.join(gov, 'stary_podpis.pdf'), stara, stara);      // stary podpisany plik (dawne pobranie)
  fs.writeFileSync(path.join(gov, 'zdjecie.png'), Buffer.from('nie obraz')); fs.writeFileSync(path.join(gov, 'notatki.txt'), 'nic'); fs.writeFileSync(path.join(gov, 'umowa.docx'), Buffer.from('PK nie docx'));
  await p.setInputFiles('#plik-folder', gov);
  const s2 = await czekajStany(['czeka', 'czeka', 'ok', 'ok', 'czeka', 'czeka', 'ok'], 120000);
  ok('wskazany folder „Pobrane” (6 oryginałów + 2 podpisane pliki + stare i cudze pliki): wczytane TYLKO dwa podpisane dokumenty 03 i 04 — oryginały bez podpisu, stary plik, zdjęcie, notatka i plik Worda pominięte po cichu', JSON.stringify(s2) === '["czeka","czeka","ok","ok","czeka","czeka","ok"]' && (await p.locator('#podp-odrzucone .wynik').count()) === 0, JSON.stringify(s2) + ' ' + (await tekst('#podp-odrzucone')));
  ok('pasek: „Wczytano 2 z 6 podpisanych poleceń”', /Wczytano 2 z 6 podpisanych poleceń/.test(await tekst('#asystent .as-status')));
  /* cudzy podpisany PDF (faktura podpisana Profilem Zaufanym) i cudze pliki: nic nie ma prawa się wczytać, a użytkownik dostaje wskazówkę */
  const cudze = path.join(tmp, 'cudze_in'); fs.mkdirSync(cudze, { recursive: true }); fs.copyFileSync(path.join(DANE, 'pdf', 'polecenie_1.pdf'), path.join(cudze, 'faktura.pdf'));
  py('podpisz_pliki.py', cudze, path.join(tmp, 'cudze_pod'), path.join(tmp, 'plan_p.json'));      // plan nie zna „faktura.pdf”: domyślnie poprawny podpis
  const folderCudzy = path.join(tmp, 'Cudzy'); fs.mkdirSync(folderCudzy, { recursive: true }); fs.copyFileSync(path.join(tmp, 'cudze_pod', 'faktura.pdf'), path.join(folderCudzy, 'faktura.pdf')); fs.writeFileSync(path.join(folderCudzy, 'inne.txt'), 'x');
  const przed = JSON.stringify(await stany()); await p.setInputFiles('#plik-folder', folderCudzy); await p.waitForSelector('#asystent .as-info', { timeout: 15000 });
  ok('folder z cudzym podpisanym PDF-em (faktura) i notatką: nic się nie wczytuje, a asystent mówi, że nie widzi nowych podpisanych plików i gdzie szukać („Pobrane”); stany dokumentów bez zmian', /Nie widzę tu nowych podpisanych plików/.test(await tekst('#asystent .as-info')) && /Pobrane/.test(await tekst('#asystent .as-info')) && JSON.stringify(await stany()) === przed, await tekst('#asystent .as-info'));

  /* ---------- ścieżka odręczna: wydruk, skany z podpisem → wskazanie folderu ---------- */
  await p.click('#asystent .as-przelacz');
  ok('„Wolę podpisać odręcznie”: tytuł „Podpisz odręcznie”, trzy kroki, JEDEN duży przycisk „Wydrukuj dokumenty”, duża strefa na skany, odnośnik do wskazania folderu i pasek „2 z 6” (wczytane wcześniej zostają)', /Podpisz odręcznie/.test(await tekst('#asystent .as-tytul')) && (await p.locator('#asystent .as-lista li').count()) === 3 && (await p.locator('#asystent .as-akcja .przycisk').count()) === 1 && /Wydrukuj dokumenty/.test(await tekst('#asystent .as-akcja')) && (await p.locator('#asystent .as-strefa-duza').count()) === 1 && (await p.locator('#asystent [data-akcja="wybierz-folder"]').count()) === 1 && /Wczytano 2 z 6/.test(await tekst('#asystent .as-status')) && (await p.locator('#otworz-gov').count()) === 0);
  await p.evaluate(() => { window.__otwarte = []; window.open = (u, ...r) => { window.__otwarte.push(String(u)); return {}; }; });
  await p.click('#asystent [data-akcja="drukuj"]'); await p.waitForFunction(() => window.__otwarte.length > 0, null, { timeout: 15000 }).catch(() => {});
  ok('„Wydrukuj dokumenty” otwiera jeden PDF ze wszystkimi dokumentami (blob:)', (await p.evaluate(() => window.__otwarte)).length === 1);
  const miejsca = await p.evaluate(() => Object.values(window.__pmtDane.czytaj().miesiace)[0].wynik.miejsca_podpisu);
  fs.writeFileSync(path.join(tmp, 'miejsca.json'), JSON.stringify(Object.fromEntries(Object.entries(miejsca).map(([k, v]) => [norm(k), v]))));
  const skanuj = (indeksy, wyj) => { const pl = Object.fromEntries(pdfy.map((f, i) => [f, indeksy.includes(i) ? 'z' : 'pominiety'])); fs.writeFileSync(path.join(tmp, wyj + '.json'), JSON.stringify(pl)); py('skanuj_pliki.py', roz, path.join(tmp, 'miejsca.json'), path.join(tmp, wyj), path.join(tmp, wyj + '.json')); return fs.readdirSync(path.join(tmp, wyj)).filter(f => /\.jpg$/.test(f)).sort(); };
  const skany = skanuj([0, 1], 'skany'), skanyGov = skanuj([4], 'skany_gov');
  const folderSkanow = path.join(tmp, 'Skany'); fs.mkdirSync(folderSkanow, { recursive: true });
  for (const f of skany) fs.copyFileSync(path.join(tmp, 'skany', f), path.join(folderSkanow, f));
  fs.copyFileSync(path.join(tmp, 'skany', skany[0]), path.join(folderSkanow, 'stary-skan.jpg')); fs.utimesSync(path.join(folderSkanow, 'stary-skan.jpg'), stara, stara);
  fs.writeFileSync(path.join(folderSkanow, 'notatki.txt'), 'nic'); fs.writeFileSync(path.join(folderSkanow, 'umowa.docx'), Buffer.from('PK nie docx'));
  await p.setInputFiles('#plik-folder', folderSkanow);
  const s3 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'czeka', 'czeka', 'ok'], 120000);
  ok('wskazany folder skanów: dwa skany z podpisem wczytane i sprawdzone („Widzę podpis…”); 90-dniowy skan, notatka i plik Worda odsiane po cichu', JSON.stringify(s3) === '["ok","ok","ok","ok","czeka","czeka","ok"]' && (await p.locator('#podp-odrzucone .wynik').count()) === 0 && /Wczytano 4 z 6/.test(await tekst('#asystent .as-status')), JSON.stringify(s3) + ' ' + (await tekst('#podp-odrzucone')));

  /* ---------- z powrotem gov.pl: skany ze wskazanego folderu są wtedy pomijane (mogłyby być przypadkowymi plikami) ---------- */
  await p.click('#asystent .as-przelacz');
  ok('powrót do gov.pl pokazuje od razu „Podpisz dokumenty na gov.pl” (dokumenty są już pobrane) z kolejną turą 05 i 06', /Podpisz dokumenty na gov\.pl/.test(await tekst('#asystent .as-tytul')) && /delegacja_05, 06/.test(await tekst('#asystent .as-lista')), await tekst('#asystent .as-lista'));
  const folderSkanGov = path.join(tmp, 'SkanGov'); fs.mkdirSync(folderSkanGov, { recursive: true }); fs.copyFileSync(path.join(tmp, 'skany_gov', skanyGov[0]), path.join(folderSkanGov, skanyGov[0]));
  await p.setInputFiles('#plik-folder', folderSkanGov); await p.waitForSelector('#asystent .as-info', { timeout: 15000 }); await p.waitForTimeout(800);
  ok('przy wyborze gov.pl skan w folderze nie jest wczytywany (informacja zamiast wczytania), stany bez zmian', JSON.stringify(await stany()) === '["ok","ok","ok","ok","czeka","czeka","ok"]');

  /* ---------- upuszczanie: plik wprost w dowolnym miejscu okna i cały folder ---------- */
  const b64 = i => fs.readFileSync(podp(pdfy[i])).toString('base64');
  await p.evaluate(() => { const dt = new DataTransfer(); dt.items.add(new File(['x'], 'a.pdf')); document.querySelector('#asystent .as-tytul').dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true, cancelable: true })); });
  const podswietlone = await p.evaluate(() => document.querySelector('#arkusz-tresc').classList.contains('upusc-pliki'));
  await p.evaluate(() => document.querySelector('#asystent .as-tytul').dispatchEvent(new DragEvent('dragleave', { bubbles: true, cancelable: true })));
  ok('przeciąganie pliku nad okno podświetla je w CAŁOŚCI („Upuść tutaj…”), a odsunięcie gasi podświetlenie', podswietlone && !(await p.evaluate(() => document.querySelector('#arkusz-tresc').classList.contains('upusc-pliki'))));
  await p.evaluate(async ([nazwa, b64]) => { const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)), dt = new DataTransfer(); dt.items.add(new File([bin], nazwa, { type: 'application/pdf' })); const tytul = document.querySelector('#asystent .as-tytul'); tytul.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true, cancelable: true })); tytul.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true })); }, [pdfy[4].replace('.pdf', '-podpisany.pdf'), b64(4)]);      // upuszczone na tytuł karty, nie na „strefę”
  const s4 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'czeka', 'ok'], 90000);
  ok('plik upuszczony w dowolnym miejscu okna (tu: na tytule karty) jest wczytany i sprawdzony; podświetlenie zgasło', JSON.stringify(s4) === '["ok","ok","ok","ok","ok","czeka","ok"]' && !(await p.evaluate(() => document.querySelector('#arkusz-tresc').classList.contains('upusc-pliki'))), JSON.stringify(s4));
  /* cały folder: udawany wpis katalogu (prawdziwy trzeba by przeciągnąć z Eksploratora) — z podpisanym 06, notatką i „zdjęciem z wakacji” w środku */
  await p.evaluate(async ([nazwa, b64]) => {
    const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)), wpis = (n, b) => ({ isFile: true, isDirectory: false, name: n, file: ok => ok(new File([b], n)) });
    const katalog = { isFile: false, isDirectory: true, name: 'Pobrane', createReader: () => { let juz = false; return { readEntries: ok => { ok(juz ? [] : [wpis(nazwa, bin), wpis('notatki.txt', 'nic'), wpis('zdjecie_z_wakacji.jpg', new Uint8Array([1, 2, 3]))]); juz = true; } }; } };
    DataTransferItem.prototype.webkitGetAsEntry = function () { return katalog; };
    const dt = new DataTransfer(); dt.items.add(new File([], 'Pobrane')); document.querySelector('#asystent').dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
  }, [pdfy[5].replace('.pdf', '_signed.pdf'), b64(5)]);
  const s5 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok'], 90000);
  ok('upuszczony FOLDER: znalazłem w nim podpisane polecenie 06 (notatka i zdjęcie z wakacji pominięte po cichu) — wszystkie 7 dokumentów sprawdzone', JSON.stringify(s5) === '["ok","ok","ok","ok","ok","ok","ok"]' && (await p.locator('#podp-odrzucone .wynik').count()) === 0, JSON.stringify(s5));

  /* ---------- widok klasyczny pod przełącznikiem ---------- */
  await p.waitForSelector('#asystent [data-akcja="wyslij"]', { timeout: 30000 });
  await p.click('details.asyst-inne > summary'); await p.click('details.asyst-inne [data-akcja="widok-podpisu"][data-w="klasyczny"]'); await p.waitForSelector('.kroki4', { timeout: 10000 });
  ok('przełącznik „Pokaż wszystkie kroki naraz” pokazuje dawne cztery kroki (bez asystenta; „Wyślij” zapalone, bo wszystko podpisane) i link „Wróć do asystenta”', (await p.locator('.krok-k').count()) === 4 && (await p.locator('.krok-k.k5.aktywny').count()) === 1 && (await p.locator('#asystent').count()) === 0 && (await p.locator('[data-akcja="widok-podpisu"][data-w="asystent"]').count()) === 1);
  await zamknijOkno(); await otworzOkno();
  ok('wybór widoku jest zapamiętany (po ponownym otwarciu okna nadal klasyczny)', (await p.locator('.kroki4').count()) === 1 && (await p.locator('#asystent').count()) === 0);
  await p.click('[data-akcja="widok-podpisu"][data-w="asystent"]'); await p.waitForSelector('#asystent', { timeout: 10000 });
  ok('„Wróć do asystenta” przywraca asystenta (z przyciskiem „Wyślij”)', (await p.locator('.kroki4').count()) === 0 && (await p.locator('#asystent [data-akcja="wyslij"]').count()) === 1);

  /* ---------- wysyłka ---------- */
  ok('po wczytaniu wszystkiego asystent pokazuje „Wszystko podpisane i sprawdzone ✔”, pasek z dwoma zaliczonymi etapami i JEDEN przycisk „Wyślij”', /Wszystko podpisane i sprawdzone/.test(await tekst('#asystent .as-tytul')) && JSON.stringify(await chipy()) === '["zrobione:✓Dokumenty","zrobione:✓Podpis","teraz:3Wysyłka"]' && (await p.locator('#asystent .as-akcja .przycisk').count()) === 1, JSON.stringify(await chipy()));
  pobrane.length = 0; await p.click('#asystent [data-akcja="wyslij"]'); await czekajNaPobrania(1, 40000);
  ok('„Wyślij” (bez folderu) pobiera gotową wiadomość PMT_wiadomosc_do_wyslania.eml z adresatem, tematem, treścią i paczką', pobrane.length === 1 && pobrane[0].suggestedFilename() === 'PMT_wiadomosc_do_wyslania.eml', pobrane.map(d => d.suggestedFilename()).join(','));
  await p.waitForSelector('#podp-wyslij-stan', { timeout: 20000 });
  ok('po wysyłce asystent mówi „Wysyłka przygotowana ✔” i co zrobić dalej (kliknij pobrany plik)', /Wysyłka przygotowana/.test(await tekst('#asystent .as-tytul')) && /kliknij|Kliknij/.test(await tekst('#asystent .as-stan')), (await tekst('#asystent .as-stan')).slice(0, 120));
  ok('bez błędów w konsoli', t.bledy.length === 0, JSON.stringify(t.bledy.slice(0, 3)));
  await t.zamknij(); console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.message); process.exit(2); });
