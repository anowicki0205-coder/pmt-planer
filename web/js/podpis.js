// PMT Planer (web) — podpisywanie, sprawdzanie podpisów i wysyłka dokumentów miesiąca.
// Okno „Dokumenty do podpisu” prowadzi czterema krokami (czwarty, „Wyślij”, jest szary, dopóki wszystkie dokumenty nie są wgrane i sprawdzone). Dawny krok „Pobierz dokumenty” (ZIP albo osobne pliki)
// zniknął (decyzja właściciela, 9.11): pobieranie jest teraz częścią kroku „Podpisz”, a numery w oknie to 1–4 (nazwy klas CSS .k2…k5 zostały — numeracja w nich pochodzi z czasów pięciu kroków):
//   1. Podpisz: elektronicznie na gov.pl (Profil Zaufany) — najpierw trzeba pobrać dokumenty POJEDYNCZO jako PDF (każdy ma swój przycisk), dopiero po pobraniu odblokowuje się „Otwórz gov.pl”
//      (strona gov.pl nie przyjmuje plików z zewnątrz: przeglądarka nie pozwala wypełnić okna wyboru pliku, więc pliki idą przez dysk) — albo odręcznie (wydruk),
//   2. Wgraj podpisane pliki (PDF z podpisem, plik .xades, paczka ZIP z gov.pl, skany i zdjęcia — wszystkie naraz; aplikacja sama dopasowuje je do dokumentów),
//   3. Sprawdzenie: dla każdego dokumentu — czy jest podpis, czy obejmuje całość, czy dokument nie został zmieniony, czy podpisała właściwa osoba (imię i nazwisko, PESEL),
//      a przy podpisie odręcznym — czy na skanie widać podpis w miejscu „podpis pracownika”. Dopiero sprawdzone dokumenty liczą się jako podpisane. ROZLICZENIE WYDATKÓW podpisu nie wymaga
//      (przyjmuję je z podpisem i bez; plik pobrany bez zmian też jest w porządku),
//   4. Wyślij: zahasłowana paczka i gotowa wiadomość na wskazany adres (hasło nadaje administrator — js/dostep.js pobierzHasloPaczki). Pole „albo przeciągnij tu podpisane pliki” leży między krokiem 2 a 3 — tam, gdzie się wgrywa.
import { scalPdf, dopasujPliki, rozpakujZip } from './pliki.js';
import { zipujKlasycznie } from './zipklasyczny.js';
import { zipujAes } from './zipaes.js';
import { zbudujEml, wczytajSposobWysylki } from './poczta.js';
import { dzwiek } from './dzwiek.js';
import { wczytajKlienta, pobierzKod, wymienKod, utworzSzkic, komunikatBledu } from './outlook.js';
import { karuzela } from './karuzela.js';
import { atrapaHtml, daneDelegacji, daneRozliczenia } from './dokument_atrapa.js';
import { ocenPodpisElektroniczny, podpisyWPdf, czasPl, xadesDotyczy } from './weryfikacja.js';
import { stronyZeSkanu, szukajPodpisu, strefaPodpisu, obrazyZPdf, skanBezJpeg } from './podpis_reczny.js';

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
       • „plik”    — DOMYŚLNIE na komputerze: plik .eml z adresem, tematem, treścią I zahasłowaną paczką; otwarty w Outlooku (klasycznym), Thunderbirdzie czy Poczcie Apple daje gotowe okno
                     nowej wiadomości. Gdy użytkownik raz zaznaczy w przeglądarce „Zawsze otwieraj pliki tego typu” (jednorazowa wskazówka niżej), „Wyślij” od razu pokazuje to okno;
       • „pulpit”  — to samo, ale zapis przez okno „Zapisz jako” otwarte na Pulpicie (Chrome, Edge);
       • „poczta”  — link mailto: z adresem, tematem i treścią, paczka w folderze Pobrane do dołączenia ręcznie (mailto: nie umie dołączyć pliku) — dla poczty w przeglądarce (Gmail, Onet…).
     Przycisk „Zmień sposób” przełącza kolejno; wybór pamiętany na urządzeniu. */
  let klientMs = '', pobieranieKlienta = false;
  const czyOutlook = () => !!klientMs && !matchMedia('(pointer:coarse)').matches && !!(globalThis.crypto && crypto.subtle);
  const METODY = ['outlook', 'plik', 'pulpit', 'poczta'];
  /* Zapamiętany sposób wysyłki jest osobny w każdej przeglądarce. Przy próbach z poprzednich wersji (m.in. gdy przeglądarka blokowała plik .eml) łatwo było zostawić „otwarcie poczty” —
     wiadomość otwiera się wtedy BEZ załącznika (mailto: nie umie go dołączyć). Wersja 2 wysyłki zeruje ten wybór jednorazowo: wszyscy zaczynają od domyślnego sposobu (plik .eml). */
  let prefPoczty = (() => { try { return wczytajSposobWysylki(localStorage, METODY); } catch (e) { return ''; } })();      // sam dostęp do localStorage może rzucić wyjątek (zablokowane dane witryn)
  /* „pulpit”: okno „Zapisz jako” otwiera się od razu na Pulpicie (File System Access API: showSaveFilePicker z startIn: 'desktop' — Chrome, Edge; Firefox i Safari go nie mają), nazwa pliku .eml jest wpisana.
     Po zapisie ikona gotowej wiadomości (adres, temat, treść i zahasłowana paczka w jednym pliku) leży na pulpicie — dwuklik otwiera pocztę. Strona nie może zapisać pliku na pulpicie sama, bez tego okna. */
  const czyPulpit = () => !matchMedia('(pointer:coarse)').matches && typeof window.showSaveFilePicker === 'function' && window.isSecureContext !== false;
  const dostepneMetody = () => matchMedia('(pointer:coarse)').matches ? ['plik'] : [...(czyOutlook() ? ['outlook'] : []), 'plik', ...(czyPulpit() ? ['pulpit'] : []), 'poczta'];
  /** Okno „Zapisz jako” na Pulpicie — wywoływane SYNCHRONICZNIE w obsłudze kliknięcia (przeglądarka pozwala na nie tylko tuż po geście użytkownika); zwraca obietnicę uchwytu pliku. */
  const zapytajOMiejsceZapisu = () => { const o = window.showSaveFilePicker({ suggestedName: 'PMT_wiadomosc_do_wyslania.eml', startIn: 'desktop', types: [{ description: 'Wiadomość e-mail (.eml)', accept: { 'message/rfc822': ['.eml'] } }] }); o.catch(() => {}); return o; };
  const metodaWysylki = () => { const d = dostepneMetody(); return d.includes(prefPoczty) ? prefPoczty : d[0]; };
  function wczytajKlientaMs() { if (pobieranieKlienta) return; pobieranieKlienta = true; wczytajKlienta().then(id => { if (id !== klientMs) { klientMs = id; odswiezWidok(); } }).finally(() => { pobieranieKlienta = false; }); }      // przy każdym otwarciu okna (mały plik, bez pamięci podręcznej): zmiana ustawienia działa od razu
  function zmienPoczte() { const d = dostepneMetody(); prefPoczty = d[(d.indexOf(metodaWysylki()) + 1) % d.length]; try { localStorage.setItem('pmt-ui-poczta', prefPoczty); } catch (e) { /* bez pamięci przeglądarki wybór obowiązuje do zamknięcia okna */ } odswiezWidok(); }
  /** mailto: (RFC 6068): „@” zostaje w adresie, temat i treść zakodowane, nowe wiersze jako CRLF. */
  const mailtoDo = (adres, tem, tr) => `mailto:${encodeURIComponent(adres).replace(/%40/g, '@')}?subject=${encodeURIComponent(tem)}&body=${encodeURIComponent(String(tr).replace(/\r?\n/g, '\r\n'))}`;
  /** Otwarcie poczty. Test może przechwycić adres (okno __testy), bo przeglądarka bez zainstalowanego programu pocztowego nic z mailto: nie robi. */
  const otworzMailto = u => { if (window.__testy && typeof window.__przechwycMailto === 'function') { window.__przechwycMailto(u); return; } try { location.href = u; } catch (e) { /* bez programu pocztowego — jest odnośnik w komunikacie */ } };
  const NAZWA_METODY = { outlook: 'szkic w Outlooku', plik: 'plik wiadomości .eml', pulpit: 'zapis na pulpicie (.eml)', poczta: 'samo otwarcie poczty — paczkę dołączysz sam' };
  const przyciskWyslij = () => mozeWyslac() ? `${dostepneMetody().length > 1 ? `<span class="wyslij-sposob">Sposób: <b>${NAZWA_METODY[metodaWysylki()]}</b></span>` : ''}<button type="button" class="przycisk glowny" data-akcja="wyslij" data-metoda="${metodaWysylki()}">${ik('i-wyslij')}Wyślij</button>${dostepneMetody().length > 1 ? `<button type="button" class="przycisk maly" data-akcja="zmien-poczte">Zmień sposób</button>` : ''}`
    : `<button type="button" class="przycisk glowny" disabled aria-disabled="true">${ik(wyslane() ? 'i-ok' : 'i-wyslij')}${wyslane() ? 'Wysłano' : 'Wyślij'}</button>`;
  const opisWyslij = () => !wszystkoPodpisane() ? 'Odblokuje się, gdy wgrasz i sprawdzę wszystkie podpisane dokumenty.'
    : wyslane() ? `Dokumenty wysłane${M().wyslaneKiedy ? ' ' + dataPl(M().wyslaneKiedy) : ''}. Gdyby wiadomość nie wyszła z poczty, „Cofnij wysłanie” na pulpicie przywraca stan sprzed wysyłki.`
    : zablokowana() ? esc(daneWysylki.komunikat)
    : `Wszystkie dokumenty sprawdzone. „Wyślij” zrobi z nich zahasłowaną paczkę i ${({ outlook: 'otworzy gotowy szkic wiadomości w Twoim Outlooku (adres, temat, treść i załącznik)', plik: matchMedia('(pointer:coarse)').matches ? 'otworzy pocztę z gotową wiadomością (paczkę dołączysz z folderu Pobrane)' : 'przygotuje gotową wiadomość (adres, temat, treść i paczka w jednym pliku .eml) — otworzy się w Twojej poczcie i zostanie tylko kliknąć „Wyślij”', pulpit: 'zapisze na pulpicie ikonę gotowej wiadomości (adres, temat, treść i paczka w jednym pliku) — klikniesz ją dwukrotnie, a otworzy się poczta ze wszystkim', poczta: 'otworzy Twój program pocztowy z adresem, tematem i treścią (paczkę zapisze w folderze Pobrane, do dołączenia)' })[metodaWysylki()] || 'przygotuje wiadomość'}.`;      // adres odbiorcy zna tylko administrator — użytkownikowi się go nie pokazuje (trafia tylko do pola „Do” gotowej wiadomości)
  function wczytajDane() { if (daneWysylki !== undefined || pobieranieDanych) return; pobieranieDanych = true; hasloDoPaczki().then(o => { daneWysylki = o; daneWysylkiTs = Date.now(); }).finally(() => { pobieranieDanych = false; odswiezWidok(); }); }
  /** Lista dokumentów do pobrania w kroku „Podpisz”: każdy PDF osobno (przycisk obok nazwy); pobrane są oznaczone. Rozliczenie wydatków nie wymaga podpisu — jest na liście, bo trafia do paczki. */
  function wierszePobierania() {
    const pob = pobrane();
    return `<ul class="kk-pliki" aria-label="Dokumenty do pobrania">${k.nazwyDok().map(d => `<li class="kk-plik${pob.has(d.i) ? ' pobrano' : ''}"><span class="kk-plik-nazwa"><b>${d.tytul}</b><small>${d.rozliczenie ? 'podpis niewymagany' : d.opis}</small></span><button type="button" class="przycisk maly" data-akcja="pobierz-dok" data-i="${d.i}" aria-label="Pobierz PDF: ${esc(d.tytul)}">${pob.has(d.i) ? `${ik('i-ok')}Pobrano` : `${ik('i-pobierz')}Pobierz PDF`}</button></li>`).join('')}</ul>`;
  }
  /** „Otwórz gov.pl” działa dopiero po pobraniu choć jednego dokumentu; wcześniej to wyszarzony przycisk bez adresu (nic nie otworzy). */
  const akcjeGov = () => `<span class="kk-przyciski" id="kk-gov-akcje"><button type="button" class="przycisk" data-akcja="osobno">${ik('i-pobierz')}Pobierz wszystkie</button>${pobrane().size
    ? `<a class="przycisk glowny" id="otworz-gov" href="${k.URL_PODPIS}" target="_blank" rel="noopener">Otwórz gov.pl</a>`
    : `<button type="button" class="przycisk glowny" id="otworz-gov" disabled aria-disabled="true">Otwórz gov.pl</button>`}</span>${pobrane().size ? '' : '<small class="kk-podp" id="kk-gov-podp">„Otwórz gov.pl” odblokuje się po pobraniu dokumentów.</small>'}`;
  function widokGlowny() {
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
      <div class="ark-dol" id="podp-dol"><button type="button" class="przycisk" data-zamknij>Zamknij</button></div>`;
  }
  function odswiezWidok() {
    if (widok !== 'glowny') return;
    odswiezKarty();
    const l = $('#podp-licznik', arkTresc); if (l) l.innerHTML = podsumowanie();
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
    k.pobierzBlob(k.blobPdf(b), bezOgonkow(d.nazwa)); oznaczPobrane([i]); odswiezPobieranie();
  }
  /** Wszystkie dokumenty po kolei, każdy jako osobny PDF (przeglądarki mogą zapytać o zgodę na kilka pobrań). */
  async function pobierzOsobno() {
    const o = await oryginaly(); if (!o.length) { pokazToast('Nie znalazłem dokumentów — wygeneruj je ponownie'); return; }
    for (const x of o) { k.pobierzBlob(k.blobPdf(x.bajty), bezOgonkow(x.d.nazwa)); oznaczPobrane([x.d.i]); await czekaj(450); }      // pauza: przeglądarki gubią pobrania uruchomione w tej samej chwili
    odswiezPobieranie();
    pokazToast(`Pobrano ${o.length} ${liczba(o.length, 'plik', 'pliki', 'plików')} do folderu Pobrane (przeglądarka mogła zapytać o zgodę na kilka pobrań)`);
  }
  /** Po pobraniu: odświeża tylko listę dokumentów i przycisk gov.pl (reszta okna, np. karuzela, zostaje jak była). */
  function odswiezPobieranie() {
    if (widok !== 'glowny') return;
    const l = $('.kk-gov .kk-pliki', arkTresc), a = $('#kk-gov-akcje', arkTresc); if (!l || !a) return;
    l.outerHTML = wierszePobierania(); const p = $('#kk-gov-podp', arkTresc); if (p) p.remove(); a.outerHTML = akcjeGov();
  }
  async function plikDoWydruku() {
    const o = await oryginaly(); if (!o.length) { pokazToast('Nie znalazłem dokumentów — wygeneruj je ponownie'); return null; }
    try { return k.blobPdf(scalPdf(o.map(x => x.bajty))); }
    catch (e) { console.error('scalanie PDF', e); pokazToast('Nie udało się połączyć dokumentów w jeden plik — pobieram je osobno'); await pobierzOsobno(); return null; }
  }
  async function drukuj() { const b = await plikDoWydruku(); if (!b) return; const u = URL.createObjectURL(b), w = window.open(u, '_blank'); if (!w) k.pobierzBlob(b, 'Dokumenty_do_wydruku.pdf'); setTimeout(() => URL.revokeObjectURL(u), 120000); }
  async function pobierzWydruk() { const b = await plikDoWydruku(); b && k.pobierzBlob(b, 'Dokumenty_do_wydruku.pdf'); }

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
  function potwierdz(i) {
    const w = weryfikacje()[i]; if (!w) return;
    zapiszWeryfikacje(i, Object.assign({}, w, { potwierdzone: true, kontrole: [...w.kontrole, { id: 'reczne', stan: 'ok', tekst: 'Podpis potwierdzony ręcznie przez Ciebie' }] }));
    k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok();
    if (wszystkoPodpisane()) { k.kurtyna() && k.kurtyna().swieto(); k.zorza() && k.zorza().flara(1); pokazToast('Wszystko podpisane — możesz wysłać dokumenty'); }
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
    if (wszystkoPodpisane()) { k.kurtyna() && k.kurtyna().swieto(); k.zorza() && k.zorza().flara(1); pokazToast('Wszystko podpisane i sprawdzone — możesz wysłać dokumenty'); }
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
  const stanPoEml = duza => radaUkryta()
    ? `Wiadomość gotowa: <span class="adr">${EML}</span> z adresatem, tematem, treścią i zahasłowaną paczką. Jeśli poczta nie otworzyła się sama, <span class="adr">kliknij pobrany plik</span> (pasek pobierania albo folder Pobrane); w poczcie kliknij „Wyślij”.${chromium() ? ' Jeśli Edge albo Chrome pyta, czy zachować plik — wybierz „Zachowaj”.' : ''} <button type="button" class="przycisk maly" data-akcja="eml-rada">Jak sprawić, żeby otwierała się sama?</button>${duza}`
    : `Pobrałem wiadomość <span class="adr">${EML}</span>. <span class="adr">Kliknij ją</span> (pasek pobierania przeglądarki albo folder Pobrane) — otworzy się poczta z adresatem, tematem, treścią i zahasłowaną paczką; kliknij tam „Wyślij”.${duza}${radaEml()}`;
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
  arkTresc.addEventListener('drop', e => { const s = e.target.closest && e.target.closest('.podp-strefa'); if (!s) return; e.preventDefault(); przyjmij(e.dataTransfer.files); });

  /* ---------------------------------- wejścia ---------------------------------- */
  return {
    /** fokus (opcjonalnie): numer dokumentu, od którego okno ma zacząć — z probówki na pulpicie: karuzela ustawia go z przodu, na liście karta mignie i przewinie się na środek. */
    otworz(fokus) { wczytajKlientaMs(); const cel = Number.isInteger(fokus) && fokus >= 0 && fokus < k.razemDok() ? fokus : null; widok = 'glowny'; wgrane = []; otwarte = new Set(); stanWysylki = ''; daneWysylki = undefined; gotowyEml = null; widziane = {}; podgladI = null; fokusI = cel; if (cel !== null) { przodI = cel; setTimeout(() => { if (fokusI === cel) fokusI = null; }, 1600); } zapamietajStany(); k.otworzArkusz(widokGlowny(), null, { szeroki: true }); uruchomKaruzele();
      if (cel !== null && widokKart === 'lista') { const c = $(`.dok-k[data-i="${cel}"]`, arkTresc); if (c) c.scrollIntoView({ block: 'center' }); } if (wszystkoPodpisane() && !wyslane()) wczytajDane(); ujednolicStare().then(dokonczSprawdzanie).then(odswiezWidok).catch(e => console.error('nazwy plików', e)); },
    otworzWyslij() { this.otworz(); },      // „Wyślij” jest krokiem 5 w tym samym oknie co pobieranie, podpis i wgrywanie
  };
}
