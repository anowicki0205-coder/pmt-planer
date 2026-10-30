// Dokumenty do podpisu — cały obieg w przeglądarce: pięć kolorowych kroków (pobierz → podpisz → wgraj → sprawdzenie → wyślij; pole przeciągania między 3 a 4), prawdziwe podpisy elektroniczne (pyHanko: PAdES, XAdES, ECDSA),
// błędne podpisy (inna osoba, zmieniony dokument, dopisek po podpisie, niepodpisany plik), podpis odręczny na sztucznych skanach (także wielostronicowy PDF ze skanem),
// ręczne potwierdzenie, wysyłka na adres z odbiorca.txt, zapis wyników sprawdzenia i praca bez internetu.
// Wymaga: poppler, unzip, ImageMagick (convert) oraz python z pyhanko, lxml, pillow, numpy (PYTHON_PODPISY=/tmp/phvenv/bin/python).
// NODE_PATH=/opt/node22/lib/node_modules node podpis_offline_app.js
const { otworz, generuj } = require('./wspolne'); const fs = require('fs'), os = require('os'), path = require('path'), cp = require('child_process');
(async () => {
  const PY = process.env.PYTHON_PODPISY || '/tmp/phvenv/bin/python', DANE = path.join(__dirname, 'dane');
  const t = await otworz({ w: 1440, h: 900, opcjeSerwera: { odbiorca: 'kierownik@example.com' } }); const p = t.p; let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'podpis-'));
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
  await wgraj(kopiaZ(path.join(tmp, 'e1'), path.join(tmp, 'e1o'), dziwne).reverse());      // odwrócona kolejność: dopasowanie ma iść po zawartości i nazwie, nie po kolejności
  const s1 = await czekajStany(['ok', 'ok', 'zle', 'zle', 'czeka', 'ok', 'zle']);
  ok('tura 1: Jan (PAdES) ✓, Jan (ECDSA) ✓, inna osoba ✗, zmieniony ✗, niepodpisany plik odrzucony, XAdES ✓, dopisek po podpisie ✗', JSON.stringify(s1) === '["ok","ok","zle","zle","czeka","ok","zle"]', JSON.stringify(s1));
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
  // dokument 7 (indeks 6): poprawny podpis zamiast dopisku
  const wejscie4 = path.join(tmp, 'tylko7'); fs.mkdirSync(wejscie4, { recursive: true }); fs.copyFileSync(path.join(roz, pdfy[6]), path.join(wejscie4, pdfy[6]));
  fs.writeFileSync(path.join(tmp, 'plan4.json'), JSON.stringify({ [pdfy[6]]: 'jan' })); py('podpisz_pliki.py', wejscie4, path.join(tmp, 'e4'), path.join(tmp, 'plan4.json'));
  await wgrajInny(6); await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'czeka']);
  await wgraj(kopiaZ(path.join(tmp, 'e4'), path.join(tmp, 'e4o'), { [pdfy[6]]: pdfy[0] }));      // podpisany dokument 7 wraca pod nazwą dokumentu 1 — ma zostać rozpoznany po zawartości
  const s4 = await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok']);
  const zap4 = await zapisane();
  ok('nazwy: plik o nazwie INNEGO dokumentu rozpoznany po zawartości i nazwany jak dokument 7; ostrzeżenie w sprawdzeniu', zap4.pliki[6][0] === pdfy[6] && zap4.pliki[0][0] === pdfy[0] && zap4.weryfikacje[6].kontrole.some(c => c.id === 'nazwa' && /to nazwa innego dokumentu \(Polecenie 1\)/.test(c.tekst)), JSON.stringify(zap4.weryfikacje[6].kontrole.filter(c => c.id === 'nazwa')));
  ok('nazwy: skany zapisane jako nazwa dokumentu + .jpg (np. „…03….jpg”), nie „_skan” i nie „IMG_”', [2, 3, 4].every(i => zap4.pliki[i].length === 1 && zap4.pliki[i][0] === pdfy[i].replace(/\.pdf$/i, '.jpg')), JSON.stringify([2, 3, 4].map(i => zap4.pliki[i])));
  ok('wszystkie 7 dokumentów podpisane i sprawdzone (e-podpis PAdES/ECDSA/XAdES i odręczny)', JSON.stringify(s4) === JSON.stringify(Array(7).fill('ok')) && /Wszystkie 7 dokumentów sprawdzone/.test(await p.locator('#podp-licznik').innerText()), JSON.stringify(s4));
  ok('po sprawdzeniu wszystkiego krok 5 „Wyślij” zapala się: przestaje być szary, przycisk jest aktywny i ma akcję', await p.evaluate(() => { const k = document.querySelector('.krok-k.k5'), b = k.querySelector('button'); return k.classList.contains('aktywny') && !k.classList.contains('nieaktywny') && !b.disabled && b.dataset.akcja === 'wyslij' && /Wszystkie dokumenty sprawdzone/.test(k.querySelector('small').innerText); }));
  ok('po sprawdzeniu wszystkiego przycisk „Wyślij” jest w oknie i na kaflu, status „Podpisane”', (await p.locator('[data-akcja="wyslij"]').count()) >= 1 && /Wyślij/.test(await p.locator('#kropla-napis').innerText()) && (await p.locator('#status').innerText()).includes('Podpisane'));
  await p.screenshot({ path: tmp + '/4_wszystko.png' });

  /* ---- wysyłka: moduł w kroku 5 TEGO SAMEGO okna; hasło do paczki nadaje administrator (z terminem ważności), adres z odbiorca.txt ---- */
  const HASLO = 'Admin-Haslo-Paczki#2026', PYZ = process.env.PYZ_PYTHON || ['/tmp/pzvenv/bin/python', 'python3'].find(b => cp.spawnSync(b, ['-c', 'import pyzipper']).status === 0);
  const rozpakujAes = (zip, kat) => { fs.mkdirSync(kat, { recursive: true }); const r = cp.spawnSync(PYZ, ['-I', '-c', 'import sys, pyzipper\nz = pyzipper.AESZipFile(sys.argv[1]); z.setpassword(sys.argv[2].encode())\nz.extractall(sys.argv[3])\nprint(len(z.namelist()))', zip, HASLO, kat], { encoding: 'utf8' }); return r.status === 0 ? Number(r.stdout.trim()) : -1; };
  const stanW = () => p.locator('#podp-wyslij-stan').innerText();
  const krok5 = p.locator('.krok-k.k5');
  ok('„Wyślij” jest krokiem 5 w tym samym oknie co pobieranie, podpis i wgrywanie; pokazuje adres z odbiorca.txt i nie ma żadnych dodatkowych opcji wysyłki', (await p.locator('#arkusz .krok-k.k5 [data-akcja="wyslij"]').count()) === 1 && /do kierownik@example\.com/.test(await krok5.innerText()) && (await p.locator('#arkusz #w-mailto, #arkusz #w-udostepnij, #arkusz #w-eml, #arkusz #w-haslo, #arkusz input[type=password], #arkusz #w-odb').count()) === 0 && !/Otwórz pocztę|dołączę sam|Udostępnij pliki|Kierownik regionu/.test(await p.locator('#arkusz').innerText()));
  await p.screenshot({ path: tmp + '/5_wyslij.png' });

  /* administrator jeszcze nie ustawił hasła → wysyłka wyłączona, jasny komunikat, nic się nie pobiera */
  await p.click('#arkusz .krok-k.k5 [data-akcja="wyslij"]'); await p.waitForFunction(() => /nie jest jeszcze włączona/.test(document.querySelector('#podp-wyslij-stan').textContent), null, { timeout: 30000 });
  ok('administrator nie ustawił hasła (zakładka Ustawienia pusta) → komunikat „wysyłka nie jest jeszcze włączona”, przycisk znów aktywny, nic nie zostało pobrane', /administrator nie ustawił hasła/i.test(await stanW()) && !(await p.locator('#arkusz .krok-k.k5 button').isDisabled()) && (await p.locator('#w-oznacz').count()) === 0);
  /* hasło po terminie → komunikat z datą, hasła nie ma nigdzie */
  t.backend.paczka = { haslo: HASLO, wazne_do: '2020-01-01' };
  await p.click('#arkusz .krok-k.k5 [data-akcja="wyslij"]'); await p.waitForFunction(() => /wygasło/.test(document.querySelector('#podp-wyslij-stan').textContent), null, { timeout: 30000 });
  ok('hasło po terminie ważności → „wygasło 01.01.2020, poczekaj na nowe od administratora”; serwer go nie wydał, więc nie ma go w stronie', /wygasło 01\.01\.2020/.test(await stanW()) && !(await p.evaluate(h => document.documentElement.outerHTML.includes(h) || JSON.stringify(window.__pmtDane.czytaj()).includes(h), HASLO)));
  /* hasło za krótkie */
  t.backend.paczka = { haslo: 'krotkie', wazne_do: '2099-12-31' };
  await p.click('#arkusz .krok-k.k5 [data-akcja="wyslij"]'); await p.waitForFunction(() => /za krótkie/.test(document.querySelector('#podp-wyslij-stan').textContent), null, { timeout: 30000 });
  ok('hasło ustawione przez administratora poniżej 8 znaków jest odrzucane z komunikatem (paczka nie powstaje)', /minimum 8 znaków/.test(await stanW()));
  /* prawidłowe hasło i termin → jedno kliknięcie = gotowa wiadomość */
  t.backend.paczka = { haslo: HASLO, wazne_do: '2099-12-31' }; const pob0 = t.backend.pobraniaHasla;
  const emlP = await pobierz('#arkusz .krok-k.k5 [data-akcja="wyslij"]');
  ok('jedno kliknięcie „Wyślij” pobiera gotową wiadomość .eml; krok 5 mówi, co z nią zrobić; hasło pobrano z serwera (1 raz), a użytkownik go nigdzie nie widzi', emlP.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && /Kliknij ją/.test(await stanW()) && t.backend.pobraniaHasla === pob0 + 1 && !(await p.evaluate(h => document.body.innerText.includes(h), HASLO)));
  await p.screenshot({ path: tmp + '/6_po_wyslaniu.png' });
  ok('hasło jest zapamiętane tylko w zaszyfrowanym koncie (do wysyłki bez internetu do terminu ważności), nie w tekście strony', await p.evaluate(h => { const c = window.__pmtDane.czytaj().ustawienia.paczka; return c && c.haslo === h && c.wazne_do === '2099-12-31'; }, HASLO));
  const emlWynik = JSON.parse(cp.spawnSync(PYZ, ['-I', '-c', `
import sys, json, email, email.policy, io, os, pyzipper
raw = open(sys.argv[1], 'rb').read(); m = email.message_from_bytes(raw, policy=email.policy.default)
cz = list(m.iter_attachments()); z = pyzipper.AESZipFile(io.BytesIO(cz[0].get_content())); z.setpassword(sys.argv[2].encode())
tr = m.get_body(preferencelist=('plain',)).get_content()
os.makedirs(sys.argv[3], exist_ok=True); z.extractall(sys.argv[3])
print(json.dumps({'x': m['X-Unsent'], 'to': m['To'], 'temat': str(m['Subject']), 'tresc': tr, 'zal': len(cz), 'nazwa': cz[0].get_filename(), 'pliki': z.namelist(), 'ascii': all(b < 128 for b in raw), 'jawne': any(s in raw for s in (b'Jan Testowy', b'90010112349', b'Admin-Haslo'))}))`, emlP.sciezka, HASLO, path.join(tmp, 'zEml')], { encoding: 'utf8' }).stdout);
  ok('wiadomość: adresat z odbiorca.txt, temat „[PMT] Delegacje — Jan Testowy — …”, nagłówek X-Unsent, dokładnie jeden załącznik ZIP', emlWynik.x === '1' && emlWynik.to === 'kierownik@example.com' && /^\[PMT\] Delegacje — Jan Testowy — \S+ 20\d\d$/.test(emlWynik.temat) && emlWynik.zal === 1 && /^Dokumenty_Jan_Testowy_.*\.zip$/.test(emlWynik.nazwa), JSON.stringify([emlWynik.x, emlWynik.to, emlWynik.temat, emlWynik.zal, emlWynik.nazwa]));
  ok('treść jest krótka, mówi o zahasłowanej paczce, liczbie plików i że hasło przekazano osobno; podpisana imieniem; bez hasła i PESEL-u', /zahasłowana paczka \(ZIP\)/.test(emlWynik.tresc) && /\(\d+ pl\S+\)/.test(emlWynik.tresc) && /przekazane osobno/.test(emlWynik.tresc) && /Jan Testowy\s*$/.test(emlWynik.tresc) && !emlWynik.tresc.includes(HASLO) && !/\d{11}/.test(emlWynik.tresc), JSON.stringify(emlWynik.tresc).slice(0, 140));
  ok('plik .eml jest czystym ASCII i nie zawiera jawnie imienia z dokumentów, PESEL-u ani hasła', emlWynik.ascii && !emlWynik.jawne);
  ok('paczka z wiadomości odszyfrowuje się hasłem administratora, a pliki mają nazwy nadane przy generowaniu', emlWynik.pliki.length >= 7 && emlWynik.pliki.every(n => pdfy.some(f => n === f || n === f + '.xades' || n === f.replace(/\.pdf$/i, '.jpg'))), emlWynik.pliki.join(', '));
  const wyslane = emlWynik.pliki;
  ok('załączniki: każdy plik ma nazwę nadaną przy generowaniu (PDF-y, .pdf.xades razem z oryginałem, skany jako nazwa dokumentu + .jpg)', wyslane.filter(n => /\.pdf$/i.test(n)).length >= 4 && wyslane.includes(pdfy[5] + '.xades') && wyslane.includes(pdfy[5]) && [2, 3, 4].every(i => wyslane.includes(pdfy[i].replace(/\.pdf$/i, '.jpg'))) && wyslane.every(n => pdfy.some(f => n === f || n === f + '.xades' || n === f.replace(/\.pdf$/i, '.jpg'))) && !wyslane.some(n => /_skan|IMG_|_signed|podpisany|zalacznik|podpis_xml|_str/.test(n)), wyslane.join(', '));
  /* bez internetu: hasło z pamięci konta (jeszcze ważne) wystarcza; bez pamięci — jasny komunikat */
  t.backend.martwy = true;
  const emlOff = await pobierz('#arkusz .krok-k.k5 [data-akcja="wyslij"]');
  ok('bez internetu wysyłka działa na zapamiętanym haśle (ważnym do terminu) — paczka otwiera się tym samym hasłem administratora', emlOff.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && JSON.parse(cp.spawnSync(PYZ, ['-I', '-c', 'import sys, json, email, email.policy, io, pyzipper\nm = email.message_from_bytes(open(sys.argv[1], "rb").read(), policy=email.policy.default)\nz = pyzipper.AESZipFile(io.BytesIO(list(m.iter_attachments())[0].get_content())); z.setpassword(sys.argv[2].encode()); print(json.dumps(len(z.namelist())))', emlOff.sciezka, HASLO], { encoding: 'utf8' }).stdout) >= 7);
  await p.evaluate(() => { const d = window.__pmtDane.czytaj(); delete d.ustawienia.paczka; window.__pmtDane.zapisz(d); });
  await p.click('#arkusz .krok-k.k5 [data-akcja="wyslij"]'); await p.waitForFunction(() => /Brak połączenia/.test(document.querySelector('#podp-wyslij-stan').textContent), null, { timeout: 60000 });
  ok('bez internetu i bez zapamiętanego hasła: „Brak połączenia — nie mogę pobrać hasła do paczki”', /Brak połączenia/.test(await stanW()));
  t.backend.martwy = false;
  await p.click('#w-oznacz').catch(() => {}); if (!(await p.locator('#status').innerText()).includes('Wysłane')) { await p.click('#arkusz .krok-k.k5 [data-akcja="wyslij"]'); await p.waitForSelector('#w-oznacz', { timeout: 60000 }); await p.click('#w-oznacz'); }
  await p.waitForTimeout(800);
  ok('„Oznacz jako wysłane” (pod krokiem 5) zmienia stan na „Wysłane”', (await p.locator('#status').innerText()).includes('Wysłane'));

  /* ---- zapis wyników sprawdzenia ---- */
  await p.reload(); await p.waitForFunction(() => document.querySelector('#kA.po-gen'), null, { timeout: 120000 }); await p.waitForTimeout(2500);
  ok('stan „Wysłane” przetrwał odświeżenie', (await p.locator('#status').innerText()).includes('Wysłane'));
  await p.click('#cofnij'); await p.waitForTimeout(600);
  ok('„Cofnij wysłanie” przywraca podpisane (wyniki sprawdzenia zostały zapamiętane)', (await p.locator('#status').innerText()).includes('Podpisane'));
  await p.click('#podpisz'); await p.waitForSelector('#dok-siatka'); await p.waitForTimeout(800);      // gdy wszystko podpisane, główny przycisk otwiera to samo okno z dokumentami (krok 5 „Wyślij”)
  ok('po odświeżeniu okno pokazuje te same, zapamiętane wyniki sprawdzenia (7 × podpis sprawdzony)', JSON.stringify(await stany()) === JSON.stringify(Array(7).fill('ok')) && /Podpisał\(a\): Jan Testowy/.test(await komunikat(0)));

  /* ---- wysyłka z dużymi skanami: ostrzeżenie o limicie poczty ---- */
  // dwa zdjęcia tego samego dokumentu (dwie strony): numerowane _str01, _str02
  const dwa = path.join(tmp, 'dwa'); fs.mkdirSync(dwa, { recursive: true }); const baza4 = pdfy[4].replace(/\.pdf$/i, ''), jpg2 = lista(path.join(tmp, 's2'))[2];
  fs.copyFileSync(jpg2, path.join(dwa, baza4 + '_a.jpg')); fs.copyFileSync(jpg2, path.join(dwa, baza4 + '_b.JPEG'));
  await wgrajInny(4); await czekajStany(['ok', 'ok', 'ok', 'ok', 'czeka', 'ok', 'ok']);
  await wgraj(lista(dwa)); await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok']);
  const zap5 = await zapisane();
  ok('nazwy: dwa zdjęcia jednego dokumentu → „…_str01.jpg” i „…_str02.jpg” (rozszerzenie JPEG ujednolicone do jpg)', JSON.stringify(zap5.pliki[4]) === JSON.stringify([baza4 + '_str01.jpg', baza4 + '_str02.jpg']) && Object.values(zap5.pierwotne[4]).sort().join('|') === [baza4 + '_a.jpg', baza4 + '_b.JPEG'].sort().join('|'), JSON.stringify(zap5.pliki[4]));
  const duzy = path.join(tmp, 'duzy'); fs.mkdirSync(duzy, { recursive: true });
  const jpg = fs.readFileSync(lista(path.join(tmp, 's2'))[2]); fs.writeFileSync(path.join(duzy, norm(pdfy[4]).replace(/\.pdf$/, '') + '_skan.jpg'), Buffer.concat([jpg, Buffer.alloc(21 * 1048576)]));
  await wgrajInny(4); await czekajStany(['ok', 'ok', 'ok', 'ok', 'czeka', 'ok', 'ok']);
  await wgraj(lista(duzy)); await czekajStany(['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok']);
  const duzyEml = await pobierz('#arkusz .krok-k.k5 [data-akcja="wyslij"]');
  ok('przy paczce powyżej 20 MB krok 5 ostrzega przed limitem poczty (wiadomość jest mimo to gotowa)', duzyEml.nazwa === 'PMT_wiadomosc_do_wyslania.eml' && /20–25 MB/.test(await stanW()), await stanW());
  await p.click('#w-oznacz'); await p.waitForTimeout(800);

  /* ---- praca bez internetu: service worker zapisał aplikację (w tym nowe moduły sprawdzania podpisów); na zwykłym http przeglądarka go nie dopuszcza ---- */
  if (!bezpieczny) {
    ok('http: aplikacja działa w całości, ale bez trybu offline (przeglądarka nie dopuszcza service workera na zwykłym http)', (await p.evaluate(async () => (navigator.serviceWorker ? (await navigator.serviceWorker.getRegistrations()).length : 0))) === 0);
    console.log('  zrzuty:', tmp); const bledyReal = t.bledy.filter(b => !/net::ERR_INTERNET_DISCONNECTED/.test(b)); console.log('  błędy konsoli:', JSON.stringify(bledyReal.slice(0, 6))); if (bledyReal.length) kod = 1;      // pomijamy odcięcie sieci, które test robi celowo (wysyłka bez internetu)
    await t.zamknij(); process.exit(kod);
  }
  await p.waitForFunction(async () => { const k = await caches.keys(); if (!k.length) return false; const c = await caches.open(k[0]); const u = (await c.keys()).map(r => r.url); return u.length >= 25 && u.some(x => /weryfikacja\.js/.test(x)) && u.some(x => /podpis_reczny\.js/.test(x)); }, null, { timeout: 120000 });
  await t.ctx.setOffline(true);
  await p.reload(); await p.waitForFunction(() => document.querySelector('#kA.po-gen'), null, { timeout: 120000 }); await p.waitForTimeout(2500);
  ok('bez internetu aplikacja startuje i pokazuje zapisany miesiąc', (await p.locator('#b-kwota-w').getAttribute('aria-label')).length > 4, await p.locator('#b-kwota-w').getAttribute('aria-label'));
  console.log('  zrzuty:', tmp); const bledyReal = t.bledy.filter(b => !/net::ERR_INTERNET_DISCONNECTED/.test(b)); console.log('  błędy konsoli:', JSON.stringify(bledyReal.slice(0, 6))); if (bledyReal.length) kod = 1;      // pomijamy odcięcie sieci, które test robi celowo (wysyłka bez internetu)
  await t.zamknij(); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
