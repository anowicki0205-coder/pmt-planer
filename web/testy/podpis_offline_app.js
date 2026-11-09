// Dokumenty do podpisu — cały obieg w przeglądarce: pięć kolorowych kroków (pobierz → podpisz → wgraj → sprawdzenie → wyślij; pole przeciągania między 3 a 4), prawdziwe podpisy elektroniczne (pyHanko: PAdES, XAdES, ECDSA),
// błędne podpisy (inna osoba, zmieniony dokument, dopisek po podpisie, niepodpisany plik), podpis odręczny na sztucznych skanach (także wielostronicowy PDF ze skanem),
// ręczne potwierdzenie, wysyłka na adres z odbiorca.txt, zapis wyników sprawdzenia i praca bez internetu.
// Wymaga: poppler, unzip, ImageMagick (convert) oraz python z pyhanko, lxml, pillow, numpy (PYTHON_PODPISY=/tmp/phvenv/bin/python).
// NODE_PATH=/opt/node22/lib/node_modules node podpis_offline_app.js
const { otworz, generuj } = require('./wspolne'); const fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
(async () => {
  const PY = process.env.PYTHON_PODPISY || '/tmp/phvenv/bin/python', DANE = path.join(__dirname, 'dane');
  const OPSERW = {}; const t = await otworz({ w: 1440, h: 900, opcjeSerwera: OPSERW }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'podpis-'));
  const HASLO = 'Admin-Haslo-Paczki#2026', ADRES = 'odbiorca@example.com';
  t.backend.paczka = { haslo: HASLO, wazne_do: '2099-12-31', adres: ADRES };      // administrator ustawił hasło, termin i adres (zakładka „Ustawienia”); scenariusze „brak/po terminie” testujemy niżej
  const pobierz = async (selektor) => { const [d] = await Promise.all([p.waitForEvent('download', { timeout: 60000 }), p.click(selektor)]); const sc = path.join(tmp, Date.now() + '_' + d.suggestedFilename()); await d.saveAs(sc); return { nazwa: d.suggestedFilename(), sciezka: sc }; };
  const stany = () => p.evaluate(() => [...document.querySelectorAll('.dok-k')].map(k => (k.className.match(/st-(\w+)/) || [])[1]));
  const czekajStany = async (oczekiwane, ms = 150000) => { await p.waitForFunction(o => { const s = [...document.querySelectorAll('.dok-k')].map(k => (k.className.match(/st-(\w+)/) || [])[1]); return !s.includes('trwa') && JSON.stringify(s) === JSON.stringify(o); }, oczekiwane, { timeout: ms, polling: 250 }).catch(() => {}); return stany(); };
  const komunikat = i => p.locator(`.dok-k[data-i="${i}"] .dok-kom`).innerText();
  const py = (skrypt, ...args) => { const r = cp.spawnSync(PY, [path.join(DANE, skrypt), ...args], { encoding: 'utf8' }); if (r.status) { console.log(r.stdout, r.stderr); throw new Error(skrypt + ' nie powiódł się'); } return r.stdout; };
  const norm = x => x.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l');
  const wgraj = files => p.setInputFiles('#plik-wgraj', files);
  const zapisane = () => p.evaluate(() => { const r = Object.values(window.__pmtDane.czytaj().miesiace)[0]; return { pliki: r.podpisaniPliki || {}, pierwotne: r.pierwotneNazwy || {}, weryfikacje: r.weryfikacje || {} }; });
  const kopiaZ = (z, dokad, mapa) => { fs.mkdirSync(dokad, { recursive: true }); for (const f of fs.readdirSync(z)) fs.copyFileSync(path.join(z, f), path.join(dokad, mapa[f] || f)); return lista(dokad); };
  const lista = kat => fs.readdirSync(kat).sort().map(f => path.join(kat, f));
  const otworzSzczegoly = async i => { if (!(await p.locator(`.dok-k[data-i="${i}"].otwarta`).count())) await p.click(`.dok-k[data-i="${i}"] [data-akcja="szczegoly"]`); await p.waitForSelector(`.dok-k[data-i="${i}"].otwarta`); };
  const wgrajInny = async i => { await otworzSzczegoly(i); await p.click(`.dok-k[data-i="${i}"].otwarta [data-akcja="cofnij"]`); };

  await p.goto(t.adres + '/index.html'); await p.waitForSelector('#arkusz-tlo.otwarty', { timeout: 120000 });
  const bezpieczny = await p.evaluate(() => isSecureContext);      // HTTP_HOST=pmt.example: ten sam przebieg na zwykłym http (bez Web Crypto) — sprawdzanie podpisów działa na własnej kryptografii
  ok(bezpieczny ? 'adres bezpieczny (localhost): Web Crypto dostępne' : `zwykłe http (${t.adres}): brak Web Crypto, przebieg na własnej kryptografii`, bezpieczny === !t.host && (await p.evaluate(() => typeof crypto.subtle !== 'undefined')) === bezpieczny);
  await p.fill('#d-imie', 'Jan Testowy'); await p.fill('#d-pesel', '90010112349'); await p.fill('#d-adres', 'ul. Testowa 1, 00-001 Warszawa');
  await p.click('#zapisz-dane'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached' }); await p.waitForTimeout(3000);
  await p.fill('#kwota-in', '5000'); await p.press('#kwota-in', 'Enter'); await p.waitForTimeout(1200);
  await generuj(p); await p.waitForTimeout(3500);
  const razem = await p.locator('#fiolki .fiolka').count(); ok('wygenerowano 7 dokumentów (6 poleceń i rozliczenie)', razem === 7, String(razem));

  /* ---- okno: pięć kolorowych kroków, karty dokumentów ---- */
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka'); await p.waitForTimeout(1200);
  ok('okno ma pięć kroków: pobierz, podpisz, wgraj, sprawdzenie, wyślij (ostatni szary)', (await p.locator('.krok-k').count()) === 5 && (await p.locator('.krok-k.k5.nieaktywny').count()) === 1 && /Pobierz dokumenty/.test(await p.locator('.k1').innerText()) && /Podpisz/.test(await p.locator('.k2').innerText()) && /Wgraj podpisane/.test(await p.locator('.k3').innerText()) && /Sprawdzenie/.test(await p.locator('.k4').innerText()));
  const kolory = await p.evaluate(() => [...document.querySelectorAll('.krok-k')].map(k => getComputedStyle(k).backgroundImage));
  ok('każdy krok ma własny kolor (pięć różnych gradientów, nie płaskie tło)', new Set(kolory).size === 5 && kolory.every(k => /gradient/.test(k)));
  ok('okno nie jest czarne: tło ma kolor (fiolet/granat)', await p.evaluate(() => /rgb\(122, 70, 252|rgb\(54, 82, 238|rgb\(182, 150, 255|rgb\(130, 174, 255|rgba\(104, 78, 240|104,\s*78,\s*240/.test(getComputedStyle(document.querySelector('#arkusz')).backgroundImage)));
  ok('krok 2: elektronicznie (link do gov.pl, limit 5 plików po 25 MB, podział na 2 tury) albo odręcznie (wydruk)', (await p.locator('.k2 a[href*="gov.pl"]').count()) === 1 && /5 plików po 25 MB/.test(await p.locator('.k2').innerText()) && /w 2 turach/.test(await p.locator('.k2').innerText()) && /Wydrukuj/.test(await p.locator('.k2').innerText()));
  ok('nie ma już dawnych zakładek partii ani wyboru ścieżek', (await p.locator('.partia, .sciezka, .partie').count()) === 0);
  ok('7 kart dokumentów, wszystkie „czekają na podpis”', (await p.locator('.dok-k').count()) === 7 && (await stany()).every(s => s === 'czeka'));
  ok('na tym etapie nie ma przycisku „Wyślij”', (await p.locator('[data-akcja="wyslij"]').count()) === 0);
  await p.screenshot({ path: tmp + '/1_start.png' });

  /* ---- krok 1: pobieranie ---- */
  const zip = await pobierz('#pobierz-wsz');
  ok('„Wszystkie (ZIP)” pobiera JEDEN plik ZIP', /\.zip$/i.test(zip.nazwa), zip.nazwa);
  const roz = path.join(tmp, 'pdf'); cp.spawnSync('unzip', ['-o', '-q', '-d', roz, zip.sciezka]);
  const pdfy = fs.readdirSync(roz).filter(f => /\.pdf$/i.test(f)).sort();
  ok('ZIP zawiera wszystkie 7 dokumentów (prawdziwe PDF-y) i przechodzi test integralności', pdfy.length === 7 && pdfy.every(f => fs.readFileSync(path.join(roz, f)).subarray(0, 5).toString() === '%PDF-') && cp.spawnSync('unzip', ['-t', zip.sciezka]).status === 0);
  const pobrane = [], nasluch = d => pobrane.push(d); p.on('download', nasluch);
  await p.click('[data-akcja="osobno"]'); for (let i = 0; i < 80 && pobrane.length < 7; i++) await p.waitForTimeout(250); p.off('download', nasluch);
  ok('„Osobne pliki” pobiera 7 osobnych PDF-ów o nazwach dokumentów (bez rozpakowywania)', pobrane.length === 7 && pobrane.map(d => d.suggestedFilename()).sort().join('|') === pdfy.join('|'), pobrane.length + ' plików');
  const wydruk = await pobierz('[data-akcja="pdf-wydruk"]');
  const strony = f => Number((cp.spawnSync('pdfinfo', [f], { encoding: 'utf8' }).stdout.match(/Pages:\s+(\d+)/) || [0, 0])[1]);
  ok('wydruk (krok 2, odręcznie): jeden PDF ze stronami WSZYSTKICH dokumentów', strony(wydruk.sciezka) === pdfy.reduce((s, f) => s + strony(path.join(roz, f)), 0), wydruk.nazwa);

  /* ---- gdzie na stronie jest miejsce na podpis (zapisane przez silnik) ---- */
  const miejsca = await p.evaluate(() => { return Object.values(window.__pmtDane.czytaj().miesiace)[0].wynik.miejsca_podpisu; });
  const m0 = miejsca[Object.keys(miejsca).find(n => /^delegacja_01/.test(n))];
  ok('silnik zapisał miejsce „podpis pracownika” (mm na stronie A4) dla każdego dokumentu', Object.keys(miejsca).length === 7 && Object.entries(miejsca).filter(([n]) => /^delegacja_/.test(n)).every(([, v]) => v.miejsca.length === 1 && v.miejsca[0].x === 138 && v.miejsca[0].y > 150 && v.miejsca[0].y < 280) && m0.strony === 1, JSON.stringify(m0));
  fs.writeFileSync(path.join(tmp, 'miejsca.json'), JSON.stringify(Object.fromEntries(Object.entries(miejsca).map(([k, v]) => [norm(k), v]))));

  /* ---- krok 3 i 4, tura 1: wgranie wszystkiego naraz (dobre i złe podpisy) ---- */
  const plan1 = { [pdfy[0]]: 'jan', [pdfy[1]]: 'ecdsa', [pdfy[2]]: 'anna', [pdfy[3]]: 'zmieniony', [pdfy[4]]: 'niepodpisany', [pdfy[5]]: 'xades', [pdfy[6]]: 'dopisek' };
  fs.writeFileSync(path.join(tmp, 'plan1.json'), JSON.stringify(plan1)); py('podpisz_pliki.py', roz, path.join(tmp, 'e1'), path.join(tmp, 'plan1.json'));
  // pliki wracają z gov.pl pod przypadkowymi nazwami: program ma rozpoznać dokument (po zawartości, a plik .xades po skrócie) i nazwać plik tak, jak go wygenerował
  const dziwne = { [pdfy[0]]: 'Podpisany dokument (1).pdf', [pdfy[1]]: 'zalacznik_nr_2_signed.pdf', [pdfy[5] + '.xades']: 'podpis_xml_numer_6.xades' };
  await p.evaluate(() => { window.__nowyZle = new Set(); window.__nowyAnim = ''; new MutationObserver(() => { document.querySelectorAll('.dok-k.nowy.st-zle').forEach(k => window.__nowyZle.add(Number(k.dataset.i))); }).observe(document.body, { subtree: true, childList: true, attributes: true }); });
  await wgraj(kopiaZ(path.join(tmp, 'e1'), path.join(tmp, 'e1o'), dziwne).reverse());      // odwrócona kolejność: dopasowanie ma iść po zawartości i nazwie, nie po kolejności
  const s1 = await czekajStany(['ok', 'ok', 'zle', 'zle', 'czeka', 'ok', 'zle']);
  ok('tura 1: Jan (PAdES) ✓, Jan (ECDSA) ✓, inna osoba ✗, zmieniony ✗, niepodpisany plik odrzucony, XAdES ✓, dopisek po podpisie ✗', JSON.stringify(s1) === '["ok","ok","zle","zle","czeka","ok","zle"]', JSON.stringify(s1));
  const nowyZle = await p.evaluate(() => [...window.__nowyZle].sort());
  ok('efekt zmiany stanu na liście: karty, które PRZED CHWILĄ zmieniły stan na „zły” (2, 3, 6), dostały znacznik „nowy” (drżenie); pozostałe nie', JSON.stringify(nowyZle) === '[2,3,6]', JSON.stringify(nowyZle));
  await p.click('[data-akcja="widok"][data-w="3d"]'); await p.waitForSelector('#k3-scena');
  const k3 = await p.evaluate(() => [...document.querySelectorAll('.karta3d')].map(k => ({ i: Number(k.dataset.i), st: (k.className.match(/k3-(czeka|trwa|ok|uwaga|zle)/) || [])[1], podpis: !!k.querySelector('.da-ok .da-podpis, .da-papier.da-ok .da-podpis') })).sort((x, y) => x.i - y.i));
  ok('widok 3D: karty mają te same stany i kolory co lista (zielona = podpis poprawny, czerwona = zły, indygo = czeka), a atrapa dokumentu poprawnie podpisanego pokazuje podpis', JSON.stringify(k3.map(k => k.st)) === JSON.stringify(s1) && k3.filter(k => k.st === 'ok').every(k => k.podpis) && k3.filter(k => k.st !== 'ok').every(k => !k.podpis) && (await p.locator('.k3-kropka.k3-ok').count()) === 3 && (await p.locator('.k3-kropka.k3-zle').count()) === 3, JSON.stringify(k3.map(k => k.st)));
  await p.click('[data-akcja="widok"][data-w="lista"]'); await p.waitForSelector('.dok-k');
  const zap1 = await zapisane();
  ok('nazwy: pliki o przypadkowych nazwach zapisane pod nazwami wygenerowanymi przy tworzeniu dokumentów (PDF, PDF.xades)', zap1.pliki[0][0] === pdfy[0] && zap1.pliki[1][0] === pdfy[1] && zap1.pliki[2][0] === pdfy[2] && zap1.pliki[5][0] === pdfy[5] + '.xades' && zap1.pliki[6][0] === pdfy[6], JSON.stringify(zap1.pliki).slice(0, 300));
  ok('nazwy: program pamięta, jak plik wrócił (pierwotna nazwa) — do informacji w sprawdzeniu', zap1.pierwotne[0][pdfy[0]] === 'Podpisany dokument (1).pdf' && zap1.pierwotne[5][pdfy[5] + '.xades'] === 'podpis_xml_numer_6.xades', JSON.stringify(zap1.pierwotne[0]));
  ok('nazwy: kontrola „nazwa” w wynikach — zmieniona nazwa opisana, zgodna nazwa potwierdzona', zap1.weryfikacje[0].kontrole.some(c => c.id === 'nazwa' && /wrócił jako „Podpisany dokument \(1\)\.pdf”/.test(c.tekst) && c.tekst.includes(pdfy[0])) && zap1.weryfikacje[2].kontrole.some(c => c.id === 'nazwa' && c.stan === 'ok' && /zgadza się/.test(c.tekst)), JSON.stringify(zap1.weryfikacje[0].kontrole.filter(c => c.id === 'nazwa')));
  ok('nazwy: lista dopasowań pokazuje „→ nowa nazwa” przy zmienionych plikach', (await p.locator('.wynik .nowa-nazwa').count()) === 3, String(await p.locator('.wynik .nowa-nazwa').count()));
  ok('poprawne podpisy: „Podpisał(a): Jan Testowy” z godziną podpisu', /Podpisał\(a\): Jan Testowy · \d\d\.\d\d\.\d{4} \d\d:\d\d/.test(await komunikat(0)) && /Podpisał\(a\): Jan Testowy/.test(await komunikat(1)) && /Podpisał\(a\): Jan Testowy/.test(await komunikat(5)), await komunikat(0));
  ok('podpis innej osoby: komunikat z nazwiskiem podpisującej', /Podpisała inna osoba: Anna Kowalska \(na dokumencie: Jan Testowy\)/.test(await komunikat(2)), await komunikat(2));
  ok('dokument zmieniony po podpisaniu: wykryty', /zmieniony po podpisaniu/.test(await komunikat(3)), await komunikat(3));
  ok('dopisek po podpisie: wykryty (podpis nie obejmuje całości)', /nie obejmuje całego dokumentu/.test(await komunikat(6)), await komunikat(6));
  ok('niepodpisany PDF: odrzucony z wyjaśnieniem pod krokami, dokument nadal czeka', (await p.locator('#podp-odrzucone .wynik.zle').count()) === 1 && /nie ma podpisu elektronicznego/.test(await p.locator('#podp-odrzucone').innerText()));
  ok('liczniki: w kroku 4 „3 z 7”, w kaflu dokumentów 3 podpisane, brak przycisku „Wyślij”', /3 z 7/.test(await p.locator('#podp-licznik').innerText()) && /3 z 7/.test(await p.locator('#k3-ile').innerText()) && (await p.locator('[data-akcja="wyslij"]').count()) === 0);
  await otworzSzczegoly(2);
  const szcz = await p.locator('.dok-k.otwarta .kontrole').innerText();
  ok('szczegóły błędnego podpisu: lista kontroli (jest podpis, całość, ten sam dokument, nie zmieniony, matematyka, KTO podpisał)', /Jest podpis elektroniczny/.test(szcz) && /obejmuje cały dokument/.test(szcz) && /nie został zmieniony/.test(szcz) && /matematycznie poprawny/.test(szcz) && /Podpisała inna osoba/.test(szcz), szcz.replace(/\n/g, ' | ').slice(0, 220));
  ok('podpisu innej osoby NIE da się potwierdzić ręcznie (trzeba podpisać ponownie)', (await p.locator('.dok-k.otwarta [data-akcja="potwierdz"]').count()) === 0 && (await p.locator('.dok-k.otwarta [data-akcja="cofnij"]').count()) === 1);
  await p.screenshot({ path: tmp + '/2_tura1.png' });
  // ponownie podpisany dokument wgrany BEZ „Wgraj inny plik” (przeglądarka dopisała „(1)” do nazwy): zastępuje błędny podpis — sprawdzany jest nowy plik, a w paczce nie ma dwóch wersji
  const tylko3 = path.join(tmp, 'tylko3'); fs.mkdirSync(tylko3, { recursive: true }); fs.copyFileSync(path.join(roz, pdfy[2]), path.join(tylko3, pdfy[2]));
  fs.writeFileSync(path.join(tmp, 'plan1b.json'), JSON.stringify({ [pdfy[2]]: 'jan' })); py('podpisz_pliki.py', tylko3, path.join(tmp, 'e1b'), path.join(tmp, 'plan1b.json'));
  const ponowny = pdfy[2].replace(/\.pdf$/i, ' (1).pdf');
  await wgraj(kopiaZ(path.join(tmp, 'e1b'), path.join(tmp, 'e1bo'), { [pdfy[2]]: ponowny }));
  const s1b = await czekajStany(['ok', 'ok', 'ok', 'zle', 'czeka', 'ok', 'zle']), zap1b = await zapisane();
  ok('ponownie podpisany dokument wgrany bez „Wgraj inny plik”: zastępuje błędny podpis (sprawdzony nowy plik, zapisany tylko on)', JSON.stringify(s1b) === '["ok","ok","ok","zle","czeka","ok","zle"]' && JSON.stringify(zap1b.pliki[2]) === JSON.stringify([pdfy[2]]) && JSON.stringify(Object.values(zap1b.pierwotne[2])) === JSON.stringify([ponowny]), JSON.stringify([s1b, zap1b.pliki[2], zap1b.pierwotne[2]]));
  // upuszczony folder i plik, którego przeglądarka nie odczyta: nie przerywają przyjmowania, każdy trafia na listę odrzuconych z podpowiedzią
  await p.evaluate(() => {
    const folder = new File([], 'Podpisane'), zly = new File([new Uint8Array(10)], 'nieczytelny.pdf');
    zly.arrayBuffer = () => Promise.reject(new DOMException('A requested file or directory could not be found', 'NotFoundError'));
    const e = new Event('drop', { bubbles: true, cancelable: true }); Object.defineProperty(e, 'dataTransfer', { value: { files: [folder, zly] } });
    document.querySelector('.podp-strefa').dispatchEvent(e);
  });
  await p.waitForFunction(() => /nieczytelny\.pdf/.test(document.querySelector('#podp-odrzucone').textContent), null, { timeout: 20000 }).catch(() => {});
  const odrz = await p.locator('#podp-odrzucone').innerText();
  ok('upuszczony folder i nieczytelny plik: oba na liście odrzuconych („otwórz go i wgraj pliki z jego środka”), stany dokumentów bez zmian', /Podpisane/.test(odrz) && /nieczytelny\.pdf/.test(odrz) && (odrz.match(/otwórz go i wgraj pliki z jego środka/g) || []).length === 2 && JSON.stringify(await stany()) === JSON.stringify(s1b), odrz);

  /* ---- tura 2: podpis odręczny — wielostronicowy PDF ze skanem rozdzielony na dokumenty; ręczne potwierdzenie; ponowne podpisanie ---- */
  await wgrajInny(2); await czekajStany(['ok', 'ok', 'czeka', 'zle', 'czeka', 'ok', 'zle']);
  await wgrajInny(3);
  ok('„Wgraj inny plik” zdejmuje błędny podpis i dokument znowu czeka', JSON.stringify(await czekajStany(['ok', 'ok', 'czeka', 'czeka', 'czeka', 'ok', 'zle'])) === '["ok","ok","czeka","czeka","czeka","ok","zle"]');
  const planSkany = Object.fromEntries(pdfy.map(f => [f, 'pominiety'])); planSkany[pdfy[2]] = 'z'; planSkany[pdfy[3]] = 'z'; planSkany[pdfy[4]] = 'z';
  fs.writeFileSync(path.join(tmp, 'plan2.json'), JSON.stringify(planSkany)); py('skanuj_pliki.py', roz, path.join(tmp, 'miejsca.json'), path.join(tmp, 's2'), path.join(tmp, 'plan2.json'));
  const bezPodp = Object.fromEntries(pdfy.map(f => [f, 'pominiety'])); bezPodp[pdfy[4]] = 'bez';
  fs.writeFileSync(path.join(tmp, 'plan3.json'), JSON.stringify(bezPodp)); py('skanuj_pliki.py', roz, path.join(tmp, 'miejsca.json'), path.join(tmp, 's3'), path.join(tmp, 'plan3.json'));
  const skany = lista(path.join(tmp, 's2')), dwuStronicowy = path.join(tmp, 'skan_dwustronicowy.pdf');
  cp.spawnSync('convert', [skany[0], skany[1], dwuStronicowy]);      // jak z aplikacji skanującej: jeden PDF, strona 1 = Polecenie 3, strona 2 = Polecenie 4
  ok('przygotowano wielostronicowy PDF ze skanem (2 strony)', strony(dwuStronicowy) === 2);
  await wgraj([dwuStronicowy]);
  const s2 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'czeka', 'ok', 'zle']);
  ok('PDF ze skanem rozdzielony na strony i przypisany po kolei do dwóch wolnych dokumentów; podpis odręczny rozpoznany na obu', JSON.stringify(s2) === '["ok","ok","ok","ok","czeka","ok","zle"]' && /Widzę podpis w miejscu „podpis pracownika”/.test(await komunikat(2)) && /Widzę podpis/.test(await komunikat(3)), JSON.stringify(s2) + ' ' + await komunikat(2));
  ok('przypisanie według kolejności jest oznaczone „sprawdź” (lista dopasowania rozwinięta)', (await p.locator('#podp-wyniki details[open]').count()) === 1 && /według kolejności/.test(await p.locator('#podp-wyniki').innerText()));
  await otworzSzczegoly(2); await p.waitForSelector('.dok-k.otwarta .podglad-podpisu img');
  const pod = await p.evaluate(() => { const i = document.querySelector('.dok-k.otwarta .podglad-podpisu img'); return { w: i.naturalWidth, h: i.naturalHeight, kontrole: document.querySelector('.dok-k.otwarta .kontrole').innerText }; });
  ok('szczegóły podpisu odręcznego: wycinek skanu z miejscem podpisu do obejrzenia + informacja, że imienia odręcznie nie odczytam', pod.w >= 400 && pod.h > 60 && /Odręcznego podpisu nie umiem odczytać/.test(pod.kontrole), `${pod.w}×${pod.h}`);
  await p.screenshot({ path: tmp + '/3_skan.png' });
  await p.click('.dok-k.otwarta [data-akcja="szczegoly"]');
  // dokument 5 (indeks 4): skan BEZ podpisu → błąd → ręczne potwierdzenie → wgranie skanu z podpisem
  await wgraj(lista(path.join(tmp, 's3')));
  ok('skan bez podpisu: „Nie widzę podpisu w miejscu podpis pracownika”', JSON.stringify(await czekajStany(['ok', 'ok', 'ok', 'ok', 'zle', 'ok', 'zle'])) === '["ok","ok","ok","ok","zle","ok","zle"]' && /Nie widzę podpisu/.test(await komunikat(4)), await komunikat(4));
  await otworzSzczegoly(4); await p.waitForSelector('.dok-k.otwarta [data-akcja="potwierdz"]');
  ok('przy podpisie odręcznym jest „Potwierdzam, że podpis jest” (program mógł się pomylić)', (await p.locator('.dok-k.otwarta [data-akcja="potwierdz"]').count()) === 1);
  await p.click('.dok-k.otwarta [data-akcja="potwierdz"]'); await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'zle']);
  ok('po ręcznym potwierdzeniu dokument liczy się jako podpisany („potwierdzony przez Ciebie”)', /potwierdzony przez Ciebie/.test(await komunikat(4)) && /6 z 7/.test(await p.locator('#podp-licznik').innerText()), await komunikat(4));
  await wgrajInny(4); await czekajStany(['ok', 'ok', 'ok', 'ok', 'czeka', 'ok', 'zle']);
  await wgraj([lista(path.join(tmp, 's2'))[2]]);
  ok('wgranie skanu Z podpisem w to samo miejsce: rozpoznany automatycznie (bez potwierdzania)', JSON.stringify(await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'zle'])) === '["ok","ok","ok","ok","ok","ok","zle"]' && /Widzę podpis/.test(await komunikat(4)));
  // ponowny skan po „Nie widzę podpisu” wgrany od razu (bez „Wgraj inny plik”, pod inną nazwą): zastępuje stary skan, a nie staje się drugą stroną dokumentu
  await wgrajInny(4); await czekajStany(['ok', 'ok', 'ok', 'ok', 'czeka', 'ok', 'zle']);
  await wgraj(lista(path.join(tmp, 's3'))); await czekajStany(['ok', 'ok', 'ok', 'ok', 'zle', 'ok', 'zle']);
  const ponSkan = path.join(tmp, 'ponowny_skan'); fs.mkdirSync(ponSkan, { recursive: true }); fs.copyFileSync(lista(path.join(tmp, 's2'))[2], path.join(ponSkan, pdfy[4].replace(/\.pdf$/i, '_ponownie.jpg')));
  await wgraj(lista(ponSkan));
  const s3b = await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'zle']), zap3b = await zapisane();
  ok('ponowny skan po „Nie widzę podpisu” (bez „Wgraj inny plik”) zastępuje stary skan zamiast dokładać kolejną stronę', JSON.stringify(s3b) === '["ok","ok","ok","ok","ok","ok","zle"]' && zap3b.pliki[4].length === 1 && /Widzę podpis/.test(await komunikat(4)), JSON.stringify([s3b, zap3b.pliki[4]]));
  // rozliczenie wydatków (dokument 7, indeks 6): podpis odręczny NIE jest tam wymagany — skan bez podpisu pod tabelą nie świeci się na czerwono (na poleceniach — jak wyżej — dalej tak)
  { const p7 = {}; pdfy.forEach(f => { p7[f] = 'pominiety'; }); p7[pdfy[6]] = 'bez'; fs.writeFileSync(path.join(tmp, 'plan7.json'), JSON.stringify(p7)); py('skanuj_pliki.py', roz, path.join(tmp, 'miejsca.json'), path.join(tmp, 's7'), path.join(tmp, 'plan7.json'));
    await wgrajInny(6); await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'czeka']);
    await wgraj(lista(path.join(tmp, 's7'))); const s7 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok']);
    ok('rozliczenie wydatków: skan BEZ podpisu odręcznego jest przyjęty (stan poprawny, nie czerwony), a komunikat mówi, że podpis nie jest tam wymagany', JSON.stringify(s7) === '["ok","ok","ok","ok","ok","ok","ok"]' && /nie jest na nim wymagany/.test(await komunikat(6)) && !/Nie widzę podpisu/.test(await komunikat(6)), await komunikat(6));
    await otworzSzczegoly(6);
    const sz7 = await p.evaluate(() => ({ kontrole: document.querySelector('.dok-k.otwarta .kontrole').innerText, podglad: !!document.querySelector('.dok-k.otwarta .podglad-podpisu'), przycisk: !!document.querySelector('.dok-k.otwarta [data-akcja="potwierdz"]') }));
    ok('szczegóły rozliczenia: „nie wymaga podpisu odręcznego”, bez wycinka „miejsce podpisu” i bez przycisku „Potwierdzam, że podpis jest”', /nie wymaga podpisu odręcznego/.test(sz7.kontrole) && !/porównaj sam/.test(sz7.kontrole) && !sz7.podglad && !sz7.przycisk, JSON.stringify(sz7).slice(0, 300));
    await p.click('.dok-k.otwarta [data-akcja="szczegoly"]'); }
  // dokument 7 (indeks 6): poprawny podpis zamiast dopisku
  const wejscie4 = path.join(tmp, 'tylko7'); fs.mkdirSync(wejscie4, { recursive: true }); fs.copyFileSync(path.join(roz, pdfy[6]), path.join(wejscie4, pdfy[6]));
  fs.writeFileSync(path.join(tmp, 'plan4.json'), JSON.stringify({ [pdfy[6]]: 'jan' })); py('podpisz_pliki.py', wejscie4, path.join(tmp, 'e4'), path.join(tmp, 'plan4.json'));
  await wgrajInny(6); await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'czeka']);
  await p.click('[data-akcja="widok"][data-w="3d"]'); await p.waitForSelector('#k3-scena');
  await p.evaluate(() => { window.__nowe = new Set(); window.__anim = ''; new MutationObserver(() => { document.querySelectorAll('.karta3d.k3-nowy.k3-ok').forEach(k => { window.__nowe.add(Number(k.dataset.i)); const sc = k.querySelector('.da-podpis path'); if (sc) window.__anim = getComputedStyle(sc).animationName; }); }).observe(document.body, { subtree: true, childList: true, attributes: true }); });
  await wgraj(kopiaZ(path.join(tmp, 'e4'), path.join(tmp, 'e4o'), { [pdfy[6]]: pdfy[0] }));      // podpisany dokument 7 wraca pod nazwą dokumentu 1 — ma zostać rozpoznany po zawartości
  await p.waitForSelector('.karta3d[data-i="6"].k3-ok', { timeout: 150000 }); await p.waitForTimeout(400);
  const efekt = await p.evaluate(() => ({ nowe: [...window.__nowe], anim: window.__anim }));
  ok('widok 3D: karta, której stan zmienił się na „poprawny” (7), dostaje efekt (podpis „rysuje się”, błysk) — tylko ona; przy włączonym „życiu” animacja zycie-kresl (mimo trybu spokojnego), bez niego brak ruchu', JSON.stringify(efekt.nowe) === '[6]' && efekt.anim === (process.env.ZYCIE === 'tak' ? 'zycie-kresl' : 'none'), JSON.stringify(efekt));
  await p.click('[data-akcja="widok"][data-w="lista"]'); await p.waitForSelector('.dok-k');
  const s4 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok']);
  const zap4 = await zapisane();
  ok('nazwy: plik o nazwie INNEGO dokumentu rozpoznany po zawartości i nazwany jak dokument 7; ostrzeżenie w sprawdzeniu', zap4.pliki[6][0] === pdfy[6] && zap4.pliki[0][0] === pdfy[0] && zap4.weryfikacje[6].kontrole.some(c => c.id === 'nazwa' && /to nazwa innego dokumentu \(Polecenie 1\)/.test(c.tekst)), JSON.stringify(zap4.weryfikacje[6].kontrole.filter(c => c.id === 'nazwa')));
  ok('nazwy: skany zapisane jako nazwa dokumentu + .jpg (np. „…03….jpg”), nie „_skan” i nie „IMG_”', [2, 3, 4].every(i => zap4.pliki[i].length === 1 && zap4.pliki[i][0] === pdfy[i].replace(/\.pdf$/i, '.jpg')), JSON.stringify([2, 3, 4].map(i => zap4.pliki[i])));
  ok('wszystkie 7 dokumentów podpisane i sprawdzone (e-podpis PAdES/ECDSA/XAdES i odręczny)', JSON.stringify(s4) === JSON.stringify(Array(7).fill('ok')) && /Wszystkie 7 dokumentów sprawdzone/.test(await p.locator('#podp-licznik').innerText()), JSON.stringify(s4));
  { const dz = await p.evaluate(() => ({ ...window.__pmtDzwiek.licznik })); ok('dźwięki przy podpisach: każdy sprawdzony dokument gra „ok”, a ostatni (wszystkie poprawne) gra dłuższy akord „wszystkie” — raz', (dz.ok || 0) >= 1 && dz.wszystkie === 1, JSON.stringify(dz)); }
  ok('po sprawdzeniu wszystkiego krok 5 „Wyślij” zapala się: przestaje być szary, przycisk jest aktywny i ma akcję', await p.evaluate(() => { const k = document.querySelector('.krok-k.k5'), b = k.querySelector('button'); return k.classList.contains('aktywny') && !k.classList.contains('nieaktywny') && !b.disabled && b.dataset.akcja === 'wyslij' && /Wszystkie dokumenty sprawdzone/.test(k.querySelector('small').innerText); }));
  ok('po sprawdzeniu wszystkiego przycisk „Wyślij” jest w oknie i na kaflu, status „Podpisane”', (await p.locator('[data-akcja="wyslij"]').count()) >= 1 && /Wyślij/.test(await p.locator('#kropla-napis').innerText()) && (await p.locator('#status').innerText()).includes('Podpisane'));
  await p.screenshot({ path: tmp + '/4_wszystko.png' });

  /* ---- wysyłka: moduł w kroku 5 TEGO SAMEGO okna; hasło do paczki, termin jego ważności i adres odbiorcy nadaje administrator (zakładka „Ustawienia” w arkuszu) ---- */
  const PYZ = process.env.PYZ_PYTHON || ['/tmp/pzvenv/bin/python', 'python3'].find(b => cp.spawnSync(b, ['-c', 'import zipfile']).status === 0);
  const stanW = () => p.locator('#podp-wyslij-stan').innerText();
  const bezAdresu = async () => { const t = await p.evaluate(() => document.documentElement.outerHTML + '\n' + document.body.innerText + '\n' + [...document.querySelectorAll('[title],[aria-label],[href],[value]')].map(e => ['title', 'aria-label', 'href', 'value'].map(a => e.getAttribute(a) || '').join(' ')).join(' ')); return !/odbiorca@|example\.com/i.test(t); };      // adres odbiorcy zna tylko administrator: nie ma go ani w tekście, ani w HTML, ani w odnośnikach okna
  const opisK5 = () => p.locator('#podp-wyslij-opis').innerText();
  const przycisk5 = () => p.locator('#podp-wyslij-akcje button');
  const wyslijSel = '#arkusz .krok-k.k5 [data-akcja="wyslij"]';
  const ponownieOtworz = async () => { await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); await p.click('#podpisz'); await p.waitForSelector('#dok-siatka', { timeout: 20000 }); await p.waitForTimeout(900); };
  const emlOtwarty = (plik) => JSON.parse(cp.spawnSync(PYZ, ['-I', '-c', `
import sys, json, email, email.policy, io, os, zipfile
raw = open(sys.argv[1], 'rb').read(); m = email.message_from_bytes(raw, policy=email.policy.default)
cz = list(m.iter_attachments()); z = zipfile.ZipFile(io.BytesIO(cz[0].get_content())); z.setpassword(sys.argv[2].encode())
tr = m.get_body(preferencelist=('plain',)).get_content()
os.makedirs(sys.argv[3], exist_ok=True); z.extractall(sys.argv[3])
print(json.dumps({'x': m['X-Unsent'], 'to': m['To'], 'temat': str(m['Subject']), 'tresc': tr, 'zal': len(cz), 'nazwa': cz[0].get_filename(), 'pliki': z.namelist(), 'ascii': all(b < 128 for b in raw), 'jawne': any(s in raw for s in (b'Jan Testowy', b'90010112349', b'Admin-Haslo'))}))`, plik, HASLO, path.join(tmp, 'z' + Date.now())], { encoding: 'utf8' }).stdout);

  /* [A] administrator niczego nie ustawił → przycisk od razu szary, jasny powód */
  t.backend.paczka = null; await ponownieOtworz();
  ok('administrator niczego nie ustawił w zakładce „Ustawienia” → krok 5 od razu mówi, że wysyłka nie jest włączona, a przycisk jest szary (bez klikania w próżnię)', /nie jest jeszcze włączona/.test(await opisK5()) && (await przycisk5().isDisabled()) && (await p.locator(wyslijSel).count()) === 0, await opisK5());
  /* [B] hasło po terminie ważności */
  t.backend.paczka = { haslo: HASLO, wazne_do: '2020-01-01', adres: ADRES }; await ponownieOtworz();
  ok('hasło po terminie ważności → „wygasło 01.01.2020, poczekaj na nowe od administratora”, przycisk szary; serwer hasła nie wydał, więc nie ma go w stronie ani w zapisanych danych', /wygasło 01\.01\.2020/.test(await opisK5()) && (await przycisk5().isDisabled()) && !(await p.evaluate(h => document.documentElement.outerHTML.includes(h) || JSON.stringify(window.__pmtDane.czytaj()).includes(h), HASLO)));
  /* [C] brak adresu odbiorcy */
  t.backend.paczka = { haslo: HASLO, wazne_do: '2099-12-31', adres: '' }; await ponownieOtworz();
  ok('brak adresu odbiorcy w arkuszu → wysyłka wyłączona (adres, tak jak hasło, wskazuje administrator)', /nie jest jeszcze włączona/.test(await opisK5()) && (await przycisk5().isDisabled()));
  /* [D] hasło za krótkie → komunikat po kliknięciu */
  t.backend.paczka = { haslo: 'krotkie', wazne_do: '2099-12-31', adres: ADRES }; await ponownieOtworz();
  await p.click(wyslijSel); await p.waitForFunction(() => /za krótkie/.test(document.querySelector('#podp-wyslij-stan').textContent), null, { timeout: 30000 });
  ok('hasło ustawione przez administratora poniżej 8 znaków jest odrzucane z komunikatem (paczka nie powstaje, status „wysłane” się nie ustawia)', /minimum 8 znaków/.test(await stanW()) && !(await p.locator('#status').innerText()).includes('Wysłane'));
  /* [E] wszystko poprawnie → jedno kliknięcie */
  t.backend.paczka = { haslo: HASLO, wazne_do: '2099-12-31', adres: ADRES }; await ponownieOtworz();
  ok('obok „Wyślij” widać, którym sposobem pójdzie wiadomość („Sposób: plik wiadomości .eml”) — żeby nikt nie wysłał przez „samo otwarcie poczty” (bez załącznika) nieświadomie', /^Sposób: plik wiadomości \.eml$/.test(await p.locator('.wyslij-sposob').innerText()) && (await p.locator('.wyslij-sposob').count()) === 1, await p.locator('.wyslij-sposob').innerText());
  ok('„Wyślij” jest krokiem 5 w tym samym oknie co pobieranie, podpis i wgrywanie; NIE pokazuje adresu odbiorcy (zna go tylko administrator); nie ma żadnych dodatkowych opcji ani przycisków wysyłki', (await p.locator(wyslijSel).count()) === 1 && /Wyślij” zrobi z nich zahasłowaną paczkę/.test(await opisK5()) && (await bezAdresu()) && (await p.locator('#arkusz #w-mailto, #arkusz #w-udostepnij, #arkusz #w-eml, #arkusz #w-haslo, #arkusz #w-odb, #arkusz #w-oznacz, #arkusz input[type=password]').count()) === 0 && !/Otwórz pocztę|dołączę sam|Udostępnij pliki|Kierownik regionu|Oznacz jako wysłane/.test(await p.locator('#arkusz').innerText()));
  ok('przed wysłaniem karty dokumentów mają przyciski „Otwórz”, a nie informację „Wysłano”', (await p.locator('.dok-k .dok-akcje [data-akcja="otworz"]').count()) >= 7 && (await p.locator('.dok-k .dok-wyslano').count()) === 0);
  await p.screenshot({ path: tmp + '/5_wyslij.png' });
  const pob0 = t.backend.pobraniaHasla;
  const emlP = await pobierz(wyslijSel);
  const emlWynik0Ok = () => emlOtwarty(emlP.sciezka).to === ADRES;
  ok('jedno kliknięcie „Wyślij” pobiera gotową wiadomość .eml; hasło pobrano z serwera, a użytkownik go nigdzie nie widzi', emlP.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && /Kliknij ją/.test(await stanW()) && !(await p.evaluate(h => document.body.innerText.includes(h), HASLO)));
  { const t0 = Date.now(); while (t.backend.pobraniaHasla <= pob0 && Date.now() - t0 < 8000) await p.waitForTimeout(100); }
  ok('hasło, adres i termin były już pobrane przy otwarciu kroku 5 (kliknięcie nie czeka na serwer), a po wysyłce serwer jest pytany jeszcze raz w tle, czy administrator niczego nie zmienił; użytkownik hasła nigdzie nie widzi', t.backend.pobraniaHasla > pob0 && !(await p.evaluate(h => document.body.innerText.includes(h), HASLO)), `pobrania: ${pob0} → ${t.backend.pobraniaHasla}`);
  ok('po pierwszym pobraniu .eml jednorazowa wskazówka: 3 kroki (ikona pobierania → prawy przycisk na pliku → „Zawsze otwieraj pliki tego typu”), makieta menu z zaznaczoną opcją, rada dla poczty w przeglądarce i przycisk „Zrobione”', (await p.locator('#podp-wyslij-stan #eml-rada').count()) === 1 && (await p.locator('#eml-rada .eml-kroki > span').count()) === 3 && /„Zawsze otwieraj pliki tego typu”/.test(await stanW()) && /Zawsze otwieraj pliki tego typu/.test(await p.locator('#eml-rada .em-wyb').innerText()) && /Gmail/.test(await stanW()) && (await p.locator('#eml-rada [data-akcja="eml-rada-ok"]').count()) === 1, await stanW());
  await p.locator('#eml-rada').scrollIntoViewIfNeeded(); await p.screenshot({ path: tmp + '/5b_rada_eml.png' });
  await p.click('#eml-rada [data-akcja="eml-rada-ok"]'); await p.waitForTimeout(200);
  ok('„Zrobione” chowa wskazówkę na stałe (zapamiętane na urządzeniu) i potwierdza, że przy włączonej opcji wiadomość będzie się od teraz otwierać sama', (await p.locator('#eml-rada').count()) === 0 && /będzie się od teraz otwierać sama/.test(await stanW()) && (await p.evaluate(() => localStorage.getItem('pmt-ui-eml-auto'))) === '1');
  await p.waitForTimeout(500);
  ok('po wysłaniu plikiem .eml adresu odbiorcy nie ma w oknie (ani w komunikacie, ani w kodzie strony) — jest tylko w polu „Do” samej wiadomości', (await bezAdresu()) && emlWynik0Ok(), await stanW());
  ok('wysyłka gra „wyslano” (jeden raz na wysyłkę)', (await p.evaluate(() => window.__pmtDzwiek.licznik)).wyslano === 1, JSON.stringify(await p.evaluate(() => window.__pmtDzwiek.licznik)));
  ok('status „Wysłane” ustawia się SAM (bez dodatkowego przycisku): kafel pulpitu, krok 5 („Dokumenty wysłane …”, przycisk „Wysłano” szary)', (await p.locator('#status').innerText()).includes('Wysłane') && /Dokumenty wysłane \d\d\.\d\d\.\d{4} \d\d:\d\d/.test(await opisK5()) && (await przycisk5().isDisabled()) && /Wysłano/.test(await przycisk5().innerText()) && (await p.locator('#w-oznacz').count()) === 0);
  ok('„chmurki” dokumentów pokazują „Wysłano” z datą zamiast przycisku „Otwórz” (zostają „Szczegóły”)', (await p.locator('.dok-k.wyslano').count()) === 7 && (await p.locator('.dok-k .dok-wyslano').count()) === 7 && /Wysłano \d\d\.\d\d\.\d{4}/.test(await p.locator('.dok-k .dok-wyslano >> nth=0').innerText()) && (await p.locator('.dok-k .dok-akcje [data-akcja="otworz"]').count()) === 0 && (await p.locator('.dok-k .dok-akcje [data-akcja="szczegoly"]').count()) === 7 && /wysłano/.test(await p.locator('.dok-k .stan >> nth=0').innerText()));
  await p.screenshot({ path: tmp + '/6_po_wyslaniu.png' });
  await p.click('[data-akcja="widok"][data-w="3d"]'); await p.waitForSelector('#k3-scena');
  ok('widok 3D po wysłaniu: wszystkie 7 kart „Wysłano” z pieczęcią na atrapie, bez przycisku „Otwórz” (zostaje „Powiększ”)', (await p.locator('.karta3d.wyslano').count()) === 7 && (await p.locator('.karta3d .da-wyslano, .karta3d.wyslano .da-papier.da-wyslano').count()) >= 7 && (await p.locator('.karta3d .dok-wyslano').count()) === 7 && (await p.locator('.karta3d [data-akcja="otworz"]').count()) === 0 && (await p.locator('.karta3d [data-akcja="powieksz"]').count()) === 7);
  await p.screenshot({ path: tmp + '/6b_po_wyslaniu_3d.png' });
  await p.click('[data-akcja="widok"][data-w="lista"]'); await p.waitForSelector('.dok-k');
  ok('hasło jest zapamiętane tylko w zaszyfrowanym koncie (z adresem i terminem, do wysyłki bez internetu), nie w tekście strony', await p.evaluate(([h, a]) => { const c = window.__pmtDane.czytaj().ustawienia.paczka; return c && c.haslo === h && c.adres === a && c.wazne_do === '2099-12-31'; }, [HASLO, ADRES]));
  const emlWynik = emlOtwarty(emlP.sciezka);
  ok('wiadomość: adresat z arkusza, temat „[PMT] Delegacje — Jan Testowy — …”, nagłówek X-Unsent, dokładnie jeden załącznik ZIP', emlWynik.x === '1' && emlWynik.to === ADRES && /^\[PMT\] Delegacje — Jan Testowy — \S+ 20\d\d$/.test(emlWynik.temat) && emlWynik.zal === 1 && /^Dokumenty_Jan_Testowy_.*\.zip$/.test(emlWynik.nazwa), JSON.stringify([emlWynik.x, emlWynik.to, emlWynik.temat, emlWynik.zal, emlWynik.nazwa]));
  ok('treść jest krótka, mówi o zahasłowanej paczce, liczbie plików i że hasło przekazano osobno; podpisana imieniem; bez hasła i PESEL-u', /zahasłowana paczka \(ZIP\)/.test(emlWynik.tresc) && /\(\d+ pl\S+\)/.test(emlWynik.tresc) && /przekazane osobno/.test(emlWynik.tresc) && /Jan Testowy\s*$/.test(emlWynik.tresc) && !emlWynik.tresc.includes(HASLO) && !/\d{11}/.test(emlWynik.tresc), JSON.stringify(emlWynik.tresc).slice(0, 140));
  ok('plik .eml jest czystym ASCII i nie zawiera jawnie imienia z dokumentów, PESEL-u ani hasła', emlWynik.ascii && !emlWynik.jawne);
  const wyslane = emlWynik.pliki;
  ok('paczka z wiadomości odszyfrowuje się hasłem administratora; każdy plik ma nazwę nadaną przy generowaniu (PDF-y, .pdf.xades razem z oryginałem, skany jako nazwa dokumentu + .jpg)', wyslane.length >= 7 && wyslane.filter(n => /\.pdf$/i.test(n)).length >= 4 && wyslane.includes(pdfy[5] + '.xades') && wyslane.includes(pdfy[5]) && [2, 3, 4].every(i => wyslane.includes(pdfy[i].replace(/\.pdf$/i, '.jpg'))) && wyslane.every(n => pdfy.some(f => n === f || n === f + '.xades' || n === f.replace(/\.pdf$/i, '.jpg'))) && !wyslane.some(n => /_skan|IMG_|_signed|podpisany|zalacznik|podpis_xml|_str/.test(n)), wyslane.join(', '));
  /* [F] „Cofnij wysłanie” przywraca stan i przyciski „Otwórz”; potem bez internetu: wysyłka na zapamiętanych danych */
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); await p.click('#cofnij'); await p.waitForTimeout(600);
  t.backend.martwy = true; await p.click('#podpisz'); await p.waitForSelector('#dok-siatka', { timeout: 20000 }); await p.waitForTimeout(1500);
  ok('po „Cofnij wysłanie” karty znów mają „Otwórz”, a krok 5 znów pozwala wysłać; bez internetu adresu odbiorcy nadal nie widać', (await p.locator('.dok-k .dok-wyslano').count()) === 0 && (await p.locator('.dok-k .dok-akcje [data-akcja="otworz"]').count()) >= 7 && (await p.locator(wyslijSel).count()) === 1 && (await bezAdresu()), await opisK5());
  const emlOff = await pobierz(wyslijSel);
  ok('bez internetu wysyłka działa na zapamiętanych danych (hasło ważne do terminu): paczka otwiera się tym samym hasłem administratora, adresat z pamięci', emlOff.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && (() => { const w = emlOtwarty(emlOff.sciezka); return w.to === ADRES && w.pliki.length >= 7; })());
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); await p.click('#cofnij'); await p.waitForTimeout(600);
  await p.evaluate(() => { const d = window.__pmtDane.czytaj(); delete d.ustawienia.paczka; window.__pmtDane.zapisz(d); });
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka', { timeout: 20000 }); await p.waitForTimeout(1500);
  await p.click(wyslijSel); await p.waitForFunction(() => /Brak połączenia/.test(document.querySelector('#podp-wyslij-stan').textContent), null, { timeout: 60000 });
  ok('bez internetu i bez zapamiętanych danych: „Brak połączenia — nie mogę pobrać hasła do paczki”; status „wysłane” się nie ustawia', /Brak połączenia/.test(await stanW()) && !(await p.locator('#status').innerText()).includes('Wysłane'));
  t.backend.martwy = false;
  const pobAgain = await pobierz(wyslijSel); await p.waitForTimeout(600);
  ok('po powrocie internetu wysyłka działa i znów ustawia status „Wysłane” (ten stan sprawdzają kolejne kroki testu)', pobAgain.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && (await p.locator('#status').innerText()).includes('Wysłane'));
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 });
  /* [H] SZKIC W OUTLOOKU (Microsoft Graph): gdy administrator wpisał identyfikator aplikacji Microsoft (plik poczta_microsoft.txt), „Wyślij” loguje do poczty użytkownika w osobnym oknie, tworzy szkic z adresem, tematem,
     treścią i zahasłowaną paczką i otwiera go w Outlooku. Microsoft jest tu atrapą (trasy Playwrighta): sprawdzamy to, co wysyłamy i jak aplikacja radzi sobie z odmową, złym tokenem i zablokowanym oknem. */
  const CORS = { 'access-control-allow-origin': '*', 'access-control-allow-headers': 'authorization,content-type,content-range', 'access-control-allow-methods': 'GET,POST,PUT,OPTIONS' };
  const ms = { klient: '11111111-2222-3333-4444-555555555555', zadania: [], szkic: null, zalaczniki: [], sesja: null, kawalki: [], putZAutoryzacja: false, odmowa: false, zlyToken: false, token: 'TOKEN-TEST-Outlook' };
  const wlaczMs = on => { OPSERW.pocztaMs = on ? ms.klient.toUpperCase() : undefined; };      // undefined = serwer oddaje prawdziwy plik z samymi komentarzami (jak produkcja), a nie 404      // plik poczta_microsoft.txt podaje serwer testowy (service worker pobiera go sam, więc trasa Playwrighta by go nie przechwyciła)
  await t.ctx.route('https://login.microsoftonline.com/**', async r => {
    const rq = r.request(), u = new URL(rq.url());
    if (rq.method() === 'OPTIONS') return r.fulfill({ status: 204, headers: CORS });
    if (u.pathname.endsWith('/authorize')) {
      ms.zadania.push({ co: 'authorize', q: Object.fromEntries(u.searchParams) }); const powrot = u.searchParams.get('redirect_uri'), st = encodeURIComponent(u.searchParams.get('state'));
      return r.fulfill({ status: 302, headers: { location: ms.odmowa ? `${powrot}?error=access_denied&error_description=AADSTS65004%3A+odmowa&state=${st}` : `${powrot}?code=KOD-TEST-Outlook&state=${st}` } });
    }
    if (u.pathname.endsWith('/token')) { ms.zadania.push({ co: 'token', body: Object.fromEntries(new URLSearchParams(rq.postData())) }); return r.fulfill({ status: 200, headers: CORS, contentType: 'application/json', body: JSON.stringify({ access_token: ms.zlyToken ? 'ZLY-TOKEN' : ms.token, token_type: 'Bearer', expires_in: 3599 }) }); }
    return r.fulfill({ status: 404, body: '' });
  });
  await t.ctx.route('https://graph.microsoft.com/**', async r => {
    const rq = r.request(), u = new URL(rq.url()), m = rq.method(); if (m === 'OPTIONS') return r.fulfill({ status: 204, headers: CORS });
    if (rq.headers()['authorization'] !== 'Bearer ' + ms.token) return r.fulfill({ status: 401, headers: CORS, contentType: 'application/json', body: JSON.stringify({ error: { code: 'InvalidAuthenticationToken', message: 'Access token is empty or invalid' } }) });
    if (u.pathname === '/v1.0/me/messages' && m === 'POST') { ms.szkic = JSON.parse(rq.postData()); return r.fulfill({ status: 201, headers: CORS, contentType: 'application/json', body: JSON.stringify({ id: 'AAMkTEST=', webLink: 'https://outlook.office365.com/owa/?ItemID=AAMkTEST%3D&exvsurl=1&viewmodel=ReadMessageItem' }) }); }
    if (/\/attachments$/.test(u.pathname) && m === 'POST') { ms.zalaczniki.push(JSON.parse(rq.postData())); return r.fulfill({ status: 201, headers: CORS, contentType: 'application/json', body: '{}' }); }
    if (/createUploadSession$/.test(u.pathname) && m === 'POST') { ms.sesja = JSON.parse(rq.postData()); return r.fulfill({ status: 201, headers: CORS, contentType: 'application/json', body: JSON.stringify({ uploadUrl: 'https://outlook.office.com/api/gv2.0/upload/SESJA-TEST' }) }); }
    return r.fulfill({ status: 404, headers: CORS, body: '' });
  });
  await t.ctx.route('https://outlook.office.com/**', async r => {
    const rq = r.request(); if (rq.method() === 'OPTIONS') return r.fulfill({ status: 204, headers: CORS });
    const zakres = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(rq.headers()['content-range'] || ''); if (rq.headers()['authorization']) ms.putZAutoryzacja = true;
    if (rq.method() === 'PUT' && zakres) { ms.kawalki.push({ od: Number(zakres[1]), do: Number(zakres[2]), razemMs: Number(zakres[3]), bajty: rq.postDataBuffer() }); return r.fulfill({ status: Number(zakres[2]) + 1 === Number(zakres[3]) ? 201 : 200, headers: CORS, contentType: 'application/json', body: '{}' }); }
    return r.fulfill({ status: 400, headers: CORS, body: '' });
  });
  await t.ctx.route('https://outlook.office365.com/**', r => r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><meta charset="utf-8"><title>Szkic testowy</title><h1>SZKIC</h1>' }));
  const cofnijIOtworz = async () => { await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 }); if (await p.locator('#cofnij').isVisible()) await p.click('#cofnij'); await p.waitForTimeout(600); await p.click('#podpisz'); await p.waitForSelector('#dok-siatka', { timeout: 20000 }); await p.waitForTimeout(1500); };
  const ustawMetode = async m => { for (let i = 0; i < 4; i++) { if ((await p.locator(`#arkusz .krok-k.k5 [data-akcja="wyslij"][data-metoda="${m}"]`).count()) === 1) return true; await p.click('[data-akcja="zmien-poczte"]'); await p.waitForTimeout(350); } return false; };      // przełącza „Zmień sposób”, aż „Wyślij” ma wybraną metodę
  const czekajStan = re => p.waitForFunction(r => new RegExp(r).test(document.querySelector('#podp-wyslij-stan').textContent), re.source, { timeout: 90000 });
  const wyslijSel2 = '#arkusz .krok-k.k5 [data-akcja="wyslij"]';
  wlaczMs(false); await cofnijIOtworz();
  ok('bez identyfikatora aplikacji Microsoft nie ma szkicu w Outlooku: „Wyślij” (tu: plik .eml, bo tak ustawia zestaw testów) i „Zmień sposób” między „otwórz pocztę” a „plik .eml”; opis bez Outlooka', (await p.locator(`${wyslijSel2}[data-metoda="plik"]`).count()) === 1 && (await p.locator('[data-akcja="zmien-poczte"]').count()) === 1 && !/Outlook/.test(await opisK5()) && (await ustawMetode('outlook')) === false, await opisK5());
  wlaczMs(true); await cofnijIOtworz();
  ok('po wpisaniu identyfikatora w pliku poczta_microsoft.txt dochodzi trzeci sposób; po przełączeniu na „outlook” opis mówi o szkicu w Outlooku, a „Zmień sposób” zostaje obok', (await ustawMetode('outlook')) === true && (await p.locator(`${wyslijSel2}[data-metoda="outlook"]`).count()) === 1 && /Zmień sposób/.test(await p.locator('[data-akcja="zmien-poczte"]').innerText()) && /szkic wiadomości w Twoim Outlooku/.test(await opisK5()) && (await bezAdresu()), await opisK5());
  await p.screenshot({ path: tmp + '/7_outlook_krok5.png' });
  // [H1] przeglądarka blokuje okno logowania → jasny komunikat i wyjście plikiem .eml
  await p.evaluate(() => { window.__openOrig = window.open; window.open = () => null; });
  await p.click(wyslijSel2); await czekajStan(/zablokowała okno logowania/);
  ok('zablokowane okno logowania: komunikat z poradą i przyciskiem „Wyślij plikiem .eml”; nic nie wysłano, status „Wysłane” się nie ustawia', (await p.locator('#podp-wyslij-stan [data-akcja="wyslij-plik"]').count()) === 1 && !(await p.locator('#status').innerText()).includes('Wysłane') && ms.zadania.length === 0);
  await p.evaluate(() => { window.open = window.__openOrig; });
  const emlZast = await pobierz('#podp-wyslij-stan [data-akcja="wyslij-plik"]'); await p.waitForTimeout(500);
  ok('„Wyślij plikiem .eml” robi to, co dawniej: pobiera gotową wiadomość i ustawia status „Wysłane”', emlZast.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && (await p.locator('#status').innerText()).includes('Wysłane'));
  await cofnijIOtworz();
  // [H2] odmowa zgody w oknie Microsoft
  ms.odmowa = true; const [oknoOdm] = await Promise.all([p.waitForEvent('popup', { timeout: 20000 }), p.click(wyslijSel2)]);
  await czekajStan(/Odmówiono zgody/); await p.waitForTimeout(600);
  ok('odmowa zgody w Microsoft: komunikat po polsku, przycisk „Wyślij plikiem .eml”, okno logowania zamknięte, status „Wysłane” się nie ustawia, szkic nie powstał', (await p.locator('#podp-wyslij-stan [data-akcja="wyslij-plik"]').count()) === 1 && oknoOdm.isClosed() && !(await p.locator('#status').innerText()).includes('Wysłane') && ms.szkic === null, await stanW());
  ms.odmowa = false;
  // [H3] token odrzucony przez Graph (401)
  ms.zlyToken = true; const [oknoZly] = await Promise.all([p.waitForEvent('popup', { timeout: 20000 }), p.click(wyslijSel2)]);
  await czekajStan(/odrzuciła dostęp/); await p.waitForTimeout(600);
  ok('token odrzucony przez Graph (401): komunikat o braku uprawnień, wyjście plikiem .eml, okno zamknięte, szkic nie powstał', (await p.locator('#podp-wyslij-stan [data-akcja="wyslij-plik"]').count()) === 1 && oknoZly.isClosed() && ms.szkic === null && !(await p.locator('#status').innerText()).includes('Wysłane'), await stanW());
  ms.zlyToken = false; ms.zadania.length = 0;
  // [H4] wszystko poprawnie
  const [oknoOk] = await Promise.all([p.waitForEvent('popup', { timeout: 20000 }), p.click(wyslijSel2)]);
  await czekajStan(/Szkic gotowy w Twoim Outlooku/); await oknoOk.waitForURL(/outlook\.office365\.com\/owa\//, { timeout: 15000 }); await p.waitForTimeout(500);
  const auth = (ms.zadania.find(z => z.co === 'authorize') || {}).q || {}, tok = (ms.zadania.find(z => z.co === 'token') || {}).body || {};
  ok('logowanie: identyfikator aplikacji z pliku, kod autoryzacji z PKCE (S256), tylko uprawnienie Mail.ReadWrite (bez „offline_access”), adres powrotu = ms_powrot.html tej strony, losowy „state”', auth.client_id === ms.klient && auth.response_type === 'code' && auth.code_challenge_method === 'S256' && auth.scope === 'https://graph.microsoft.com/Mail.ReadWrite' && /\/ms_powrot\.html$/.test(auth.redirect_uri || '') && (auth.state || '').length >= 24 && !/offline_access/.test(JSON.stringify(auth)), JSON.stringify(auth));
  const sk = require('crypto').createHash('sha256').update(tok.code_verifier || '').digest('base64url');
  ok('wymiana kodu na token: ten sam adres powrotu, kod z odpowiedzi, a „code_verifier” pasuje do „code_challenge” z logowania (PKCE)', tok.grant_type === 'authorization_code' && tok.code === 'KOD-TEST-Outlook' && tok.redirect_uri === auth.redirect_uri && sk === auth.code_challenge && tok.client_id === ms.klient, JSON.stringify(tok));
  ok('szkic: adresat z arkusza, temat „[PMT] Delegacje — Jan Testowy — …”, treść zwykłym tekstem o zahasłowanej paczce, podpisana imieniem; bez hasła i PESEL-u', !!ms.szkic && ms.szkic.toRecipients[0].emailAddress.address === ADRES && /^\[PMT\] Delegacje — Jan Testowy — \S+ 20\d\d$/.test(ms.szkic.subject) && ms.szkic.body.contentType === 'text' && /zahasłowana paczka \(ZIP\)/.test(ms.szkic.body.content) && /Jan Testowy\s*$/.test(ms.szkic.body.content) && !ms.szkic.body.content.includes(HASLO) && !JSON.stringify(ms.szkic).includes('90010112349'), JSON.stringify(ms.szkic).slice(0, 200));
  const sklejone = ms.zalaczniki.length ? Buffer.from(ms.zalaczniki[0].contentBytes, 'base64') : Buffer.alloc(0);
  ok('mała paczka (poniżej 3 MB) poszła jednym zapytaniem jako załącznik pliku: nazwa Dokumenty_….zip, typ ZIP, bez sesji wysyłania i bez kawałków', ms.zalaczniki.length === 1 && !ms.sesja && ms.kawalki.length === 0 && ms.zalaczniki[0]['@odata.type'] === '#microsoft.graph.fileAttachment' && /^Dokumenty_.*\.zip$/.test(ms.zalaczniki[0].name) && ms.zalaczniki[0].contentType === 'application/zip' && sklejone.length > 1000, `bajtów: ${sklejone.length}`);
  const zipOut = path.join(tmp, 'z_outlook.zip'); fs.writeFileSync(zipOut, sklejone);
  const zipOutlookOk = cp.spawnSync(PYZ, ['-I', '-c', 'import sys, zipfile\nz = zipfile.ZipFile(sys.argv[1]); z.setpassword(sys.argv[2].encode()); print(len(z.namelist()) if z.testzip() is None else 0)', zipOut, HASLO], { encoding: 'utf8' }).stdout.trim();
  ok('to, co trafiło do Outlooka, jest tą samą zahasłowaną paczką: otwiera się hasłem administratora, ≥ 7 plików', Number(zipOutlookOk) >= 7, zipOutlookOk);
  ok('okno logowania przeszło na gotowy szkic (adres Outlooka), status „Wysłane” ustawiony sam, w kroku 5 jest odnośnik „Otwórz szkic” na wypadek zablokowanego przekierowania', /outlook\.office365\.com\/owa\//.test(oknoOk.url()) && (await p.locator('#status').innerText()).includes('Wysłane') && (await p.locator('#podp-wyslij-stan a[href^="https://outlook.office365.com/"]').count()) === 1 && /Kliknij tam „Wyślij”/.test(await stanW()), oknoOk.url());
  ok('token ani kod autoryzacji nie zostają w pamięci przeglądarki (localStorage, sessionStorage, strona)', !(await p.evaluate(() => JSON.stringify(localStorage) + JSON.stringify(sessionStorage) + document.documentElement.outerHTML)).match(/TOKEN-TEST-Outlook|KOD-TEST-Outlook/));
  ok('po utworzeniu szkicu w Outlooku adresu odbiorcy nie ma w oknie aplikacji (jest tylko w szkicu w skrzynce)', (await bezAdresu()) && /Szkic gotowy w Twoim Outlooku \(z zahasłowaną paczką\)/.test(await stanW()), await stanW());
  await oknoOk.close(); await p.screenshot({ path: tmp + '/7b_outlook_gotowe.png' });
  // [H5] „Zmień sposób” przełącza kolejno: outlook → plik .eml → poczta (mailto) → outlook; wybór jest pamiętany
  await cofnijIOtworz();
  await p.evaluate(() => { window.__mailto = []; window.__przechwycMailto = u => window.__mailto.push(u); });
  await p.click('[data-akcja="zmien-poczte"]'); await p.waitForTimeout(400);
  ok('„Zmień sposób” z Outlooka przechodzi na plik .eml (drugi w kolejce, domyślny bez Outlooka); opis: gotowa wiadomość w jednym pliku .eml, w poczcie zostaje tylko „Wyślij”; wybór zapamiętany', (await p.locator(`${wyslijSel2}[data-metoda="plik"]`).count()) === 1 && /jednym pliku \.eml/.test(await opisK5()) && /zostanie tylko kliknąć „Wyślij”/.test(await opisK5()) && !/Outlooku/.test(await opisK5()) && (await p.evaluate(() => localStorage.getItem('pmt-ui-poczta'))) === 'plik', await opisK5());
  const emlPref = await pobierz(wyslijSel2); await p.waitForTimeout(400);
  ok('przy sposobie „plik .eml” „Wyślij” nie otwiera ani poczty, ani okna logowania — pobiera plik .eml', emlPref.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && (await p.evaluate(() => window.__mailto.length)) === 0);
  ok('po „Zrobione” kolejne wysyłki mają krótki komunikat (bez wskazówki) z przyciskiem „Jak sprawić, żeby otwierała się sama?”', (await p.locator('#eml-rada').count()) === 0 && /Wiadomość gotowa/.test(await stanW()) && /kliknij pobrany plik/.test(await stanW()) && (await p.locator('#podp-wyslij-stan [data-akcja="eml-rada"]').count()) === 1, await stanW());
  await p.click('#podp-wyslij-stan [data-akcja="eml-rada"]'); await p.waitForTimeout(200);
  ok('ten przycisk pokazuje wskazówkę ponownie (w miejscu przycisku)', (await p.locator('#podp-wyslij-stan #eml-rada').count()) === 1 && (await p.locator('#podp-wyslij-stan [data-akcja="eml-rada"]').count()) === 0);
  await cofnijIOtworz(); await p.click('[data-akcja="zmien-poczte"]'); await p.waitForTimeout(400);
  ok('kolejne „Zmień sposób”: z pliku .eml na „otwórz pocztę” (mailto), opis mówi o programie pocztowym i folderze Pobrane, wybór zapamiętany na urządzeniu', (await p.locator(`${wyslijSel2}[data-metoda="poczta"]`).count()) === 1 && /program pocztowy z adresem, tematem i treścią/.test(await opisK5()) && /folderze Pobrane/.test(await opisK5()) && !/Outlooku/.test(await opisK5()) && (await p.evaluate(() => localStorage.getItem('pmt-ui-poczta'))) === 'poczta' && /samo otwarcie poczty — paczkę dołączysz sam/.test(await p.locator('.wyslij-sposob').innerText()), await opisK5());
  // [H6] OTWARCIE POCZTY (mailto:) — jak w pierwszej wersji: jeden klik, program pocztowy dostaje adres, temat i treść; paczka ZIP zapisuje się w Pobranych
  await p.evaluate(() => { window.__mailto = []; window.__przechwycMailto = u => window.__mailto.push(u); });
  const zipPoczta = await pobierz(wyslijSel2); await p.waitForTimeout(600);
  const mailto = await p.evaluate(() => window.__mailto), mm = /^mailto:([^?]+)\?subject=([^&]*)&body=(.*)$/s.exec(mailto[0] || ''), temM = mm ? decodeURIComponent(mm[2]) : '', trM = mm ? decodeURIComponent(mm[3]) : '';
  ok('jedno kliknięcie: poczta otwarta dokładnie raz, adres z arkusza z „@” wprost (bez %40), temat „[PMT] Delegacje — Jan Testowy — …”, treść o zahasłowanej paczce z nowymi wierszami CRLF i podpisem; bez hasła, PESEL-u i bez dopisków w nawiasach', mailto.length === 1 && !!mm && mm[1] === ADRES && /^\[PMT\] Delegacje — Jan Testowy — \S+ 20\d\d$/.test(temM) && /zahasłowana paczka \(ZIP\)/.test(trM) && /\r\n/.test(trM) && /Jan Testowy\s*$/.test(trM) && !trM.includes(HASLO) && !mailto[0].includes('90010112349') && !/\(Dołącz/.test(trM), mailto[0]);
  const zipPocztaOk = cp.spawnSync(PYZ, ['-I', '-c', 'import sys, zipfile\nz = zipfile.ZipFile(sys.argv[1]); z.setpassword(sys.argv[2].encode()); print(len(z.namelist()) if z.testzip() is None else 0)', zipPoczta.sciezka, HASLO], { encoding: 'utf8' }).stdout.trim();
  ok('paczka zapisała się do Pobranych sama (nazwa Dokumenty_….zip), otwiera się hasłem administratora, ≥ 7 plików', /^Dokumenty_.*\.zip$/.test(zipPoczta.nazwa) && Number(zipPocztaOk) >= 7, zipPoczta.nazwa + ' / ' + zipPocztaOk);
  ok('komunikat: „Otworzyłem pocztę z gotową wiadomością…”, nazwa paczki, instrukcja „dołącz ją do wiadomości”; adresu odbiorcy nie ma w oknie, a przycisk „Otwórz wiadomość” nie niesie go w odnośniku; status „Wysłane” ustawiony sam; nie otwarto okna logowania ani pliku .eml', /Otworzyłem pocztę z gotową wiadomością/.test(await stanW()) && /dołącz ją do wiadomości/.test(await stanW()) && (await p.locator('#podp-otworz-poczte').evaluate(e => e.tagName + '|' + (e.getAttribute('href') || ''))) === 'BUTTON|' && (await bezAdresu()) && (await p.locator('#status').innerText()).includes('Wysłane') && !/\.eml/.test(zipPoczta.nazwa));
  await p.click('#podp-otworz-poczte'); await p.waitForTimeout(200);
  ok('przycisk „Otwórz wiadomość” otwiera tę samą wiadomość jeszcze raz (adresat wpisany)', (await p.evaluate(() => window.__mailto.length)) === 2 && (await p.evaluate(() => window.__mailto[1] === window.__mailto[0])));
  await p.screenshot({ path: tmp + '/7c_poczta_mailto.png' });
  await cofnijIOtworz(); await p.click('[data-akcja="zmien-poczte"]'); await p.waitForTimeout(400);
  ok('trzecie „Zmień sposób” zamyka koło i wraca do szkicu w Outlooku', (await p.locator(`${wyslijSel2}[data-metoda="outlook"]`).count()) === 1 && (await p.evaluate(() => localStorage.getItem('pmt-ui-poczta'))) === 'outlook');
  // bez identyfikatora Microsoft nie ma Outlooka: zapamiętany „outlook” nie obowiązuje, domyślną staje się „poczta”, a koło ma dwa sposoby
  wlaczMs(false); await cofnijIOtworz();
  ok('po usunięciu identyfikatora z pliku zapamiętany „outlook” przestaje obowiązywać: „Wyślij” pobiera plik .eml (domyślny), „Zmień sposób” przełącza już tylko między plikiem .eml a pocztą', (await p.locator(`${wyslijSel2}[data-metoda="plik"]`).count()) === 1 && (await p.locator('[data-akcja="zmien-poczte"]').count()) === 1 && (await ustawMetode('outlook')) === false);
  ok('wracamy do „plik .eml” dla kolejnych kroków testu', (await ustawMetode('plik')) === true && (await p.evaluate(() => localStorage.getItem('pmt-ui-poczta'))) === 'plik');
  const pobPoOutlook = await pobierz(wyslijSel2);      // dokumenty są teraz niewysłane i okno otwarte: plik .eml await p.waitForTimeout(500);      // przywraca stan „Wysłane”, którego oczekują kolejne kroki testu
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 });
  ok('po całym scenariuszu wysyłki stan „Wysłane” jest przywrócony dla kolejnych kroków', pobPoOutlook.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && (await p.locator('#status').innerText()).includes('Wysłane'));

  /* [I] ZAPIS NA PULPICIE (Chrome, Edge): „Wyślij” otwiera okno „Zapisz jako” od razu na Pulpicie z nazwą pliku .eml; po zapisie ikona gotowej wiadomości leży na pulpicie, dwuklik otwiera pocztę.
     Natywnego okna zapisu w teście nie da się obsłużyć, więc podstawiamy atrapę showSaveFilePicker (zapisuje do pamięci i pamięta, z czym ją wywołano). */
  let pobraniePrzyZapisie = 0; p.on('download', () => { pobraniePrzyZapisie++; });
  await p.evaluate(() => {
    window.__zapisy = []; window.__anulujZapis = false;
    window.showSaveFilePicker = async o => {
      const z = { o, kawalki: [], zamkniety: false }; window.__zapisy.push(z);
      if (window.__anulujZapis) throw new DOMException('Użytkownik anulował', 'AbortError');
      return { name: o.suggestedName, createWritable: async () => ({ write: async b => { z.kawalki.push(Array.from(new Uint8Array(await new Response(b).arrayBuffer()))); }, close: async () => { z.zamkniety = true; } }) };
    };
  });
  await cofnijIOtworz();
  ok('gdy przeglądarka umie okno zapisu, dochodzi sposób „pulpit” (w kole „Zmień sposób” zaraz po pliku .eml); opis mówi o ikonie na pulpicie', (await ustawMetode('pulpit')) === true && /ikonę gotowej wiadomości/.test(await opisK5()) && /dwukrotnie/.test(await opisK5()), await opisK5());
  // anulowanie okna zapisu: nic się nie dzieje, nic nie jest przygotowywane ani oznaczone jako wysłane
  await p.evaluate(() => { window.__anulujZapis = true; });
  const hasloPrzed = t.backend.pobraniaHasla;
  await p.click(wyslijSel2); await czekajStan(/Anulowano — nic nie zapisano/);
  ok('anulowanie okna zapisu: komunikat „Anulowano”, status „Wysłane” się nie ustawia, nic nie zapisano, hasło do paczki nie pobierane, bez pobierania pliku', (await p.evaluate(() => window.__zapisy.length)) === 1 && (await p.evaluate(() => window.__zapisy[0].kawalki.length)) === 0 && !(await p.locator('#status').innerText()).includes('Wysłane') && t.backend.pobraniaHasla === hasloPrzed && pobraniePrzyZapisie === 0, await stanW());
  // zapis
  await p.evaluate(() => { window.__anulujZapis = false; });
  await p.click(wyslijSel2); await czekajStan(/Zapisałem wiadomość/); await p.waitForTimeout(500);
  const zapis = await p.evaluate(() => { const z = window.__zapisy[1]; return { o: z.o, zamkniety: z.zamkniety, bajty: [].concat(...z.kawalki) }; });
  ok('okno zapisu otwarte na PULPICIE (startIn: desktop), z nazwą PMT_wiadomosc_do_wyslania.eml i filtrem .eml; plik zapisany i zamknięty; bez zwykłego pobierania', zapis.o.startIn === 'desktop' && zapis.o.suggestedName === 'PMT_wiadomosc_do_wyslania.eml' && JSON.stringify(zapis.o.types[0].accept) === '{"message/rfc822":[".eml"]}' && zapis.zamkniety && zapis.bajty.length > 1000 && pobraniePrzyZapisie === 0, `bajtów: ${zapis.bajty.length}`);
  const emlPulpit = path.join(tmp, 'z_pulpit.eml'); fs.writeFileSync(emlPulpit, Buffer.from(zapis.bajty)); const wPulpit = emlOtwarty(emlPulpit);
  ok('zapisany plik to ta sama gotowa wiadomość: adresat z arkusza, temat „[PMT] Delegacje — Jan Testowy — …”, nagłówek X-Unsent, jeden załącznik ZIP, który otwiera się hasłem administratora (≥ 7 plików); czysty ASCII, bez jawnego PESEL-u i hasła', wPulpit.x === '1' && wPulpit.to === ADRES && /^\[PMT\] Delegacje — Jan Testowy — \S+ 20\d\d$/.test(wPulpit.temat) && wPulpit.zal === 1 && wPulpit.pliki.length >= 7 && wPulpit.ascii && !wPulpit.jawne, JSON.stringify([wPulpit.to, wPulpit.temat, wPulpit.zal, wPulpit.pliki.length]));
  ok('komunikat: „Zapisałem wiadomość … ikona jest na pulpicie … Kliknij ją dwukrotnie”; adresu odbiorcy nie ma w oknie; status „Wysłane” ustawiony sam', (await bezAdresu()) && /Zapisałem wiadomość/.test(await stanW()) && /ikona jest na pulpicie/.test(await stanW()) && /dwukrotnie/.test(await stanW()) && (await p.locator('#status').innerText()).includes('Wysłane'), await stanW());
  await p.screenshot({ path: tmp + '/7d_pulpit.png' });
  // błąd zapisu (np. brak uprawnień) → wyjście zwykłym plikiem .eml
  await cofnijIOtworz(); await ustawMetode('pulpit');
  await p.evaluate(() => { window.showSaveFilePicker = async o => ({ name: o.suggestedName, createWritable: async () => { throw new DOMException('brak uprawnień do zapisu', 'NotAllowedError'); } }); });
  await p.click(wyslijSel2); await czekajStan(/Nie udało się zapisać wiadomości na pulpicie/);
  ok('błąd zapisu na pulpicie: komunikat z przyczyną i przycisk „Wyślij plikiem .eml”; status „Wysłane” się nie ustawia', (await p.locator('#podp-wyslij-stan [data-akcja="wyslij-plik"]').count()) === 1 && /brak uprawnień do zapisu/.test(await stanW()) && !(await p.locator('#status').innerText()).includes('Wysłane'), await stanW());
  // przeglądarka bez okna zapisu (Firefox, Safari): sposób „pulpit” nie jest oferowany, domyślny wraca do „poczta”/„plik”
  await p.evaluate(() => { window.showSaveFilePicker = undefined; });
  await cofnijIOtworz();
  ok('bez okna zapisu w przeglądarce sposób „pulpit” znika, a zapamiętany wybór nie obowiązuje (domyślnie plik .eml)', (await p.locator(`${wyslijSel2}[data-metoda="plik"]`).count()) === 1 && (await ustawMetode('pulpit')) === false);
  ok('wracamy do „plik .eml” dla kolejnych kroków testu', (await ustawMetode('plik')) === true);
  const pobPoPulpicie = await pobierz(wyslijSel2); await p.waitForTimeout(400);      // przywraca stan „Wysłane” sposobem „plik”
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 });
  ok('po scenariuszu „pulpit” stan „Wysłane” jest przywrócony dla kolejnych kroków', pobPoPulpicie.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && (await p.locator('#status').innerText()).includes('Wysłane'));

  /* [J] Chromium (Edge, Chrome) puszcza plik .eml bez ostrzeżenia o „niebezpiecznym pliku” tylko wtedy, gdy pobranie następuje tuż po kliknięciu (ok. 5 s), więc kliknięcie nie może czekać na wolny serwer */
  await cofnijIOtworz(); await ustawMetode('plik'); await p.waitForTimeout(1500);
  t.backend.opoznienieMs = 5500; const t0J = Date.now(); const emlWolny = await pobierz(wyslijSel2); const trwalo = Date.now() - t0J;
  ok('wolny serwer (odpowiedź po 5,5 s) nie opóźnia pobrania: plik .eml schodzi w ciągu kilku sekund od kliknięcia, bo dane z serwera są już w pamięci', emlWolny.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && trwalo < 4000 && emlOtwarty(emlWolny.sciezka).to === ADRES, `${trwalo} ms`);
  await p.waitForTimeout(6000); t.backend.opoznienieMs = 0;      // dokończ spóźnione sprawdzenie w tle
  // administrator zmienia hasło tuż po pobraniu danych przez okno: paczka ma stare hasło — użytkownik jest o tym uprzedzony
  await cofnijIOtworz(); await ustawMetode('plik'); await p.waitForTimeout(1500);
  t.backend.paczka = { haslo: 'Zmienione-Haslo#7-2026', wazne_do: '2099-12-31', adres: ADRES };
  await pobierz(wyslijSel2); await czekajStan(/administrator zmienił właśnie hasło/);
  ok('zmiana hasła przez administratora w trakcie pracy okna: po wysyłce ostrzeżenie „administrator zmienił właśnie hasło… Cofnij wysłanie i wyślij jeszcze raz”', /Cofnij wysłanie/.test(await stanW()), await stanW());
  t.backend.paczka = { haslo: HASLO, wazne_do: '2099-12-31', adres: ADRES };
  /* [K] administrator wybiera w arkuszu szyfr AES-256 (format_paczki = aes): paczka jest w AES (metoda 99), hasło może mieć polskie litery, a wiadomość uprzedza odbiorcę o 7-Zip/WinRAR; szyfr klasyczny to ustawienie domyślne */
  await cofnijIOtworz(); await ustawMetode('plik'); await p.waitForTimeout(1500);
  const HASLO_AES = 'Zażółć-hasło-AES-2026'; t.backend.paczka = { haslo: HASLO_AES, wazne_do: '2099-12-31', adres: ADRES, format: 'aes' };
  const emlAes = await pobierz(wyslijSel2);
  const aesJson = cp.spawnSync(PYZ, ['-I', '-c', `
import sys, json, email, email.policy, io
try:
    import pyzipper
except ImportError:
    print(json.dumps({'brak': True})); raise SystemExit
m = email.message_from_bytes(open(sys.argv[1], 'rb').read(), policy=email.policy.default); cz = list(m.iter_attachments()); dane = cz[0].get_content()
z = pyzipper.AESZipFile(io.BytesIO(dane)); z.setpassword(sys.argv[2].encode('utf-8'))
print(json.dumps({'metoda': z.infolist()[0].compress_type, 'ok': z.testzip() is None, 'pliki': len(z.namelist()), 'tresc': m.get_body(preferencelist=('plain',)).get_content()}))`, emlAes.sciezka, HASLO_AES], { encoding: 'utf-8' });
  const aes = aesJson.status === 0 ? JSON.parse(aesJson.stdout) : { blad: aesJson.stderr };
  if (aes.brak) console.log('  UWAGA brak pyzipper — pominięto odczyt paczki AES (zestaw: /tmp/pzvenv)');
  else ok('szyfr „aes” z arkusza: paczka w AES-256 (metoda 99) otwiera się hasłem z polskimi literami, wszystkie pliki; wiadomość uprzedza odbiorcę, że potrzebny 7-Zip/WinRAR', aes.metoda === 99 && aes.ok === true && aes.pliki >= 7 && /AES-256/.test(aes.tresc) && /7-Zip/.test(aes.tresc), JSON.stringify(aes).slice(0, 300));
  t.backend.paczka = { haslo: HASLO, wazne_do: '2099-12-31', adres: ADRES };
  const emlKl = await (async () => { await cofnijIOtworz(); await ustawMetode('plik'); await p.waitForTimeout(1500); return pobierz(wyslijSel2); })();
  const klJson = cp.spawnSync(PYZ, ['-I', '-c', 'import sys, email, email.policy, io, zipfile, json\nm = email.message_from_bytes(open(sys.argv[1], "rb").read(), policy=email.policy.default); d = list(m.iter_attachments())[0].get_content(); z = zipfile.ZipFile(io.BytesIO(d)); i = z.infolist()[0]; print(json.dumps({"flag": i.flag_bits, "metoda": i.compress_type, "tresc": m.get_body(preferencelist=("plain",)).get_content()}))', emlKl.sciezka], { encoding: 'utf-8' });
  const kl = klJson.status === 0 ? JSON.parse(klJson.stdout) : { blad: klJson.stderr };
  ok('bez ustawienia szyfru (domyślnie): paczka klasyczna — zaszyfrowana (bit 0), nazwy UTF-8 (bit 11), kompresja deflate (8) albo brak (0), a wiadomość NIE mówi o 7-Zip (Eksplorator wystarcza)', (kl.flag & 1) === 1 && (kl.flag & 0x800) !== 0 && [0, 8].includes(kl.metoda) && !/7-Zip|AES/.test(kl.tresc), JSON.stringify(kl).slice(0, 300));
  // minęło zbyt dużo czasu od kliknięcia (aktywność użytkownika wygasła): zamiast pobrania, które Chromium uznałby za niebezpieczne, jest przycisk „Zapisz wiadomość”
  await cofnijIOtworz(); await ustawMetode('plik'); await p.waitForTimeout(1500);
  const pobraniaPrzed = pobraniePrzyZapisie;
  await p.evaluate(() => Object.defineProperty(navigator, 'userActivation', { get: () => ({ isActive: false, hasBeenActive: true }), configurable: true }));
  await p.click(wyslijSel2); await czekajStan(/Zapisz wiadomość/); await p.waitForTimeout(1200);
  ok('bez aktywności użytkownika (Edge/Chrome): nic się nie pobiera samo, w kroku 5 jest przycisk „Zapisz wiadomość”, status „Wysłane” jeszcze się nie ustawia', (await p.locator('#podp-wyslij-stan [data-akcja="zapisz-eml"]').count()) === 1 && pobraniePrzyZapisie === pobraniaPrzed && !(await p.locator('#status').innerText()).includes('Wysłane'), await stanW());
  const emlZPrzycisku = await (async () => { const [d] = await Promise.all([p.waitForEvent('download', { timeout: 30000 }), p.click('#podp-wyslij-stan [data-akcja="zapisz-eml"]')]); const sc = path.join(tmp, Date.now() + '_' + d.suggestedFilename()); await d.saveAs(sc); return { nazwa: d.suggestedFilename(), sciezka: sc }; })();
  await p.waitForTimeout(500);
  ok('po kliknięciu „Zapisz wiadomość” pobiera się ta sama wiadomość (adresat, paczka otwierana hasłem administratora), status „Wysłane” ustawia się dopiero teraz, a komunikat mówi, co dalej', emlZPrzycisku.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && (() => { const w = emlOtwarty(emlZPrzycisku.sciezka); return w.to === ADRES && w.pliki.length >= 7; })() && (await p.locator('#status').innerText()).includes('Wysłane') && /Kliknij ją|kliknij pobrany plik/.test(await stanW()) && /Zachowaj/.test(await stanW()), await stanW());
  await p.evaluate(() => { delete navigator.userActivation; });
  ok('ostrzeżenie przeglądarki („plik może zaszkodzić urządzeniu”) nie zaskakuje: wskazówka mówi, że w Edge/Chrome wystarczy wybrać „Zachowaj”', /Zachowaj/.test(await stanW()));
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 });

  /* [G] telefon, na którym udostępnienie ZIP-a się nie udaje (Chrome na Androidzie odrzuca pliki ZIP błędem NotAllowedError): pobrana paczka + wiadomość przez mailto:, a nie błąd bez wyjścia */
  await p.click('#cofnij'); await p.waitForTimeout(600);
  await p.evaluate(() => { const mm = window.matchMedia.bind(window); window.matchMedia = q => /pointer:\s*coarse/.test(q) ? { matches: true, media: q, addEventListener() {}, removeEventListener() {} } : mm(q); navigator.canShare = () => true; window.__udostepniono = false; navigator.share = () => { window.__udostepniono = true; return Promise.reject(new DOMException('Permission denied', 'NotAllowedError')); }; window.__mailto = []; window.__przechwycMailto = u => window.__mailto.push(u); });
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka', { timeout: 20000 }); await p.waitForTimeout(900);
  const zipTel = await pobierz(wyslijSel); await p.waitForTimeout(800);
  const zipTelOk = cp.spawnSync(PYZ, ['-I', '-c', 'import sys, zipfile\nz = zipfile.ZipFile(sys.argv[1]); z.setpassword(sys.argv[2].encode()); print(len(z.namelist()) if z.testzip() is None else 0)', zipTel.sciezka, HASLO], { encoding: 'utf8' }).stdout.trim();
  ok('telefon: zawsze pobrana zahasłowana paczka (otwiera się hasłem administratora) + poczta z gotowym adresatem, tematem i treścią (mailto:), bo udostępnianie systemowe nie wpisuje adresata; adresu nie widać w oknie; status „Wysłane”', /^Dokumenty_.*\.zip$/.test(zipTel.nazwa) && Number(zipTelOk) >= 7 && /Pobrałem zahasłowaną paczkę/.test(await stanW()) && /adresat, temat i treść są już wpisane/.test(await stanW()) && !(await p.evaluate(() => window.__udostepniono)) && (await p.evaluate(() => window.__mailto.length)) === 1 && (await p.evaluate(() => /^mailto:odbiorca@example\.com\?subject=/.test(window.__mailto[0]) && /Dołącz pobrany plik Dokumenty_/.test(decodeURIComponent(window.__mailto[0])))) && (await bezAdresu()) && (await p.locator('#podp-otworz-poczte').evaluate(e => e.tagName)) === 'BUTTON' && (await p.locator('#status').innerText()).includes('Wysłane'), `${zipTel.nazwa}, ${zipTelOk} plików — ${await stanW()}`);
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 });

  /* ---- zapis wyników sprawdzenia ---- */
  await p.reload(); await p.waitForFunction(() => document.querySelector('#kA.po-gen'), null, { timeout: 120000 }); await p.waitForTimeout(2500);
  ok('stan „Wysłane” przetrwał odświeżenie', (await p.locator('#status').innerText()).includes('Wysłane'));
  await p.click('#cofnij'); await p.waitForTimeout(600);
  ok('„Cofnij wysłanie” przywraca podpisane (wyniki sprawdzenia zostały zapamiętane)', (await p.locator('#status').innerText()).includes('Podpisane'));
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka'); await p.waitForTimeout(800);      // gdy wszystko podpisane, główny przycisk otwiera to samo okno z dokumentami (krok 5 „Wyślij”)
  ok('po odświeżeniu okno pokazuje te same, zapamiętane wyniki sprawdzenia (7 × podpis sprawdzony)', JSON.stringify(await stany()) === JSON.stringify(Array(7).fill('ok')) && /Podpisał\(a\): Jan Testowy/.test(await komunikat(0)));
  // sprawdzanie przerwane odświeżeniem strony: plik dokumentu jest zapisany, wyniku nie ma — po otwarciu okna dokument sprawdza się sam, zamiast wisieć na „sprawdzam…” bez przycisków
  await p.keyboard.press('Escape'); await p.waitForSelector('#arkusz-tlo:not(.otwarty)', { state: 'attached', timeout: 20000 });
  await p.evaluate(() => { const d = window.__pmtDane.czytaj(); delete Object.values(d.miesiace)[0].weryfikacje[1]; window.__pmtDane.zapisz(d); });
  await p.reload(); await p.waitForFunction(() => document.querySelector('#kA.po-gen'), null, { timeout: 120000 }); await p.waitForTimeout(2500);
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka');
  const s5 = await czekajStany(Array(7).fill('ok'));
  ok('sprawdzanie przerwane odświeżeniem strony: dokument z plikiem, ale bez wyniku, sprawdza się sam po otwarciu okna', JSON.stringify(s5) === JSON.stringify(Array(7).fill('ok')) && !!(await zapisane()).weryfikacje[1], JSON.stringify(s5));

  /* ---- wysyłka z dużymi skanami: ostrzeżenie o limicie poczty ---- */
  // dwa zdjęcia tego samego dokumentu (dwie strony): numerowane _str01, _str02
  const dwa = path.join(tmp, 'dwa'); fs.mkdirSync(dwa, { recursive: true }); const baza4 = pdfy[4].replace(/\.pdf$/i, ''), jpg2 = lista(path.join(tmp, 's2'))[2];
  fs.copyFileSync(jpg2, path.join(dwa, baza4 + '_a.jpg')); fs.copyFileSync(jpg2, path.join(dwa, baza4 + '_b.JPEG'));
  await wgrajInny(4); await czekajStany(['ok', 'ok', 'ok', 'ok', 'czeka', 'ok', 'ok']);
  await wgraj(lista(dwa)); await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok']);
  const zap5 = await zapisane();
  ok('nazwy: dwa zdjęcia jednego dokumentu → „…_str01.jpg” i „…_str02.jpg” (rozszerzenie JPEG ujednolicone do jpg)', JSON.stringify(zap5.pliki[4]) === JSON.stringify([baza4 + '_str01.jpg', baza4 + '_str02.jpg']) && Object.values(zap5.pierwotne[4]).sort().join('|') === [baza4 + '_a.jpg', baza4 + '_b.JPEG'].sort().join('|'), JSON.stringify(zap5.pliki[4]));
  const duzy = path.join(tmp, 'duzy'); fs.mkdirSync(duzy, { recursive: true });
  const jpg = fs.readFileSync(lista(path.join(tmp, 's2'))[2]); fs.writeFileSync(path.join(duzy, norm(pdfy[4]).replace(/\.pdf$/, '') + '_skan.jpg'), Buffer.concat([jpg, require('crypto').randomBytes(21 * 1048576)]));
  await wgrajInny(4); await czekajStany(['ok', 'ok', 'ok', 'ok', 'czeka', 'ok', 'ok']);
  await wgraj(lista(duzy)); await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok']);
  const duzyEml = await pobierz(wyslijSel);
  ok('przy paczce powyżej 20 MB krok 5 ostrzega przed limitem poczty (wiadomość jest mimo to gotowa)', duzyEml.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && /20–25 MB/.test(await stanW()), await stanW());

  /* [H7] DUŻA paczka (22 MB, więcej niż 3 MB) w szkicu w Outlooku: nie jednym zapytaniem, tylko przez sesję wysyłania w kawałkach */
  Object.assign(ms, { szkic: null, sesja: null, kawalki: [], zalaczniki: [], putZAutoryzacja: false }); ms.zadania.length = 0; wlaczMs(true);
  await cofnijIOtworz(); await ustawMetode('outlook');
  const [oknoDuze] = await Promise.all([p.waitForEvent('popup', { timeout: 20000 }), p.click(wyslijSel2)]);
  await czekajStan(/Szkic gotowy w Twoim Outlooku/); await oknoDuze.waitForURL(/outlook\.office365\.com\/owa\//, { timeout: 15000 }); await p.waitForTimeout(500);
  const razemMs = ms.kawalki.length ? ms.kawalki[0].razemMs : 0, kawalkiPosort = ms.kawalki.slice().sort((a, b) => a.od - b.od), sklejoneDuze = Buffer.concat(kawalkiPosort.map(x => x.bajty));
  ok('duża paczka poszła przez sesję wysyłania: kawałki idą po kolei bez dziur i nakładania, razem tyle, ile zapowiedziała sesja, bez nagłówka Authorization w wysyłaniu; jeden załącznik, bez zapytania „załącznik”; nazwa i typ ZIP', ms.zalaczniki.length === 0 && !!ms.sesja && ms.sesja.AttachmentItem.size === razemMs && razemMs === sklejoneDuze.length && razemMs > 20 * 1048576 && ms.kawalki.length >= 5 && kawalkiPosort.every((x, i, w) => i === 0 ? x.od === 0 : x.od === w[i - 1].do + 1) && kawalkiPosort[kawalkiPosort.length - 1].do + 1 === razemMs && !ms.putZAutoryzacja && /^Dokumenty_.*\.zip$/.test(ms.sesja.AttachmentItem.name) && ms.sesja.AttachmentItem.contentType === 'application/zip', `kawałków: ${ms.kawalki.length}, razem: ${razemMs}`);
  const zipDuzy = path.join(tmp, 'z_outlook_duzy.zip'); fs.writeFileSync(zipDuzy, sklejoneDuze);
  const zipDuzyOk = cp.spawnSync(PYZ, ['-I', '-c', 'import sys, zipfile\nz = zipfile.ZipFile(sys.argv[1]); z.setpassword(sys.argv[2].encode()); print(len(z.namelist()) if z.testzip() is None else 0)', zipDuzy, HASLO], { encoding: 'utf8' }).stdout.trim();
  ok('sklejone kawałki to ta sama zahasłowana paczka: otwiera się hasłem administratora, ≥ 7 plików; w komunikacie jest ostrzeżenie o limicie poczty (> 20 MB)', Number(zipDuzyOk) >= 7 && /20–25 MB/.test(await stanW()), zipDuzyOk);
  await oknoDuze.close(); wlaczMs(false);
  await cofnijIOtworz(); await ustawMetode('plik'); await pobierz(wyslijSel2); await p.waitForTimeout(400);      // wracamy do pliku .eml i stanu „Wysłane”, jak przed tym scenariuszem

  /* ---- praca bez internetu: service worker zapisał aplikację (w tym nowe moduły sprawdzania podpisów); na zwykłym http przeglądarka go nie dopuszcza ---- */
  if (!bezpieczny) {
    ok('http: aplikacja działa w całości, ale bez trybu offline (przeglądarka nie dopuszcza service workera na zwykłym http)', (await p.evaluate(async () => (navigator.serviceWorker ? (await navigator.serviceWorker.getRegistrations()).length : 0))) === 0);
    console.log('  zrzuty:', tmp); const bledyReal = t.bledy.filter(b => !/net::ERR_INTERNET_DISCONNECTED/.test(b) && !/wysyłka (Error: (access_denied|szkic: HTTP 401)|NotAllowedError: brak uprawnień do zapisu)|status of 401 \(Unauthorized\)/.test(b)); console.log('  błędy konsoli:', JSON.stringify(bledyReal.slice(0, 6))); if (bledyReal.length) kod = 1;      // pomijamy odcięcie sieci, które test robi celowo (wysyłka bez internetu), oraz komunikaty z celowych scenariuszy negatywnych wysyłki (odmowa zgody w Outlooku, zły token → 401, błąd zapisu na pulpicie)
    await t.zamknij(); process.exit(kod);
  }
  await p.waitForFunction(async () => { const k = await caches.keys(); if (!k.length) return false; const c = await caches.open(k[0]); const u = (await c.keys()).map(r => r.url); return u.length >= 25 && u.some(x => /weryfikacja\.js/.test(x)) && u.some(x => /podpis_reczny\.js/.test(x)); }, null, { timeout: 120000 });
  await t.ctx.setOffline(true);
  await p.reload(); await p.waitForFunction(() => document.querySelector('#kA.po-gen'), null, { timeout: 120000 }); await p.waitForTimeout(2500);
  ok('bez internetu aplikacja startuje i pokazuje zapisany miesiąc', (await p.locator('#b-kwota-w').getAttribute('aria-label')).length > 4, await p.locator('#b-kwota-w').getAttribute('aria-label'));
  console.log('  zrzuty:', tmp); const bledyReal = t.bledy.filter(b => !/net::ERR_INTERNET_DISCONNECTED/.test(b) && !/wysyłka (Error: (access_denied|szkic: HTTP 401)|NotAllowedError: brak uprawnień do zapisu)|status of 401 \(Unauthorized\)/.test(b)); console.log('  błędy konsoli:', JSON.stringify(bledyReal.slice(0, 6))); if (bledyReal.length) kod = 1;      // pomijamy odcięcie sieci, które test robi celowo (wysyłka bez internetu), oraz komunikaty z celowych scenariuszy negatywnych wysyłki (odmowa zgody w Outlooku, zły token → 401, błąd zapisu na pulpicie)
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
