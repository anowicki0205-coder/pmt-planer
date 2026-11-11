// PMT Planer (web) — podpisywanie, sprawdzanie podpisów i wysyłka dokumentów miesiąca.
// Okno „Dokumenty do podpisu” prowadzi czterema krokami (czwarty, „Wyślij”, jest szary, dopóki wszystkie dokumenty nie są wgrane i sprawdzone). Dawny krok „Pobierz dokumenty” (ZIP albo osobne pliki)
// zniknął (decyzja właściciela, 9.11): pobieranie jest teraz częścią kroku „Podpisz”, a numery w oknie to 1–4 (nazwy klas CSS .k2…k5 zostały — numeracja w nich pochodzi z czasów pięciu kroków):
//   1. Podpisz: elektronicznie na gov.pl (Profil Zaufany). W Chrome i Edge na komputerze dokumenty zapisują się w FOLDZIE NA PULPICIE (wskazanym raz — js/folder.js), a aplikacja sama zauważa podpisane pliki, które użytkownik
//      zapisze w tym folderze, wczytuje je i sprawdza (bez ręcznego wgrywania). Gdzie tego nie ma (Firefox, Safari, telefon) — dokumenty pobiera się POJEDYNCZO jako PDF (każdy ma swój przycisk), dopiero po pobraniu odblokowuje się „Otwórz gov.pl”
//      (strona gov.pl nie przyjmuje plików z zewnątrz: przeglądarka nie pozwala wypełnić okna wyboru pliku, więc pliki idą przez dysk) — albo odręcznie (wydruk),
//   2. Wgraj podpisane pliki (PDF z podpisem, plik .xades, paczka ZIP z gov.pl, skany i zdjęcia — wszystkie naraz; aplikacja sama dopasowuje je do dokumentów),
//   3. Sprawdzenie: dla każdego dokumentu — czy jest podpis, czy obejmuje całość, czy dokument nie został zmieniony, czy podpisała właściwa osoba (imię i nazwisko, PESEL),
//      a przy podpisie odręcznym — czy na skanie widać podpis w miejscu „podpis pracownika”. Dopiero sprawdzone dokumenty liczą się jako podpisane. ROZLICZENIE WYDATKÓW podpisu nie wymaga
//      (przyjmuję je z podpisem i bez; plik pobrany bez zmian też jest w porządku),
//   4. Wyślij: zahasłowana paczka i gotowa wiadomość na wskazany adres (hasło nadaje administrator — js/dostep.js pobierzHasloPaczki). Pole „albo przeciągnij tu podpisane pliki” leży między krokiem 2 a 3 — tam, gdzie się wgrywa.
import { scalPdf, dopasujPliki, rozpakujZip, zawieraOryginal, normalizujNazwe } from './pliki.js';
import { zipujKlasycznie } from './zipklasyczny.js';
import { zipujAes } from './zipaes.js';
import { zbudujEml, wczytajSposobWysylki } from './poczta.js';
import { dzwiek } from './dzwiek.js';
import { wczytajKlienta, pobierzKod, wymienKod, utworzSzkic, komunikatBledu } from './outlook.js';
import { karuzela } from './karuzela.js';
import { obslugiwany as folderMozliwy, wczytajFolder, zapamietajFolder, zapomnijFolder, wskazFolder, zgoda as zgodaFolderu, podfolder, korzenDelegacji, NAZWA_FOLDERU, zapiszPlik, wypisz as wypiszFolder } from './folder.js';
import { atrapaHtml, daneDelegacji, daneRozliczenia } from './dokument_atrapa.js';
import { ocenPodpisElektroniczny, podpisyWPdf, czasPl, xadesDotyczy } from './weryfikacja.js';
import { stronyZeSkanu, szukajPodpisu, strefaPodpisu, obrazyZPdf, skanBezJpeg } from './podpis_reczny.js';
import { wpisyZUpuszczenia, przejdzWpisy, obslugiwanyPlik } from './upuszczanie.js';

const TYPY = { pdf: 'application/pdf', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', heic: 'image/heic', heif: 'image/heif', webp: 'image/webp', tif: 'image/tiff', tiff: 'image/tiff',
  xades: 'application/xml', xml: 'application/xml', sig: 'application/octet-stream', p7s: 'application/pkcs7-signature', p7m: 'application/pkcs7-mime' };
const rozszerzenie = n => (String(n).toLowerCase().match(/\.([a-z0-9]+)$/) || [, ''])[1];
const rozNorm = n => { const r = rozszerzenie(n); return r === 'jpeg' ? 'jpg' : r === 'tif' ? 'tiff' : r === 'xml' ? 'xades' : r; };
const typPliku = n => TYPY[rozszerzenie(n)] || 'application/octet-stream';
const OBRAZ = /\.(png|jpe?g|heic|heif|webp|tiff?|gif|bmp)$/i, XADES = /\.(xades|xml)$/i, INNY_PODPIS = /\.(sig|p7s|p7m)$/i;
const AKCEPT = '.pdf,.xades,.xml,.zip,.png,.jpg,.jpeg,.heic,.heif,.webp,application/pdf,application/zip,image/*';
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const liczba = (n, jeden, kilka, wiele) => n === 1 ? jeden : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 > 20)) ? kilka : wiele;
const mb = b => b < 52429 ? '<0,1 MB' : (b / 1048576).toFixed(1).replace('.', ',') + ' MB';
const czekaj = ms => new Promise(r => setTimeout(r, ms));
const LIMIT_POCZTY = 20 * 1048576;      // typowy limit załączników poczty to 20–25 MB
const LIMIT_GOV = 5;                    // gov.pl przyjmuje naraz do 5 plików (każdy do 25 MB)
const IKONA_STANU = { ok: 'i-ok', zle: 'i-zamknij', uwaga: 'i-info', info: 'i-info' };

