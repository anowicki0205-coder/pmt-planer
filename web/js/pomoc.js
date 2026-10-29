// PMT Planer (web) — pomoc dla użytkownika: instalacja na telefonie (Android, iPhone, komputer; kod QR z adresem) oraz „Napisz uwagę”
// (uwaga razem z danymi technicznymi — przeglądarka, karta graficzna, płynność, ostatnie błędy — do skopiowania, udostępnienia albo wysłania pocztą).
// W danych technicznych nie ma imienia, PESEL-u, adresu ani kwot.

/* ---- zbieranie błędów od samego startu (ostatnie 6 trafia do uwagi) ---- */
const BLEDY = [];
const dopisz = t => { BLEDY.push(String(t).slice(0, 220)); if (BLEDY.length > 6) BLEDY.shift(); };
addEventListener('error', e => dopisz(`${e.message} @${String(e.filename || '').split('/').pop()}:${e.lineno}`));
addEventListener('unhandledrejection', e => dopisz(`obietnica: ${e.reason && e.reason.message || e.reason}`));

/* ---- instalacja: zdarzenie przeglądarki (Chrome, Edge, Android) przychodzi tylko raz, więc łapiemy je od razu ---- */
let zdarzenieInstalacji = null;
const naZmianeInstalacji = new Set();
addEventListener('beforeinstallprompt', e => { e.preventDefault(); zdarzenieInstalacji = e; naZmianeInstalacji.forEach(f => f()); });
addEventListener('appinstalled', () => { zdarzenieInstalacji = null; naZmianeInstalacji.forEach(f => f()); });

export const czyZainstalowana = () => { try { return matchMedia('(display-mode: standalone)').matches || navigator.standalone === true; } catch (e) { return false; } };
const czyIOS = () => /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
const czyAndroid = () => /Android/i.test(navigator.userAgent);
const czyLokalny = () => location.protocol === 'file:' || /^(localhost|127\.|\[?::1\]?$)/.test(location.hostname);
const adresAplikacji = () => new URL('./', location.href).href;
/** Stały, publiczny adres aplikacji z adres_aplikacji.txt (jedna linia http/https; wdrożenie na GitHub Pages wpisuje go samo): kod QR prowadzi tam ZAWSZE,
 *  więc działa niezależnie od komputera, na którym otwarto aplikację — telefon łączy się z serwerem aplikacji, a nie z komputerem. Pusty, gdy pliku nie ma albo nie ma w nim adresu. */
