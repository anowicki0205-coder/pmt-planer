// PMT Planer (web) — podpisywanie, sprawdzanie podpisów i wysyłka dokumentów miesiąca.
// Okno „Dokumenty do podpisu” prowadzi pięcioma krokami (piąty, „Wyślij”, jest szary, dopóki wszystkie dokumenty nie są wgrane i sprawdzone):
//   1. Pobierz dokumenty (jeden ZIP albo osobne pliki),
//   2. Podpisz: elektronicznie na gov.pl (Profil Zaufany) albo odręcznie (wydruk) — aplikacja nie ma jak wysłać plików na gov.pl, bo to osobna strona, więc pliki idą przez dysk,
//   3. Wgraj podpisane pliki (PDF z podpisem, plik .xades, paczka ZIP, skany i zdjęcia — wszystkie naraz; aplikacja sama dopasowuje je do dokumentów),
//   4. Sprawdzenie: dla każdego dokumentu — czy jest podpis, czy obejmuje całość, czy dokument nie został zmieniony, czy podpisała właściwa osoba (imię i nazwisko, PESEL),
//      a przy podpisie odręcznym — czy na skanie widać podpis w miejscu „podpis pracownika”. Dopiero sprawdzone dokumenty liczą się jako podpisane,
//   5. Wyślij: zahasłowana paczka i gotowa wiadomość na wskazany adres (hasło nadaje administrator — js/dostep.js pobierzHasloPaczki). Pole „albo przeciągnij tu podpisane pliki” leży między krokiem 3 a 4 — tam, gdzie się wgrywa.
import { zipuj, scalPdf, dopasujPliki, rozpakujZip } from './pliki.js';
import { zipujAes } from './zipaes.js';
import { zbudujEml } from './poczta.js';
import { karuzela } from './karuzela.js';
import { atrapaHtml, daneDelegacji, daneRozliczenia } from './dokument_atrapa.js';
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
    const st = stanKarty(d.i), otw = otwarte.has(d.i) && st !== 'czeka', wys = wyslane() && st === 'ok';      // po wysłaniu zamiast „Otwórz” karta pokazuje, że dokument poszedł
    const szczegolyBtn = st !== 'czeka' && st !== 'trwa' ? `<button type="button" class="przycisk maly" data-akcja="szczegoly" data-i="${d.i}">Szczegóły</button>` : '';
    return `<div class="dok-k st-${st}${wys ? ' wyslano' : ''}${otw ? ' otwarta' : ''}" data-i="${d.i}"><div class="dok-k-g"><b>${d.tytul}</b><span class="stan st-${st}"><i></i>${wys ? 'wysłano' : CHIP[st]}</span></div><small>${d.opis}</small>
      <p class="dok-kom">${komunikatKarty(d.i)}</p>
      ${otw ? szczegoly(d) : wys ? `<div class="dok-akcje"><span class="dok-wyslano">${ik('i-ok')}Wysłano${M().wyslaneKiedy ? ' ' + dataPl(M().wyslaneKiedy) : ''}</span>${szczegolyBtn}</div>` : `<div class="dok-akcje"><button type="button" class="przycisk maly" data-akcja="otworz" data-nazwa="${esc(d.nazwa)}">Otwórz</button>${szczegolyBtn}</div>`}</div>`;
  }
  const listaKart = () => `<div class="dok-siatka" id="dok-siatka">${k.nazwyDok().map(kartaDok).join('')}</div>`;

  /* ---------------------------------- widok 3D: karuzela z atrapami dokumentów ---------------------------------- */
  let widokKart = (() => { try { return localStorage.getItem('pmt-ui-karty') === '3d' ? '3d' : 'lista'; } catch (e) { return 'lista'; } })();      // „lista” jest domyślna; 3D to opcja, wybór pamiętany na urządzeniu
  let kar = null;                 // aktywna karuzela
  let podgladI = null;            // numer dokumentu w powiększonym podglądzie (tylko w widoku 3D)
  let przodI = 0;                 // która karta była z przodu (wraca po powiększeniu)
  const ruchDozwolony = () => !!k.zycie && !matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ctxDok = () => { const p = k.PROFIL() || {}, w = M().wynik || {}; return { imie: p.imie || '', pesel: p.pesel || '', adres: p.adres || '', stanowisko: p.stanowisko || 'merchandiser', przelozony: w.przelozony || '', miesiac: String(k.MIES[M().mies - 1] || ''), rok: M().rok }; };
  const daneDok = d => { const w = M().wynik; if (!w) return null; const pol = M().polecenia || []; return d.i < pol.length ? daneDelegacji(w, pol[d.i].nr, ctxDok()) : daneRozliczenia(w, ctxDok()); };
  const przelacznikWidoku = () => `<div class="k3-przel" role="group" aria-label="Sposób wyświetlania dokumentów"><button type="button" data-akcja="widok" data-w="lista" aria-pressed="${widokKart === 'lista'}">Karty</button><button type="button" data-akcja="widok" data-w="3d" aria-pressed="${widokKart === '3d'}">${ik('i-pioro')}Widok 3D</button></div>`;
  function karta3d(d) {
    const st = stanKarty(d.i), wys = wyslane() && st === 'ok', dane = daneDok(d);
    return `<div class="karta3d k3-${st}${wys ? ' wyslano' : ''}" data-i="${d.i}" role="group" aria-label="${esc(d.tytul)}: ${wys ? 'wysłano' : CHIP[st]}">
      <div class="k3-gl"><b>${d.tytul}</b><span class="stan st-${st}"><i></i>${wys ? 'wysłano' : CHIP[st]}</span></div>
      ${dane ? atrapaHtml(dane, { stan: st, maks: 6, wyslano: wys }) : '<div class="da-papier"></div>'}
      <div class="k3-st"><span>${d.opis}</span><div class="k3-akcje"><button type="button" class="przycisk maly" data-akcja="powieksz" data-i="${d.i}" tabindex="-1">Powiększ</button>${wys ? `<span class="dok-wyslano">${ik('i-ok')}Wysłano</span>` : `<button type="button" class="przycisk maly" data-akcja="otworz" data-nazwa="${esc(d.nazwa)}" tabindex="-1">Otwórz</button>`}</div></div></div>`;
  }
  const kropkiKart = () => k.nazwyDok().map(d => { const st = stanKarty(d.i); return `<button type="button" class="k3-kropka k3-${st}${d.i === przodI ? ' akt' : ''}" data-akcja="k3-do" data-i="${d.i}" title="${esc(d.tytul)} — ${CHIP[st]}" aria-label="${esc(d.tytul)}: ${CHIP[st]}"></button>`; }).join('');
  const nazwaPrzodu = () => { const d = k.nazwyDok()[przodI]; return d ? `${d.tytul} · ${CHIP[stanKarty(d.i)]} (${przodI + 1} z ${k.razemDok()})` : ''; };
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
      <div class="k3-pg-tresc"><div class="k3-pg-kartka">${dane ? atrapaHtml(dane, { stan: st, pelnyPesel: true, wyslano: wys }) : ''}</div>
        <aside class="k3-pg-panel k3-${st}"><span class="stan st-${st}"><i></i>${wys ? 'wysłano' : CHIP[st]}</span><p class="dok-kom">${wys ? `Wysłano${M().wyslaneKiedy ? ' ' + dataPl(M().wyslaneKiedy) : ''}` : komunikatKarty(i)}</p>${sz}
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
      $('#k3-pier', arkTresc).innerHTML = k.nazwyDok().map(karta3d).join(''); $('#k3-pasek', arkTresc).innerHTML = kropkiKart(); kar.przelicz(); return;
    }
    o.innerHTML = przelacznikWidoku() + obszarKart(); uruchomKaruzele();
  }
  function otworzPodglad(i) { if (widokKart !== '3d') return; zatrzymajKaruzele(); podgladI = i; przodI = i; const o = $('#dok-obszar', arkTresc); if (o) o.innerHTML = przelacznikWidoku() + podglad3d(i); const f = $('.k3-pg-gora button', arkTresc); f && f.focus({ preventScroll: true }); }
  function zamknijPodglad() { if (podgladI === null) return; podgladI = null; const o = $('#dok-obszar', arkTresc); if (o) { o.innerHTML = przelacznikWidoku() + widok3d(); uruchomKaruzele(); const s = $('#k3-scena', arkTresc); s && s.focus({ preventScroll: true }); } }
  function przejdzPodglad(s) { const n = k.razemDok(); if (podgladI === null || !n) return; podgladI = (podgladI + s + n) % n; przodI = podgladI; const o = $('#dok-obszar', arkTresc); if (o) o.innerHTML = przelacznikWidoku() + podglad3d(podgladI); }
  function ustawWidok(w) { if (w === widokKart) return; widokKart = w; podgladI = null; try { localStorage.setItem('pmt-ui-karty', w); } catch (e) { /* bez pamięci przeglądarki wybór obowiązuje do zamknięcia okna */ } const o = $('#dok-obszar', arkTresc); if (o) { zatrzymajKaruzele(); o.innerHTML = przelacznikWidoku() + obszarKart(); uruchomKaruzele(); const sc = $('#k3-scena', arkTresc); if (sc) sc.scrollIntoView({ block: 'center', behavior: ruchDozwolony() ? 'smooth' : 'auto' }); } }
  addEventListener('keydown', e => { if (e.key === 'Escape' && podgladI !== null && arkTresc.isConnected && arkTresc.querySelector('.k3-podglad')) { e.stopImmediatePropagation(); e.preventDefault(); zamknijPodglad(); } else if (podgladI !== null && (e.key === 'ArrowLeft' || e.key === 'ArrowRight') && arkTresc.querySelector('.k3-podglad') && !/^(INPUT|SELECT|TEXTAREA)$/.test((document.activeElement || {}).tagName || '')) { e.preventDefault(); przejdzPodglad(e.key === 'ArrowRight' ? 1 : -1); } }, true);
  function podsumowanie() {
    const razem = k.razemDok(), ok = k.ilePodpisanych(), wgr = k.nazwyDok().filter(d => plikiDok(d.i).length).length;
    if (!wgr) return `${razem} ${liczba(razem, 'dokument czeka', 'dokumenty czekają', 'dokumentów czeka')} na podpis`;
    return wszystkoPodpisane() ? `<b>Wszystkie ${razem} dokumentów sprawdzone — możesz wysłać</b>` : `<b>${ok} z ${razem}</b> sprawdzonych pozytywnie${wgr - ok > 0 ? ` · ${wgr - ok} do poprawy lub potwierdzenia` : ''}`;
  }
  /** Krok 5. Hasło do paczek, termin jego ważności i adres odbiorcy ustawia administrator w arkuszu (zakładka „Ustawienia”); aplikacja pobiera je, gdy wszystkie dokumenty są podpisane.
      Do czasu, aż wszystko jest wgrane i sprawdzone, przycisk jest wyszarzony i NIE niesie data-akcja (nic go nie uruchomi). */
  let daneWysylki;                // undefined = jeszcze nie pobrano; { ok:true, haslo, wazneDo, adres } albo { ok:false, powod, komunikat }
  let pobieranieDanych = false;
  let stanWysylki = '';           // komunikat pod krokiem 5 po kliknięciu „Wyślij” (html)
  const KONCOWE = ['brak', 'wygaslo', 'dostep'];      // przy tych powodach ponowna próba nic nie da, dopóki administrator czegoś nie zmieni
  const zablokowana = () => !!(daneWysylki && !daneWysylki.ok && KONCOWE.includes(daneWysylki.powod));
  const wyslane = () => !!M().wyslane;
  const mozeWyslac = () => wszystkoPodpisane() && !wyslane() && !zablokowana();
  const dataPl = iso => { const d = new Date(iso); if (isNaN(d.getTime())) return ''; const p = n => String(n).padStart(2, '0'); return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`; };
  const przyciskWyslij = () => mozeWyslac() ? `<button type="button" class="przycisk glowny" data-akcja="wyslij">${ik('i-wyslij')}Wyślij</button>`
    : `<button type="button" class="przycisk glowny" disabled aria-disabled="true">${ik(wyslane() ? 'i-ok' : 'i-wyslij')}${wyslane() ? 'Wysłano' : 'Wyślij'}</button>`;
  const opisWyslij = () => !wszystkoPodpisane() ? 'Odblokuje się, gdy wgrasz i sprawdzę wszystkie podpisane dokumenty.'
    : wyslane() ? `Dokumenty wysłane${M().wyslaneKiedy ? ' ' + dataPl(M().wyslaneKiedy) : ''}. Gdyby wiadomość nie wyszła z poczty, „Cofnij wysłanie” na pulpicie przywraca stan sprzed wysyłki.`
    : zablokowana() ? esc(daneWysylki.komunikat)
    : `Wszystkie dokumenty sprawdzone. „Wyślij” zrobi z nich zahasłowaną paczkę i przygotuje wiadomość${daneWysylki && daneWysylki.ok ? ` do <span class="adr">${esc(daneWysylki.adres)}</span>` : ''}`;
  function wczytajDane() { if (daneWysylki !== undefined || pobieranieDanych) return; pobieranieDanych = true; hasloDoPaczki().then(o => { daneWysylki = o; }).finally(() => { pobieranieDanych = false; odswiezWidok(); }); }
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
        <li class="krok-k k5 ${wszystkoPodpisane() ? 'aktywny' : 'nieaktywny'}"><span class="kk-nr">5</span><div class="kk-tresc"><b>Wyślij</b><small id="podp-wyslij-opis">${opisWyslij()}</small><small class="podp-stan" id="podp-wyslij-stan" aria-live="polite">${stanWysylki}</small></div>
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
    podgladI = null; wstaw(widokGlowny()); uruchomKaruzele(); pokazWyniki();
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
    if (wszystkoPodpisane()) { k.kurtyna() && k.kurtyna().swieto(); k.zorza() && k.zorza().flara(1); pokazToast('Wszystko podpisane i sprawdzone — możesz wysłać dokumenty'); }
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
  const temat = () => `[PMT] Delegacje — ${k.PROFIL().imie} — ${k.MIES[M().mies - 1]} ${M().rok}`;      // stały początek „[PMT]” pozwala odbiorcy ustawić regułę poczty (osobny folder)
  const miesiacTekst = () => { const m = String(k.MIES[M().mies - 1]); return m.charAt(0).toUpperCase() + m.slice(1); };
  const trescWiad = n => `Dzień dobry,\n\nw załączeniu zahasłowana paczka (ZIP) z podpisanymi dokumentami delegacyjnymi za ${miesiacTekst()} ${M().rok} (${n} ${liczba(n, 'plik', 'pliki', 'plików')}). Hasło zostało przekazane osobno.\n\nPozdrawiam\n${k.PROFIL().imie}`;
  const stanW = (html, zle = false) => { stanWysylki = html ? (zle ? `<span class="zle">${html}</span>` : html) : ''; const s = $('#podp-wyslij-stan', arkTresc); if (s) s.innerHTML = stanWysylki; };
  /** Hasło, termin i adres odbiorcy nadaje administrator (nie użytkownik): pobieramy je z serwera; bez internetu wystarcza zapamiętane, o ile hasło jeszcze nie wygasło. */
  async function hasloDoPaczki() {
    const o = await k.hasloPaczki();
    if (o.ok) { magUst.ustaw('paczka', { haslo: o.haslo, wazne_do: o.wazneDo, adres: o.adres }); return o; }
    if (o.powod === 'siec') { const c = magUst.daj('paczka', null); if (c && c.haslo && c.adres && c.wazne_do >= k.isoDzis()) return { ok: true, haslo: c.haslo, wazneDo: c.wazne_do, adres: c.adres }; }
    if (o.powod === 'brak' || o.powod === 'wygaslo') magUst.ustaw('paczka', null);
    return o;
  }
  let wysylanie = false;
  /** Przycisk „Wyślij” w kroku 5: dane od administratora → jedna paczka ZIP z AES-256 → gotowa wiadomość (plik .eml: adresat, temat, treść i załącznik; na telefonie systemowe udostępnianie).
      Samo kliknięcie jest akceptacją: gdy wiadomość jest gotowa, dokumenty dostają status „wysłane” (karty pokazują „Wysłano”); „Cofnij wysłanie” na pulpicie go przywraca. */
  async function wyslij() {
    if (wysylanie) return; wysylanie = true;
    const przycisk = () => $('#podp-wyslij-akcje button', arkTresc); if (przycisk()) przycisk().disabled = true;
    try {
      stanW('Pobieram hasło do paczki i adres odbiorcy…');
      const h = await hasloDoPaczki(); daneWysylki = h; if (!h.ok) { stanW(esc(h.komunikat), true); odswiezWidok(); return; }
      const adres = h.adres;
      stanW('Przygotowuję zahasłowaną paczkę…'); await czekaj(40);      // pozwala narysować komunikat, zanim szyfrowanie zajmie procesor
      const zal = await zalaczniki(); if (!zal.length) { stanW('Nie ma plików do wysłania.', true); return; }
      const blob = zipujAes(zal.map(z => ({ nazwa: z.nazwa, bajty: z.bajty })), h.haslo), tr = trescWiad(zal.length), tem = temat();
      const plik = new File([blob], nazwaZip(), { type: 'application/zip' }), duza = blob.size > LIMIT_POCZTY ? `<br><span class="zle">Uwaga: paczka waży ${mb(blob.size)}, a poczta zwykle przyjmuje do 20–25 MB. Największe są zdjęcia — zrób skany do PDF (mniejsze pliki).</span>` : '';
      if (matchMedia('(pointer:coarse)').matches && navigator.canShare && navigator.canShare({ files: [plik] })) {      // telefon: systemowe udostępnianie prosto do aplikacji pocztowej (adresat do wpisania)
        try { await navigator.share({ files: [plik], title: tem, text: tr }); oznaczWyslane(); stanW(`Wybierz aplikację poczty i wyślij wiadomość na adres <span class="adr">${esc(adres)}</span>.${duza}`); }
        catch (e) { if (e.name !== 'AbortError') stanW('Nie udało się przekazać paczki do poczty.', true); else stanW(''); }
        return;
      }
      const eml = zbudujEml({ adres, temat: tem, tresc: tr, zalacznik: { nazwa: nazwaZip(), bajty: new Uint8Array(await blob.arrayBuffer()), typ: 'application/zip' } });
      k.pobierzBlob(new Blob([eml], { type: 'message/rfc822' }), 'PMT_wiadomosc_do_wyslania.eml');
      oznaczWyslane();
      stanW(`Pobrałem wiadomość <span class="adr">PMT_wiadomosc_do_wyslania.eml</span>. <span class="adr">Kliknij ją</span> (pasek pobierania przeglądarki albo folder Pobrane) — otworzy się poczta z adresatem, tematem, treścią i zahasłowaną paczką; kliknij tam „Wyślij”.${duza}`);
      pokazToast('Wiadomość gotowa — kliknij pobrany plik .eml, żeby ją wysłać');
    } catch (e) { console.error('wysyłka', e); stanW('Nie udało się przygotować wiadomości. Spróbuj jeszcze raz.', true); }
    finally { wysylanie = false; if (przycisk() && mozeWyslac()) przycisk().disabled = false; }
  }
  function oznaczWyslane() { const m = M(); m.wyslane = true; m.wyslaneKiedy = new Date().toISOString(); k.zapiszRekord(); k.odswiezHero(); k.zorza() && k.zorza().flara(.7); odswiezWidok(); }

  /* ---------------------------------- zdarzenia ---------------------------------- */
  arkTresc.addEventListener('click', async e => {
    const b = e.target.closest('[data-akcja]'); if (!b) return;
    const a = b.dataset.akcja;
    if (a === 'otworz') k.otworzPdf(b.dataset.nazwa);
    else if (a === 'zip') zip();
    else if (a === 'osobno') pobierzOsobno();
    else if (a === 'glowny') pokaz('glowny');
    else if (a === 'wyslij') wyslij();
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
    otworz() { widok = 'glowny'; wgrane = []; otwarte = new Set(); stanWysylki = ''; daneWysylki = undefined; podgladI = null; k.otworzArkusz(widokGlowny(), null, { szeroki: true }); uruchomKaruzele(); if (wszystkoPodpisane() && !wyslane()) wczytajDane(); ujednolicStare().then(odswiezWidok).catch(e => console.error('nazwy plików', e)); },
    otworzWyslij() { this.otworz(); },      // „Wyślij” jest krokiem 5 w tym samym oknie co pobieranie, podpis i wgrywanie
  };
}