export function zainstalujPodpis(k) {
  const { $, ik, arkTresc, bezZnacznikow: esc, bezOgonkow, pokazToast, magPliki, magMiesiace, magUst } = k;
  const M = () => k.M();
  const rec = () => magMiesiace.daj(M().rok, M().mies) || {};
  const rejestr = () => rec().podpisaniPliki || {};
  const weryfikacje = () => rec().weryfikacje || {};
  const listaZ = v => Array.isArray(v) ? v : v ? [v] : [];
  const plikiDok = i => listaZ(rejestr()[i]);
  const pierwotne = () => rec().pierwotneNazwy || {};      // { i: { zapisana nazwa: nazwa, z jaką plik wrócił } }
  const nazwaWgranego = (i, orig) => { const o = pierwotne()[i] || {}; return Object.keys(o).find(n => o[n] === orig) || orig; };
  let wgrane = [];                // pliki z ostatnich wgrań: { plik, bajty, i, jak, powod, rodzaj }
  let partia = new Set();         // pierwotne nazwy plików z ostatniego wgrania (pliki dokumentu spoza niego to starsze wersje, które nowy podpis może zastąpić)
  let widok = 'glowny', otwarte = new Set(); const sprawdzane = new Set();
  /* Dwa wyglądy okna: ASYSTENT (domyślny w każdej przeglądarce: jedna rzecz do zrobienia naraz) i KLASYCZNY (wszystkie cztery kroki naraz — dla kogoś, kto woli widzieć całość; przełącznik na dole asystenta
     i okna klasycznego, wybór pamiętany na urządzeniu). Przeglądarki z dostępem do folderów (Chrome, Edge na komputerze) mają zawsze asystenta — klasycznego okna tam nie ma. */
  let widokPodpisu = (() => { try { return localStorage.getItem('pmt-ui-widok-podpisu') === 'klasyczny' ? 'klasyczny' : 'asystent'; } catch (e) { return 'asystent'; } })();
  const uzywaAsystenta = () => folderMozliwy() || widokPodpisu !== 'klasyczny';
  const ustawWidokPodpisu = w => { widokPodpisu = w === 'klasyczny' ? 'klasyczny' : 'asystent'; try { localStorage.setItem('pmt-ui-widok-podpisu', widokPodpisu); } catch (e) { /* bez pamięci przeglądarki wybór obowiązuje do zamknięcia okna */ } pokaz('glowny'); };

  /* ---------------------------------- pomocnicze ---------------------------------- */
  const nagl = (tytul, wstecz) => `<div class="ark-gora">${wstecz ? `<button type="button" class="ark-wstecz" data-akcja="glowny" aria-label="Wstecz">${ik('i-lewo')}</button>` : ''}<h2 id="ark-tyt">${tytul}</h2><button type="button" class="ark-zam" data-zamknij aria-label="Zamknij">${ik('i-zamknij')}</button></div>`;
  const wszystkoPodpisane = () => k.razemDok() > 0 && k.ilePodpisanych() >= k.razemDok();
  /* Pobrane (jako PDF) dokumenty tego miesiąca: dopiero po pierwszym pobraniu odblokowuje się „Otwórz gov.pl”. Pamięć na urządzeniu (jak inne ustawienia miesiąca); po ponownym generowaniu zerowana. */
  const kluczPobrane = () => 'pobrane-' + magMiesiace.klucz(M().rok, M().mies);
  const pobrane = () => { const v = magUst.daj(kluczPobrane(), []); return new Set(Array.isArray(v) ? v : []); };
  const oznaczPobrane = idx => { const s = pobrane(); idx.forEach(i => s.add(i)); magUst.ustaw(kluczPobrane(), [...s]); };
  const nazwaZip = () => `Dokumenty_${bezOgonkow(k.PROFIL().imie).replace(/\s+/g, '_')}_${bezOgonkow(String(k.MIES[M().mies - 1]))}_${M().rok}.zip`;
  async function oryginal(d) { return magPliki.daj(k.klucz(d.nazwa)); }
  async function oryginaly() { const wyn = []; for (const d of k.nazwyDok()) { const b = await oryginal(d); if (b) wyn.push({ d, bajty: b }); } return wyn; }
  const miejscaPodpisu = d => ((M().wynik || {}).miejsca_podpisu || {})[d.nazwa] || null;

  /* ---------------------------------- widok główny: cztery kroki ---------------------------------- */
  const stanKarty = i => { const w = weryfikacje()[i]; if (sprawdzane.has(i)) return 'trwa'; if (!w) return plikiDok(i).length ? 'trwa' : 'czeka'; return M().podpisane[i] ? 'ok' : (w.stan === 'zle' ? 'zle' : 'uwaga'); };
  const CHIP = { czeka: 'czeka na podpis', trwa: 'sprawdzam…', ok: 'podpis sprawdzony', uwaga: 'do sprawdzenia', zle: 'błąd podpisu' };
  const CHIP_ROZL = { czeka: 'czeka na plik', trwa: 'sprawdzam…', ok: 'przyjęte', uwaga: 'do sprawdzenia', zle: 'błąd podpisu' };      // rozliczenie wydatków nie wymaga podpisu: czeka na PLIK, a po sprawdzeniu jest „przyjęte”
  const chip = (d, st) => (d && d.rozliczenie ? CHIP_ROZL : CHIP)[st];
  function komunikatKarty(i) {
    const w = weryfikacje()[i]; if (!w) return plikiDok(i).length ? 'Sprawdzam plik…' : (k.nazwyDok().find(x => x.i === i) || {}).rozliczenie ? 'Wgraj ten dokument — podpis nie jest wymagany (może być plik pobrany bez zmian)' : 'Wgraj podpisany plik tego dokumentu';
    if (M().podpisane[i]) return w.potwierdzone ? (w.bezWymogu ? 'Plik potwierdzony przez Ciebie' : 'Podpis potwierdzony przez Ciebie') : w.bezWymogu ? 'Rozliczenie przyjęte — podpis nie jest na nim wymagany' : w.rodzaj === 'odreczny' ? 'Widzę podpis w miejscu „podpis pracownika”' : `Podpisał(a): ${esc(w.sygnatariusz || '—')}${w.czas ? ' · ' + czasPl(new Date(w.czas)) : ''}`;
    const zly = (w.kontrole.find(c => c.stan === 'zle') || w.kontrole.find(c => c.stan === 'uwaga')); return zly ? esc(zly.tekst) : 'Wymaga sprawdzenia';
  }
  function szczegoly(d) {
    const w = weryfikacje()[d.i]; if (!w) return '';
    const pliki = plikiDok(d.i), mozna = !M().podpisane[d.i] && !w.potwierdzone && (w.rodzaj === 'odreczny' || (w.rodzaj !== 'brak' && !w.kontrole.some(c => c.stan === 'zle')));
    return `<div class="dok-szcz"><ul class="kontrole">${w.kontrole.map(c => `<li class="kt-${c.stan}">${ik(IKONA_STANU[c.stan] || 'i-info')}<span>${esc(c.tekst)}</span></li>`).join('')}</ul>
      ${w.podglad ? `<figure class="podglad-podpisu"><img src="${w.podglad}" alt="Wycinek skanu z miejscem na podpis"><figcaption>Tak widzę miejsce „podpis pracownika” na skanie</figcaption></figure>` : ''}
      <small class="dok-plik">Plik: ${esc(pliki.join(', '))}</small>
      <div class="dok-akcje">${mozna ? `<button type="button" class="przycisk maly glowny" data-akcja="potwierdz" data-i="${d.i}">${ik('i-ok')}${w.bezWymogu ? 'Potwierdzam, że to właściwy dokument' : 'Potwierdzam, że podpis jest'}</button>` : ''}<button type="button" class="przycisk maly" data-akcja="cofnij" data-i="${d.i}">${ik('i-cofnij')}Wgraj inny plik</button><button type="button" class="przycisk maly" data-akcja="szczegoly" data-i="${d.i}">Zwiń</button></div></div>`;
  }
  let fokusI = null;              // dokument wskazany z probówki na pulpicie: jego karta na liście mruga (znacznik przeżywa ponowne rysowanie listy)
  let widziane = {};              // stan każdej karty z ostatniego narysowania: efekty (podpis „rysuje się”, zły dokument drży) tylko przy ZMIANIE stanu, nie przy każdym odświeżeniu
  const nowyStan = i => widziane[i] !== undefined && widziane[i] !== stanKarty(i);
  /* Dźwięk przy ZMIANIE stanu dokumentów (tak samo jak efekt wizualny „rysującego się” podpisu): podpis sprawdzony, zły dokument, a gdy wszystkie są poprawne — dłuższy akord. */
  const zapamietajStany = () => {
    const nowe = {}; let nowoOk = 0, nowoZle = 0;
    k.nazwyDok().forEach(d => { const st = stanKarty(d.i); nowe[d.i] = st; const o = widziane[d.i]; if (o !== undefined && o !== st) { if (st === 'ok') nowoOk++; else if (st === 'zle') nowoZle++; } });
    const wszystkie = Object.values(nowe).length > 0 && Object.values(nowe).every(st => st === 'ok'), bylo = Object.keys(widziane).length > 0 && Object.values(widziane).every(st => st === 'ok');
    widziane = nowe;
    if (wszystkie && nowoOk && !bylo) dzwiek.efekt('wszystkie'); else if (nowoOk) dzwiek.efekt('ok'); else if (nowoZle) dzwiek.efekt('zle');
  };
  function kartaDok(d) {
    const st = stanKarty(d.i), otw = otwarte.has(d.i) && st !== 'czeka', wys = wyslane() && st === 'ok';      // po wysłaniu zamiast „Otwórz” karta pokazuje, że dokument poszedł
    const szczegolyBtn = st !== 'czeka' && st !== 'trwa' ? `<button type="button" class="przycisk maly" data-akcja="szczegoly" data-i="${d.i}">Szczegóły</button>` : '';
    return `<div class="dok-k st-${st}${nowyStan(d.i) ? ' nowy' : ''}${fokusI === d.i ? ' blysk' : ''}${wys ? ' wyslano' : ''}${otw ? ' otwarta' : ''}" data-i="${d.i}"><div class="dok-k-g"><b>${d.tytul}</b><span class="stan st-${st}"><i></i>${wys ? 'wysłano' : chip(d, st)}</span></div><small>${d.opis}</small>
      <p class="dok-kom">${komunikatKarty(d.i)}</p>
      ${otw ? szczegoly(d) : wys ? `<div class="dok-akcje"><span class="dok-wyslano">${ik('i-ok')}Wysłano${M().wyslaneKiedy ? ' ' + dataPl(M().wyslaneKiedy) : ''}</span>${szczegolyBtn}</div>` : `<div class="dok-akcje"><button type="button" class="przycisk maly" data-akcja="otworz" data-nazwa="${esc(d.nazwa)}">Otwórz</button>${szczegolyBtn}</div>`}</div>`;
  }
  const listaKart = () => `<div class="dok-siatka" id="dok-siatka">${k.nazwyDok().map(kartaDok).join('')}</div>`;

  /* ---------------------------------- widok 3D: karuzela z atrapami dokumentów ---------------------------------- */
  // Domyślnie WIDOK 3D, „Karty” (lista) to opcja (decyzja właściciela po teście, 4.11 — wcześniej było odwrotnie); wybór pamiętany na urządzeniu. Nowy klucz (nie dawny „pmt-ui-karty”), żeby wybór sprzed zmiany domyślnej nie przesłonił nowego widoku.
  let widokKart = (() => { try { return localStorage.getItem('pmt-ui-widok-dok') === 'lista' ? 'lista' : '3d'; } catch (e) { return '3d'; } })();
  let kar = null;                 // aktywna karuzela
  let podgladI = null;            // numer dokumentu w powiększonym podglądzie (tylko w widoku 3D)
  let przodI = 0;                 // która karta była z przodu (wraca po powiększeniu)
  const ruchDozwolony = () => !!k.zycie && !matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ctxDok = () => { const p = k.PROFIL() || {}, w = M().wynik || {}; return { imie: p.imie || '', pesel: p.pesel || '', adres: p.adres || '', stanowisko: p.stanowisko || 'merchandiser', przelozony: w.przelozony || '', miesiac: String(k.MIES[M().mies - 1] || ''), rok: M().rok }; };
  const daneDok = d => { const w = M().wynik; if (!w) return null; const pol = M().polecenia || []; return d.i < pol.length ? daneDelegacji(w, pol[d.i].nr, ctxDok()) : daneRozliczenia(w, ctxDok()); };
  const przelacznikWidoku = () => `<div class="k3-przel" role="group" aria-label="Sposób wyświetlania dokumentów"><button type="button" data-akcja="widok" data-w="3d" aria-pressed="${widokKart === '3d'}">${ik('i-pioro')}Widok 3D</button><button type="button" data-akcja="widok" data-w="lista" aria-pressed="${widokKart === 'lista'}">Karty</button></div>`;      // „Widok 3D” pierwszy (domyślny), „Karty” jako opcja
  function karta3d(d) {
    const st = stanKarty(d.i), wys = wyslane() && st === 'ok', dane = daneDok(d);
    return `<div class="karta3d k3-${st}${nowyStan(d.i) ? ' k3-nowy' : ''}${wys ? ' wyslano' : ''}" data-i="${d.i}" role="group" aria-label="${esc(d.tytul)}: ${wys ? 'wysłano' : chip(d, st)}">
      <div class="k3-gl"><b>${d.tytul}</b><span class="stan st-${st}"><i></i>${wys ? 'wysłano' : chip(d, st)}</span></div>
      ${dane ? atrapaHtml(dane, { stan: st, maks: 6, wyslano: wys, nowy: nowyStan(d.i) }) : '<div class="da-papier"></div>'}
      <div class="k3-st"><span>${d.opis}</span><div class="k3-akcje"><button type="button" class="przycisk maly" data-akcja="powieksz" data-i="${d.i}" tabindex="-1">Powiększ</button>${wys ? `<span class="dok-wyslano">${ik('i-ok')}Wysłano</span>` : `<button type="button" class="przycisk maly" data-akcja="otworz" data-nazwa="${esc(d.nazwa)}" tabindex="-1">Otwórz</button>`}</div></div></div>`;
  }
  const kropkiKart = () => k.nazwyDok().map(d => { const st = stanKarty(d.i); return `<button type="button" class="k3-kropka k3-${st}${d.i === przodI ? ' akt' : ''}" data-akcja="k3-do" data-i="${d.i}" title="${esc(d.tytul)} — ${chip(d, st)}" aria-label="${esc(d.tytul)}: ${chip(d, st)}"></button>`; }).join('');
  const nazwaPrzodu = () => { const d = k.nazwyDok()[przodI]; return d ? `${d.tytul} · ${chip(d, stanKarty(d.i))} (${przodI + 1} z ${k.razemDok()})` : ''; };
  const widok3d = () => `<div class="k3-wrap" id="dok-siatka">
      <div class="k3-pasek" id="k3-pasek" aria-label="Stan wszystkich dokumentów">${kropkiKart()}</div>
      <div class="k3-scena" id="k3-scena" tabindex="0" role="group" aria-roledescription="karuzela" aria-label="Dokumenty do podpisu — strzałki obracają, Enter powiększa wybrany dokument"><div class="k3-podloga"></div><div class="k3-pier" id="k3-pier">${k.nazwyDok().map(karta3d).join('')}</div></div>
      <div class="k3-dol"><button type="button" class="przycisk ikb" data-akcja="k3-lewo" aria-label="Poprzedni dokument">‹</button><span class="k3-nazwa" id="k3-nazwa" aria-live="polite">${esc(nazwaPrzodu())}</span><button type="button" class="przycisk ikb" data-akcja="k3-prawo" aria-label="Następny dokument">›</button></div></div>`;
  function podglad3d(i) {
    const d = k.nazwyDok()[i]; if (!d) return '';
    const st = stanKarty(i), wys = wyslane() && st === 'ok', dane = daneDok(d), sz = szczegoly(d);
    return `<div class="k3-podglad" id="dok-siatka" data-i="${i}">
      <div class="k3-pg-gora"><button type="button" class="przycisk maly" data-akcja="k3-wroc">${ik('i-lewo')}Wróć do karuzeli</button><b>${d.tytul} <small>· ${d.opis}</small></b>
        <span class="k3-pg-nawig"><button type="button" class="przycisk ikb" data-akcja="k3-poprz" aria-label="Poprzedni dokument">‹</button><button type="button" class="przycisk ikb" data-akcja="k3-nast" aria-label="Następny dokument">›</button></span></div>
      <div class="k3-pg-tresc"><div class="k3-pg-kartka">${dane ? atrapaHtml(dane, { stan: st, pelnyPesel: true, wyslano: wys, nowy: nowyStan(i) }) : ''}</div>
        <aside class="k3-pg-panel k3-${st}"><span class="stan st-${st}"><i></i>${wys ? 'wysłano' : chip(d, st)}</span><p class="dok-kom">${wys ? `Wysłano${M().wyslaneKiedy ? ' ' + dataPl(M().wyslaneKiedy) : ''}` : komunikatKarty(i)}</p>${sz}
          <div class="dok-akcje"><button type="button" class="przycisk maly" data-akcja="otworz" data-nazwa="${esc(d.nazwa)}">Otwórz plik PDF</button></div>
          <small class="k3-pg-uwaga">To podgląd danych z wygenerowanego dokumentu (układ jak w pliku PDF). Sprawdź imię, adres, trasę i kwoty przed podpisem.</small></aside></div></div>`;
  }
  const obszarKart = () => widokKart === '3d' ? (podgladI !== null ? podglad3d(podgladI) : widok3d()) : listaKart();
  function zatrzymajKaruzele() { if (kar) { kar.zniszcz(); kar = null; } }
  /** Po wstawieniu widoku do okna: uruchamia karuzelę (tylko w widoku 3D i nie w powiększonym podglądzie). */
  function uruchomKaruzele() {
    zatrzymajKaruzele(); const scena = $('#k3-scena', arkTresc), pier = $('#k3-pier', arkTresc); if (!scena || !pier) return;
    kar = karuzela(scena, pier, { W: 232, H: 372, start: przodI, zycie: ruchDozwolony(), auto: () => ruchDozwolony() && !document.hidden && podgladI === null && !scena.matches(':hover') && !scena.contains(document.activeElement),
      onWybor: i => otworzPodglad(i), onZmiana: i => { przodI = i; const n = $('#k3-nazwa', arkTresc); if (n) n.textContent = nazwaPrzodu(); [...arkTresc.querySelectorAll('.k3-kropka')].forEach((b, j) => b.classList.toggle('akt', j === i)); } });
  }
  function odswiezKarty() {
    const o = $('#dok-obszar', arkTresc); if (!o) return;
    if (widokKart === '3d' && podgladI === null && kar && $('#k3-pier', arkTresc)) {      // karuzela zostaje na miejscu (obrót się nie zeruje): podmieniamy tylko karty i kropki
      $('#k3-pier', arkTresc).innerHTML = k.nazwyDok().map(karta3d).join(''); $('#k3-pasek', arkTresc).innerHTML = kropkiKart(); kar.przelicz(); zapamietajStany(); return;
    }
    o.innerHTML = przelacznikWidoku() + obszarKart(); uruchomKaruzele(); zapamietajStany();
  }
  function otworzPodglad(i) { if (widokKart !== '3d') return; zatrzymajKaruzele(); podgladI = i; przodI = i; const o = $('#dok-obszar', arkTresc); if (o) o.innerHTML = przelacznikWidoku() + podglad3d(i); const f = $('.k3-pg-gora button', arkTresc); f && f.focus({ preventScroll: true }); }
  function zamknijPodglad() { if (podgladI === null) return; podgladI = null; const o = $('#dok-obszar', arkTresc); if (o) { o.innerHTML = przelacznikWidoku() + widok3d(); uruchomKaruzele(); const s = $('#k3-scena', arkTresc); s && s.focus({ preventScroll: true }); } }
  function przejdzPodglad(s) { const n = k.razemDok(); if (podgladI === null || !n) return; podgladI = (podgladI + s + n) % n; przodI = podgladI; const o = $('#dok-obszar', arkTresc); if (o) o.innerHTML = przelacznikWidoku() + podglad3d(podgladI); }
  function ustawWidok(w) { if (w === widokKart) return; widokKart = w; podgladI = null; try { localStorage.setItem('pmt-ui-widok-dok', w); } catch (e) { /* bez pamięci przeglądarki wybór obowiązuje do zamknięcia okna */ } const o = $('#dok-obszar', arkTresc); if (o) { zatrzymajKaruzele(); o.innerHTML = przelacznikWidoku() + obszarKart(); uruchomKaruzele(); const sc = $('#k3-scena', arkTresc); if (sc) sc.scrollIntoView({ block: 'center', behavior: ruchDozwolony() ? 'smooth' : 'auto' }); } }
  addEventListener('keydown', e => { if (e.key === 'Escape' && podgladI !== null && arkTresc.isConnected && arkTresc.querySelector('.k3-podglad')) { e.stopImmediatePropagation(); e.preventDefault(); zamknijPodglad(); } else if (podgladI !== null && (e.key === 'ArrowLeft' || e.key === 'ArrowRight') && arkTresc.querySelector('.k3-podglad') && !/^(INPUT|SELECT|TEXTAREA)$/.test((document.activeElement || {}).tagName || '')) { e.preventDefault(); przejdzPodglad(e.key === 'ArrowRight' ? 1 : -1); } }, true);
  function podsumowanie() {
    const razem = k.razemDok(), ok = k.ilePodpisanych(), wgr = k.nazwyDok().filter(d => plikiDok(d.i).length).length;
    if (!wgr) return `${razem} ${liczba(razem, 'dokument czeka', 'dokumenty czekają', 'dokumentów czeka')} na podpis`;
    return wszystkoPodpisane() ? `<b>Wszystkie ${razem} dokumentów sprawdzone — możesz wysłać</b>` : `<b>${ok} z ${razem}</b> sprawdzonych pozytywnie${wgr - ok > 0 ? ` · ${wgr - ok} do poprawy lub potwierdzenia` : ''}`;
  }
  /** Krok 5. Hasło do paczek, termin jego ważności i adres odbiorcy ustawia administrator w arkuszu (zakładka „Ustawienia”); aplikacja pobiera je, gdy wszystkie dokumenty są podpisane.
      Do czasu, aż wszystko jest wgrane i sprawdzone, przycisk jest wyszarzony i NIE niesie data-akcja (nic go nie uruchomi). */
  let daneWysylkiTs = 0;          // kiedy pobrano daneWysylki (ms) — świeże dane pozwalają kliknięciu „Wyślij” nie czekać na serwer
  let daneWysylki;                // undefined = jeszcze nie pobrano; { ok:true, haslo, wazneDo, adres, format } albo { ok:false, powod, komunikat }
  let pobieranieDanych = false;
  let stanWysylki = '';           // komunikat pod krokiem 5 po kliknięciu „Wyślij” (html)
  const KONCOWE = ['brak', 'wygaslo', 'dostep'];      // przy tych powodach ponowna próba nic nie da, dopóki administrator czegoś nie zmieni
  const zablokowana = () => !!(daneWysylki && !daneWysylki.ok && KONCOWE.includes(daneWysylki.powod));
  const wyslane = () => !!M().wyslane;
  const mozeWyslac = () => wszystkoPodpisane() && !wyslane() && !zablokowana();
  const dataPl = iso => { const d = new Date(iso); if (isNaN(d.getTime())) return ''; const p = n => String(n).padStart(2, '0'); return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`; };
  /* Sposoby wysyłki (na telefonie zawsze systemowe udostępnianie z plikiem — to jest gałąź „plik”); na komputerze domyślny jest pierwszy dostępny w tej kolejności:
       • „outlook” — szkic w skrzynce Outlook (Microsoft Graph, js/outlook.js), tylko gdy administrator wpisał identyfikator aplikacji Microsoft (plik poczta_microsoft.txt) i strona ma https;
       • „folder”  — DOMYŚLNIE na komputerze z folderem „delegacje” (Chrome, Edge — gdy folder jest wskazany): ten sam plik .eml zapisany WPROST do folderu, bez pobierania. Chromium traktuje pobrany .eml jako
                     „potencjalnie niebezpieczny” (ostrzeżenie, o ile strona nie była odwiedzona dzień wcześniej albo użytkownik nie ustawił „zawsze otwieraj”); zapis do wskazanego folderu przez
                     File System Access API nie przechodzi przez mechanizm pobierania, więc ostrzeżenia nie ma. Pliku nie da się otworzyć ze strony — użytkownik klika go dwukrotnie w folderze;
       • „plik”    — bez folderu: plik .eml z adresem, tematem, treścią I zahasłowaną paczką; otwarty w Outlooku (klasycznym), Thunderbirdzie czy Poczcie Apple daje gotowe okno
                     nowej wiadomości. Gdy użytkownik raz zaznaczy w przeglądarce „Zawsze otwieraj pliki tego typu” (jednorazowa wskazówka niżej), „Wyślij” od razu pokazuje to okno;
       • „pulpit”  — to samo, ale zapis przez okno „Zapisz jako” otwarte na Pulpicie (Chrome, Edge);
       • „poczta”  — link mailto: z adresem, tematem i treścią, paczka w folderze Pobrane do dołączenia ręcznie (mailto: nie umie dołączyć pliku) — dla poczty w przeglądarce (Gmail, Onet…).
     Przycisk „Zmień sposób” przełącza kolejno; wybór pamiętany na urządzeniu. */
  let klientMs = '', pobieranieKlienta = false;
  const czyOutlook = () => !!klientMs && !matchMedia('(pointer:coarse)').matches && !!(globalThis.crypto && crypto.subtle);
  const METODY = ['outlook', 'folder', 'plik', 'pulpit', 'poczta'];
  /* Zapamiętany sposób wysyłki jest osobny w każdej przeglądarce. Przy próbach z poprzednich wersji (m.in. gdy przeglądarka blokowała plik .eml) łatwo było zostawić „otwarcie poczty” —
     wiadomość otwiera się wtedy BEZ załącznika (mailto: nie umie go dołączyć). Wersja 2 wysyłki zeruje ten wybór jednorazowo: wszyscy zaczynają od domyślnego sposobu (plik .eml). */
  let prefPoczty = (() => { try { return wczytajSposobWysylki(localStorage, METODY); } catch (e) { return ''; } })();      // sam dostęp do localStorage może rzucić wyjątek (zablokowane dane witryn)
  /* „pulpit”: okno „Zapisz jako” otwiera się od razu na Pulpicie (File System Access API: showSaveFilePicker z startIn: 'desktop' — Chrome, Edge; Firefox i Safari go nie mają), nazwa pliku .eml jest wpisana.
     Po zapisie ikona gotowej wiadomości (adres, temat, treść i zahasłowana paczka w jednym pliku) leży na pulpicie — dwuklik otwiera pocztę. Strona nie może zapisać pliku na pulpicie sama, bez tego okna. */
  const czyPulpit = () => !matchMedia('(pointer:coarse)').matches && typeof window.showSaveFilePicker === 'function' && window.isSecureContext !== false;
  const czyFolder = () => !matchMedia('(pointer:coarse)').matches && folderMozliwy() && fol.stan === 'zapisany' && !!fol.korzen;      // folder „delegacje” wskazany, zgoda jest, dokumenty zapisane
  const dostepneMetody = () => matchMedia('(pointer:coarse)').matches ? ['plik'] : [...(czyOutlook() ? ['outlook'] : []), ...(czyFolder() ? ['folder'] : []), 'plik', ...(czyPulpit() ? ['pulpit'] : []), 'poczta'];
  /** Okno „Zapisz jako” na Pulpicie — wywoływane SYNCHRONICZNIE w obsłudze kliknięcia (przeglądarka pozwala na nie tylko tuż po geście użytkownika); zwraca obietnicę uchwytu pliku. */
  const zapytajOMiejsceZapisu = () => { const o = window.showSaveFilePicker({ suggestedName: 'PMT_wiadomosc_do_wyslania.eml', startIn: 'desktop', types: [{ description: 'Wiadomość e-mail (.eml)', accept: { 'message/rfc822': ['.eml'] } }] }); o.catch(() => {}); return o; };
  const metodaWysylki = () => { const d = dostepneMetody(); return d.includes(prefPoczty) ? prefPoczty : d[0]; };
  function wczytajKlientaMs() { if (pobieranieKlienta) return; pobieranieKlienta = true; wczytajKlienta().then(id => { if (id !== klientMs) { klientMs = id; odswiezWidok(); } }).finally(() => { pobieranieKlienta = false; }); }      // przy każdym otwarciu okna (mały plik, bez pamięci podręcznej): zmiana ustawienia działa od razu
  function zmienPoczte() { const d = dostepneMetody(); prefPoczty = d[(d.indexOf(metodaWysylki()) + 1) % d.length]; try { localStorage.setItem('pmt-ui-poczta', prefPoczty); } catch (e) { /* bez pamięci przeglądarki wybór obowiązuje do zamknięcia okna */ } odswiezWidok(); }
  /** mailto: (RFC 6068): „@” zostaje w adresie, temat i treść zakodowane, nowe wiersze jako CRLF. */
  const mailtoDo = (adres, tem, tr) => `mailto:${encodeURIComponent(adres).replace(/%40/g, '@')}?subject=${encodeURIComponent(tem)}&body=${encodeURIComponent(String(tr).replace(/\r?\n/g, '\r\n'))}`;
  /** Otwarcie poczty. Test może przechwycić adres (okno __testy), bo przeglądarka bez zainstalowanego programu pocztowego nic z mailto: nie robi. */
  const otworzMailto = u => { if (window.__testy && typeof window.__przechwycMailto === 'function') { window.__przechwycMailto(u); return; } try { location.href = u; } catch (e) { /* bez programu pocztowego — jest odnośnik w komunikacie */ } };
  const NAZWA_METODY = { outlook: 'szkic w Outlooku', folder: 'wiadomość w folderze „delegacje”', plik: 'plik wiadomości .eml', pulpit: 'zapis na pulpicie (.eml)', poczta: 'samo otwarcie poczty — paczkę dołączysz sam' };
  const przyciskWyslij = () => mozeWyslac() ? `${dostepneMetody().length > 1 ? `<span class="wyslij-sposob">Sposób: <b>${NAZWA_METODY[metodaWysylki()]}</b></span>` : ''}<button type="button" class="przycisk glowny" data-akcja="wyslij" data-metoda="${metodaWysylki()}">${ik('i-wyslij')}Wyślij</button>${dostepneMetody().length > 1 ? `<button type="button" class="przycisk maly" data-akcja="zmien-poczte">Zmień sposób</button>` : ''}`
    : `<button type="button" class="przycisk glowny" disabled aria-disabled="true">${ik(wyslane() ? 'i-ok' : 'i-wyslij')}${wyslane() ? 'Wysłano' : 'Wyślij'}</button>`;
  const opisWyslij = () => !wszystkoPodpisane() ? 'Odblokuje się, gdy wgrasz i sprawdzę wszystkie podpisane dokumenty.'
    : wyslane() ? `Dokumenty wysłane${M().wyslaneKiedy ? ' ' + dataPl(M().wyslaneKiedy) : ''}. Gdyby wiadomość nie wyszła z poczty, „Cofnij wysłanie” na pulpicie przywraca stan sprzed wysyłki.`
    : zablokowana() ? esc(daneWysylki.komunikat)
    : `Wszystkie dokumenty sprawdzone. „Wyślij” zrobi z nich zahasłowaną paczkę i ${({ outlook: 'otworzy gotowy szkic wiadomości w Twoim Outlooku (adres, temat, treść i załącznik)', folder: 'zapisze w folderze „delegacje” gotową wiadomość (adres, temat, treść i paczka w jednym pliku .eml) — klikniesz ją dwukrotnie, a otworzy się poczta i zostanie tylko kliknąć „Wyślij”', plik: matchMedia('(pointer:coarse)').matches ? 'otworzy pocztę z gotową wiadomością (paczkę dołączysz z folderu Pobrane)' : 'przygotuje gotową wiadomość (adres, temat, treść i paczka w jednym pliku .eml) — otworzy się w Twojej poczcie i zostanie tylko kliknąć „Wyślij”', pulpit: 'zapisze na pulpicie ikonę gotowej wiadomości (adres, temat, treść i paczka w jednym pliku) — klikniesz ją dwukrotnie, a otworzy się poczta ze wszystkim', poczta: 'otworzy Twój program pocztowy z adresem, tematem i treścią (paczkę zapisze w folderze Pobrane, do dołączenia)' })[metodaWysylki()] || 'przygotuje wiadomość'}.`;      // adres odbiorcy zna tylko administrator — użytkownikowi się go nie pokazuje (trafia tylko do pola „Do” gotowej wiadomości)
  function wczytajDane() { if (daneWysylki !== undefined || pobieranieDanych) return; pobieranieDanych = true; hasloDoPaczki().then(o => { daneWysylki = o; daneWysylkiTs = Date.now(); }).finally(() => { pobieranieDanych = false; odswiezWidok(); }); }
  /* ---------------------------------- folder roboczy na pulpicie (Chrome, Edge) ---------------------------------- */
  /* stan: 'start' (sprawdzam) | 'bez-folderu' | 'gotowy' (folder wskazany, dokumenty tego miesiąca jeszcze nie zapisane) | 'zapisany' (dokumenty w folderze, folder jest obserwowany) | 'zgoda' (przeglądarka chce
     ponownej zgody — jedno kliknięcie) | 'blad'. Zapamiętane w pamięci miesiąca (magUst 'folder-…'): odciski plików zapisanych przez aplikację (baza) i już wczytanych (przetworzone) — dzięki temu ani oryginały, ani
     ponownie otwarte okno niczego nie wczytują drugi raz. */
  const fol = { sluchacze: false, uchwyt: null, korzen: null, miesiac: null, stan: 'start', blad: '', ostatnio: 0, wykryto: 0, timer: 0, zajety: false, widziane: new Map() };
  const kluczFolderu = () => 'folder-' + magMiesiace.klucz(M().rok, M().mies);
  const stanFolderu = () => Object.assign({ zapisano: false, baza: {}, przetworzone: [] }, magUst.daj(kluczFolderu(), null) || {});
  const zapiszStanFolderu = st => magUst.ustaw(kluczFolderu(), st);
  const nazwaPodfolderu = () => `${String(k.MIES[M().mies - 1]).toLowerCase()} ${M().rok}`;      // np. „wrzesień 2026” — podfolder miesiąca w folderze „delegacje”
  const godz = ms => { const d = new Date(ms), p = n => String(n).padStart(2, '0'); return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`; };
  /* Jednolinijkowa, opcjonalna podpowiedź: gov.pl oddaje podpisane pliki do folderu Pobrane (strona nie może tego zmienić, a przeglądarka nie pozwala aplikacji czytać Pobranych). Gdy raz ustawi się
     „Pobrane → Lokalizacja” na folder „delegacje”, podpisane pliki trafiają tam same i aplikacja je wczytuje — bez przenoszenia. Znika po pierwszym wczytanym pliku, po „Ukryj” i gdy wszystko jest podpisane. */
  const radaPobraneUkryta = () => { try { return localStorage.getItem('pmt-ui-pobrane-rada') === '1'; } catch (e) { return false; } };
  function radaPobrane() {
    if (radaPobraneUkryta() || fol.wykryto > 0 || wszystkoPodpisane()) return '';
    const adres = (przegladarka() === 'edge' ? 'edge' : 'chrome') + '://settings/downloads';
    return `<div class="kk-pobrane" id="kk-pobrane-rada"><span>Raz ustaw w przeglądarce <b>Pobrane → Lokalizacja</b> na ten folder — podpisane pliki z gov.pl trafią tu same, bez przenoszenia.</span>
      <div class="kk-pobrane-dol"><details class="kk-jak"><summary>Jak to zrobić?</summary><ol><li>Skopiuj adres <span class="adr">${adres}</span> <button type="button" class="przycisk maly" data-akcja="pobrane-kopiuj" data-adres="${adres}">Kopiuj</button> i wklej go w pasku adresu przeglądarki.</li><li>Przy „Lokalizacja” kliknij „Zmień” i wskaż folder „${NAZWA_FOLDERU}” (na Pulpicie).</li></ol><small>Firma może to blokować — wtedy po podpisaniu przeciągnij pliki z Pobranych do folderu albo użyj „Wgraj ręcznie”.</small></details>
      <button type="button" class="kk-link" data-akcja="pobrane-rada-ok">Ukryj</button></div></div>`;
  }
  function odswiezFolder() { if (widok !== 'glowny') return; odswiezPobieranie(); }
  /** Przy otwarciu okna: wczytuje zapamiętany folder i sprawdza, czy przeglądarka pamięta zgodę; jeśli dokumenty już są w folderze, zaczyna go obserwować. */
  async function inicjujFolder() {
    if (!folderMozliwy()) return;
    clearInterval(fol.timer); fol.timer = 0; fol.uchwyt = null; fol.korzen = null; fol.miesiac = null; fol.blad = ''; fol.stan = 'start'; fol.widziane = new Map(); fol.wykryto = 0; fol.ostatnio = 0;
    const uchwyt = await wczytajFolder();
    if (!uchwyt) { fol.stan = 'bez-folderu'; return odswiezFolder(); }
    fol.uchwyt = uchwyt; await wznowFolder(false);
  }
  async function wznowFolder(zadaj) {
    fol.blad = '';
    const z = await zgodaFolderu(fol.uchwyt, zadaj);
    if (z !== 'granted') { fol.stan = z === 'denied' && zadaj ? 'blad' : 'zgoda'; if (fol.stan === 'blad') fol.blad = 'Brak zgody na dostęp do folderu.'; return odswiezFolder(); }
    try {
      fol.korzen = await korzenDelegacji(fol.uchwyt);      // „delegacje”: wskazany folder albo nowy w jego środku
      if (!stanFolderu().zapisano) { fol.stan = 'gotowy'; odswiezFolder(); return zapiszDokumentyWFolderze(false); }      // dokumenty tego miesiąca jeszcze nie leżą w folderze: zapisuję je od razu
      fol.miesiac = await podfolder(fol.korzen, nazwaPodfolderu()); fol.stan = 'zapisany'; zacznijObserwowac();
    } catch (e) { fol.stan = 'blad'; fol.blad = 'Nie mogę otworzyć folderu „' + NAZWA_FOLDERU + '” (' + String((e && e.message) || e).slice(0, 100) + ').'; }
    odswiezFolder();
  }
  async function wskazFolderRoboczy() {
    fol.blad = '';
    try {
      const u = await wskazFolder(); if (!u) return;      // użytkownik zrezygnował
      await zapamietajFolder(u); fol.uchwyt = u; await wznowFolder(true);
    } catch (e) {
      fol.blad = e && (e.name === 'SecurityError' || /system|blocked|zablok/i.test(String(e.message))) ? 'Przeglądarka nie pozwala wskazać samego Pulpitu ani Dokumentów. W oknie wyboru kliknij „Nowy folder”, nazwij go „delegacje” i wskaż go.' : 'Nie udało się wskazać folderu: ' + String((e && e.message) || e).slice(0, 100);
      odswiezFolder();
    }
  }
  /** Zapisuje oryginały wszystkich dokumentów w podfolderze miesiąca i zaczyna obserwować folder. Rozliczenie wydatków (podpisu nie wymaga) od razu wchodzi do aplikacji jako przyjęte. */
  async function zapiszDokumentyWFolderze(zadaj = true) {
    fol.blad = '';
    try {
      if ((await zgodaFolderu(fol.uchwyt, zadaj)) !== 'granted') { fol.stan = 'zgoda'; return odswiezFolder(); }
      const o = await oryginaly(); if (!o.length) { if (zadaj) pokazToast('Nie znalazłem dokumentów — wygeneruj je ponownie'); return; }
      fol.korzen = fol.korzen || await korzenDelegacji(fol.uchwyt); fol.miesiac = await podfolder(fol.korzen, nazwaPodfolderu());
      zaznaczOd(); const st = stanFolderu(); st.zapisano = true;
      for (const x of o) { const nazwa = bezOgonkow(x.d.nazwa), odc = await zapiszPlik(fol.miesiac, nazwa, x.bajty); st.baza[nazwa] = `${odc.nazwa}|${odc.rozmiar}|${odc.zmiana}`; }
      zapiszStanFolderu(st); oznaczPobrane(o.map(x => x.d.i)); fol.stan = 'zapisany'; fol.widziane = new Map(); zacznijObserwowac();
      pokazToast(`Zapisano ${o.length} ${liczba(o.length, 'dokument', 'dokumenty', 'dokumentów')} w folderze „${fol.korzen.name}” › „${nazwaPodfolderu()}”`);
      odswiezFolder();
      await przyjmijRozliczenie();
    } catch (e) { console.error('zapis w folderze', e); fol.stan = 'blad'; fol.blad = 'Nie udało się zapisać dokumentów w folderze: ' + String((e && e.message) || e).slice(0, 100); odswiezFolder(); }
  }
  /** Rozliczenie wydatków nie wymaga podpisu: aplikacja przyjmuje je sama (plik bez zmian), bez wgrywania i bez śladu na liście „dopasowanych plików”. */
  async function przyjmijRozliczenie() {
    const d = k.nazwyDok().find(x => x.rozliczenie); if (!d || plikiDok(d.i).length) return;
    const b = await oryginal(d); if (!b) return;
    const plik = new File([b], bezOgonkow(d.nazwa), { type: 'application/pdf' });
    await przyjmij([plik]); wgrane = wgrane.filter(w => w.plik !== plik); pokazWyniki();
  }
  async function zmienFolderRoboczy() {
    clearInterval(fol.timer); fol.timer = 0; await zapomnijFolder();
    zapiszStanFolderu(Object.assign(stanFolderu(), { zapisano: false, baza: {} }));      // nowe miejsce: dokumenty tego miesiąca zapiszą się tam od nowa (pliki już wczytane nie wczytają się drugi raz)
    fol.uchwyt = null; fol.korzen = null; fol.miesiac = null; fol.stan = 'bez-folderu'; fol.blad = ''; odswiezFolder(); await wskazFolderRoboczy();
  }
  function zacznijObserwowac() {
    clearInterval(fol.timer); fol.timer = setInterval(odczytajFolder, 2500); odczytajFolder();
    if (!fol.sluchacze) { fol.sluchacze = true; const odrazu = () => { if (fol.stan === 'zapisany' && !document.hidden) odczytajFolder(); }; document.addEventListener('visibilitychange', odrazu); window.addEventListener('focus', odrazu); }      // wracasz z gov.pl na kartę aplikacji — pliki wczytują się od razu, bez czekania na kolejny obrót
  }
  /** Jeden obrót obserwacji: nowy albo zmieniony plik (inny odcisk niż oryginały i już wczytane) trzeba zobaczyć w dwóch kolejnych odczytach i nie może być świeżo zapisany — wtedy idzie do zwykłego wgrywania
   *  (to samo, co „Wybierz pliki”: rozpoznanie dokumentu, sprawdzenie podpisu w tle). */
  async function odczytajFolder() {
    if (!arkTresc.isConnected || !$('#dok-obszar', arkTresc) || widok !== 'glowny') { clearInterval(fol.timer); fol.timer = 0; return; }
    if (fol.zajety || fol.stan !== 'zapisany' || !fol.miesiac) return;      // także gdy karta jest w tle (użytkownik podpisuje na gov.pl): po powrocie wszystko jest już wczytane i sprawdzone
    fol.zajety = true;
    try {
      /* podpisane pliki mogą trafić do podfolderu miesiąca (zapisane tam) ALBO do folderu głównego „delegacje” (gdy pobieranie w przeglądarce ustawiono na ten folder) — patrzymy w oba */
      const lista = [...(await wypiszFolder(fol.miesiac)).map(f => ({ ...f, zr: 'm' })), ...(fol.korzen ? (await wypiszFolder(fol.korzen)).map(f => ({ ...f, zr: 'k' })) : [])]; fol.ostatnio = Date.now();
      const st = stanFolderu(), znane = new Set([...Object.values(st.baza), ...st.przetworzone]), nowe = [];
      for (const f of lista) {
        if (znane.has(f.odcisk)) continue;
        const wiek = Date.now() - f.zmiana, widzianyJuz = fol.widziane.get(f.zr + f.nazwa) === f.odcisk; fol.widziane.set(f.zr + f.nazwa, f.odcisk);
        if (!widzianyJuz && wiek < 4000) continue;      // świeży plik: poczekaj na drugi odczyt (czy zapis skończony); starszy niż 4 s (np. przeniesiony z Pobranych) — bierzemy od razu
        if (wiek < 1500) continue;
        nowe.push(f);
      }
      if (nowe.length) {
        const pliki = []; for (const f of nowe) pliki.push(await f.uchwyt.getFile());
        st.przetworzone.push(...nowe.map(f => f.odcisk)); zapiszStanFolderu(st); fol.wykryto += nowe.length;
        const s = $('#kk-folder-stan', arkTresc); if (s) s.textContent = `Wykryto ${nowe.length} ${liczba(nowe.length, 'nowy plik', 'nowe pliki', 'nowych plików')} — wczytuję i sprawdzam…`;
        await przyjmij(pliki);
        if (document.hidden) { const { n, ok } = ileDoPodpisu(); oznaczKarte(`✔ ${ok}/${n}`); }      // karta w tle: znacznik w tytule karty pokazuje, że podpisane pliki już są
        const rada = $('#kk-pobrane-rada', arkTresc); if (rada) rada.remove();      // podpisane pliki już docierają — podpowiedź o lokalizacji pobierania niepotrzebna
      }
      const s = $('#kk-folder-stan', arkTresc); if (s) s.textContent = `Obserwuję folder · ostatnio sprawdziłem ${godz(fol.ostatnio)}${fol.wykryto ? ` · wczytane pliki: ${fol.wykryto}` : ''}`;
    } catch (e) { fol.blad = 'Folder przestał odpowiadać (' + String((e && e.message) || e).slice(0, 80) + '). Wskaż go ponownie.'; fol.stan = 'blad'; clearInterval(fol.timer); fol.timer = 0; odswiezFolder(); }
    finally { fol.zajety = false; }
  }
  /** Lista dokumentów do pobrania w kroku „Podpisz”: każdy PDF osobno (przycisk obok nazwy); pobrane są oznaczone. Rozliczenie wydatków nie wymaga podpisu — jest na liście, bo trafia do paczki. */
  function wierszePobierania() {
    const pob = pobrane();
    return `<ul class="kk-pliki" aria-label="Dokumenty do pobrania">${k.nazwyDok().map(d => `<li class="kk-plik${pob.has(d.i) ? ' pobrano' : ''}"><span class="kk-plik-nazwa"><b>${d.tytul}</b><small>${d.rozliczenie ? 'podpis niewymagany' : d.opis}</small></span><button type="button" class="przycisk maly" data-akcja="pobierz-dok" data-i="${d.i}" aria-label="Pobierz PDF: ${esc(d.tytul)}">${pob.has(d.i) ? `${ik('i-ok')}Pobrano` : `${ik('i-pobierz')}Pobierz PDF`}</button></li>`).join('')}</ul>`;
  }
  /** „Otwórz gov.pl” działa dopiero po pobraniu choć jednego dokumentu; wcześniej to wyszarzony przycisk bez adresu (nic nie otworzy). */
  const akcjeGov = () => `<span class="kk-przyciski" id="kk-gov-akcje"><button type="button" class="przycisk" data-akcja="osobno">${ik('i-pobierz')}Pobierz wszystkie</button>${pobrane().size
    ? `<a class="przycisk glowny" id="otworz-gov" href="${k.URL_PODPIS}" target="_blank" rel="noopener">Otwórz gov.pl</a>`
    : `<button type="button" class="przycisk glowny" id="otworz-gov" disabled aria-disabled="true">Otwórz gov.pl</button>`}</span>${pobrane().size ? '' : '<small class="kk-podp" id="kk-gov-podp">„Otwórz gov.pl” odblokuje się po pobraniu dokumentów.</small>'}`;
  /* ---------------------------------- asystent podpisu (tryb z folderem: Chrome, Edge na komputerze) ---------------------------------- */
  /* Laik ma widzieć JEDNĄ rzecz do zrobienia: pasek „Folder · Podpis · Wysyłka”, tytuł, kilka krótkich zdań, jeden duży przycisk i na żywo postęp. Stan wynika z tego, co aplikacja sama wykryła
     (folder wskazany, dokumenty zapisane, ile podpisanych poleceń wczytano) — nic nie trzeba przełączać. Wszystko inne (odręcznie, ręczne wgrywanie, zmiana folderu, sposób wysyłki) jest pod
     „Inne sposoby i szczegóły”. Bez folderu (telefon, Firefox, Safari) okno wygląda po staremu (widokKlasyczny). */
  const ileDoPodpisu = () => { const d = k.nazwyDok().filter(x => !x.rozliczenie), ok = d.filter(x => M().podpisane[x.i]).length; return { n: d.length, ok, czeka: d.filter(x => !M().podpisane[x.i]) }; };
  /** Następna tura na gov.pl: do 5 jeszcze niepodpisanych poleceń — „delegacja_01, 02, 03” (nazwy plików do wybrania w oknie gov.pl). */
  function nastepnaTura() {
    const tura = ileDoPodpisu().czeka.slice(0, LIMIT_GOV), nazwy = tura.map((d, i) => { const m = /^delegacja_(\d+)/i.exec(d.nazwa); return m ? (i ? m[1] : 'delegacja_' + m[1]) : d.nazwa; });
    return { ile: tura.length, tekst: nazwy.join(', ') };
  }
  /* Sposób podpisu: 'gov' (Profil Zaufany na gov.pl) albo 'reczny' (wydruk, podpis długopisem, skan). Zapamiętany na urządzeniu; gdy jeszcze nie wybrano, asystent pyta jednym ekranem z dwiema kartami
     (a gdy coś już wczytano — wnioskuje: skan z podpisem odręcznym → odręcznie, inaczej gov.pl). Oba sposoby kończą się tak samo: pliki trafiają do folderu „delegacje”, aplikacja je wczytuje i sprawdza. */
  const SPOSOBY_PODPISU = ['gov', 'reczny'];
  let sposobPodpisu = (() => { try { const v = localStorage.getItem('pmt-ui-sposob-podpisu'); return SPOSOBY_PODPISU.includes(v) ? v : ''; } catch (e) { return ''; } })();
  const ustawSposobPodpisu = v => { sposobPodpisu = SPOSOBY_PODPISU.includes(v) ? v : ''; try { if (sposobPodpisu) localStorage.setItem('pmt-ui-sposob-podpisu', sposobPodpisu); else localStorage.removeItem('pmt-ui-sposob-podpisu'); } catch (e) { /* bez pamięci przeglądarki wybór obowiązuje do zamknięcia okna */ } };
  const sposobPodpisuTeraz = () => sposobPodpisu || (!ileDoPodpisu().ok ? '' : Object.values(weryfikacje()).some(w => w && w.rodzaj === 'odreczny') ? 'reczny' : 'gov');
  const statusObserwacji = () => fol.ostatnio ? `Obserwuję folder · ostatnio sprawdziłem ${godz(fol.ostatnio)}${fol.wykryto ? ` · wczytane pliki: ${fol.wykryto}` : ''}` : 'Obserwuję folder…';
  /* Od kiedy pliki w wybranym folderze (np. „Pobrane”) uznajemy za nowe: pierwsze pobranie, wydruk albo zapis dokumentów w tym miesiącu (z 2 min zapasu na różnice zegarów). */
  const kluczOd = () => 'od-' + magMiesiace.klucz(M().rok, M().mies);
  const odKiedy = () => Number(magUst.daj(kluczOd(), 0)) || Date.now() - 21 * 86400000;
  const zaznaczOd = () => { if (!Number(magUst.daj(kluczOd(), 0))) magUst.ustaw(kluczOd(), Date.now() - 120000); };
  const dotyk = () => matchMedia('(pointer:coarse)').matches;
  let infoWgrania = '';           // komunikat po wskazaniu folderu albo upuszczeniu plików („nie znalazłem nowych podpisanych plików…”); znika przy kolejnym wgraniu
  let pobieranieTrwa = false;     // trwa pobieranie dokumentów do podpisu (przycisk jest wtedy wyszarzony)
  const radaPrzegladarkiUkryta = () => { try { return localStorage.getItem('pmt-ui-rada-przegladarki') === '1'; } catch (e) { return false; } };
  /** Podpowiedź (tylko na komputerze w przeglądarce bez dostępu do folderów): najwygodniej jest w Edge albo Chrome — tam aplikacja zapisuje i wczytuje pliki sama. Zamykana, wybór pamiętany. */
  function radaPrzegladarki() {
    if (folderMozliwy() || dotyk() || radaPrzegladarkiUkryta()) return '';
    const pr = przegladarka(), brave = !!(navigator.brave && navigator.brave.isBrave);
    if (!brave && (pr === 'chrome' || pr === 'edge')) return '';
    const co = brave ? 'Brave domyślnie blokuje dostęp aplikacji do folderów' : `W ${pr === 'firefox' ? 'Firefoksie' : pr === 'safari' ? 'Safari' : 'tej przeglądarce'} pliki pobierasz i wskazujesz ręcznie — przeglądarka nie pozwala aplikacji zapisywać ich w folderze`;
    return `<p class="as-rada-przegl" id="as-rada-przegl"><span>${co}. <b>W Microsoft Edge albo Google Chrome na komputerze robię to za Ciebie</b> — wystarczy raz wskazać folder.${brave ? ' (W Brave włączysz to w adresie brave://flags/#file-system-access-api.)' : ''}</span><button type="button" class="kk-link kk-link-jasny" data-akcja="rada-przegladarki-ok">Rozumiem</button></p>`;
  }
  function htmlAsystenta() {
    const tryb = folderMozliwy() ? 'folder' : 'pobieranie', { n, ok } = ileDoPodpisu(), proc = n ? Math.round(ok / n * 100) : 0, sp = sposobPodpisuTeraz();
    const korzen = esc((fol.korzen || fol.uchwyt || { name: NAZWA_FOLDERU }).name), pod = esc(nazwaPodfolderu()), wyk = wszystkoPodpisane(), wys = wyslane();
    const blad = fol.blad ? `<p class="as-blad kk-folder-blad" role="alert">${esc(fol.blad)}</p>` : '';
    const krok = wys || wyk ? 3 : tryb === 'folder' ? (fol.stan === 'zapisany' ? 2 : 1) : (sp && (sp === 'reczny' || (pobrane().size && !pobieranieTrwa)) ? 2 : 1);
    const chipy = (tryb === 'folder' ? ['Folder', 'Podpis', 'Wysyłka'] : ['Dokumenty', 'Podpis', 'Wysyłka']).map((t, i) => `<li class="${i + 1 < krok ? 'zrobione' : i + 1 === krok ? 'teraz' : ''}"><i>${i + 1 < krok ? '✓' : i + 1}</i>${t}</li>`).join('');
    const duzy = (akcja, tekst, ikona, wylacz) => `<button type="button" class="przycisk glowny as-duzy" data-akcja="${akcja}"${wylacz ? ' disabled' : ''}>${ikona ? ik(ikona) : ''}${tekst}</button>`;
    const pasek = czekam => `<div class="as-status"><div class="as-pasek" role="progressbar" aria-valuemin="0" aria-valuemax="${n}" aria-valuenow="${ok}"><i style="width:${proc}%"></i></div><b>${ok ? `Wczytano ${ok} z ${n} podpisanych poleceń` : `${czekam} · 0 z ${n}`}</b>${tryb === 'folder' ? `<small id="kk-folder-stan" aria-live="polite">${statusObserwacji()}</small>` : ''}</div>`;
    const przelacz = inny => `<button type="button" class="kk-link as-przelacz" data-akcja="sposob" data-sposob="${inny}">${inny === 'gov' ? 'Wolę podpisać elektronicznie (gov.pl)' : 'Wolę podpisać odręcznie (wydruk i skan)'}</button>`;
    const info = infoWgrania ? `<p class="as-info" role="status">${esc(infoWgrania)}</p>` : '';
    const linkFolderu = `<button type="button" class="kk-link as-folder-link" data-akcja="wybierz-folder">${tryb === 'folder' ? 'Podpisane pliki trafiły gdzie indziej (np. do „Pobrane”)? Wskaż ten folder — znajdę je sam' : 'Wolę wskazać cały folder (np. „Pobrane”) — znajdę podpisane pliki sam'}</button>`;
    const strefaPlikow = () => dotyk() ? `<button type="button" class="przycisk as-wybierz" data-akcja="wybierz-pliki">${ik('i-skan')}Wybierz podpisane pliki</button>` : `<button type="button" class="podp-strefa as-strefa as-strefa-duza" data-strefa data-akcja="wybierz-pliki"><b>Przeciągnij tu podpisane pliki</b><span>albo kliknij i wybierz je z listy</span></button>`;
    const wybory = gdzie => `${gdzie}<div class="as-wybory"><button type="button" class="as-wybor" data-akcja="sposob" data-sposob="gov"><b>${ik('i-pioro')}Elektronicznie — gov.pl</b><small>Bez drukowania. Potrzebny Profil Zaufany (bezpłatny).</small></button><button type="button" class="as-wybor" data-akcja="sposob" data-sposob="reczny"><b>${ik('i-drukuj')}Odręcznie — wydruk i skan</b><small>Drukujesz, podpisujesz długopisem i skanujesz. Nie potrzeba żadnych kont.</small></button></div>`;
    const bezWydruku = (t) => `<ol class="as-lista"><li>Kliknij <b>„Wydrukuj dokumenty”</b> i wydrukuj je (rozliczenia wydatków nie podpisujesz).</li><li>Podpisz długopisem każde polecenie w miejscu <b>„podpis pracownika”</b>.</li><li>${t}</li></ol>`;
    let tytul, opis = '', akcja = '', status = '';
    if (wys) { tytul = 'Wysyłka przygotowana ✔'; opis = `<div id="podp-wyslij-stan" class="as-stan" aria-live="polite">${stanWysylki || opisWyslij()}</div>`; }
    else if (wyk) {
      if (zablokowana()) { tytul = 'Wysyłka jest teraz niedostępna'; opis = `<p>${esc(daneWysylki.komunikat)}</p>`; }
      else {
        tytul = 'Wszystko podpisane i sprawdzone ✔'; opis = `<p>Kliknij „Wyślij” — przygotuję wiadomość z zahasłowaną paczką.</p><div id="podp-wyslij-stan" class="as-stan" aria-live="polite">${stanWysylki}</div>`;
        akcja = `<span id="podp-wyslij-akcje"><button type="button" class="przycisk glowny as-duzy" data-akcja="wyslij" data-metoda="${metodaWysylki()}"${wysylanie ? ' disabled' : ''}>${ik('i-wyslij')}Wyślij</button></span>`;
      }
    }
    else if (tryb === 'pobieranie') {      // przeglądarka bez dostępu do folderów (Firefox, Safari, telefon): pliki idą przez folder Pobrane, a asystent prowadzi: pobierz → podpisz → wskaż lub przeciągnij podpisane pliki
      if (!sp) { tytul = 'Jak chcesz podpisać dokumenty?'; opis = wybory(''); }
      else if (sp === 'reczny') {
        tytul = 'Podpisz odręcznie';
        opis = bezWydruku(`Zeskanuj podpisane strony (${dotyk() ? 'aplikacją skanującą w telefonie' : 'skanerem albo aplikacją skanującą w telefonie'} — nie zdjęciem pod kątem) i <b>wgraj skany tutaj</b>. Resztę zrobię sam.`);
        akcja = `<button type="button" class="przycisk glowny as-duzy" data-akcja="drukuj">${ik('i-drukuj')}Wydrukuj dokumenty</button><button type="button" class="kk-link" data-akcja="pdf-wydruk">albo pobierz PDF do wydruku</button>`;
        status = `${strefaPlikow()}${dotyk() ? '' : linkFolderu}${pasek('Czekam na skany podpisanych poleceń')}${info}${przelacz('gov')}`;
      } else if (!pobrane().size || pobieranieTrwa) {      // także w trakcie pobierania: karta zmienia się dopiero, gdy wszystkie pliki poszły
        tytul = 'Pobierz dokumenty do podpisu';
        opis = `<p>Strona gov.pl nie przyjmuje plików prosto z aplikacji, więc najpierw zapisz dokumenty na dysku. Kliknij przycisk — pliki trafią do folderu <b>Pobrane</b>.</p><p class="as-gdzie">Przeglądarka może zapytać o zgodę na pobranie kilku plików — kliknij „Zezwól”.</p>`;
        akcja = duzy('pobierz-do-podpisu', pobieranieTrwa ? 'Pobieram…' : 'Pobierz dokumenty', 'i-pobierz', pobieranieTrwa);
        status = przelacz('reczny');
      } else {
        const t = nastepnaTura();
        tytul = 'Podpisz dokumenty na gov.pl';
        opis = `<p class="as-gdzie">Dokumenty są w folderze <b>Pobrane</b>. <button type="button" class="kk-link" data-akcja="pobierz-do-podpisu">Pobierz je jeszcze raz</button></p><ol class="as-lista"><li>Kliknij <b>„Otwórz gov.pl”</b> i zaloguj się Profilem Zaufanym.</li><li>Wybierz z folderu <b>Pobrane</b> pliki: <b>${esc(t.tekst)}</b>${ok === 0 ? ' (rozliczenia wydatków nie podpisujesz)' : ''}.</li><li>Podpisz i <b>pobierz</b> podpisane pliki — potem wróć tutaj i <b>wgraj je</b> (${dotyk() ? 'dotknij „Wybierz podpisane pliki”' : 'przeciągnij je albo wybierz'}). Resztę zrobię sam.</li></ol>`;
        akcja = `<a class="przycisk glowny as-duzy" id="otworz-gov" href="${k.URL_PODPIS}" target="_blank" rel="noopener">Otwórz gov.pl</a>`;
        status = `${strefaPlikow()}${dotyk() ? '' : linkFolderu}${pasek('Czekam na podpisane pliki')}${info}${przelacz('reczny')}`;
      }
    }
    else if (fol.stan === 'zapisany') {
      const gdzie = `<p class="as-gdzie">Dokumenty czekają w folderze „${korzen}” › „${pod}”.</p>`;
      if (!sp) { tytul = 'Jak chcesz podpisać dokumenty?'; opis = wybory(gdzie); }
      else if (sp === 'reczny') {
        tytul = 'Podpisz odręcznie';
        opis = `${gdzie}` + bezWydruku(`Zeskanuj podpisane strony (aplikacją skanującą w telefonie albo skanerem — nie zdjęciem pod kątem) i <b>zapisz skany w folderze „${korzen}”</b> albo przeciągnij je tutaj. Resztę zrobię sam.`);
        akcja = `<button type="button" class="przycisk glowny as-duzy" data-akcja="drukuj">${ik('i-drukuj')}Wydrukuj dokumenty</button><button type="button" class="kk-link" data-akcja="pdf-wydruk">albo pobierz PDF do wydruku</button>`;
        status = `<button type="button" class="podp-strefa as-strefa" data-strefa data-akcja="wybierz-pliki"><span>Skany możesz też przeciągnąć tutaj albo kliknąć i wybrać</span></button>${pasek('Czekam na skany podpisanych poleceń')}${info}${blad}${linkFolderu}${przelacz('gov')}`;
      } else {
        const t = nastepnaTura();
        tytul = 'Podpisz dokumenty na gov.pl';
        opis = `${gdzie}<ol class="as-lista"><li>Kliknij <b>„Otwórz gov.pl”</b> i zaloguj się Profilem Zaufanym.</li><li>Wybierz z folderu pliki: <b>${esc(t.tekst)}</b>${ok === 0 ? ' (rozliczenia wydatków nie podpisujesz)' : ''}.</li><li>Podpisz i <b>pobierz</b> podpisane pliki — wrócisz tu, a resztę zrobię sam.</li></ol>`;
        akcja = `<a class="przycisk glowny as-duzy" id="otworz-gov" href="${k.URL_PODPIS}" target="_blank" rel="noopener">Otwórz gov.pl</a>`;
        status = `${pasek('Czekam na podpisane pliki')}${radaPobrane()}${info}${blad}${linkFolderu}${przelacz('reczny')}`;
      }
    }
    else if (fol.stan === 'zgoda') { tytul = 'Pozwól na dostęp do folderu'; opis = `<p>Przeglądarka pyta o zgodę na folder „${esc(fol.uchwyt ? fol.uchwyt.name : NAZWA_FOLDERU)}”. Kliknij <b>„Pozwól”</b>, a w oknie przeglądarki wybierz <b>„Zezwalaj przy każdej wizycie”</b> (albo „Edytuj pliki”) — wtedy to pytanie już nie wróci.</p>${blad}`; akcja = duzy('folder-wznow', 'Pozwól'); }
    else if (fol.stan === 'gotowy') { tytul = 'Zapisuję dokumenty w folderze…'; opis = `<p>To trwa chwilę. Jeśli nic się nie dzieje, kliknij „Zapisz dokumenty”.</p>${blad}`; akcja = duzy('folder-zapisz', 'Zapisz dokumenty', 'i-pobierz'); }
    else if (fol.stan === 'blad') { tytul = 'Problem z folderem'; opis = blad || '<p>Nie mogę korzystać z wybranego folderu.</p>'; akcja = duzy('folder-zmien', 'Wskaż folder od nowa', 'i-pobierz'); }
    else if (fol.stan === 'start') { tytul = 'Sprawdzam folder…'; }
    else {
      tytul = 'Wskaż folder na dokumenty';
      opis = `<p>Robisz to tylko raz. Po kliknięciu otworzy się okno wyboru folderu:</p><ol class="as-lista"><li>Kliknij <b>„Nowy folder”</b>.</li><li>Wpisz nazwę <b>${NAZWA_FOLDERU}</b>.</li><li>Kliknij <b>„Wybierz folder”</b> (a jeśli przeglądarka zapyta o zgodę — <b>„Edytuj pliki”</b>).</li></ol>${blad}`;
      akcja = duzy('folder-wskaz', 'Wskaż folder', 'i-pobierz');
    }
    return `<ol class="as-kroki" aria-label="Postęp">${chipy}</ol><div class="as-karta"><h3 class="as-tytul">${tytul}</h3>${opis}${akcja ? `<div class="as-akcja">${akcja}</div>` : ''}${status}</div>${radaPrzegladarki()}`;
  }
  /* Znacznik w tytule karty przeglądarki („✔ 2/6 · PMT Planer”), gdy podpisane pliki wczytały się, gdy użytkownik był na innej karcie (gov.pl); znika po powrocie na kartę aplikacji. */
  let tytulKarty = '';
  function oznaczKarte(znacznik) { try { tytulKarty = tytulKarty || document.title.replace(/^✔ [^·]*· /, ''); document.title = `${znacznik} · ${tytulKarty}`; } catch (e) { /* tytuł niedostępny */ } }
  function przywrocTytul() { if (tytulKarty && !document.hidden) { document.title = tytulKarty; } }
  document.addEventListener('visibilitychange', przywrocTytul); window.addEventListener('focus', przywrocTytul);
  function odswiezAsystenta() { const e = $('#asystent', arkTresc); if (e && widok === 'glowny') e.innerHTML = htmlAsystenta(); }
  /** „Sposób wysyłki” pod „Inne sposoby”: na komputerze jest kilka dróg (plik w folderze, plik .eml, poczta…); domyślna działa sama, tu można ją zmienić. */
  const htmlSposobu = () => dostepneMetody().length > 1 ? `Sposób: <b>${NAZWA_METODY[metodaWysylki()]}</b> <button type="button" class="kk-link" data-akcja="zmien-poczte">Zmień sposób</button>` : `Sposób: <b>${NAZWA_METODY[metodaWysylki()]}</b>`;
  function widokAsystenta() {
    const folder = folderMozliwy();
    return `${nagl('Dokumenty do podpisu')}
      <div class="asystent" id="asystent">${htmlAsystenta()}</div>
      <div id="podp-odrzucone" aria-live="polite"></div>
      <details class="asyst-inne"><summary>Inne sposoby i szczegóły</summary>
        <div class="asyst-inne-tresc">
          <section><b>${ik('i-skan')}Wgraj podpisane pliki ręcznie</b><small>PDF z podpisem, plik .xades, paczka ZIP z gov.pl, skany i zdjęcia (wszystkie naraz). Sam dopasuję je do dokumentów. Możesz też przeciągnąć je w dowolne miejsce tego okna — także cały folder.</small><span class="kk-przyciski"><label class="przycisk glowny podp-wgraj">${ik('i-skan')}Wybierz pliki<input type="file" id="plik-wgraj" multiple accept="${AKCEPT}" data-wgraj hidden></label><button type="button" class="przycisk" data-akcja="wybierz-folder">Wskaż folder (np. Pobrane)</button><input type="file" id="plik-folder" webkitdirectory multiple data-wgraj-folder hidden></span><label class="podp-strefa" for="plik-wgraj" data-strefa><span>albo przeciągnij tu podpisane pliki</span></label></section>
          <section><b>${ik('i-pobierz')}Pobierz dokumenty osobno</b><small>${folder ? 'Gdy folder nie działa: każdy PDF osobno do folderu Pobrane.' : 'Każdy PDF osobno do folderu Pobrane.'}</small>${wierszePobierania()}</section>
          <section><b>Wysyłka</b><small id="asyst-sposob">${htmlSposobu()}</small></section>
          ${folder ? `<section><b>Folder</b><small>Dokumenty leżą w folderze „${esc((fol.korzen || { name: NAZWA_FOLDERU }).name)}”.</small><span class="kk-przyciski"><button type="button" class="przycisk maly" data-akcja="folder-zmien">Zmień folder</button></span></section>`
            : `<section><b>Wygląd okna</b><small>Wolisz widzieć wszystkie kroki naraz, bez prowadzenia za rękę?</small><span class="kk-przyciski"><button type="button" class="przycisk maly" data-akcja="widok-podpisu" data-w="klasyczny">Pokaż wszystkie kroki naraz</button></span></section>`}
        </div></details>
      <div id="dok-obszar">${przelacznikWidoku()}${obszarKart()}</div>
      <div id="podp-wyniki"></div>
      <div class="ark-dol" id="podp-dol"><button type="button" class="przycisk" data-zamknij>Zamknij</button></div>`;
  }
  function widokGlowny() { return uzywaAsystenta() ? widokAsystenta() : widokKlasyczny(); }
  function widokKlasyczny() {
    const razem = k.razemDok(), tury = Math.ceil(razem / LIMIT_GOV);
    return `${nagl('Dokumenty do podpisu')}
      <ol class="kroki4">
        <li class="krok-k k2"><span class="kk-nr">1</span><div class="kk-tresc"><b>Podpisz</b>
          <div class="kk-opcje">
            <div class="kk-opcja kk-gov"><b>${ik('i-pioro')}Elektronicznie (gov.pl)</b><small>Profil Zaufany, bezpłatnie. Najpierw pobierz dokumenty (każdy osobno, jako PDF) — strona gov.pl nie przyjmie plików z aplikacji, więc podpisujesz te z dysku. gov.pl przyjmuje naraz do ${LIMIT_GOV} plików po 25 MB${tury > 1 ? ` — przy ${razem} dokumentach podpisz w ${tury} ${liczba(tury, 'turze', 'turach', 'turach')}` : ''}.</small>
              ${wierszePobierania()}
              ${akcjeGov()}</div>
            <div class="kk-opcja"><b>${ik('i-drukuj')}Odręcznie</b><small>Wydrukuj, podpisz długopisem w miejscu „podpis pracownika” (na rozliczeniu wydatków podpis nie jest wymagany), zeskanuj (aplikacja skanująca, nie zdjęcie pod kątem).</small><span class="kk-przyciski"><button type="button" class="przycisk" data-akcja="drukuj">Wydrukuj</button><button type="button" class="przycisk" data-akcja="pdf-wydruk">Pobierz PDF</button></span></div>
          </div></div></li>
        <li class="krok-k k3"><span class="kk-nr">2</span><div class="kk-tresc"><b>Wgraj podpisane pliki</b><small>Wszystkie naraz: PDF z podpisem, plik .xades, paczka ZIP z gov.pl, skany i zdjęcia. Sam dopasuję je do dokumentów.</small></div>
          <span class="kk-akcje"><label class="przycisk glowny podp-wgraj">${ik('i-skan')}Wybierz pliki<input type="file" id="plik-wgraj" multiple accept="${AKCEPT}" data-wgraj hidden></label></span></li>
        <li class="krok-strefa"><label class="podp-strefa" for="plik-wgraj" data-strefa><span>albo przeciągnij tu podpisane pliki</span></label></li>
        <li class="krok-k k4"><span class="kk-nr">3</span><div class="kk-tresc"><b>Sprawdzenie</b><small class="podp-licznik" id="podp-licznik">${podsumowanie()}</small></div></li>
        <li class="krok-k k5 ${wszystkoPodpisane() ? 'aktywny' : 'nieaktywny'}"><span class="kk-nr">4</span><div class="kk-tresc"><b>Wyślij</b><small id="podp-wyslij-opis">${opisWyslij()}</small><small class="podp-stan" id="podp-wyslij-stan" aria-live="polite">${stanWysylki}</small></div>
          <span class="kk-akcje" id="podp-wyslij-akcje">${przyciskWyslij()}</span></li>
      </ol>
      <div id="podp-odrzucone" aria-live="polite"></div>
      <div id="dok-obszar">${przelacznikWidoku()}${obszarKart()}</div>
      <div id="podp-wyniki"></div>
      <div class="ark-dol" id="podp-dol"><button type="button" class="kk-link kk-link-jasny" data-akcja="widok-podpisu" data-w="asystent">Wróć do asystenta (jedna rzecz naraz)</button><button type="button" class="przycisk" data-zamknij>Zamknij</button></div>`;
  }
  function odswiezWidok() {
    if (widok !== 'glowny') return;
    odswiezKarty();
    const l = $('#podp-licznik', arkTresc); if (l) l.innerHTML = podsumowanie();
    if (uzywaAsystenta()) { odswiezAsystenta(); const sp = $('#asyst-sposob', arkTresc); if (sp) sp.innerHTML = htmlSposobu(); }
    const k5 = $('.krok-k.k5', arkTresc);
    if (k5) { const akt = mozeWyslac(); k5.classList.toggle('aktywny', akt); k5.classList.toggle('nieaktywny', !akt); $('#podp-wyslij-opis', k5).innerHTML = opisWyslij(); $('#podp-wyslij-akcje', k5).innerHTML = przyciskWyslij(); }
    pokazWyniki(); if (wszystkoPodpisane() && !wyslane()) wczytajDane();
  }
  function pokaz(nowy) {
    widok = nowy;
    const wstaw = html => { k.zmienArkusz(html); const a = $('#arkusz'); a.classList.remove('widok-wejscie'); void a.offsetWidth; a.classList.add('widok-wejscie'); };
    podgladI = null; zapamietajStany(); wstaw(widokGlowny()); uruchomKaruzele(); pokazWyniki();
  }

  /* ---------------------------------- pobieranie i drukowanie ---------------------------------- */
  /** Jeden dokument jako osobny PDF (oryginał z generowania, bez podpisu). Oznacza go jako pobrany — to odblokowuje „Otwórz gov.pl”. */
  async function pobierzDokument(i) {
    const d = k.nazwyDok().find(x => x.i === i); if (!d) return;
    const b = await oryginal(d); if (!b) { pokazToast('Nie znalazłem dokumentu — wygeneruj go ponownie'); return; }
    zaznaczOd(); k.pobierzBlob(k.blobPdf(b), bezOgonkow(d.nazwa)); oznaczPobrane([i]); odswiezPobieranie();
  }
  /** Wszystkie dokumenty po kolei, każdy jako osobny PDF (przeglądarki mogą zapytać o zgodę na kilka pobrań). */
  async function pobierzOsobno(tylkoDoPodpisu = false) {      // tylkoDoPodpisu: bez rozliczenia wydatków (nie wymaga podpisu, więc nie ma po co go podpisywać na gov.pl)
    const o = (await oryginaly()).filter(x => !(tylkoDoPodpisu && x.d.rozliczenie)); if (!o.length) { pokazToast('Nie znalazłem dokumentów — wygeneruj je ponownie'); return; }
    if (pobieranieTrwa) return; pobieranieTrwa = true; zaznaczOd(); odswiezPobieranie();
    try { for (const x of o) { k.pobierzBlob(k.blobPdf(x.bajty), bezOgonkow(x.d.nazwa)); oznaczPobrane([x.d.i]); await czekaj(450); } }      // pauza: przeglądarki gubią pobrania uruchomione w tej samej chwili
    finally { pobieranieTrwa = false; }
    odswiezPobieranie();
    pokazToast(`Pobrano ${o.length} ${liczba(o.length, 'plik', 'pliki', 'plików')} do folderu Pobrane (przeglądarka mogła zapytać o zgodę na kilka pobrań)`);
  }
  /** Po pobraniu: odświeża tylko listę dokumentów i przycisk gov.pl (reszta okna, np. karuzela, zostaje jak była). */
  function odswiezPobieranie() {
    if (widok !== 'glowny') return;
    odswiezAsystenta();
    const l = $('.kk-pliki', arkTresc), a = $('#kk-gov-akcje', arkTresc);      // listy może nie być (gdy folder działa), przycisk gov.pl jest zawsze
    if (l) l.outerHTML = wierszePobierania();
    const p = $('#kk-gov-podp', arkTresc); if (p) p.remove(); if (a) a.outerHTML = akcjeGov();
  }
  async function plikDoWydruku() {
    const o = await oryginaly(); if (!o.length) { pokazToast('Nie znalazłem dokumentów — wygeneruj je ponownie'); return null; }
    try { return k.blobPdf(scalPdf(o.map(x => x.bajty))); }
    catch (e) { console.error('scalanie PDF', e); pokazToast('Nie udało się połączyć dokumentów w jeden plik — pobieram je osobno'); await pobierzOsobno(); return null; }
  }
  async function drukuj() { zaznaczOd(); const b = await plikDoWydruku(); if (!b) return; const u = URL.createObjectURL(b), w = window.open(u, '_blank'); if (!w) k.pobierzBlob(b, 'Dokumenty_do_wydruku.pdf'); setTimeout(() => URL.revokeObjectURL(u), 120000); }
  async function pobierzWydruk() { zaznaczOd(); const b = await plikDoWydruku(); b && k.pobierzBlob(b, 'Dokumenty_do_wydruku.pdf'); }

  /* ---------------------------------- przypisanie plików do dokumentów ---------------------------------- */
  /** Nazwy, pod jakimi zapisuję pliki dokumentu: dokładnie takie, jak przy generowaniu (PDF, PDF.xades, a skany: nazwa dokumentu + numer strony). */
  function docelowe(d, zrodla) {
    const baza = bezOgonkow(d.nazwa).replace(/\.pdf$/i, ''), obrazow = zrodla.filter(z => OBRAZ.test(z.orig)).length, uzyte = new Set();
    let nr = 0;
    return zrodla.map(z => {
      let rdzen = baza, koniec;
      if (OBRAZ.test(z.orig)) { nr++; if (obrazow > 1) rdzen += '_str' + String(nr).padStart(2, '0'); koniec = '.' + (rozNorm(z.orig) || 'jpg'); }
      else if (XADES.test(z.orig)) koniec = '.pdf.xades';
      else if (INNY_PODPIS.test(z.orig)) koniec = '.pdf.' + rozszerzenie(z.orig);
      else koniec = '.pdf';
      let cel = rdzen + koniec;
      for (let n = 2; uzyte.has(cel.toLowerCase()); n++) cel = `${rdzen}_${n}${koniec}`;
      uzyte.add(cel.toLowerCase()); return cel;
    });
  }
  function zmienPliki(i, nowa, metoda, org, zachowaj) {
    const m = M(), r = rejestr();
    const wszystkie = Object.assign({}, r, { [i]: nowa }); if (!nowa.length) delete wszystkie[i];
    m.podpisaniPliki = wszystkie;
    m.pierwotneNazwy = Object.assign({}, rec().pierwotneNazwy || {}, m.pierwotneNazwy || {}); if (nowa.length) m.pierwotneNazwy[i] = org; else delete m.pierwotneNazwy[i];
    m.metodaPodpisu = Object.assign({}, rec().metodaPodpisu || {}, m.metodaPodpisu || {}); if (nowa.length && metoda) m.metodaPodpisu[i] = metoda; if (!nowa.length) delete m.metodaPodpisu[i];
    if (!zachowaj) { m.weryfikacje = Object.assign({}, rec().weryfikacje || {}, m.weryfikacje || {}); delete m.weryfikacje[i]; m.podpisane[i] = false; }      // nowy zestaw plików = sprawdzenie od nowa; dokument liczy się jako podpisany dopiero po pozytywnym sprawdzeniu
    k.zapiszRekord();
  }
  /** Dodaje i/lub zdejmuje pliki dokumentu i wszystkie zapisane pliki nazywa na nowo (np. przy dodaniu drugiej strony skanu zmieniają się numery stron). */
  async function zapiszPliki(i, { dodaj, usun, metoda, zachowaj, zastap } = {}) {
    const d = k.nazwyDok().find(x => x.i === i); if (!d) return;
    const org = pierwotne()[i] || {};
    let zrodla = plikiDok(i).filter(n => n !== usun).map(n => ({ n, orig: org[n] || n }));
    if (dodaj) { zrodla = zrodla.filter(z => z.orig !== dodaj.orig && !(zastap && !partia.has(z.orig))); zrodla.push({ n: null, orig: dodaj.orig, bajty: dodaj.bajty }); }
    for (const z of zrodla) if (!z.bajty) z.bajty = await magPliki.daj(k.kluczPodp(i, z.n));
    zrodla = zrodla.filter(z => z.bajty);
    const nowe = docelowe(d, zrodla);
    for (let j = 0; j < zrodla.length; j++) if (zrodla[j].n !== nowe[j]) await magPliki.zapisz(k.kluczPodp(i, nowe[j]), zrodla[j].bajty);
    for (const n of plikiDok(i)) if (!nowe.includes(n)) { try { await magPliki.usun(k.kluczPodp(i, n)); } catch (e) { /* plik mógł już zniknąć */ } }
    zmienPliki(i, nowe, metoda, Object.fromEntries(nowe.map((n, j) => [n, zrodla[j].orig])), zachowaj);
  }
  /** Nowy podpis elektroniczny zastępuje pliki dokumentu z wcześniejszych wgrań (np. poprawiony podpis po „błędzie podpisu”), a skan — wcześniejszy, nieprzyjęty podpis elektroniczny
      albo skan z kompletem stron, na którym nie widać podpisu (ponowny skan po „podpisz długopisem i zeskanuj ponownie”): inaczej sprawdzany byłby nadal stary plik,
      a do paczki szłyby obie wersje. Poza tym skan dokładany do skanów to kolejna strona dokumentu — także przy dokumencie wielostronicowym po „nie widać podpisu”
      (ponownie skanuje się zwykle tylko stronę z podpisem; zastąpienie skasowałoby pozostałe strony, a do paczki poszedłby niepełny dokument). */
  async function przypisz(w, i) {
    const d = k.nazwyDok().find(x => x.i === i), jednaStrona = (Number((d && miejscaPodpisu(d) || {}).strony) || 1) <= 1;
    const wer = weryfikacje()[i], odrzucony = jednaStrona && !!wer && wer.stan === 'zle' && !wer.kontrole.some(c => c.id === 'strony');
    const zastap = w.rodzaj === 'e' || (!M().podpisane[i] && (Object.assign({}, rec().metodaPodpisu, M().metodaPodpisu)[i] === 'e' || odrzucony));
    await zapiszPliki(i, { dodaj: { orig: w.plik.name, bajty: w.bajty }, metoda: w.rodzaj === 'e' ? 'e' : 'reczny', zastap }); w.i = i;
  }
  async function odlacz(w) {
    if (w.i === null || w.i === undefined) return null;
    const i = w.i; await zapiszPliki(i, { usun: nazwaWgranego(i, w.plik.name) }); w.i = null; return i;
  }
  async function cofnij(i) {
    for (const n of plikiDok(i)) { try { await magPliki.usun(k.kluczPodp(i, n)); } catch (e) { /* bez znaczenia */ } }
    zmienPliki(i, [], undefined, {}); wgrane = wgrane.filter(w => w.i !== i); otwarte.delete(i); k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok();
  }
  /** Pliki zapisane wcześniej (starsza wersja programu) nazywam na nowo — raz, bez kasowania wyników sprawdzenia. */
  async function ujednolicStare() {
    for (const d of k.nazwyDok()) {
      const org = pierwotne()[d.i], nazwy = plikiDok(d.i); if (!nazwy.length) continue;
      const zrodla = nazwy.map(n => ({ orig: (org || {})[n] || n })), cel = docelowe(d, zrodla);
      if (!org || cel.some((n, j) => n !== nazwy[j])) await zapiszPliki(d.i, { zachowaj: true });
    }
  }

  /* ---------------------------------- sprawdzanie jednego dokumentu ---------------------------------- */
  const zapiszWeryfikacje = (i, w) => { const m = M(); m.weryfikacje = Object.assign({}, rec().weryfikacje || {}, m.weryfikacje || {}, { [i]: w }); m.podpisane[i] = w.stan === 'ok' || !!w.potwierdzone; k.zapiszRekord(); };
  /** Podpis odręczny jest WYMAGANY tylko na poleceniach wyjazdu służbowego (delegacjach). Rozliczenie wydatków podpisu odręcznego nie potrzebuje: brak podpisu pod tabelą nie jest błędem
   *  (nie świeci się na czerwono i nie trzeba go potwierdzać) — sprawdzam wtedy tylko, czy plik da się odczytać. Podpis elektroniczny (PAdES/XAdES) sprawdzany jest tak samo na każdym dokumencie. */
  async function ocenOdreczny(d, pliki) {
    const kontrole = [], dodaj = (id, stan, tekst) => kontrole.push({ id, stan, tekst }), wymagany = !d.rozliczenie;
    const strony = []; let powod = '';
    for (const p of pliki) { const s = await stronyZeSkanu(p.bajty, p.nazwa); strony.push(...s.strony); if (s.powod) powod = s.powod; }
    const sp = strefaPodpisu(miejscaPodpisu(d));
    dodaj('podpis', 'info', wymagany ? 'Podpis odręczny (skan albo zdjęcie dokumentu)' : 'Skan albo zdjęcie dokumentu — rozliczenie wydatków nie wymaga podpisu odręcznego');
    let podglad = '';
    if (!strony.length) dodaj('miejsce', 'uwaga', (powod || 'Nie umiem odczytać obrazu') + (wymagany ? ' — obejrzyj plik sam i potwierdź podpis' : ' — obejrzyj plik sam i potwierdź, że to właściwy dokument'));
    else if (!sp && wymagany) dodaj('miejsce', 'uwaga', 'Ten miesiąc wygenerowano starszą wersją programu — nie znam miejsca podpisu. Obejrzyj skan sam i potwierdź podpis');
    else if (!sp) dodaj('miejsce', 'ok', 'Rozliczenie wydatków nie wymaga podpisu odręcznego');
    else {
      const bm = strony[Math.min(Math.max(0, sp.strona - 1), strony.length - 1)];
      if (wymagany && sp.strona > strony.length) dodaj('strony', 'uwaga', `Dokument ma ${sp.strona} ${liczba(sp.strona, 'stronę', 'strony', 'stron')}, a we wgranym pliku jest ich ${strony.length} — sprawdzam ostatnią`);
      const o = szukajPodpisu(bm, sp.strefa); podglad = wymagany ? (o.podglad || '') : '';      // wycinek do obejrzenia tylko tam, gdzie podpis jest wymagany
      if (!wymagany) dodaj('miejsce', 'ok', o.stan === 'jest' ? 'Widzę ślad podpisu pod tabelą — na rozliczeniu wydatków podpis odręczny nie jest wymagany' : 'Rozliczenie wydatków nie wymaga podpisu odręcznego — brak podpisu pod tabelą jest w porządku');
      else if (o.stan === 'jest') dodaj('miejsce', 'ok', `Widzę ślad podpisu w miejscu „${sp.opis}”`);
      else if (o.stan === 'brak') dodaj('miejsce', 'zle', `Nie widzę podpisu w miejscu „${sp.opis}” — podpisz długopisem i zeskanuj ponownie (albo potwierdź, jeśli podpis tam jest)`);
      else dodaj('miejsce', 'uwaga', o.powod || 'Nie umiem ocenić skanu');
    }
    if (wymagany) dodaj('osoba', 'info', `Imię i nazwisko na dokumencie: ${k.PROFIL().imie} (wydrukowane z Twoich danych). Odręcznego podpisu nie umiem odczytać — porównaj sam`);
    const stan = kontrole.some(c => c.stan === 'zle') ? 'zle' : kontrole.some(c => c.stan === 'uwaga') ? 'uwaga' : 'ok';
    return { rodzaj: 'odreczny', kontrole, stan, sygnatariusz: '', czas: null, podglad, bezWymogu: !wymagany };
  }
  /** Czy plik wrócił pod właściwą nazwą: jeśli nie, aplikacja rozpoznała dokument i nazwała plik tak, jak przy generowaniu. */
  function kontroleNazwy(d, pliki) {
    const org = pierwotne()[d.i] || {}, wyn = [];
    for (const p of pliki) {
      const orig = org[p.nazwa] || p.nazwa; if (orig === p.nazwa) continue;
      const inny = k.nazwyDok().find(x => x.i !== d.i && bezOgonkow(x.nazwa).toLowerCase() === orig.toLowerCase());
      wyn.push({ id: 'nazwa', stan: 'info', tekst: `Plik wrócił jako „${orig}”${inny ? ` — to nazwa innego dokumentu (${inny.tytul})` : ''}. Rozpoznałem w nim dokument „${d.tytul}” i nazwałem go „${p.nazwa}”, tak jak przy generowaniu` });
    }
    return wyn.length ? wyn : [{ id: 'nazwa', stan: 'ok', tekst: `Nazwa pliku zgadza się z dokumentem: ${pliki.map(p => p.nazwa).join(', ')}` }];
  }
  /** Miesiąc, w którym zaczęła się operacja: sprawdzanie i wgrywanie trwają chwilę, a w tym czasie można zamknąć okno i przejść strzałką do innego miesiąca. */
  const tenMiesiac = () => { const { rok, mies } = M(); return () => M().rok === rok && M().mies === mies; };
  async function sprawdz(i) {
    const d = k.nazwyDok().find(x => x.i === i); if (!d) return;
    const tenSam = tenMiesiac(); sprawdzane.add(i); odswiezWidok();
    try {
      const nazwy = plikiDok(i), pliki = [];
      for (const n of nazwy) { const b = await magPliki.daj(k.kluczPodp(i, n)); if (b) pliki.push({ nazwa: n, bajty: b }); }
      const orig = await oryginal(d), profil = k.PROFIL();
      const pdfPodpisany = [...pliki].reverse().find(p => /\.pdf$/i.test(p.nazwa) && podpisyWPdf(p.bajty).length), xades = [...pliki].reverse().find(p => XADES.test(p.nazwa));      // ostatnio wgrany
      let w;
      if (pdfPodpisany) w = await ocenPodpisElektroniczny({ bajty: pdfPodpisany.bajty, oryginal: orig, imie: profil.imie, pesel: profil.pesel });
      else if (xades) w = await ocenPodpisElektroniczny({ xades: new TextDecoder('utf-8').decode(xades.bajty), oryginal: orig, imie: profil.imie, pesel: profil.pesel });
      else if (pliki.some(p => INNY_PODPIS.test(p.nazwa))) w = { rodzaj: 'e', kontrole: [{ id: 'podpis', stan: 'uwaga', tekst: 'Ten rodzaj pliku podpisu (.p7s/.sig) nie jest obsługiwany do sprawdzania — użyj podpisu w PDF albo pliku .xades' }], stan: 'uwaga', sygnatariusz: '', czas: null };
      else if (d.rozliczenie && orig && pliki.length && pliki.every(p => /\.pdf$/i.test(p.nazwa) && p.bajty.length === orig.length && p.bajty.every((b, n) => b === orig[n]))) w = { rodzaj: 'bez-podpisu', kontrole: [{ id: 'podpis', stan: 'ok', tekst: 'Rozliczenie wydatków nie wymaga podpisu — przyjąłem plik bez zmian' }], stan: 'ok', sygnatariusz: '', czas: null, podglad: '', bezWymogu: true };
      else w = await ocenOdreczny(d, pliki);
      w.kontrole = [...w.kontrole, ...kontroleNazwy(d, pliki)];
      w.kiedy = new Date().toISOString(); w.czas = w.czas ? new Date(w.czas).toISOString() : null;
      if (tenSam()) zapiszWeryfikacje(i, w);      // po zmianie miesiąca wynik nie trafia do cudzego rekordu; pliki zostają i sprawdzą się przy otwarciu okna
    } catch (e) {
      console.error('sprawdzanie podpisu', e);
      if (tenSam()) zapiszWeryfikacje(i, { rodzaj: 'brak', kontrole: [{ id: 'blad', stan: 'uwaga', tekst: 'Nie udało się sprawdzić pliku: ' + (e.message || e) }], stan: 'uwaga', sygnatariusz: '', czas: null });
    } finally { sprawdzane.delete(i); }
    k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok();
  }
  /** Dokumenty z plikami, ale bez wyniku (sprawdzanie przerwane odświeżeniem strony, zamknięciem karty albo zmianą miesiąca) — inaczej wisiałyby na „sprawdzam…”. */
  async function dokonczSprawdzanie() {
    for (const d of k.nazwyDok()) {
      const w = weryfikacje()[d.i], stary = !!(d.rozliczenie && w && w.rodzaj === 'odreczny' && !w.bezWymogu && !w.potwierdzone);      // rozliczenie ocenione, zanim przestało wymagać podpisu odręcznego: sprawdzam je jeszcze raz (z zapisanego pliku), żeby nie wisiało na czerwono
      if (plikiDok(d.i).length && (!w || stary) && !sprawdzane.has(d.i)) await sprawdz(d.i);
    }
  }
  const przewinDoWyslania = () => { const e = $('.krok-k.k5, #asystent', arkTresc); if (e && widok === 'glowny' && e.scrollIntoView) e.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); };      // wszystko sprawdzone: „Wyślij” ma być na widoku
  function potwierdz(i) {
    const w = weryfikacje()[i]; if (!w) return;
    zapiszWeryfikacje(i, Object.assign({}, w, { potwierdzone: true, kontrole: [...w.kontrole, { id: 'reczne', stan: 'ok', tekst: 'Podpis potwierdzony ręcznie przez Ciebie' }] }));
    k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok();
    if (wszystkoPodpisane()) { k.kurtyna() && k.kurtyna().swieto(); k.zorza() && k.zorza().flara(1); pokazToast('Wszystko podpisane — możesz wysłać dokumenty'); przewinDoWyslania(); }
  }

  /* ---------------------------------- wgrywanie ---------------------------------- */
  /** Paczki ZIP (np. podpisane pliki pobrane z gov.pl) rozpakowuję od razu; zepsutego archiwum nie ukrywam — trafia na listę z powodem. */
  async function rozwinZip(lista) {
    const pliki = [], zepsute = [];
    for (const plik of lista) {
      if (!/\.zip$/i.test(plik.name)) { pliki.push(plik); continue; }
      try {
        const w = await rozpakujZip(new Uint8Array(await plik.arrayBuffer()));
        if (!w.length) zepsute.push({ plik, powod: 'archiwum ZIP jest puste' });
        for (const x of w) pliki.push(new File([x.bajty], x.nazwa, { type: typPliku(x.nazwa) }));
      } catch (e) { zepsute.push({ plik, powod: `nie otworzę tego ZIP-a (${e.message}) — rozpakuj go na dysku i wgraj pliki z folderu` }); }
    }
    return { pliki, zepsute };
  }
  /** Czy `bajty` to dokładnie ten PDF rozliczenia wydatków, który wygenerował program (bez podpisu): taki plik przyjmuję, bo rozliczenie podpisu nie wymaga. */
  const rozliczenieBezZmian = (dok, orgBajty, bajty) => { const d = dok.find(x => x.rozliczenie), o = d && orgBajty.get(d.i); return !!o && o.length === bajty.length && o.every((b, n) => b === bajty[n]); };
  /** Skan zapisany jako jeden PDF z wieloma stronami (aplikacje skanujące) rozbijam na osobne obrazy — jedna strona to jeden dokument. */
  function rozbijSkan(plik, bajty) {
    const o = obrazyZPdf(bajty), baza = plik.name.replace(/\.pdf$/i, '');
    return o.map((dane, n) => ({ plik: new File([dane], `${baza}_str${String(n + 1).padStart(2, '0')}.jpg`, { type: 'image/jpeg' }), bajty: new Uint8Array(dane) }));
  }
  /** Wgrywanie bez obsługi błędu przepadałoby po cichu (np. upuszczony folder, brak miejsca na urządzeniu) — dlatego błąd zawsze kończy się komunikatem. */
  async function przyjmij(lista) {
    infoWgrania = '';
    try { await przyjmijPliki(lista); }
    catch (e) { console.error('wgrywanie', e); pokazToast('Nie udało się przyjąć plików: ' + (e.message || e)); k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok(); }
  }
  async function przyjmijPliki(lista) {
    const { pliki, zepsute } = await rozwinZip([...lista]); if (!pliki.length && !zepsute.length) return;
    const tenSam = tenMiesiac(), nowe = zepsute.map(z => ({ plik: z.plik, bajty: new Uint8Array(0), i: null, jak: null, powod: z.powod, rodzaj: '' }));
    const odrzuc = (plik, powod) => nowe.push({ plik, bajty: new Uint8Array(0), i: null, jak: null, powod, rodzaj: '' });
    const dok = k.nazwyDok(), orgBajty = new Map(); for (const d of dok) orgBajty.set(d.i, await oryginal(d));
    for (const plik of pliki) {
      // rodzaj po nazwie, zanim zacznę czytać: folder (bez rozszerzenia) i nieobsługiwany plik nie przerywają przyjmowania pozostałych
      if (!/\.pdf$/i.test(plik.name) && !XADES.test(plik.name) && !INNY_PODPIS.test(plik.name) && !OBRAZ.test(plik.name)) { odrzuc(plik, 'ten rodzaj pliku nie jest obsługiwany (PDF z podpisem, .xades, ZIP, skan lub zdjęcie)' + (/\.[a-z0-9]{1,5}$/i.test(plik.name) ? '' : ' — jeśli to folder, otwórz go i wgraj pliki z jego środka')); continue; }
      let bajty; try { bajty = new Uint8Array(await plik.arrayBuffer()); } catch (e) { odrzuc(plik, 'nie mogę odczytać pliku — jeśli to folder, otwórz go i wgraj pliki z jego środka'); continue; }
      let rodzaj = '', powod = '';
      if (!bajty.length) powod = 'plik jest pusty';
      else if (XADES.test(plik.name) || INNY_PODPIS.test(plik.name)) rodzaj = 'e';
      else if (OBRAZ.test(plik.name)) rodzaj = 'skan';
      else if (/\.pdf$/i.test(plik.name)) {
        if (podpisyWPdf(bajty).length) rodzaj = 'e';
        else if (rozliczenieBezZmian(dok, orgBajty, bajty)) rodzaj = 'jawny';      // rozliczenie wydatków nie wymaga podpisu: plik pobrany bez zmian jest w porządku
        else {
          const sk = rozbijSkan(plik, bajty);
          if (sk.length > 1) { for (const s of sk) nowe.push({ plik: s.plik, bajty: s.bajty, i: null, jak: null, powod: '', rodzaj: 'skan' }); continue; }
          if (sk.length === 1 || skanBezJpeg(bajty)) rodzaj = 'skan';      // skan czarno-biały (CCITT, JBIG2…): obrazu nie odczytam, ale przyjmuję go do obejrzenia i ręcznego potwierdzenia
          else powod = 'ten PDF nie ma podpisu elektronicznego ani nie jest skanem, który umiem odczytać — podpisz go na gov.pl albo wydrukuj, podpisz i zeskanuj w kolorze lub odcieniach szarości (albo zapisz skan jako JPG)';
        }
      }
      nowe.push({ plik, bajty, i: null, jak: null, powod, rodzaj });
    }
    const dobre = nowe.filter(w => !w.powod); partia = new Set(dobre.map(w => w.plik.name));
    const wynik = await dopasujPliki(dobre.map(w => w.plik), dok.map(d => ({ i: d.i, nazwa: d.nazwa, tytul: d.tytul, wolny: plikiDok(d.i).length === 0, bajty: async () => orgBajty.get(d.i), xades: async t => xadesDotyczy(t, orgBajty.get(d.i)) })), async f => dobre.find(w => w.plik === f).bajty);
    const dotkniete = new Set();
    for (const r of wynik) { if (!tenSam()) break; const w = dobre.find(x => x.plik === r.plik); w.jak = r.jak; if (r.i !== null) { await przypisz(w, r.i); dotkniete.add(r.i); } }
    // dawne odrzucenia znikają przy kolejnym wgraniu, a pliki zastąpione nowym podpisem — z listy dopasowań
    wgrane = [...nowe, ...wgrane.filter(p => !p.powod && !nowe.some(n => n.plik.name === p.plik.name) && (p.i === null || p.i === undefined || Object.values(pierwotne()[p.i] || {}).includes(p.plik.name)))];
    for (const i of dotkniete) otwarte.delete(i);
    k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok();
    for (const i of dotkniete) { if (!tenSam()) break; await sprawdz(i); }
    if (!tenSam()) return;
    const ok = [...dotkniete].filter(i => M().podpisane[i]).length;
    if (k.zorza() && ok) k.zorza().flara(.22);
    if (wszystkoPodpisane()) { k.kurtyna() && k.kurtyna().swieto(); k.zorza() && k.zorza().flara(1); pokazToast('Wszystko podpisane i sprawdzone — możesz wysłać dokumenty'); przewinDoWyslania(); }
    else if (!dotkniete.size) pokazToast('Żaden plik nie został przyjęty — powody są pod krokami');
    else pokazToast(ok === dotkniete.size ? `Sprawdzono ${ok} ${liczba(ok, 'dokument', 'dokumenty', 'dokumentów')} — podpisy w porządku` : `Sprawdzono ${dotkniete.size}: ${ok} w porządku, ${dotkniete.size - ok} do poprawy — szczegóły w kartach dokumentów`);
  }
  const OPIS_JAK = { tresc: 'rozpoznany po zawartości', nazwa: 'dopasowany po nazwie', liczba: 'dopasowany po numerze w nazwie — sprawdź', kolejnosc: 'przypisany według kolejności — sprawdź', reczne: 'przypisany przez Ciebie' };
  const niepewne = jak => jak === 'kolejnosc' || jak === 'liczba';
  let wynikiOtwarte = false;      // czy użytkownik sam rozwinął listę dopasowań (gdy wszystko jest w porządku, lista jest zwinięta)
  function pokazWyniki() {
    const odrz = $('#podp-odrzucone', arkTresc), c = $('#podp-wyniki', arkTresc); if (!c || !odrz) return;
    const dok = k.nazwyDok(), zle = wgrane.filter(w => w.powod), reszta = wgrane.filter(w => !w.powod);
    odrz.innerHTML = zle.length ? `<div class="wyniki">${zle.map(w => `<div class="wynik zle"><span class="wn">${esc(w.plik.name)}</span><small>${esc(w.powod)}</small></div>`).join('')}</div>` : '';
    const zapisana = w => { if (w.i === null || w.i === undefined) return ''; const n = nazwaWgranego(w.i, w.plik.name); return n !== w.plik.name ? n : ''; };
    const wiersze = reszta.map(w => { const n = wgrane.indexOf(w), nowa = zapisana(w); return `<div class="wynik${w.i === null ? ' brak' : ''}"><span class="wn">${esc(w.plik.name)}${nowa ? `<em class="nowa-nazwa" title="Nazwa pliku zmieniona na taką, jak przy generowaniu">→ ${esc(nowa)}</em>` : ''}</span><select data-przypisz="${n}" aria-label="Dokument dla pliku ${esc(w.plik.name)}"><option value="">— nie przypisuj —</option>${dok.map(d => `<option value="${d.i}"${w.i === d.i ? ' selected' : ''}>${d.tytul}</option>`).join('')}</select>${w.jak ? `<small class="${niepewne(w.jak) ? 'uwaga' : ''}">${OPIS_JAK[w.jak]}</small>` : (w.i === null ? '<small class="uwaga">brak wolnego dokumentu — wybierz ręcznie</small>' : '')}</div>`; }).join('');
    const doSprawdzenia = reszta.filter(w => w.i === null || niepewne(w.jak)).length, ile = reszta.length;
    c.innerHTML = ile ? `<details class="wyniki-det"${doSprawdzenia || wynikiOtwarte ? ' open' : ''}><summary>${doSprawdzenia ? `Dopasowanie plików do sprawdzenia: ${doSprawdzenia} z ${ile}` : `${ik('i-ok')}Pliki dopasowane do dokumentów (${ile})`}<span>${doSprawdzenia || wynikiOtwarte ? '' : 'zmień przypisanie'}</span></summary><div class="wyniki">${wiersze}</div></details>` : '';
  }

  /* ---------------------------------- wskazany folder i upuszczone pliki ---------------------------------- */
  /** Z listy plików wskazanego albo upuszczonego folderu (np. „Pobrane”, gdzie leży też mnóstwo cudzych plików) zostawia tylko te, które wyglądają na podpisane dokumenty TEGO miesiąca — po cichu, bez
      komunikatów o reszcie: plik nie starszy niż pierwsze pobranie/wydruk, a przy podpisie elektronicznym — zawierający jeden z naszych dokumentów (albo noszący jego nazwę). Skany (obrazy i PDF-y
      bez podpisu) bierzemy tylko przy podpisie odręcznym; przy gov.pl pomijamy je, bo mogłyby być przypadkowymi plikami. */
  async function odsiejZFolderu(lista) {
    const od = odKiedy(), sp = sposobPodpisuTeraz(), dok = k.nazwyDok(), org = new Map(), dobre = [], widziane = new Set();
    for (const d of dok) org.set(d.i, await oryginal(d));
    const nazwyDok = dok.map(d => normalizujNazwe(d.nazwa)).filter(Boolean);
    const znanaNazwa = nazwa => { const n = normalizujNazwe(nazwa); return nazwyDok.some(x => n.includes(x)) || /(?:polecenie|delegacja)\s*0*\d+/.test(n); };
    const naszDokument = bajty => [...org.values()].some(o => o && zawieraOryginal(bajty, o));
    for (const f of [...lista].sort((a, b) => a.name.localeCompare(b.name, 'pl', { numeric: true }))) {
      if (!obslugiwanyPlik(f.name) || (f.lastModified && f.lastModified < od)) continue;
      const klucz = `${f.name}|${f.size}|${f.lastModified}`; if (widziane.has(klucz)) continue; widziane.add(klucz);
      if (/\.zip$/i.test(f.name)) { if (f.name !== nazwaZip()) dobre.push(f); continue; }      // paczka z gov.pl; własnej zahasłowanej paczki aplikacji nie wczytujemy
      if (INNY_PODPIS.test(f.name)) continue;
      let bajty; try { bajty = new Uint8Array(await f.arrayBuffer()); } catch (e) { continue; }
      if (!bajty.length) continue;
      if (XADES.test(f.name)) { const t = new TextDecoder('utf-8').decode(bajty); if (dok.some(d => org.get(d.i) && xadesDotyczy(t, org.get(d.i)))) dobre.push(f); continue; }
      if (OBRAZ.test(f.name)) { if (sp !== 'gov') dobre.push(f); continue; }
      if (podpisyWPdf(bajty).length) { if (naszDokument(bajty) || znanaNazwa(f.name)) dobre.push(f); continue; }
      if (rozliczenieBezZmian(dok, org, bajty) || naszDokument(bajty)) continue;      // niepodpisany oryginał z naszego pobrania
      if (sp !== 'gov' && (skanBezJpeg(bajty) || obrazyZPdf(bajty).length)) dobre.push(f);
    }
    return dobre;
  }
  const JAK_NIE_ZNALEZIONO = 'Nie widzę tu nowych podpisanych plików z tego miesiąca. Sprawdź, czy to właściwy folder (pliki z gov.pl trafiają zwykle do „Pobrane”) i czy podpisane pliki zostały pobrane.';
  async function wczytajZFolderu(lista) {
    const dobre = await odsiejZFolderu(lista);
    if (!dobre.length) { infoWgrania = lista.length ? JAK_NIE_ZNALEZIONO : 'Ten folder jest pusty.'; odswiezAsystenta(); pokazToast('Nie znalazłem nowych podpisanych plików'); return; }
    await przyjmij(dobre);
  }
  /** Upuszczenie na okno: pliki wprost trafiają do zwykłego wgrywania, a z upuszczonych folderów — tylko wyglądające na podpisane dokumenty (jak przy wskazaniu folderu). */
  async function przyjmijUpuszczone(zrodla) {
    try {
      const { pliki, obciete } = await przejdzWpisy(zrodla), wprost = pliki.filter(x => !x.zFolderu).map(x => x.plik), zFolderu = pliki.filter(x => x.zFolderu).map(x => x.plik);
      const wybrane = zFolderu.length ? await odsiejZFolderu(zFolderu) : [], wszystkie = [...wprost, ...wybrane];
      if (!wszystkie.length) { infoWgrania = zFolderu.length ? JAK_NIE_ZNALEZIONO : 'Nie widzę tu plików do wczytania.'; odswiezAsystenta(); pokazToast(zFolderu.length ? 'Nie znalazłem nowych podpisanych plików w tym folderze' : 'Nie upuszczono żadnego pliku'); return; }
      if (obciete) pokazToast('Folder ma bardzo dużo plików — przejrzałem pierwsze 600');
      await przyjmij(wszystkie);
    } catch (e) { console.error('upuszczanie', e); pokazToast('Nie udało się odczytać upuszczonych plików: ' + (e.message || e)); }
  }

  /* ---------------------------------- wysyłka ---------------------------------- */
  async function zalaczniki() {
    const wyn = [];
    for (const d of k.nazwyDok()) {
      const nazwy = plikiDok(d.i);
      if (!nazwy.length || nazwy.some(n => XADES.test(n) || INNY_PODPIS.test(n))) { const b = await oryginal(d); if (b) wyn.push({ nazwa: bezOgonkow(d.nazwa), bajty: b, typ: 'application/pdf' }); }      // podpis w osobnym pliku (.xades) idzie razem z dokumentem
      for (const n of nazwy) { const b = await magPliki.daj(k.kluczPodp(d.i, n)); if (b) wyn.push({ nazwa: n, bajty: b, typ: typPliku(n) }); }
    }
    return wyn;
  }
  const temat = () => `[PMT] Delegacje — ${k.PROFIL().imie} — ${k.MIES[M().mies - 1]} ${M().rok}`;      // stały początek „[PMT]” pozwala odbiorcy ustawić regułę poczty (osobny folder)
  const miesiacTekst = () => { const m = String(k.MIES[M().mies - 1]); return m.charAt(0).toUpperCase() + m.slice(1); };
  const trescWiad = (n, format) => `Dzień dobry,\n\nw załączeniu zahasłowana paczka (ZIP) z podpisanymi dokumentami delegacyjnymi za ${miesiacTekst()} ${M().rok} (${n} ${liczba(n, 'plik', 'pliki', 'plików')}). Hasło zostało przekazane osobno.${format === 'aes' ? ' Paczka jest szyfrowana AES-256 — otworzysz ją w 7-Zip, WinRAR lub podobnym programie (zwykły Eksplorator Windows jej nie rozpakuje).' : ''}\n\nPozdrawiam\n${k.PROFIL().imie}`;
  const stanW = (html, zle = false) => { stanWysylki = html ? (zle ? `<span class="zle">${html}</span>` : html) : ''; const s = $('#podp-wyslij-stan', arkTresc); if (s) s.innerHTML = stanWysylki; };
  /** Paczka ZIP w szyfrze wybranym przez administratora: klasyczny (domyślny, otwiera go Eksplorator Windows) albo AES-256 (7-Zip/WinRAR). */
  const zrobPaczke = async (pliki, h) => (h.format === 'aes' ? zipujAes(pliki, h.haslo) : zipujKlasycznie(pliki, h.haslo));
  /** Hasło, termin i adres odbiorcy nadaje administrator (nie użytkownik): pobieramy je z serwera; bez internetu wystarcza zapamiętane, o ile hasło jeszcze nie wygasło. */
  async function hasloDoPaczki() {
    const o = await k.hasloPaczki();
    if (o.ok) { magUst.ustaw('paczka', { haslo: o.haslo, wazne_do: o.wazneDo, adres: o.adres, format: o.format }); return o; }
    if (o.powod === 'siec') { const c = magUst.daj('paczka', null); if (c && c.haslo && c.adres && c.wazne_do >= k.isoDzis()) return { ok: true, haslo: c.haslo, wazneDo: c.wazne_do, adres: c.adres, format: c.format === 'aes' ? 'aes' : 'klasyczny' }; }
    if (o.powod === 'brak' || o.powod === 'wygaslo') magUst.ustaw('paczka', null);
    return o;
  }
  let wysylanie = false, ostatniMailto = '', gotowyEml = null, sprawdzPoWyslaniu = null;      // gotowyEml: przygotowana wiadomość czeka na osobne kliknięcie, gdy zwykłe pobranie nie jest już możliwe; sprawdzPoWyslaniu: dane użyte z pamięci, do porównania z serwerem      // ostatniMailto: adres mailto: trzymany tylko w pamięci, żeby przycisk „Otwórz wiadomość” nie niósł adresata w treści strony
  /** Przycisk „Wyślij” w kroku 5: dane od administratora → jedna paczka ZIP z klasycznym szyfrowaniem (otwiera ją Eksplorator Windows) → gotowa wiadomość (plik .eml: adresat, temat, treść i załącznik; na telefonie systemowe udostępnianie, a bez niego pobrana paczka i wiadomość przez mailto:).
      Samo kliknięcie jest akceptacją: gdy wiadomość jest gotowa, dokumenty dostają status „wysłane” (karty pokazują „Wysłano”); „Cofnij wysłanie” na pulpicie go przywraca. */
  /** Okno logowania do Outlooka — musi się otworzyć SYNCHRONICZNIE w obsłudze kliknięcia, inaczej przeglądarka je zablokuje (null = zablokowane). */
  function otworzOknoLogowania() {
    let o = null; try { o = window.open('about:blank', 'pmt-outlook', 'popup=yes,width=560,height=760'); } catch (e) { return null; }
    try { if (o) { o.document.title = 'PMT Planer — Outlook'; o.document.body.style.cssText = 'margin:0;display:grid;place-items:center;height:100vh;font:16px system-ui,sans-serif;background:#2a2f70;color:#fff'; o.document.body.textContent = 'Przygotowuję paczkę…'; } } catch (e) { /* okno bez dostępu — zostaje puste */ }
    return o;
  }
  /** Logowanie → szkic z załącznikiem → okno przechodzi na gotowy szkic. Zwraca true, gdy okno zostało przekierowane na szkic (wtedy zostaje otwarte). */
  async function szkicOutlook(okno, { adres, tem, tr, blob, duza }) {
    const powrot = new URL('ms_powrot.html', location.href).href;
    stanW('Zaloguj się do Outlooka w otwartym oknie (potwierdzenie dostępu do szkiców) — to potrwa chwilę…');
    const { kod, verifier } = await pobierzKod({ okno, klient: klientMs, powrot });
    stanW('Tworzę szkic wiadomości w Outlooku…');
    const token = await wymienKod({ klient: klientMs, powrot, kod, verifier });
    const szkic = await utworzSzkic({ token, adres, temat: tem, tresc: tr, zalacznik: { nazwa: nazwaZip(), bajty: new Uint8Array(await blob.arrayBuffer()), typ: 'application/zip' }, postep: pr => stanW(`Dołączam zahasłowaną paczkę do szkicu… ${pr}%`) });
    oznaczWyslane();
    const link = /^https:\/\//i.test(szkic.webLink || '') ? szkic.webLink : '';
    let otwarte = false; try { if (link && okno && !okno.closed) { okno.location.href = link; otwarte = true; } } catch (e) { /* okno niedostępne — jest odnośnik niżej */ }
    stanW(`Szkic gotowy w Twoim Outlooku (z zahasłowaną paczką). Kliknij tam „Wyślij”. ${link ? `Jeśli się nie otworzył: <a class="przycisk maly" href="${esc(link)}" target="_blank" rel="noopener noreferrer">Otwórz szkic</a>` : 'Znajdziesz go w „Wersjach roboczych”.'}${duza}`);
    pokazToast('Szkic gotowy w Outlooku — kliknij tam „Wyślij”');
    return otwarte;
  }
  /* Jednorazowa wskazówka po pierwszym pobraniu .eml: przeglądarka może sama otwierać pobrane pliki .eml („Zawsze otwieraj pliki tego typu”) — wtedy „Wyślij” od razu pokazuje okno poczty.
     Strona nie umie tego ustawić ani sprawdzić (to ustawienie przeglądarki), więc wskazówka znika dopiero po „Zrobione”; potem w komunikacie zostaje tylko odnośnik do niej. */
  const EML = 'PMT_wiadomosc_do_wyslania.eml';
  const radaUkryta = () => { try { return localStorage.getItem('pmt-ui-eml-auto') === '1'; } catch (e) { return false; } };
  const chromium = () => ['edge', 'chrome'].includes(przegladarka());
  const przegladarka = () => { const u = navigator.userAgent || ''; return /Edg\//.test(u) ? 'edge' : /Firefox\//.test(u) ? 'firefox' : /Chrome\//.test(u) ? 'chrome' : /Safari\//.test(u) ? 'safari' : 'inna'; };
  function radaEml() {
    const pr = przegladarka(), opcja = pr === 'firefox' ? 'Zawsze otwieraj podobne pliki' : 'Zawsze otwieraj pliki tego typu';
    const gdzie = { edge: 'Kliknij ikonę „Pobrane” u góry po prawej (strzałka w dół)', chrome: 'Kliknij ikonę pobierania u góry po prawej (strzałka w dół)', firefox: 'Kliknij strzałkę pobierania u góry po prawej' }[pr];
    if (!gdzie) return `<span class="eml-rada" id="eml-rada"><b>Wskazówka</b><span>Ta przeglądarka nie umie sama otwierać pobranych wiadomości — otwórz plik <span class="adr">${EML}</span> z folderu Pobrane.</span><span class="eml-rada-dol"><button type="button" class="przycisk maly" data-akcja="eml-rada-ok">Rozumiem — nie pokazuj więcej</button></span></span>`;
    return `<span class="eml-rada" id="eml-rada"><b>Jednorazowo: niech wiadomość otwiera się sama</b>
      <span class="eml-kroki"><span><i>1</i>${gdzie}.</span><span><i>2</i>Kliknij <span class="adr">prawym</span> przyciskiem myszy plik <span class="adr">${EML}</span> (albo „⋯” obok niego).</span><span><i>3</i>Wybierz <span class="adr">„${opcja}”</span>.</span></span>
      <span class="eml-makieta" aria-hidden="true"><span class="em-plik">${ik('i-pobierz')}${EML}</span><span class="em-menu"><span>Otwórz</span><span class="em-wyb">${opcja}</span><span>Pokaż w folderze</span></span></span>
      <span>Od następnego razu „Wyślij” od razu pokaże okno poczty z gotową wiadomością i paczką — zostanie tylko kliknąć w nim „Wyślij”. Nie ma tej opcji? Wystarczy kliknąć pobrany plik.</span>
      ${chromium() ? '<span class="eml-inna">Edge i Chrome czasem pytają, czy zachować taki plik („ten typ pliku może zaszkodzić urządzeniu”). To wiadomość z tej aplikacji — kliknij „⋯” przy pliku w oknie pobierania i wybierz „Zachowaj”.</span>' : ''}
      <span class="eml-inna">Masz pocztę tylko w przeglądarce (Gmail, Onet, WP…)? Kliknij „Zmień sposób”, aż opis kroku 5 powie o programie pocztowym — adres, temat i treść wstawią się same, a paczkę dołączysz z Pobranych.</span>
      <span class="eml-rada-dol"><button type="button" class="przycisk maly" data-akcja="eml-rada-ok">Zrobione — nie pokazuj więcej</button></span></span>`;
  }
  const radaFolder = () => chromium() && folderMozliwy() && !czyFolder() ? ' <span class="eml-inna">Żeby to ostrzeżenie nie wracało: wskaż folder „delegacje” w kroku „Podpisz” — wiadomość trafi wtedy prosto do folderu, bez pobierania.</span>' : '';
  const stanPoEml = duza => radaUkryta()
    ? `Wiadomość gotowa: <span class="adr">${EML}</span> z adresatem, tematem, treścią i zahasłowaną paczką. Jeśli poczta nie otworzyła się sama, <span class="adr">kliknij pobrany plik</span> (pasek pobierania albo folder Pobrane); w poczcie kliknij „Wyślij”.${chromium() ? ' Jeśli Edge albo Chrome pyta, czy zachować plik — wybierz „Zachowaj”.' : ''} <button type="button" class="przycisk maly" data-akcja="eml-rada">Jak sprawić, żeby otwierała się sama?</button>${duza}${radaFolder()}`
    : `Pobrałem wiadomość <span class="adr">${EML}</span>. <span class="adr">Kliknij ją</span> (pasek pobierania przeglądarki albo folder Pobrane) — otworzy się poczta z adresatem, tematem, treścią i zahasłowaną paczką; kliknij tam „Wyślij”.${duza}${radaFolder()}${radaEml()}`;
  async function wyslij(metoda = 'plik', okno = null, zapis = null) {
    if (wysylanie) { try { okno && okno.close(); } catch (e) { /* zamknięte */ } return; } wysylanie = true; gotowyEml = null;
    const przycisk = () => $('#podp-wyslij-akcje button', arkTresc); if (przycisk()) przycisk().disabled = true;
    let oknoZostaje = false, uchwyt = null;
    try {
      if (metoda === 'pulpit') {      // najpierw ludzka decyzja (okno „Zapisz jako” już stoi na ekranie), dopiero potem hasło, paczka i szyfrowanie
        try { uchwyt = await zapis; } catch (e) { if (e && e.name === 'AbortError') { stanW('Anulowano — nic nie zapisano. Kliknij „Wyślij”, żeby spróbować jeszcze raz.'); return; } throw e; }
        if (!uchwyt) { stanW('Nie udało się otworzyć okna zapisu. <button type="button" class="przycisk maly" data-akcja="wyslij-plik">Wyślij plikiem .eml</button>', true); return; }
      }
      if (metoda === 'outlook' && !okno) { stanW('Przeglądarka zablokowała okno logowania do Outlooka. Zezwól tej stronie na wyskakujące okna i kliknij „Wyślij” jeszcze raz — albo <button type="button" class="przycisk maly" data-akcja="wyslij-plik">Wyślij plikiem .eml</button>', true); return; }
      stanW('Przygotowuję dane do wysyłki…');
      /* Przeglądarki oparte na Chromium (Edge, Chrome) uznają plik .eml za potencjalnie niebezpieczny (Outlook otwiera go sam) i puszczają go bez ostrzeżenia tylko wtedy, gdy pobranie
         następuje w ciągu ok. 5 sekund od kliknięcia użytkownika; podobnie otwarcie programu pocztowego (mailto:). Dlatego w trakcie kliknięcia nie czekamy na serwer: hasło, adres i termin
         pobrane przy otwieraniu kroku 5 (jeśli mają mniej niż 10 minut i nie wygasły) wystarczą, a po wysłaniu sprawdzamy w tle, czy administrator ich nie zmienił. */
      const swieze = !!(daneWysylki && daneWysylki.ok && Date.now() - daneWysylkiTs < 10 * 60 * 1000 && daneWysylki.wazneDo >= k.isoDzis());
      const h = swieze ? daneWysylki : await hasloDoPaczki(); daneWysylki = h; if (!swieze) daneWysylkiTs = Date.now(); if (!h.ok) { stanW(esc(h.komunikat), true); odswiezWidok(); return; }
      if (swieze) sprawdzPoWyslaniu = h;
      const adres = h.adres;
      stanW('Przygotowuję zahasłowaną paczkę…'); await czekaj(40);      // pozwala narysować komunikat, zanim szyfrowanie zajmie procesor
      const zal = await zalaczniki(); if (!zal.length) { stanW('Nie ma plików do wysłania.', true); return; }
      if (metoda === 'poczta') {      // otwieramy pocztę JAK NAJSZYBCIEJ po kliknięciu (przeglądarka pozwala na to tylko tuż po geście użytkownika), zanim szyfrowanie zajmie procesor
        const mailto = mailtoDo(adres, temat(), trescWiad(zal.length, h.format));
        otworzMailto(mailto); stanW('Otwieram pocztę i przygotowuję zahasłowaną paczkę…'); await czekaj(60);
        const blobP = await zrobPaczke(zal.map(z => ({ nazwa: z.nazwa, bajty: z.bajty })), h);
        k.pobierzBlob(blobP, nazwaZip()); await czekaj(450);
        oznaczWyslane();
        ostatniMailto = mailto; stanW(`Otworzyłem pocztę z gotową wiadomością (adresat, temat i treść są już wpisane). Zahasłowana paczka <span class="adr">${esc(nazwaZip())}</span> zapisała się w folderze Pobrane — <span class="adr">dołącz ją do wiadomości</span> (spinacz → ostatnio pobrane albo przeciągnij z paska pobierania) i wyślij. Jeśli poczta się nie otworzyła: <button type="button" class="przycisk maly" id="podp-otworz-poczte" data-akcja="otworz-mailto">Otwórz wiadomość</button>${blobP.size > LIMIT_POCZTY ? `<br><span class="zle">Uwaga: paczka waży ${mb(blobP.size)}, a poczta zwykle przyjmuje do 20–25 MB. Największe są zdjęcia — zrób skany do PDF (mniejsze pliki).</span>` : ''}`);
        pokazToast('Poczta otwarta — dołącz paczkę z folderu Pobrane i wyślij');
        return;
      }
      const blob = await zrobPaczke(zal.map(z => ({ nazwa: z.nazwa, bajty: z.bajty })), h), tr = trescWiad(zal.length, h.format), tem = temat();
      const plik = new File([blob], nazwaZip(), { type: 'application/zip' }), duza = blob.size > LIMIT_POCZTY ? `<br><span class="zle">Uwaga: paczka waży ${mb(blob.size)}, a poczta zwykle przyjmuje do 20–25 MB. Największe są zdjęcia — zrób skany do PDF (mniejsze pliki).</span>` : '';
      if (metoda === 'outlook') { oknoZostaje = await szkicOutlook(okno, { adres, tem, tr, blob, duza }); return; }
      if (metoda === 'folder') {
        if (!czyFolder() || (await zgodaFolderu(fol.uchwyt, false)) !== 'granted') { stanW('Przeglądarka nie daje teraz dostępu do folderu „' + NAZWA_FOLDERU + '” — kliknij „Pozwól” w kroku „Podpisz” i „Wyślij” jeszcze raz, albo <button type="button" class="przycisk maly" data-akcja="wyslij-plik">Wyślij plikiem .eml</button>', true); return; }
        const eml = zbudujEml({ adres, temat: tem, tresc: tr, zalacznik: { nazwa: nazwaZip(), bajty: new Uint8Array(await blob.arrayBuffer()), typ: 'application/zip' } });
        await zapiszPlik(fol.korzen, EML, eml);      // wprost do folderu (File System Access API): bez pobierania, więc bez ostrzeżenia o „niebezpiecznym pliku”
        oznaczWyslane();
        stanW(`<b>Wiadomość gotowa w folderze „${esc(fol.korzen.name)}”.</b> Zostały dwa kliknięcia:<ol class="as-lista"><li>Otwórz folder „${esc(fol.korzen.name)}” (na Pulpicie) i <b>kliknij dwukrotnie</b> plik <span class="adr">${EML}</span> — otworzy się poczta z gotową wiadomością i paczką.</li><li>W poczcie kliknij <b>„Wyślij”</b>.</li></ol>${duza}`);
        pokazToast('Wiadomość czeka w folderze „' + fol.korzen.name + '” — kliknij ją dwukrotnie');
        return;
      }
      if (metoda === 'pulpit') {
        const eml = zbudujEml({ adres, temat: tem, tresc: tr, zalacznik: { nazwa: nazwaZip(), bajty: new Uint8Array(await blob.arrayBuffer()), typ: 'application/zip' } });
        const wpis = await uchwyt.createWritable(); await wpis.write(new Blob([eml], { type: 'message/rfc822' })); await wpis.close();
        oznaczWyslane();
        stanW(`Zapisałem wiadomość <span class="adr">${esc(uchwyt.name || 'PMT_wiadomosc_do_wyslania.eml')}</span> — ikona jest na pulpicie (albo tam, gdzie ją zapisałeś). <span class="adr">Kliknij ją dwukrotnie</span>: otworzy się poczta z adresatem, tematem, treścią i zahasłowaną paczką; kliknij tam „Wyślij”.${duza}`);
        pokazToast('Ikona wiadomości na pulpicie — kliknij ją dwukrotnie');
        return;
      }
      if (matchMedia('(pointer:coarse)').matches) {      // telefon: systemowe udostępnianie nie wpisuje adresata (a adresu odbiorcy użytkownikowi nie pokazujemy), więc zawsze: pobrana paczka + poczta z gotowym adresatem, tematem i treścią (mailto:)
        const mailto = mailtoDo(adres, tem, tr + `\n\n(Dołącz pobrany plik ${nazwaZip()})`);
        k.pobierzBlob(blob, nazwaZip()); await czekaj(450);      // pauza: przejście do poczty tuż po pobraniu potrafi je przerwać
        ostatniMailto = mailto; otworzMailto(mailto);
        oznaczWyslane(); stanW(`Pobrałem zahasłowaną paczkę <span class="adr">${esc(nazwaZip())}</span> i otworzyłem pocztę z gotową wiadomością (adresat, temat i treść są już wpisane). <span class="adr">Dołącz paczkę</span> jako załącznik (folder Pobrane) i wyślij. Jeśli poczta się nie otworzyła, dotknij: <button type="button" class="przycisk maly" id="podp-otworz-poczte" data-akcja="otworz-mailto">Otwórz wiadomość</button>${duza}`);
        return;
      }
      const eml = zbudujEml({ adres, temat: tem, tresc: tr, zalacznik: { nazwa: nazwaZip(), bajty: new Uint8Array(await blob.arrayBuffer()), typ: 'application/zip' } });
      const blobEml = new Blob([eml], { type: 'message/rfc822' });
      if (chromium() && navigator.userActivation && !navigator.userActivation.isActive) {      // minęło za dużo czasu od kliknięcia (wolny komputer albo sieć): Chromium uznałby plik .eml za niebezpieczny — prosimy o osobne kliknięcie
        gotowyEml = { blob: blobEml, duza };
        stanW(`Wiadomość jest gotowa. Kliknij <button type="button" class="przycisk glowny maly" data-akcja="zapisz-eml">Zapisz wiadomość</button> — przeglądarka chce osobnego kliknięcia, zanim zapisze taki plik.${duza}`);
        return;
      }
      k.pobierzBlob(blobEml, EML);
      oznaczWyslane();
      stanW(stanPoEml(duza));
      pokazToast('Wiadomość gotowa — kliknij pobrany plik .eml, żeby ją wysłać');
    } catch (e) {
      console.error('wysyłka', e);
      if (metoda === 'outlook') stanW(esc(komunikatBledu(e)) + ' <button type="button" class="przycisk maly" data-akcja="wyslij-plik">Wyślij plikiem .eml</button>', true);
      else if (metoda === 'folder') stanW('Nie udało się zapisać wiadomości w folderze (' + esc(String((e && e.message) || e).slice(0, 120)) + '). <button type="button" class="przycisk maly" data-akcja="wyslij-plik">Wyślij plikiem .eml</button>', true);
      else if (metoda === 'pulpit') stanW('Nie udało się zapisać wiadomości na pulpicie (' + esc(String((e && e.message) || e).slice(0, 120)) + '). <button type="button" class="przycisk maly" data-akcja="wyslij-plik">Wyślij plikiem .eml</button>', true);
      else stanW('Nie udało się przygotować wiadomości. Spróbuj jeszcze raz.', true);
    }
    finally {
      wysylanie = false; const uzyte = sprawdzPoWyslaniu; sprawdzPoWyslaniu = null;
      if (uzyte && wyslane()) hasloDoPaczki().then(o => { daneWysylki = o; daneWysylkiTs = Date.now(); if (o.ok && (o.haslo !== uzyte.haslo || o.adres !== uzyte.adres || o.format !== uzyte.format)) stanW('<span class="zle">Uwaga: administrator zmienił właśnie hasło do paczek (albo ich szyfr) — ta paczka ma poprzednie ustawienia. Kliknij „Cofnij wysłanie” na pulpicie i wyślij jeszcze raz.</span>'); }).catch(() => { /* bez sieci zostają dane z pamięci */ });
      if (okno && !oknoZostaje) { try { okno.close(); } catch (e) { /* zamknięte */ } } if (przycisk() && mozeWyslac()) przycisk().disabled = false; }
  }
  function oznaczWyslane() { dzwiek.efekt('wyslano'); const m = M(); m.wyslane = true; m.wyslaneKiedy = new Date().toISOString(); k.zapiszRekord(); k.odswiezHero(); k.zorza() && k.zorza().flara(.7); odswiezWidok(); }

  /* ---------------------------------- zdarzenia ---------------------------------- */
  arkTresc.addEventListener('click', async e => {
    const b = e.target.closest('[data-akcja]'); if (!b) return;
    const a = b.dataset.akcja;
    if (a === 'otworz') k.otworzPdf(b.dataset.nazwa);
    else if (a === 'pobierz-dok') pobierzDokument(Number(b.dataset.i));
    else if (a === 'osobno') pobierzOsobno();
    else if (a === 'folder-wskaz') wskazFolderRoboczy();
    else if (a === 'folder-zapisz') zapiszDokumentyWFolderze();
    else if (a === 'folder-wznow') wznowFolder(true);
    else if (a === 'folder-zmien') zmienFolderRoboczy();
    else if (a === 'sposob') { ustawSposobPodpisu(b.dataset.sposob); odswiezAsystenta(); }
    else if (a === 'wybierz-pliki') { const inp = $('#plik-wgraj', arkTresc); if (inp) inp.click(); }
    else if (a === 'wybierz-folder') { const inp = $('#plik-folder', arkTresc); if (inp) inp.click(); }
    else if (a === 'pobierz-do-podpisu') pobierzOsobno(true);
    else if (a === 'widok-podpisu') ustawWidokPodpisu(b.dataset.w);
    else if (a === 'rada-przegladarki-ok') { try { localStorage.setItem('pmt-ui-rada-przegladarki', '1'); } catch (e) { /* bez pamięci przeglądarki podpowiedź wróci przy następnym otwarciu */ } const r = $('#as-rada-przegl', arkTresc); if (r) r.remove(); }
    else if (a === 'pobrane-rada-ok') { try { localStorage.setItem('pmt-ui-pobrane-rada', '1'); } catch (e) { /* bez pamięci przeglądarki podpowiedź wróci przy następnym otwarciu */ } const r = $('#kk-pobrane-rada', arkTresc); if (r) r.remove(); }
    else if (a === 'pobrane-kopiuj') { try { await navigator.clipboard.writeText(b.dataset.adres); pokazToast('Skopiowano — wklej adres w pasku adresu przeglądarki'); } catch (e) { pokazToast('Nie udało się skopiować — zaznacz adres i skopiuj go ręcznie'); } }
    else if (a === 'glowny') pokaz('glowny');
    else if (a === 'wyslij') { const m = dostepneMetody().includes(b.dataset.metoda) ? b.dataset.metoda : 'plik'; wyslij(m, m === 'outlook' ? otworzOknoLogowania() : null, m === 'pulpit' ? zapytajOMiejsceZapisu() : null); }      // okno logowania otwieramy tu, w obsłudze kliknięcia (inaczej zablokuje je przeglądarka)
    else if (a === 'wyslij-plik') wyslij('plik', null);
    else if (a === 'zapisz-eml') { if (!gotowyEml) return; const g = gotowyEml; gotowyEml = null; k.pobierzBlob(g.blob, EML); oznaczWyslane(); stanW(stanPoEml(g.duza)); pokazToast('Wiadomość zapisana — kliknij pobrany plik .eml, żeby ją wysłać'); }
    else if (a === 'otworz-mailto') { if (ostatniMailto) otworzMailto(ostatniMailto); }
    else if (a === 'zmien-poczte') zmienPoczte();
    else if (a === 'eml-rada-ok') { try { localStorage.setItem('pmt-ui-eml-auto', '1'); } catch (e) { /* bez pamięci przeglądarki wskazówka wróci przy następnej wysyłce */ } const r = $('#eml-rada', arkTresc); if (r) r.outerHTML = '<span class="eml-rada-zrobione">Gotowe — przy włączonej opcji wiadomość będzie się od teraz otwierać sama.</span>'; stanWysylki = $('#podp-wyslij-stan', arkTresc)?.innerHTML || stanWysylki; }
    else if (a === 'eml-rada') { const s = $('#podp-wyslij-stan', arkTresc); if (s && !$('#eml-rada', s)) { b.insertAdjacentHTML('afterend', radaEml()); b.remove(); stanWysylki = s.innerHTML; } }
    else if (a === 'widok') ustawWidok(b.dataset.w === '3d' ? '3d' : 'lista');
    else if (a === 'powieksz') otworzPodglad(Number(b.dataset.i));
    else if (a === 'k3-wroc') zamknijPodglad();
    else if (a === 'k3-poprz') przejdzPodglad(-1);
    else if (a === 'k3-nast') przejdzPodglad(1);
    else if (a === 'k3-lewo') kar && kar.kroki(1);
    else if (a === 'k3-prawo') kar && kar.kroki(-1);
    else if (a === 'k3-do') kar && kar.doKarty(Number(b.dataset.i));
    else if (a === 'drukuj') drukuj();
    else if (a === 'pdf-wydruk') pobierzWydruk();
    else if (a === 'cofnij') cofnij(Number(b.dataset.i));
    else if (a === 'potwierdz') potwierdz(Number(b.dataset.i));
    else if (a === 'szczegoly') { const i = Number(b.dataset.i); if (otwarte.has(i)) otwarte.delete(i); else otwarte.add(i); odswiezWidok(); }
  });
  arkTresc.addEventListener('click', e => {
    if (e.target.closest('.dok-k-g') && widok === 'glowny') { const kt = e.target.closest('.dok-k'); const i = Number(kt && kt.dataset.i); if (kt && !kt.classList.contains('st-czeka') && !kt.classList.contains('st-trwa')) { if (otwarte.has(i)) otwarte.delete(i); else otwarte.add(i); odswiezWidok(); } }
  });
  arkTresc.addEventListener('toggle', e => { if (e.target.classList && e.target.classList.contains('wyniki-det') && !e.target.querySelector('.wynik.zle,.wynik.brak,.wynik small.uwaga')) wynikiOtwarte = e.target.open; }, true);
  arkTresc.addEventListener('change', async e => {
    const inp = e.target.closest('[data-wgraj]');
    if (inp) { const pliki = [...inp.files]; inp.value = ''; await przyjmij(pliki); return; }
    const inpF = e.target.closest('[data-wgraj-folder]');
    if (inpF) { const pliki = [...inpF.files]; inpF.value = ''; await wczytajZFolderu(pliki); return; }
    const sel = e.target.closest('[data-przypisz]');
    if (sel) {
      const w = wgrane[Number(sel.dataset.przypisz)]; if (!w) return; const cel = sel.value === '' ? null : Number(sel.value);
      const staryI = await odlacz(w); if (cel !== null) await przypisz(w, cel); w.jak = cel === null ? null : 'reczne';
      k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok();
      if (staryI !== null && plikiDok(staryI).length) await sprawdz(staryI);
      if (cel !== null) await sprawdz(cel);
    }
  });
  for (const ev of ['dragover', 'dragenter']) arkTresc.addEventListener(ev, e => { const s = e.target.closest && e.target.closest('.podp-strefa'); if (s) { e.preventDefault(); s.classList.add('nad'); } });
  for (const ev of ['dragleave', 'drop']) arkTresc.addEventListener(ev, e => { const s = e.target.closest && e.target.closest('.podp-strefa'); if (s) s.classList.remove('nad'); });
  /* Pliki i foldery można upuścić w DOWOLNYM miejscu okna podpisu (nie tylko w przerywanym polu): z Eksploratora, z paska pobierania przeglądarki albo z folderu „Pobrane”. */
  const przenoszonePliki = e => { const dt = e.dataTransfer; if (!dt) return false; return dt.types ? Array.from(dt.types).includes('Files') : !!(dt.files && dt.files.length); };      // Array.from: w starszym Safari types to lista DOMStringList
  const oknoPodpisuAktywne = () => arkTresc.isConnected && widok === 'glowny' && !!$('#dok-obszar', arkTresc);
  let wChwycone = 0;
  const zgasUpuszczanie = () => { wChwycone = 0; arkTresc.classList.remove('upusc-pliki'); };
  arkTresc.addEventListener('dragenter', e => { if (!oknoPodpisuAktywne() || !przenoszonePliki(e)) return; e.preventDefault(); wChwycone++; arkTresc.classList.add('upusc-pliki'); });
  arkTresc.addEventListener('dragover', e => { if (!oknoPodpisuAktywne() || !przenoszonePliki(e)) return; e.preventDefault(); try { e.dataTransfer.dropEffect = 'copy'; } catch (x) { /* zdarzenie bez możliwości ustawienia */ } });
  arkTresc.addEventListener('dragleave', () => { if (!arkTresc.classList.contains('upusc-pliki')) return; wChwycone = Math.max(0, wChwycone - 1); if (!wChwycone) zgasUpuszczanie(); });      // licznik: dragenter/dragleave odpalają się też dla elementów wewnątrz okna
  window.addEventListener('dragend', zgasUpuszczanie); window.addEventListener('drop', zgasUpuszczanie, true);
  arkTresc.addEventListener('drop', e => { zgasUpuszczanie(); if (!oknoPodpisuAktywne() || !przenoszonePliki(e)) return; e.preventDefault(); przyjmijUpuszczone(wpisyZUpuszczenia(e.dataTransfer)); });      // wpisy trzeba pobrać synchronicznie

  /* ---------------------------------- wejścia ---------------------------------- */
  return {
    /** fokus (opcjonalnie): numer dokumentu, od którego okno ma zacząć — z probówki na pulpicie: karuzela ustawia go z przodu, na liście karta mignie i przewinie się na środek. */
    otworz(fokus) { wczytajKlientaMs(); const cel = Number.isInteger(fokus) && fokus >= 0 && fokus < k.razemDok() ? fokus : null; widok = 'glowny'; wgrane = []; otwarte = new Set(); stanWysylki = ''; daneWysylki = undefined; gotowyEml = null; widziane = {}; podgladI = null; fokusI = cel; if (cel !== null) { przodI = cel; setTimeout(() => { if (fokusI === cel) fokusI = null; }, 1600); } zapamietajStany(); k.otworzArkusz(widokGlowny(), null, { szeroki: true }); uruchomKaruzele(); inicjujFolder();
      if (cel !== null && widokKart === 'lista') { const c = $(`.dok-k[data-i="${cel}"]`, arkTresc); if (c) c.scrollIntoView({ block: 'center' }); } if (wszystkoPodpisane() && !wyslane()) wczytajDane(); ujednolicStare().then(() => !folderMozliwy() && uzywaAsystenta() ? przyjmijRozliczenie() : null).then(dokonczSprawdzanie).then(odswiezWidok).catch(e => console.error('nazwy plików', e)); },
    otworzWyslij() { this.otworz(); },      // „Wyślij” jest krokiem 5 w tym samym oknie co pobieranie, podpis i wgrywanie
  };
}