let adresPublicznyObietnica = null;
const adresPubliczny = () => adresPublicznyObietnica || (adresPublicznyObietnica = fetch('adres_aplikacji.txt', { cache: 'no-store' }).then(r => r.ok ? r.text() : '').then(t => {
  const l = String(t).split(/\r?\n/).map(x => x.trim()).find(x => /^https?:\/\/\S+$/i.test(x)); if (!l) return '';
  try { const u = new URL(l); return /\/$|\.html?$/i.test(u.pathname) ? u.href : u.href + '/'; } catch (e) { return ''; }
}).catch(() => ''));
/** Adres tego komputera w sieci (podaje go serwer_lokalny.py), żeby kod QR dla telefonu był od razu; bez tego serwera zostaje ręczne wpisanie adresu. */
let adresSieciObietnica = null;
const adresWSieci = () => adresSieciObietnica || (adresSieciObietnica = fetch('__adres.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null).then(j => (j && /^http:\/\/[\d.]+:\d+\//.test(j.adres || '')) ? j.adres : '').catch(() => ''));

const IKONA_UDOSTEPNIJ = '<svg class="ik" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15V3M8 7l4-4 4 4M7 10H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2h-1"/></svg>';
const IKONA_PLUS = '<svg class="ik" viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 8v8M8 12h8"/></svg>';

async function kodQr(tekst) {
  const { default: qrcode } = await import('../vendor/qr/qrcode.mjs');
  const q = qrcode(0, 'M'); q.addData(tekst); q.make();
  const n = q.getModuleCount(), m = 4, w = n + 2 * m; let d = '';
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (q.isDark(r, c)) d += `M${c + m} ${r + m}h1v1h-1z`;
  return `<svg viewBox="0 0 ${w} ${w}" shape-rendering="crispEdges" role="img" aria-label="Kod QR z adresem aplikacji"><rect width="${w}" height="${w}" fill="#fff"/><path d="${d}" fill="#0A0E22"/></svg>`;
}

async function kopiuj(tekst) {
  try { await navigator.clipboard.writeText(tekst); return true; } catch (e) { /* starsza przeglądarka albo brak zgody: zwykłe kopiowanie z pola */ }
  try { const t = document.createElement('textarea'); t.value = tekst; t.style.cssText = 'position:fixed;left:-999px;top:0;opacity:0'; document.body.appendChild(t); t.select(); const ok = document.execCommand('copy'); t.remove(); return ok; } catch (e) { return false; }
}

export function zainstalujPomoc(k) {
  const { $, doc, otworzArkusz, naglowekArkusza, zamknijArkusz, arkTresc, bezZnacznikow, pokazToast, zamknijDymki } = k;

  /* ---------------- instalacja / pobranie na telefon ---------------- */
  function odswiezPrzyciskInstalacji() { const b = $('#instaluj'); if (b) b.hidden = czyZainstalowana(); }
  naZmianeInstalacji.add(odswiezPrzyciskInstalacji); odswiezPrzyciskInstalacji();

  function krokiTegoUrzadzenia() {
    if (czyZainstalowana()) return '<p class="ark-opis">Aplikacja jest już zainstalowana na tym urządzeniu — działa jak zwykła aplikacja i zachowuje dane.</p>';
    if (zdarzenieInstalacji) return `<p class="ark-opis">Ta przeglądarka potrafi zainstalować aplikację od razu: pojawi się na ekranie głównym i będzie działać bez paska adresu.</p><div class="ark-dol"><button type="button" class="przycisk glowny" id="inst-teraz" data-pierwsze>${IKONA_PLUS}Zainstaluj teraz</button></div>`;
    if (czyIOS()) return `<p class="ark-opis"><b>iPhone / iPad (Safari):</b></p>
      <ol class="krok-lista">
        <li><span>Otwórz tę stronę w <b>Safari</b> (na iOS 16.4 i nowszym menu „Udostępnij” ma też Chrome, Edge i Firefox).</span></li>
        <li><span>Dotknij przycisku <b>Udostępnij</b> ${IKONA_UDOSTEPNIJ} (pasek u dołu albo u góry ekranu).</span></li>
        <li><span>Przewiń listę i wybierz <b>„Dodaj do ekranu początkowego”</b> ${IKONA_PLUS}, potem <b>„Dodaj”</b>.</span></li>
        <li><span>Uruchamiaj aplikację ikoną <b>PMT Planer</b> z ekranu początkowego.</span></li>
      </ol>
      <p class="ark-opis">Tak zainstalowana aplikacja zachowuje Twoje dane. W samej karcie Safari iOS może je wyczyścić po tygodniu nieużywania.</p>`;
    if (czyAndroid()) return `<p class="ark-opis"><b>Telefon z Androidem:</b></p>
      <ol class="krok-lista">
        <li><span>Otwórz menu przeglądarki <b>⋮</b> (trzy kropki).</span></li>
        <li><span>Wybierz <b>„Zainstaluj aplikację”</b> albo <b>„Dodaj do ekranu głównego”</b>.</span></li>
        <li><span>Potwierdź — ikona <b>PMT Planer</b> pojawi się na ekranie głównym.</span></li>
      </ol>`;
    return `<p class="ark-opis"><b>Komputer:</b> w Edge i Chrome kliknij ikonę instalacji w pasku adresu (po prawej) albo menu <b>⋯ → Aplikacje → Zainstaluj tę witrynę jako aplikację</b>. Aplikacja dostanie własne okno i ikonę.</p>`;
  }

  async function arkuszInstalacji() {
    const publiczny = await adresPubliczny();      // stały adres z adres_aplikacji.txt: kod QR niezależny od komputera, bez wpisywania czegokolwiek
    const lokalny = !publiczny && czyLokalny(), https = (publiczny || location.href).startsWith('https:'), telefon = czyIOS() || czyAndroid();      // na telefonie kod QR jest zbędny: aplikacja jest już na nim
    otworzArkusz(`${naglowekArkusza('Zainstaluj na telefonie')}
      <div class="inst-kolumny">
        <section class="inst-kolumna" aria-label="Na tym urządzeniu">${krokiTegoUrzadzenia()}</section>
        ${telefon ? '' : `<section class="inst-kolumna inst-qr" aria-label="Na telefonie">
          <p class="ark-opis"><b>Na telefon z komputera:</b> ${lokalny ? 'wpisz adres tego komputera w sieci, a pokażę kod QR.' : 'zeskanuj kod aparatem telefonu i otwórz stronę.'}</p>
          ${lokalny ? '<label class="pole"><span>Adres komputera w sieci (np. 192.168.0.12)</span><input id="inst-ip" type="text" inputmode="decimal" autocomplete="off" placeholder="192.168.0.12"><small>Sprawdzisz go poleceniem ipconfig. Komputer i telefon w tej samej sieci Wi-Fi.</small></label>' : ''}
          <div class="qr-ramka" id="inst-qr" aria-live="polite"></div>
          <p class="inst-adres" id="inst-adres"></p>
          <p class="ark-opis inst-uwaga">${https || lokalny ? '' : 'Uwaga: ta strona nie jest szyfrowana (http) — instalacja na ekranie głównym wymaga https.'}${lokalny ? 'Po zwykłym http (sieć domowa) aplikacja działa w przeglądarce telefonu; instalacja z ikoną i praca bez internetu wymagają https po wdrożeniu.' : ''}</p>
        </section>`}
      </div>
      <div class="ark-dol">${telefon ? '' : '<button type="button" class="przycisk" id="inst-kopiuj">Kopiuj adres</button>'}<button type="button" class="przycisk glowny" data-zamknij>Zamknij</button></div>`);
    let adres = publiczny || (lokalny ? '' : adresAplikacji());
    if (lokalny && !telefon) adresWSieci().then(a => { if (a && !adres && doc.contains($('#inst-qr', arkTresc))) { adres = a; const ipEl = $('#inst-ip', arkTresc); if (ipEl) ipEl.value = a.replace(/^http:\/\//, '').replace(/[:/].*$/, ''); if (typeof pokaz === 'function') pokaz(); } });
    const teraz = $('#inst-teraz', arkTresc);
    if (teraz) teraz.addEventListener('click', async () => {
      const e = zdarzenieInstalacji; if (!e) return;
      try { e.prompt(); const w = await e.userChoice; if (w && w.outcome === 'accepted') { pokazToast('Instaluję aplikację…'); zamknijArkusz(); } } catch (x) { pokazToast('Przeglądarka nie dała się zainstalować — użyj menu przeglądarki'); }
      zdarzenieInstalacji = null; naZmianeInstalacji.forEach(f => f());
    });
    if (telefon) return;
    const pokaz = async () => {
      const box = $('#inst-qr', arkTresc), tx = $('#inst-adres', arkTresc); if (!box) return;
      if (!adres) { box.innerHTML = '<span class="qr-pusty">kod QR pojawi się po wpisaniu adresu</span>'; tx.textContent = ''; return; }
      try { box.innerHTML = await kodQr(adres); } catch (e) { box.innerHTML = '<span class="qr-pusty">nie udało się wygenerować kodu</span>'; }
      tx.textContent = adres;
    };
    pokaz();
    const ip = $('#inst-ip', arkTresc);
    if (ip) ip.addEventListener('input', () => { const v = ip.value.trim().replace(/^https?:\/\//, '').replace(/[/].*$/, ''); adres = /^[\w.\-]+(:\d+)?$/.test(v) && v.length > 3 ? `http://${v.includes(':') ? v : v + (location.port ? ':' + location.port : '')}/` : ''; pokaz(); });
    const kop = $('#inst-kopiuj', arkTresc); if (kop) kop.addEventListener('click', async () => { if (!adres) { pokazToast('Najpierw wpisz adres komputera'); return; } pokazToast(await kopiuj(adres) ? 'Adres skopiowany' : 'Nie udało się skopiować adresu'); });
  }

  /* ---------------- kafel z kodem QR na pulpicie (komputer): zeskanowanie otwiera aplikację na telefonie ---------------- */
  async function odswiezKafelQr() {
    const kafel = $('#kQ'), box = $('#qr-kafel'); if (!kafel || !box) return;
    const pokaz = !(czyIOS() || czyAndroid() || czyZainstalowana());      // na telefonie i w zainstalowanej aplikacji kod QR byłby bez sensu
    kafel.hidden = !pokaz; doc.documentElement.classList.toggle('ma-qr', pokaz);
    if (!pokaz) return;
    const publiczny = await adresPubliczny();
    if (publiczny) { try { box.innerHTML = await kodQr(publiczny); box.dataset.adres = publiczny; delete box.dataset.lokalny; return; } catch (e) { /* poniżej: pozostałe źródła adresu */ } }
    if (czyLokalny()) {
      const siec = await adresWSieci();      // serwer lokalny zna adres komputera w sieci Wi-Fi — wtedy kod QR jest od razu
      if (siec) { try { box.innerHTML = await kodQr(siec); box.dataset.adres = siec; delete box.dataset.lokalny; return; } catch (e) { /* poniżej: ręczny adres */ } }
      box.innerHTML = '<span class="qr-pusty">wpisz adres<br>komputera</span>'; box.dataset.lokalny = '1'; return;      // inaczej telefon nie dotrze: adres podaje się w oknie instalacji
    }
    try { box.innerHTML = await kodQr(adresAplikacji()); box.dataset.adres = adresAplikacji(); delete box.dataset.lokalny; } catch (e) { box.innerHTML = '<span class="qr-pusty">brak kodu</span>'; }
  }
  const kafelQr = $('#qr-kafel'); if (kafelQr) kafelQr.addEventListener('click', () => arkuszInstalacji());
  naZmianeInstalacji.add(odswiezKafelQr); odswiezKafelQr();

  /* ---------------- „Napisz uwagę” ---------------- */
  let adresUwagObietnica = null;
  const adresUwag = () => adresUwagObietnica || (adresUwagObietnica = fetch('uwagi.txt', { cache: 'no-store' }).then(r => r.ok ? r.text() : '').then(t => String(t).split(/\r?\n/).map(x => x.trim()).find(l => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(l)) || '').catch(() => ''));
  const zmierzFps = (ms = 1500) => new Promise(ok => { let n = 0; const t0 = performance.now(); const f = t => { n++; if (t - t0 < ms) requestAnimationFrame(f); else ok(n / ((t - t0) / 1000)); }; requestAnimationFrame(f); });
  async function daneTechniczne() {
    let gpu = '?', prog = false;
    try { const g = doc.createElement('canvas').getContext('webgl'), e = g && g.getExtension('WEBGL_debug_renderer_info'); gpu = e ? String(g.getParameter(e.UNMASKED_RENDERER_WEBGL)) : (g ? 'WebGL' : 'brak WebGL'); prog = /SwiftShader|llvmpipe|softpipe|Software|Basic Render|Microsoft Basic/i.test(gpu); } catch (e) { gpu = 'brak WebGL'; }
    let wer = ''; try { const t = await (await fetch('sw.js', { cache: 'no-store' })).text(), m = t.match(/WERSJA = '([0-9a-f]+)'/); wer = m ? m[1] : ''; } catch (e) { /* offline */ }
    const fps = await zmierzFps();
    const wiersze = [
      `wersja aplikacji: ${wer || '?'}`,
      `przeglądarka: ${navigator.userAgent}`,
      `ekran: ${innerWidth}×${innerHeight} px, skalowanie ${devicePixelRatio || 1}, ${screen.width}×${screen.height}`,
      `karta graficzna: ${gpu}${prog ? ' (GRAFIKA LICZONA PROCESOREM)' : ''}`,
      `płynność strony w tej chwili: ${fps.toFixed(1)} klatek/s`,
      `tło: ${window.__zorzaWyjscie || '?'}`,
      `procesor: ${navigator.hardwareConcurrency || '?'} rdzeni, pamięć ${navigator.deviceMemory || '?'} GB`,
      `motyw: ${document.documentElement.dataset.theme || 'auto'}; zainstalowana: ${czyZainstalowana() ? 'tak' : 'nie'}; sieć: ${navigator.onLine ? 'jest' : 'brak'}; język: ${navigator.language}`,
      `ostatnie błędy: ${BLEDY.length ? BLEDY.join(' | ') : 'brak'}`,
    ];
    return wiersze.join('\n');
  }
  async function arkuszUwagi() {
    otworzArkusz(`${naglowekArkusza('Napisz uwagę')}
      <p class="ark-opis">Coś nie działa, przycina się albo masz pomysł? Napisz — dołączę dane techniczne (przeglądarka, karta graficzna, płynność), żeby łatwiej to znaleźć. Nie ma w nich Twoich danych osobowych, PESEL-u ani kwot.</p>
      <label class="pole"><span>Twoja uwaga</span><textarea id="uw-tekst" rows="5" maxlength="2000" placeholder="Co zauważyłeś? Gdzie, kiedy, co klikałeś?" data-pierwsze></textarea></label>
      <label class="uw-dane"><input type="checkbox" id="uw-dolacz" checked><span>Dołącz dane techniczne</span></label>
      <details class="uw-szczegoly"><summary>Zobacz, co zostanie dołączone</summary><pre id="uw-dane">Zbieram dane…</pre></details>
      <div class="ark-dol"><button type="button" class="przycisk" id="uw-kopiuj">Kopiuj</button><button type="button" class="przycisk" id="uw-udostepnij" hidden>Udostępnij</button><button type="button" class="przycisk glowny" id="uw-mail" hidden>Wyślij e-mailem</button></div>`);
    const daneP = daneTechniczne(); daneP.then(d => { const pre = $('#uw-dane', arkTresc); if (pre) pre.textContent = d; });
    const adresP = adresUwag(); adresP.then(a => { const m = $('#uw-mail', arkTresc); if (m && a) m.hidden = false; });
    const udost = $('#uw-udostepnij', arkTresc); if (udost && navigator.share) udost.hidden = false;
    const tresc = async () => { const t = ($('#uw-tekst', arkTresc).value || '').trim(), d = $('#uw-dolacz', arkTresc).checked; return (t || '(bez opisu)') + (d ? '\n\n--- dane techniczne ---\n' + await daneP : ''); };
    const wymagaTekstu = () => { if (($('#uw-tekst', arkTresc).value || '').trim()) return true; pokazToast('Napisz najpierw, co zauważyłeś'); $('#uw-tekst', arkTresc).focus(); return false; };
    $('#uw-kopiuj', arkTresc).addEventListener('click', async () => { if (!wymagaTekstu()) return; pokazToast(await kopiuj(await tresc()) ? 'Skopiowane — wklej w wiadomości' : 'Nie udało się skopiować'); });
    if (udost) udost.addEventListener('click', async () => { if (!wymagaTekstu()) return; try { await navigator.share({ title: 'Uwaga do PMT Planer', text: await tresc() }); } catch (e) { if (e.name !== 'AbortError') pokazToast('Nie udało się udostępnić'); } });
    $('#uw-mail', arkTresc).addEventListener('click', async () => { if (!wymagaTekstu()) return; const adres = await adresP; location.href = `mailto:${adres}?subject=${encodeURIComponent('Uwaga do PMT Planer')}&body=${encodeURIComponent(await tresc())}`; pokazToast('Otwieram pocztę…'); });
  }

  const wejscie = (id, f) => { const b = $(id); b && b.addEventListener('click', () => { zamknijDymki && zamknijDymki(null); f(); }); };
  wejscie('#instaluj', arkuszInstalacji); wejscie('#uwagi', arkuszUwagi);
  return { otworzInstalacje: arkuszInstalacji, otworzUwagi: arkuszUwagi, czyZainstalowana, odswiezPrzyciskInstalacji };
}
