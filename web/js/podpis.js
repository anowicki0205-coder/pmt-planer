// PMT Planer (web) — podpisywanie, sprawdzanie podpisów i wysyłka dokumentów miesiąca.
// Okno „Dokumenty do podpisu” prowadzi pięcioma krokami (piąty, „Wyślij”, jest szary, dopóki wszystkie dokumenty nie są wgrane i sprawdzone):
//   1. Pobierz dokumenty (jeden ZIP albo osobne pliki),
//   2. Podpisz: elektronicznie na gov.pl (Profil Zaufany) albo odręcznie (wydruk) — aplikacja nie ma jak wysłać plików na gov.pl, bo to osobna strona, więc pliki idą przez dysk,
//   3. Wgraj podpisane pliki (PDF z podpisem, plik .xades, paczka ZIP, skany i zdjęcia — wszystkie naraz; aplikacja sama dopasowuje je do dokumentów),
//   4. Sprawdzenie: dla każdego dokumentu — czy jest podpis, czy obejmuje całość, czy dokument nie został zmieniony, czy podpisała właściwa osoba (imię i nazwisko, PESEL),
//      a przy podpisie odręcznym — czy na skanie widać podpis w miejscu „podpis pracownika”. Dopiero sprawdzone dokumenty liczą się jako podpisane,
//   5. Wyślij: wysyłka na adres Kierownika regionu. Pole „albo przeciągnij tu podpisane pliki” leży między krokiem 3 a 4 — tam, gdzie się wgrywa.
import { zipuj, scalPdf, dopasujPliki, rozpakujZip } from './pliki.js';
import { ocenPodpisElektroniczny, podpisyWPdf, czasPl, xadesDotyczy } from './weryfikacja.js';
import { stronyZeSkanu, szukajPodpisu, strefaPodpisu, obrazyZPdf } from './podpis_reczny.js';

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
  let widok = 'glowny', otwarte = new Set(); const sprawdzane = new Set();

  /* ---------------------------------- pomocnicze ---------------------------------- */
  const nagl = (tytul, wstecz) => `<div class="ark-gora">${wstecz ? `<button type="button" class="ark-wstecz" data-akcja="glowny" aria-label="Wstecz">${ik('i-lewo')}</button>` : ''}<h2 id="ark-tyt">${tytul}</h2><button type="button" class="ark-zam" data-zamknij aria-label="Zamknij">${ik('i-zamknij')}</button></div>`;
  const wszystkoPodpisane = () => k.razemDok() > 0 && k.ilePodpisanych() >= k.razemDok();
  const nazwaZip = () => `Dokumenty_${bezOgonkow(k.PROFIL().imie).replace(/\s+/g, '_')}_${bezOgonkow(String(k.MIES[M().mies - 1]))}_${M().rok}.zip`;
  async function oryginal(d) { return magPliki.daj(k.klucz(d.nazwa)); }
  async function oryginaly() { const wyn = []; for (const d of k.nazwyDok()) { const b = await oryginal(d); if (b) wyn.push({ d, bajty: b }); } return wyn; }
  let adresObietnica = null;
  const adresOdbiorcy = () => adresObietnica || (adresObietnica = fetch('odbiorca.txt', { cache: 'no-store' }).then(r => r.ok ? r.text() : '')
    .then(t => String(t).split(/\r?\n/).map(x => x.trim()).find(l => EMAIL.test(l)) || '').catch(() => ''));
  const miejscaPodpisu = d => ((M().wynik || {}).miejsca_podpisu || {})[d.nazwa] || null;

  /* ---------------------------------- widok główny: cztery kroki ---------------------------------- */
  const stanKarty = i => { const w = weryfikacje()[i]; if (sprawdzane.has(i)) return 'trwa'; if (!w) return plikiDok(i).length ? 'trwa' : 'czeka'; return M().podpisane[i] ? 'ok' : (w.stan === 'zle' ? 'zle' : 'uwaga'); };
  const CHIP = { czeka: 'czeka na podpis', trwa: 'sprawdzam…', ok: 'podpis sprawdzony', uwaga: 'do sprawdzenia', zle: 'błąd podpisu' };
  function komunikatKarty(i) {
    const w = weryfikacje()[i]; if (!w) return plikiDok(i).length ? 'Sprawdzam plik…' : 'Wgraj podpisany plik tego dokumentu';
    if (M().podpisane[i]) return w.potwierdzone ? 'Podpis potwierdzony przez Ciebie' : w.rodzaj === 'odreczny' ? 'Widzę podpis w miejscu „podpis pracownika”' : `Podpisał(a): ${esc(w.sygnatariusz || '—')}${w.czas ? ' · ' + czasPl(new Date(w.czas)) : ''}`;
    const zly = (w.kontrole.find(c => c.stan === 'zle') || w.kontrole.find(c => c.stan === 'uwaga')); return zly ? esc(zly.tekst) : 'Wymaga sprawdzenia';
  }
  function szczegoly(d) {
    const w = weryfikacje()[d.i]; if (!w) return '';
    const pliki = plikiDok(d.i), mozna = !M().podpisane[d.i] && !w.potwierdzone && (w.rodzaj === 'odreczny' || (w.rodzaj !== 'brak' && !w.kontrole.some(c => c.stan === 'zle')));
    return `<div class="dok-szcz"><ul class="kontrole">${w.kontrole.map(c => `<li class="kt-${c.stan}">${ik(IKONA_STANU[c.stan] || 'i-info')}<span>${esc(c.tekst)}</span></li>`).join('')}</ul>
      ${w.podglad ? `<figure class="podglad-podpisu"><img src="${w.podglad}" alt="Wycinek skanu z miejscem na podpis"><figcaption>Tak widzę miejsce „podpis pracownika” na skanie</figcaption></figure>` : ''}
      <small class="dok-plik">Plik: ${esc(pliki.join(', '))}</small>
      <div class="dok-akcje">${mozna ? `<button type="button" class="przycisk maly glowny" data-akcja="potwierdz" data-i="${d.i}">${ik('i-ok')}Potwierdzam, że podpis jest</button>` : ''}<button type="button" class="przycisk maly" data-akcja="cofnij" data-i="${d.i}">${ik('i-cofnij')}Wgraj inny plik</button><button type="button" class="przycisk maly" data-akcja="szczegoly" data-i="${d.i}">Zwiń</button></div></div>`;
  }
  function kartaDok(d) {
    const st = stanKarty(d.i), otw = otwarte.has(d.i) && st !== 'czeka';
    return `<div class="dok-k st-${st}${otw ? ' otwarta' : ''}" data-i="${d.i}"><div class="dok-k-g"><b>${d.tytul}</b><span class="stan st-${st}"><i></i>${CHIP[st]}</span></div><small>${d.opis}</small>
      <p class="dok-kom">${komunikatKarty(d.i)}</p>
      ${otw ? szczegoly(d) : `<div class="dok-akcje"><button type="button" class="przycisk maly" data-akcja="otworz" data-nazwa="${esc(d.nazwa)}">Otwórz</button>${st !== 'czeka' && st !== 'trwa' ? `<button type="button" class="przycisk maly" data-akcja="szczegoly" data-i="${d.i}">Szczegóły</button>` : ''}</div>`}</div>`;
  }
  const kartyDok = () => `<div class="dok-siatka" id="dok-siatka">${k.nazwyDok().map(kartaDok).join('')}</div>`;
  function podsumowanie() {
    const razem = k.razemDok(), ok = k.ilePodpisanych(), wgr = k.nazwyDok().filter(d => plikiDok(d.i).length).length;
    if (!wgr) return `${razem} ${liczba(razem, 'dokument czeka', 'dokumenty czekają', 'dokumentów czeka')} na podpis`;
    return wszystkoPodpisane() ? `<b>Wszystkie ${razem} dokumentów sprawdzone — możesz wysłać</b>` : `<b>${ok} z ${razem}</b> sprawdzonych pozytywnie${wgr - ok > 0 ? ` · ${wgr - ok} do poprawy lub potwierdzenia` : ''}`;
  }
  /** Krok 5: do czasu, aż wszystkie dokumenty są wgrane i sprawdzone, przycisk jest wyszarzony i NIE niesie data-akcja (nic go nie uruchomi). */
  const przyciskWyslij = () => wszystkoPodpisane() ? `<button type="button" class="przycisk glowny" data-akcja="wyslij">${ik('i-wyslij')}Wyślij</button>` : `<button type="button" class="przycisk glowny" disabled aria-disabled="true">${ik('i-wyslij')}Wyślij</button>`;
  const opisWyslij = () => wszystkoPodpisane() ? 'Wszystkie dokumenty sprawdzone — możesz wysłać je Kierownikowi regionu.' : 'Odblokuje się, gdy wgrasz i sprawdzę wszystkie podpisane dokumenty.';
  function widokGlowny() {
    const razem = k.razemDok(), tury = Math.ceil(razem / LIMIT_GOV);
    return `${nagl('Dokumenty do podpisu')}
      <ol class="kroki4">
        <li class="krok-k k1"><span class="kk-nr">1</span><div class="kk-tresc"><b>Pobierz dokumenty</b><small>${razem} ${liczba(razem, 'dokument gotowy', 'dokumenty gotowe', 'dokumentów gotowych')} do podpisu. Zapisz je na dysku — program nie ma jak wysłać ich na gov.pl sam.</small></div>
          <span class="kk-akcje"><button type="button" class="przycisk glowny" id="pobierz-wsz" data-akcja="zip">${ik('i-pobierz')}Wszystkie (ZIP)</button><button type="button" class="przycisk" data-akcja="osobno">Osobne pliki</button></span></li>
        <li class="krok-k k2"><span class="kk-nr">2</span><div class="kk-tresc"><b>Podpisz</b>
          <div class="kk-opcje">
            <div class="kk-opcja"><b>${ik('i-pioro')}Elektronicznie (gov.pl)</b><small>Profil Zaufany, bezpłatnie. gov.pl przyjmuje naraz do ${LIMIT_GOV} plików po 25 MB${tury > 1 ? ` — przy ${razem} dokumentach podpisz w ${tury} ${liczba(tury, 'turze', 'turach', 'turach')}` : ''}.</small><a class="przycisk" href="${k.URL_PODPIS}" target="_blank" rel="noopener">Otwórz gov.pl</a></div>
            <div class="kk-opcja"><b>${ik('i-drukuj')}Odręcznie</b><small>Wydrukuj, podpisz długopisem w miejscu „podpis pracownika”, zeskanuj (aplikacja skanująca, nie zdjęcie pod kątem).</small><span class="kk-przyciski"><button type="button" class="przycisk" data-akcja="drukuj">Wydrukuj</button><button type="button" class="przycisk" data-akcja="pdf-wydruk">Pobierz PDF</button></span></div>
          </div></div></li>
        <li class="krok-k k3"><span class="kk-nr">3</span><div class="kk-tresc"><b>Wgraj podpisane pliki</b><small>Wszystkie naraz: PDF z podpisem, plik .xades, paczka ZIP z gov.pl, skany i zdjęcia. Sam dopasuję je do dokumentów.</small></div>
          <span class="kk-akcje"><label class="przycisk glowny podp-wgraj">${ik('i-skan')}Wybierz pliki<input type="file" id="plik-wgraj" multiple accept="${AKCEPT}" data-wgraj hidden></label></span></li>
        <li class="krok-strefa"><label class="podp-strefa" for="plik-wgraj" data-strefa><span>albo przeciągnij tu podpisane pliki</span></label></li>
        <li class="krok-k k4"><span class="kk-nr">4</span><div class="kk-tresc"><b>Sprawdzenie</b><small class="podp-licznik" id="podp-licznik">${podsumowanie()}</small></div></li>
        <li class="krok-k k5 ${wszystkoPodpisane() ? 'aktywny' : 'nieaktywny'}"><span class="kk-nr">5</span><div class="kk-tresc"><b>Wyślij</b><small id="podp-wyslij-opis">${opisWyslij()}</small></div>
          <span class="kk-akcje" id="podp-wyslij-akcje">${przyciskWyslij()}</span></li>
      </ol>
      <div id="podp-odrzucone" aria-live="polite"></div>
      ${kartyDok()}
      <div id="podp-wyniki"></div>
      <div class="ark-dol" id="podp-dol"><button type="button" class="przycisk" data-zamknij>Zamknij</button></div>`;
  }
  function odswiezWidok() {
    if (widok !== 'glowny') return;
    const s = $('#dok-siatka', arkTresc); if (s) s.outerHTML = kartyDok();
    const l = $('#podp-licznik', arkTresc); if (l) l.innerHTML = podsumowanie();
    const k5 = $('.krok-k.k5', arkTresc);
    if (k5) { const akt = wszystkoPodpisane(); k5.classList.toggle('aktywny', akt); k5.classList.toggle('nieaktywny', !akt); $('#podp-wyslij-opis', k5).textContent = opisWyslij(); $('#podp-wyslij-akcje', k5).innerHTML = przyciskWyslij(); }
    pokazWyniki();
  }
  async function widokWyslij() {
    const adres = await adresOdbiorcy(), zal = await zalaczniki(), odb = magUst.daj('odbiorca', ''), razemB = zal.reduce((a, z) => a + z.bajty.length, 0);
    const pole = adres ? `<p class="ark-opis">Adresat: <b id="w-adres">${esc(adres)}</b></p>`
      : `<label class="pole"><span>Adres Kierownika regionu</span><input id="w-odb" type="email" inputmode="email" autocomplete="email" value="${esc(odb)}" placeholder="adres@firma.pl" data-pierwsze><small></small></label>`;
    return `${nagl('Wyślij do Kierownika regionu', true)}
      <p class="ark-opis">Dołączę <b>${zal.length} ${liczba(zal.length, 'plik', 'pliki', 'plików')}</b> (${mb(razemB)}) z podpisanymi dokumentami — wszystkie sprawdzone. Poczta otworzy się u Ciebie — wiadomość wysyłasz sam, więc hasła do skrzynki nie podajesz nigdzie.</p>
      ${razemB > LIMIT_POCZTY ? `<p class="ark-opis zle" id="w-duze">Załączniki ważą ${mb(razemB)}, a poczta zwykle przyjmuje do 20–25 MB. Największe są zdjęcia — zrób skan do PDF (np. w aplikacji skanującej na telefonie) albo wyślij dokumenty w dwóch wiadomościach.</p>` : ''}
      ${pole}
      <div class="ark-dol"><button type="button" class="przycisk" data-akcja="glowny">Wstecz</button><button type="button" class="przycisk" id="w-mailto">Otwórz pocztę</button><button type="button" class="przycisk glowny" id="w-udostepnij"${adres ? ' data-pierwsze' : ''}>${ik('i-wyslij')}Udostępnij pliki</button></div>
      <p class="ark-opis podp-pod">Poczta w przeglądarce nie dołączy plików sama: „Otwórz pocztę” pobiera plik ZIP do załączenia, a „Udostępnij pliki” (telefon) przekazuje je prosto do aplikacji pocztowej.</p>
      <div class="ark-dol"><button type="button" class="przycisk" id="w-oznacz">Już wysłane — oznacz</button></div>`;
  }
  function pokaz(nowy) {
    widok = nowy;
    const wstaw = html => { k.zmienArkusz(html); const a = $('#arkusz'); a.classList.remove('widok-wejscie'); void a.offsetWidth; a.classList.add('widok-wejscie'); };
    if (nowy === 'wyslij') { widokWyslij().then(wstaw); return; }
    wstaw(widokGlowny()); pokazWyniki();
  }

  /* ---------------------------------- pobieranie i drukowanie ---------------------------------- */
  async function zip() {
    const o = await oryginaly(); if (!o.length) { pokazToast('Nie znalazłem dokumentów — wygeneruj je ponownie'); return; }
    k.pobierzBlob(zipuj(o.map(x => ({ nazwa: bezOgonkow(x.d.nazwa), bajty: x.bajty }))), nazwaZip());
    pokazToast(`Pobrano ${o.length} ${liczba(o.length, 'dokument', 'dokumenty', 'dokumentów')} w jednym pliku ZIP`);
  }
  async function pobierzOsobno() {
    const o = await oryginaly(); if (!o.length) { pokazToast('Nie znalazłem dokumentów — wygeneruj je ponownie'); return; }
    for (const x of o) { k.pobierzBlob(k.blobPdf(x.bajty), bezOgonkow(x.d.nazwa)); await czekaj(450); }      // pauza: przeglądarki gubią pobrania uruchomione w tej samej chwili
    pokazToast(`Pobrano ${o.length} ${liczba(o.length, 'plik', 'pliki', 'plików')} do folderu Pobrane (przeglądarka mogła zapytać o zgodę na kilka pobrań)`);
  }
  async function plikDoWydruku() {
    const o = await oryginaly(); if (!o.length) { pokazToast('Nie znalazłem dokumentów — wygeneruj je ponownie'); return null; }
    try { return k.blobPdf(scalPdf(o.map(x => x.bajty))); }
    catch (e) { console.error('scalanie PDF', e); pokazToast('Nie udało się połączyć dokumentów w jeden plik — pobieram je osobno w ZIP-ie'); await zip(); return null; }
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
  async function zapiszPliki(i, { dodaj, usun, metoda, zachowaj } = {}) {
    const d = k.nazwyDok().find(x => x.i === i); if (!d) return;
    const org = pierwotne()[i] || {};
    let zrodla = plikiDok(i).filter(n => n !== usun).map(n => ({ n, orig: org[n] || n }));
    if (dodaj) { zrodla = zrodla.filter(z => z.orig !== dodaj.orig); zrodla.push({ n: null, orig: dodaj.orig, bajty: dodaj.bajty }); }
    for (const z of zrodla) if (!z.bajty) z.bajty = await magPliki.daj(k.kluczPodp(i, z.n));
    zrodla = zrodla.filter(z => z.bajty);
    const nowe = docelowe(d, zrodla);
    for (let j = 0; j < zrodla.length; j++) if (zrodla[j].n !== nowe[j]) await magPliki.zapisz(k.kluczPodp(i, nowe[j]), zrodla[j].bajty);
    for (const n of plikiDok(i)) if (!nowe.includes(n)) { try { await magPliki.usun(k.kluczPodp(i, n)); } catch (e) { /* plik mógł już zniknąć */ } }
    zmienPliki(i, nowe, metoda, Object.fromEntries(nowe.map((n, j) => [n, zrodla[j].orig])), zachowaj);
  }
  async function przypisz(w, i) { await zapiszPliki(i, { dodaj: { orig: w.plik.name, bajty: w.bajty }, metoda: w.rodzaj === 'e' ? 'e' : 'reczny' }); w.i = i; }
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
  async function ocenOdreczny(d, pliki) {
    const kontrole = [], dodaj = (id, stan, tekst) => kontrole.push({ id, stan, tekst });
    const strony = []; let powod = '';
    for (const p of pliki) { const s = await stronyZeSkanu(p.bajty, p.nazwa); strony.push(...s.strony); if (s.powod) powod = s.powod; }
    const sp = strefaPodpisu(miejscaPodpisu(d));
    dodaj('podpis', 'info', 'Podpis odręczny (skan albo zdjęcie dokumentu)');
    let podglad = '';
    if (!strony.length) dodaj('miejsce', 'uwaga', (powod || 'Nie umiem odczytać obrazu') + ' — obejrzyj plik sam i potwierdź podpis');
    else if (!sp) dodaj('miejsce', 'uwaga', 'Ten miesiąc wygenerowano starszą wersją programu — nie znam miejsca podpisu. Obejrzyj skan sam i potwierdź podpis');
    else {
      const bm = strony[Math.min(Math.max(0, sp.strona - 1), strony.length - 1)];
      if (sp.strona > strony.length) dodaj('strony', 'uwaga', `Dokument ma ${sp.strona} ${liczba(sp.strona, 'stronę', 'strony', 'stron')}, a we wgranym pliku jest ich ${strony.length} — sprawdzam ostatnią`);
      const o = szukajPodpisu(bm, sp.strefa); podglad = o.podglad || '';
      if (o.stan === 'jest') dodaj('miejsce', 'ok', `Widzę ślad podpisu w miejscu „${sp.opis}”`);
      else if (o.stan === 'brak') dodaj('miejsce', 'zle', `Nie widzę podpisu w miejscu „${sp.opis}” — podpisz długopisem i zeskanuj ponownie (albo potwierdź, jeśli podpis tam jest)`);
      else dodaj('miejsce', 'uwaga', o.powod || 'Nie umiem ocenić skanu');
    }
    dodaj('osoba', 'info', `Imię i nazwisko na dokumencie: ${k.PROFIL().imie} (wydrukowane z Twoich danych). Odręcznego podpisu nie umiem odczytać — porównaj sam`);
    const stan = kontrole.some(c => c.stan === 'zle') ? 'zle' : kontrole.some(c => c.stan === 'uwaga') ? 'uwaga' : 'ok';
    return { rodzaj: 'odreczny', kontrole, stan, sygnatariusz: '', czas: null, podglad };
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
  async function sprawdz(i) {
    const d = k.nazwyDok().find(x => x.i === i); if (!d) return;
    sprawdzane.add(i); odswiezWidok();
    try {
      const nazwy = plikiDok(i), pliki = [];
      for (const n of nazwy) { const b = await magPliki.daj(k.kluczPodp(i, n)); if (b) pliki.push({ nazwa: n, bajty: b }); }
      const orig = await oryginal(d), profil = k.PROFIL();
      const pdfPodpisany = pliki.find(p => /\.pdf$/i.test(p.nazwa) && podpisyWPdf(p.bajty).length), xades = pliki.find(p => XADES.test(p.nazwa));
      let w;
      if (pdfPodpisany) w = await ocenPodpisElektroniczny({ bajty: pdfPodpisany.bajty, oryginal: orig, imie: profil.imie, pesel: profil.pesel });
      else if (xades) w = await ocenPodpisElektroniczny({ xades: new TextDecoder('utf-8').decode(xades.bajty), oryginal: orig, imie: profil.imie, pesel: profil.pesel });
      else if (pliki.some(p => INNY_PODPIS.test(p.nazwa))) w = { rodzaj: 'e', kontrole: [{ id: 'podpis', stan: 'uwaga', tekst: 'Ten rodzaj pliku podpisu (.p7s/.sig) nie jest obsługiwany do sprawdzania — użyj podpisu w PDF albo pliku .xades' }], stan: 'uwaga', sygnatariusz: '', czas: null };
      else w = await ocenOdreczny(d, pliki);
      w.kontrole = [...w.kontrole, ...kontroleNazwy(d, pliki)];
      w.kiedy = new Date().toISOString(); w.czas = w.czas ? new Date(w.czas).toISOString() : null;
      zapiszWeryfikacje(i, w);
    } catch (e) {
      console.error('sprawdzanie podpisu', e);
      zapiszWeryfikacje(i, { rodzaj: 'brak', kontrole: [{ id: 'blad', stan: 'uwaga', tekst: 'Nie udało się sprawdzić pliku: ' + (e.message || e) }], stan: 'uwaga', sygnatariusz: '', czas: null });
    } finally { sprawdzane.delete(i); }
    k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok();
  }
  function potwierdz(i) {
    const w = weryfikacje()[i]; if (!w) return;
    zapiszWeryfikacje(i, Object.assign({}, w, { potwierdzone: true, kontrole: [...w.kontrole, { id: 'reczne', stan: 'ok', tekst: 'Podpis potwierdzony ręcznie przez Ciebie' }] }));
    k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok();
    if (wszystkoPodpisane()) { k.kurtyna() && k.kurtyna().swieto(); k.zorza() && k.zorza().flara(1); pokazToast('Wszystko podpisane — możesz wysłać do Kierownika regionu'); }
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
  /** Skan zapisany jako jeden PDF z wieloma stronami (aplikacje skanujące) rozbijam na osobne obrazy — jedna strona to jeden dokument. */
  function rozbijSkan(plik, bajty) {
    const o = obrazyZPdf(bajty), baza = plik.name.replace(/\.pdf$/i, '');
    return o.map((dane, n) => ({ plik: new File([dane], `${baza}_str${String(n + 1).padStart(2, '0')}.jpg`, { type: 'image/jpeg' }), bajty: new Uint8Array(dane) }));
  }
  async function przyjmij(lista) {
    const { pliki, zepsute } = await rozwinZip([...lista]); if (!pliki.length && !zepsute.length) return;
    const nowe = zepsute.map(z => ({ plik: z.plik, bajty: new Uint8Array(0), i: null, jak: null, powod: z.powod, rodzaj: '' }));
    const dok = k.nazwyDok(), orgBajty = new Map(); for (const d of dok) orgBajty.set(d.i, await oryginal(d));
    for (const plik of pliki) {
      const bajty = new Uint8Array(await plik.arrayBuffer()); let rodzaj = '', powod = '';
      if (!bajty.length) powod = 'plik jest pusty';
      else if (XADES.test(plik.name) || INNY_PODPIS.test(plik.name)) rodzaj = 'e';
      else if (OBRAZ.test(plik.name)) rodzaj = 'skan';
      else if (/\.pdf$/i.test(plik.name)) {
        if (podpisyWPdf(bajty).length) rodzaj = 'e';
        else {
          const sk = rozbijSkan(plik, bajty);
          if (sk.length > 1) { for (const s of sk) nowe.push({ plik: s.plik, bajty: s.bajty, i: null, jak: null, powod: '', rodzaj: 'skan' }); continue; }
          if (sk.length === 1) rodzaj = 'skan';
          else powod = 'ten PDF nie ma podpisu elektronicznego ani nie jest skanem — podpisz go na gov.pl albo wydrukuj, podpisz i zeskanuj';
        }
      } else powod = 'ten rodzaj pliku nie jest obsługiwany (PDF z podpisem, .xades, ZIP, skan lub zdjęcie)';
      nowe.push({ plik, bajty, i: null, jak: null, powod, rodzaj });
    }
    const dobre = nowe.filter(w => !w.powod);
    const wynik = await dopasujPliki(dobre.map(w => w.plik), dok.map(d => ({ i: d.i, nazwa: d.nazwa, tytul: d.tytul, wolny: plikiDok(d.i).length === 0, bajty: async () => orgBajty.get(d.i), xades: async t => xadesDotyczy(t, orgBajty.get(d.i)) })), async f => dobre.find(w => w.plik === f).bajty);
    const dotkniete = new Set();
    for (const r of wynik) { const w = dobre.find(x => x.plik === r.plik); w.jak = r.jak; if (r.i !== null) { await przypisz(w, r.i); dotkniete.add(r.i); } }
    wgrane = [...nowe, ...wgrane.filter(p => !p.powod && !nowe.some(n => n.plik.name === p.plik.name))];      // dawne odrzucenia znikają przy kolejnym wgraniu
    for (const i of dotkniete) otwarte.delete(i);
    k.odswiezPodpisy(); k.odswiezHero(); odswiezWidok();
    for (const i of dotkniete) await sprawdz(i);
    const ok = [...dotkniete].filter(i => M().podpisane[i]).length;
    if (k.zorza() && ok) k.zorza().flara(.22);
    if (wszystkoPodpisane()) { k.kurtyna() && k.kurtyna().swieto(); k.zorza() && k.zorza().flara(1); pokazToast('Wszystko podpisane i sprawdzone — możesz wysłać do Kierownika regionu'); }
    else if (!dotkniete.size) pokazToast('Żaden plik nie został przyjęty — powody są pod krokami');
    else pokazToast(ok === dotkniete.size ? `Sprawdzono ${ok} ${liczba(ok, 'dokument', 'dokumenty', 'dokumentów')} — podpisy w porządku` : `Sprawdzono ${dotkniete.size}: ${ok} w porządku, ${dotkniete.size - ok} do poprawy — szczegóły w kartach dokumentów`);
  }
  const OPIS_JAK = { tresc: 'rozpoznany po zawartości', nazwa: 'dopasowany po nazwie', kolejnosc: 'przypisany według kolejności — sprawdź', reczne: 'przypisany przez Ciebie' };
  let wynikiOtwarte = false;      // czy użytkownik sam rozwinął listę dopasowań (gdy wszystko jest w porządku, lista jest zwinięta)
  function pokazWyniki() {
    const odrz = $('#podp-odrzucone', arkTresc), c = $('#podp-wyniki', arkTresc); if (!c || !odrz) return;
    const dok = k.nazwyDok(), zle = wgrane.filter(w => w.powod), reszta = wgrane.filter(w => !w.powod);
    odrz.innerHTML = zle.length ? `<div class="wyniki">${zle.map(w => `<div class="wynik zle"><span class="wn">${esc(w.plik.name)}</span><small>${esc(w.powod)}</small></div>`).join('')}</div>` : '';
    const zapisana = w => { if (w.i === null || w.i === undefined) return ''; const n = nazwaWgranego(w.i, w.plik.name); return n !== w.plik.name ? n : ''; };
    const wiersze = reszta.map(w => { const n = wgrane.indexOf(w), nowa = zapisana(w); return `<div class="wynik${w.i === null ? ' brak' : ''}"><span class="wn">${esc(w.plik.name)}${nowa ? `<em class="nowa-nazwa" title="Nazwa pliku zmieniona na taką, jak przy generowaniu">→ ${esc(nowa)}</em>` : ''}</span><select data-przypisz="${n}" aria-label="Dokument dla pliku ${esc(w.plik.name)}"><option value="">— nie przypisuj —</option>${dok.map(d => `<option value="${d.i}"${w.i === d.i ? ' selected' : ''}>${d.tytul}</option>`).join('')}</select>${w.jak ? `<small class="${w.jak === 'kolejnosc' ? 'uwaga' : ''}">${OPIS_JAK[w.jak]}</small>` : (w.i === null ? '<small class="uwaga">brak wolnego dokumentu — wybierz ręcznie</small>' : '')}</div>`; }).join('');
    const doSprawdzenia = reszta.filter(w => w.i === null || w.jak === 'kolejnosc').length, ile = reszta.length;
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
  const temat = () => `Delegacje — ${k.PROFIL().imie} — ${k.MIES[M().mies - 1]} ${M().rok}`;
  const tresc = 'W załączeniu dokumenty delegacyjne.';
  async function wyslij(tryb) {
    const adres = await adresOdbiorcy(), pole = $('#w-odb', arkTresc), v = adres || (pole ? pole.value.trim() : '');
    if (!adres && pole) { if (v) magUst.ustaw('odbiorca', v); }
    const zal = await zalaczniki();
    if (tryb === 'share') {
      const pliki = zal.map(z => new File([z.bajty], z.nazwa, { type: z.typ }));
      if (navigator.canShare && navigator.canShare({ files: pliki })) { try { await navigator.share({ files: pliki, title: temat(), text: tresc }); oznaczWyslane(); } catch (e) { if (e.name !== 'AbortError') pokazToast('Nie udało się udostępnić plików'); } }
      else { k.pobierzBlob(zipuj(zal.map(z => ({ nazwa: z.nazwa, bajty: z.bajty }))), nazwaZip()); pokazToast('Ta przeglądarka nie udostępnia plików do poczty — pobrałem ZIP z dokumentami, dołącz go do wiadomości'); }
      return;
    }
    if (!EMAIL.test(v)) { const s = pole && pole.parentElement.querySelector('small'); if (s) { s.textContent = 'Wpisz poprawny adres e-mail'; s.classList.add('zle'); } return; }
    k.pobierzBlob(zipuj(zal.map(z => ({ nazwa: z.nazwa, bajty: z.bajty }))), nazwaZip());
    location.href = `mailto:${encodeURIComponent(v)}?subject=${encodeURIComponent(temat())}&body=${encodeURIComponent(tresc + '\n\n(Dołącz pobrany plik ZIP z dokumentami.)')}`;
    pokazToast('Poczta otwarta — dołącz pobrany plik ZIP i wyślij wiadomość, potem kliknij „Już wysłane”');
  }
  function oznaczWyslane() { const m = M(); m.wyslane = true; k.zapiszRekord(); k.odswiezHero(); k.zamknijArkusz(); k.zorza() && k.zorza().flara(.7); pokazToast('Oznaczono jako wysłane. Gdyby nie poszło, kliknij „Cofnij wysłanie".'); }

  /* ---------------------------------- zdarzenia ---------------------------------- */
  arkTresc.addEventListener('click', async e => {
    const b = e.target.closest('[data-akcja]'); if (!b) return;
    const a = b.dataset.akcja;
    if (a === 'otworz') k.otworzPdf(b.dataset.nazwa);
    else if (a === 'zip') zip();
    else if (a === 'osobno') pobierzOsobno();
    else if (a === 'glowny') pokaz('glowny');
    else if (a === 'wyslij') pokaz('wyslij');
    else if (a === 'drukuj') drukuj();
    else if (a === 'pdf-wydruk') pobierzWydruk();
    else if (a === 'cofnij') cofnij(Number(b.dataset.i));
    else if (a === 'potwierdz') potwierdz(Number(b.dataset.i));
    else if (a === 'szczegoly') { const i = Number(b.dataset.i); if (otwarte.has(i)) otwarte.delete(i); else otwarte.add(i); odswiezWidok(); }
  });
  arkTresc.addEventListener('click', e => {
    if (e.target.closest('.dok-k-g') && widok === 'glowny') { const kt = e.target.closest('.dok-k'); const i = Number(kt && kt.dataset.i); if (kt && !kt.classList.contains('st-czeka') && !kt.classList.contains('st-trwa')) { if (otwarte.has(i)) otwarte.delete(i); else otwarte.add(i); odswiezWidok(); } }
    if (widok !== 'wyslij') return;
    if (e.target.closest('#w-udostepnij')) wyslij('share');
    else if (e.target.closest('#w-mailto')) wyslij('poczta');
    else if (e.target.closest('#w-oznacz')) { const p = $('#w-odb', arkTresc); p && p.value.trim() && magUst.ustaw('odbiorca', p.value.trim()); oznaczWyslane(); }
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
    otworz() { widok = 'glowny'; wgrane = []; otwarte = new Set(); k.otworzArkusz(widokGlowny(), null, { szeroki: true }); ujednolicStare().then(odswiezWidok).catch(e => console.error('nazwy plików', e)); },
    otworzWyslij() { wgrane = []; widok = 'wyslij'; k.otworzArkusz('', null, { szeroki: true }); pokaz('wyslij'); },
  };
}
