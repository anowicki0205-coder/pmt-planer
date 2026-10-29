/* ====================== arkusze (okna z treścią) ====================== */
let arkuszOtwarty = null, arkuszPoZamknieciu = null, fokusPrzed = null;
const arkTlo = $('#arkusz-tlo'), arkTresc = $('#arkusz-tresc');
function otworzArkusz(html, poZamknieciu) {
  fokusPrzed = doc.activeElement; arkuszPoZamknieciu = poZamknieciu || null;
  arkTresc.innerHTML = html; arkTlo.classList.add('otwarty'); arkuszOtwarty = true;
  $('#arkusz').scrollTop = 0;
  const pierwsze = $('[data-pierwsze]', arkTresc) || $('input,select,button', arkTresc); pierwsze && pierwsze.focus({ preventScroll: true });
  szkla.forEach(budujSoczewke);
  requestAnimationFrame(() => szkla.forEach(budujSoczewke));
}
function zamknijArkusz() {
  if (!arkuszOtwarty) return;
  arkTlo.classList.remove('otwarty'); arkuszOtwarty = false; arkTresc.innerHTML = '';
  const f = arkuszPoZamknieciu; arkuszPoZamknieciu = null; f && f();
  fokusPrzed && fokusPrzed.focus && fokusPrzed.focus({ preventScroll: true });
}
arkTlo.addEventListener('click', e => { if (e.target === arkTlo) zamknijArkusz(); });
arkTresc.addEventListener('click', e => { if (e.target.closest('[data-zamknij]')) zamknijArkusz(); });
const naglowekArkusza = (tytul) => `<div class="ark-gora"><h2 id="ark-tyt">${tytul}</h2><button type="button" class="ark-zam" data-zamknij aria-label="Zamknij">${ik('i-zamknij')}</button></div>`;
const bezZnacznikow = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* ====================== Moje dane ====================== */
const peselPoprawny = p => { p = String(p).replace(/\s/g, ''); if (!/^\d{11}$/.test(p)) return false; const w = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]; let s = 0; for (let i = 0; i < 10; i++) s += w[i] * +p[i]; return (10 - s % 10) % 10 === +p[10]; };
function otworzMojeDane(pierwsze) {
  const p = PROFIL || { imie: '', pesel: '', adres: '', stanowisko: 'merchandiser', silnik_powyzej_900: true, tryb: 'wieczory' };
  otworzArkusz(`${naglowekArkusza(pierwsze ? 'Zacznijmy od Twoich danych' : 'Moje dane')}
    <p class="ark-opis">Dane zostają tylko na tym urządzeniu. Trafiają na dokumenty delegacji, nigdzie więcej.</p>
    <form id="form-dane" class="ark-pola" novalidate autocomplete="off">
      <label class="pole pelne"><span>Imię i nazwisko</span><input id="d-imie" data-pierwsze value="${bezZnacznikow(p.imie)}" autocomplete="name" required><small></small></label>
      <label class="pole"><span>PESEL</span><input id="d-pesel" inputmode="numeric" maxlength="11" value="${bezZnacznikow(p.pesel)}" autocomplete="off" required><small></small></label>
      <label class="pole"><span>Stanowisko</span><select id="d-stan"><option value="merchandiser"${p.stanowisko === 'KR' ? '' : ' selected'}>merchandiser</option><option value="KR"${p.stanowisko === 'KR' ? ' selected' : ''}>KR</option></select><small></small></label>
      <label class="pole pelne"><span>Adres zamieszkania</span><input id="d-adres" value="${bezZnacznikow(p.adres)}" placeholder="ul. Przykładowa 12, 00-001 Warszawa" autocomplete="street-address" required><small></small></label>
      <div class="par-w"><span>Silnik auta</span><div class="seg" role="group" aria-label="Pojemność silnika"><button type="button" data-silnik="1" aria-pressed="${p.silnik_powyzej_900}">powyżej 900 cm³</button><button type="button" data-silnik="0" aria-pressed="${!p.silnik_powyzej_900}">poniżej 900 cm³</button></div></div>
      <div class="par-w"><span>Tryb pracy</span><div class="seg" role="group" aria-label="Tryb pracy"><button type="button" data-tryb="wieczory" aria-pressed="${p.tryb !== 'tydzien'}">Wieczory</button><button type="button" data-tryb="tydzien" aria-pressed="${p.tryb === 'tydzien'}">Tydzień</button></div></div>
    </form>
    <div class="ark-dol">${pierwsze ? '' : '<button type="button" class="przycisk" data-zamknij>Anuluj</button>'}<button type="button" class="przycisk glowny" id="zapisz-dane">Zapisz</button></div>`);
  const f = $('#form-dane', arkTresc);
  f.addEventListener('click', e => { const b = e.target.closest('.seg button'); if (!b) return; $$('button', b.parentElement).forEach(x => x.setAttribute('aria-pressed', String(x === b))); });
  const zle = (id, t) => { const s = $('#' + id, arkTresc).parentElement.querySelector('small'); s.textContent = t || ''; s.classList.toggle('zle', !!t); return !t; };
  $('#zapisz-dane', arkTresc).addEventListener('click', async () => {
    const imie = $('#d-imie', arkTresc).value.split(/\s+/).filter(Boolean).join(' '), pesel = $('#d-pesel', arkTresc).value.replace(/\s/g, ''), adres = $('#d-adres', arkTresc).value.trim();
    let ok = true;
    ok = zle('d-imie', imie.split(' ').length < 2 ? 'Wpisz imię i nazwisko' : '') && ok;
    ok = zle('d-pesel', peselPoprawny(pesel) ? '' : 'PESEL jest niepoprawny') && ok;
    let adr = null;
    if (adres) { try { adr = await silnik.adres({ adres }); } catch (e) { adr = { ok: false }; } }
    ok = zle('d-adres', adr && adr.ok ? '' : 'Podaj ulicę, numer, kod i miejscowość, np. ul. Polna 5, 00-001 Warszawa') && ok;
    if (!ok) return;
    PROFIL = { imie, pesel, adres: adr.adres_caly, stanowisko: $('#d-stan', arkTresc).value, silnik_powyzej_900: $('[data-silnik][aria-pressed="true"]', f).dataset.silnik === '1', tryb: $('[data-tryb][aria-pressed="true"]', f).dataset.tryb };
    magProfil.zapisz(PROFIL);
    if (M && M.stan === 'plan') { M.silnik = PROFIL.silnik_powyzej_900; M.tryb = PROFIL.tryb; }
    zamknijArkusz(); odswiezProfilWNaglowku(); await przeladujMiesiac(M.rok, M.mies, true);
    pokazToast('Zapisano Twoje dane');
  });
}
function odswiezProfilWNaglowku() {
  const ini = PROFIL ? PROFIL.imie.split(' ').map(x => x[0]).slice(0, 2).join('').toUpperCase() : '?';
  $('#awatar').textContent = ini; $('#awatar-menu').textContent = ini;
  $('#imie-pasek').textContent = PROFIL ? PROFIL.imie : 'Moje dane'; $('#konto-imie').textContent = PROFIL ? PROFIL.imie : 'Moje dane';
  $('#konto-opis').textContent = PROFIL ? `auto ${PROFIL.silnik_powyzej_900 ? 'powyżej' : 'poniżej'} 900 cm³ · ${fmt(PROFIL.silnik_powyzej_900 ? 1.15 : 0.89)} zł/km` : 'uzupełnij dane';
  $('#konto').setAttribute('aria-label', PROFIL ? `Konto: ${PROFIL.imie}` : 'Konto');
}

/* ====================== parametry przed generowaniem ====================== */
const parsujKwote = t => { const n = Number(String(t).replace(/\s/g, '').replace(',', '.')); return Number.isFinite(n) ? Math.round(n * 100) / 100 : 0; };
const parametrySilnika = () => ({ imie: PROFIL ? PROFIL.imie : '', pesel: PROFIL ? PROFIL.pesel : '', adres: PROFIL ? PROFIL.adres : '', stanowisko: PROFIL ? PROFIL.stanowisko : 'merchandiser',
  kwota: M.kwota, rok: M.rok, miesiac: M.mies, tryb: M.tryb, silnik_powyzej_900: M.silnik, wolne: [...M.wolne].sort((a, b) => a - b) });
let infoNr = 0;
async function odswiezParametry() {
  if (!M) return;
  $$('#parametry [data-tryb]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.tryb === M.tryb)));
  $$('#parametry [data-silnik]').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.silnik === '1') === M.silnik)));
  const wej = $('#kwota-in'); if (M.stan === 'plan' && doc.activeElement !== wej) wej.value = M.kwota ? fmt(M.kwota).replace(/ /g, '') : '';
  const info = $('#par-info'), nr = ++infoNr;
  if (M.stan !== 'plan') { info.innerHTML = ''; btn.classList.remove('zablok'); return; }
  let w; try { w = await silnik.maks(parametrySilnika()); } catch (e) { return; }
  if (nr !== infoNr) return;
  M.maksymalna = w.maks; M.stawkaPodglad = w.stawka;
  const kw = M.kwota; let h = `<b>${w.dni}</b> ${w.dni === 1 ? 'dzień roboczy' : 'dni roboczych'} · stawka <b>${fmt(w.stawka)} zł/km</b> · maks. <b>${fmt(w.maks, 0)} zł</b>`;
  let blad = '';
  if (!kw) blad = 'Wpisz kwotę do rozliczenia.';
  else if (kw < MIN_KWOTA) blad = `Minimum to ${fmt(MIN_KWOTA, 0)} zł.`;
  else if (kw > w.maks) blad = `Za dużo: dla tylu dni maksimum to ${fmt(w.maks, 0)} zł. Odznacz dni wolne albo zmniejsz kwotę.`;
  else h += ` · ${w.dokumentow} ${w.dokumentow === 1 ? 'polecenie' : w.dokumentow < 5 ? 'polecenia' : 'poleceń'}`;
  if (!PROFIL) blad = 'Najpierw uzupełnij Moje dane.';
  info.innerHTML = h + (blad ? `<br><span class="zle">${blad}</span>` : '');
  btn.classList.toggle('zablok', !!blad);
}

/* ====================== generowanie: prawdziwy silnik ====================== */
let generowanie = false;
function postepGeneracji(tekst, v) {
  const p = Math.max(0, Math.min(1, v || 0));
  btn.style.setProperty('--pk', String(p * 100)); $('#licz-k').textContent = String(Math.round(p * 100));
  zorza && zorza.flara(.12);
}
async function generuj() {
  if (generowanie) { silnik.przerwij(); return; }
  if (!PROFIL) { otworzMojeDane(true); return; }
  M.kwota = parsujKwote($('#kwota-in').value);
  const par = parametrySilnika();
  let pr; try { pr = await silnik.przygotuj(par); } catch (e) { pokazToast('Silnik nie odpowiada — spróbuj ponownie'); return; }
  if (!pr.ok) {
    const opisy = { 'brak menedzer.txt': 'Brakuje pliku menedzer.txt obok aplikacji (nazwisko przełożonego na dokumentach).', 'PESEL': 'PESEL jest niepoprawny — popraw go w Moich danych.', 'adres': 'Adres jest niepoprawny — popraw go w Moich danych.', 'brak dni': 'Ten miesiąc nie ma dni roboczych przy tych ustawieniach.' };
    pokazToast(opisy[pr.powod] || ('Nie można generować: ' + pr.powod)); await odswiezParametry(); return;
  }
  magUst.ustaw('kwota-' + magMiesiace.klucz(M.rok, M.mies), M.kwota);
  generowanie = true; btn.classList.add('zbiera'); btn.setAttribute('aria-busy', 'true'); btn.setAttribute('aria-label', 'Przerwij generowanie');
  btn.style.setProperty('--hh', (btn.offsetHeight / 2) + 'px'); postepGeneracji('', 0.02); zorza && zorza.flara(.35);
  let w;
  try {
    w = await silnik.generuj(par, (t, v) => postepGeneracji(t, v));
  } catch (e) {
    generowanie = false; btn.classList.remove('zbiera'); btn.removeAttribute('aria-busy');
    if (e.przerwano) { pokazToast('Przerwano — nic nie zostało zapisane'); } else {
      otworzArkusz(`${naglowekArkusza('Nie udało się wygenerować')}<p class="ark-opis">${bezZnacznikow(e.message)}</p><div class="ark-dol"><button type="button" class="przycisk glowny" data-zamknij data-pierwsze>Rozumiem</button></div>`);
    }
    odswiezHero(); await odswiezParametry(); return;
  }
  const rec = { params: par, wynik: w.wynik, podpisane: [], wyslane: false, utworzono: new Date().toISOString() };
  magMiesiace.zapisz(M.rok, M.mies, rec);
  await magPliki.usunMiesiac(magMiesiace.klucz(M.rok, M.mies) + '/');
  for (const p of w.pdf) await magPliki.zapisz(nazwaKlucza(M.rok, M.mies, p.nazwa), p.bajty);
  postepGeneracji('', 1); await zegar(450);
  generowanie = false; btn.classList.remove('zbiera'); btn.removeAttribute('aria-busy');
  M = zbudujModel(M.rok, M.mies, rec, [...M.robocze0]); wybrany = M.dniT[0] || 0;
  przejscie(() => odswiezWszystko(), () => { kurtyna && kurtyna.restart(); kurtyna && kurtyna.wybierz(wybrany); });
  zorza && zorza.flara(1); kurtyna && kurtyna.swieto();
  pokazToast(`Gotowe: ${M.polecenia.length} ${M.polecenia.length === 1 ? 'polecenie' : M.polecenia.length < 5 ? 'polecenia' : 'poleceń'} i rozliczenie na ${fmt(M.suma)} zł${w.wynik.niepelna ? ' (silnik nie dobił do zamówionej kwoty)' : ''}`);
  if (w.wynik.zrodlo && w.wynik.zrodlo.etykieta && /szacunek/i.test(w.wynik.zrodlo.etykieta)) setTimeout(() => pokazToast('Kilometry z szacunku — bez internetu nie sprawdzę dróg. Dokument to zaznacza.'), 3300);
}
async function przeladujMiesiac(rok, mies, cicho) {
  let r0; try { r0 = await silnik.dni({ rok, miesiac: mies, tryb: (magMiesiace.daj(rok, mies) || {}).params ? magMiesiace.daj(rok, mies).params.tryb : (PROFIL ? PROFIL.tryb : 'wieczory'), wolne: [] }); } catch (e) { r0 = { dni: [] }; }
  const rec = magMiesiace.daj(rok, mies);
  const robocze = r0.dni.map(s => Number(s.slice(8)));
  const pred = M && M.rok === rok && M.mies === mies ? M : null;
  M = zbudujModel(rok, mies, rec, robocze);
  if (!rec) { M.kwota = magUst.daj('kwota-' + magMiesiace.klucz(rok, mies), 0); if (pred && pred.stan === 'plan') { M.tryb = pred.tryb; M.silnik = pred.silnik; M.wolne = pred.wolne; for (const d of M.robocze0) if (!M.wolne.has(d)) M.robocze.add(d); } }
  wybrany = M.stan === 'gotowe' ? (M.trasy[wybrany] ? wybrany : M.dniT[0]) : 0;
  if (cicho) odswiezWszystko(); else przejscie(() => odswiezWszystko(), () => { kurtyna && kurtyna.wybierz(wybrany); });
}
async function przelaczTryb(tryb) {
  if (M.stan !== 'plan' || M.tryb === tryb) return; M.tryb = tryb;
  if (PROFIL) { PROFIL.tryb = tryb; magProfil.zapisz(PROFIL); }
  M.wolne = new Set(); await przeladujMiesiac(M.rok, M.mies, true);
}
async function przelaczWolne(d) {
  if (M.stan !== 'plan') return;
  if (M.wolne.has(d)) M.wolne.delete(d); else M.wolne.add(d);
  M.robocze = new Set([...M.robocze0].filter(x => !M.wolne.has(x)));
  tytulKalendarza(); budujKalendarz(); odswiezHero(); await odswiezParametry();
}

/* ====================== dokumenty, podpis, wysyłka ====================== */
const nazwyDok = () => { const n = M.polecenia.length; return [...M.polecenia.map((p, i) => ({ i, nazwa: p.plik, tytul: `Polecenie ${p.nr}`, opis: `${dwa(p.od)}–${dwa(p.do)}.${dwa(M.mies)} · ${fmt(p.kw)} zł` })), ...(M.rozliczenie ? [{ i: n, nazwa: M.rozliczenie, tytul: 'Rozliczenie', opis: `${n} ${n === 1 ? 'polecenie' : 'polecenia'} · ${fmt(M.suma)} zł` }] : [])]; };
const klucz = n => nazwaKlucza(M.rok, M.mies, n);
const kluczPodp = (n, nazwaPliku) => nazwaKlucza(M.rok, M.mies, 'podpisane/' + n + '/' + nazwaPliku);
const URL_PODPIS = 'https://www.gov.pl/web/gov/podpisz-dokument-elektronicznie-wykorzystaj-podpis-zaufany';
function zapiszRekord() { const rec = magMiesiace.daj(M.rok, M.mies) || {}; rec.podpisane = M.podpisane; rec.wyslane = M.wyslane; rec.podpisaniPliki = M.podpisaniPliki || rec.podpisaniPliki || {}; magMiesiace.zapisz(M.rok, M.mies, rec); }
const blobPdf = (bajty) => new Blob([bajty], { type: 'application/pdf' });
function pobierzBlob(blob, nazwa) { const a = doc.createElement('a'); a.href = URL.createObjectURL(blob); a.download = nazwa; doc.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000); }
async function otworzPdf(nazwa) { const b = await magPliki.daj(klucz(nazwa)); if (!b) { pokazToast('Nie znalazłem pliku — wygeneruj dokumenty ponownie'); return; } const u = URL.createObjectURL(blobPdf(b)); const w = window.open(u, '_blank'); if (!w) pobierzBlob(blobPdf(b), nazwa); setTimeout(() => URL.revokeObjectURL(u), 60000); }
async function arkuszPodpis() {
  const lista = nazwyDok(), rec = magMiesiace.daj(M.rok, M.mies) || {}, pp = rec.podpisaniPliki || {};
  otworzArkusz(`${naglowekArkusza('Podpisz dokumenty')}
    <ol class="krok-lista"><li><span>Pobierz dokumenty — albo otwórz i sprawdź kwoty.</span></li>
      <li><span>Podpisz każdy Profilem Zaufanym na <a href="${URL_PODPIS}" target="_blank" rel="noopener" style="color:var(--a-cyan)">stronie gov.pl</a>. To bezpłatne, a podpisu nie widzę — robisz go u siebie.</span></li>
      <li><span>Wgraj podpisany plik (PDF albo plik podpisu .xades) przy właściwym dokumencie.</span></li></ol>
    <div class="dok-lista" id="dok-lista">${lista.map(d => `<div class="dok-w" data-i="${d.i}"><div><b>${d.tytul}</b><small>${d.opis}</small></div><span class="stan${M.podpisane[d.i] ? ' ok' : ''}"><i></i>${M.podpisane[d.i] ? 'podpisane' : 'do podpisu'}</span>
      <div class="dok-akcje"><button type="button" class="przycisk" data-otworz="${d.nazwa}">Otwórz</button><button type="button" class="przycisk" data-pobierz="${d.nazwa}">Pobierz</button>
      <label class="przycisk" style="cursor:pointer">${M.podpisane[d.i] ? 'Wgraj ponownie' : 'Wgraj podpisany'}<input type="file" accept=".pdf,.xades,.xml,.sig,.p7s,.p7m,application/pdf" data-wgraj="${d.i}" hidden></label>${M.podpisane[d.i] && pp[d.i] ? `<small style="align-self:center;color:var(--t2)">${bezZnacznikow(pp[d.i])}</small>` : ''}</div></div>`).join('')}</div>
    <div class="ark-dol"><button type="button" class="przycisk" id="pobierz-wsz">Pobierz wszystkie</button><button type="button" class="przycisk glowny" data-zamknij data-pierwsze>Gotowe</button></div>`);
  $('#pobierz-wsz', arkTresc).addEventListener('click', async () => { for (const d of lista) { const b = await magPliki.daj(klucz(d.nazwa)); b && pobierzBlob(blobPdf(b), d.nazwa); await zegar(350); } });
}
arkTresc.addEventListener('click', async e => {
  const o = e.target.closest('[data-otworz]'); if (o) { otworzPdf(o.dataset.otworz); return; }
  const p = e.target.closest('[data-pobierz]'); if (p) { const b = await magPliki.daj(klucz(p.dataset.pobierz)); b && pobierzBlob(blobPdf(b), p.dataset.pobierz); }
});
arkTresc.addEventListener('change', async e => {
  const inp = e.target.closest('[data-wgraj]'); if (!inp || !inp.files[0]) return;
  const i = Number(inp.dataset.wgraj), plik = inp.files[0], bajty = new Uint8Array(await plik.arrayBuffer());
  const nazwa = plik.name.toLowerCase(), odlaczony = /\.(xades|xml|sig|p7s|p7m)$/.test(nazwa);
  const tekst = new TextDecoder('latin1').decode(bajty.subarray(0, Math.min(bajty.length, 4e6)) );
  const pdf = tekst.startsWith('%PDF'), podpisanyPdf = pdf && (/\/ByteRange/.test(tekst) || /[-_](podpisany|signed|sig|xades)/i.test(nazwa));
  if (!odlaczony && !podpisanyPdf) { pokazToast(pdf ? 'Ten PDF nie wygląda na podpisany — podpisz go na gov.pl i wgraj ponownie' : 'To nie jest podpisany dokument'); inp.value = ''; return; }
  await magPliki.zapisz(kluczPodp(i, plik.name), bajty);
  M.podpisane[i] = true; M.podpisaniPliki = Object.assign(M.podpisaniPliki || {}, { [i]: plik.name }); zapiszRekord();
  odswiezPodpisy(); odswiezHero(); zorza && zorza.flara(.22);
  const prz = $('.dok-w[data-i="' + i + '"] .stan', arkTresc); if (prz) { prz.classList.add('ok'); prz.innerHTML = '<i></i>podpisane'; }
  pokazToast(`${nazwyDok()[i].tytul}: podpis zapisany (${ilePodpisanych()} z ${razemDok()})`);
  if (ilePodpisanych() >= razemDok()) { zamknijArkusz(); kurtyna && kurtyna.swieto(); zorza && zorza.flara(1); pokazToast('Wszystko podpisane — możesz wysłać do Kierownika regionu'); }
});
async function arkuszWyslij() {
  const lista = nazwyDok(), odb = magUst.daj('odbiorca', '');
  otworzArkusz(`${naglowekArkusza('Wyślij do Kierownika regionu')}
    <p class="ark-opis">Dołączę do wiadomości <b>${lista.length} ${lista.length === 1 ? 'dokument' : 'dokumenty'}</b> i pliki podpisów. Poczta otworzy się u Ciebie — wiadomość wysyłasz sam, więc hasła do skrzynki nie podajesz nigdzie.</p>
    <label class="pole"><span>Adres Kierownika regionu</span><input id="w-odb" type="email" inputmode="email" autocomplete="email" value="${bezZnacznikow(odb)}" placeholder="adres@firma.pl" data-pierwsze><small></small></label>
    <div class="ark-dol"><button type="button" class="przycisk" data-zamknij>Anuluj</button><button type="button" class="przycisk" id="w-mailto">Otwórz pocztę</button><button type="button" class="przycisk glowny" id="w-udostepnij">Udostępnij pliki</button></div>`);
  const temat = `Delegacje — ${PROFIL.imie} — ${MIES[M.mies - 1]} ${M.rok}`, tresc = 'W załączeniu dokumenty delegacyjne.';
  const zbierz = async () => {
    const rec = magMiesiace.daj(M.rok, M.mies) || {}, pliki = [];
    for (const d of lista) { const b = await magPliki.daj(klucz(d.nazwa)); if (b) pliki.push(new File([b], d.nazwa, { type: 'application/pdf' })); }
    return pliki;
  };
  const zaznacz = () => { const v = $('#w-odb', arkTresc).value.trim(); if (v) magUst.ustaw('odbiorca', v); return v; };
  const potwierdz = () => { M.wyslane = true; zapiszRekord(); odswiezHero(); zamknijArkusz(); zorza && zorza.flara(.7); pokazToast('Oznaczono jako wysłane. Gdyby nie poszło, kliknij „Cofnij wysłanie".'); };
  $('#w-udostepnij', arkTresc).addEventListener('click', async () => {
    const pliki = await zbierz(); zaznacz();
    if (navigator.canShare && navigator.canShare({ files: pliki })) { try { await navigator.share({ files: pliki, title: temat, text: tresc }); potwierdz(); } catch (e) { if (e.name !== 'AbortError') pokazToast('Nie udało się udostępnić plików'); } }
    else { for (const f of pliki) { pobierzBlob(f, f.name); await zegar(350); } pokazToast('Ta przeglądarka nie udostępnia plików do poczty — pobrałem dokumenty, dołącz je do wiadomości'); }
  });
  $('#w-mailto', arkTresc).addEventListener('click', async () => {
    const v = zaznacz(); if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { const s = $('#w-odb', arkTresc).parentElement.querySelector('small'); s.textContent = 'Wpisz poprawny adres e-mail'; s.classList.add('zle'); return; }
    const pliki = await zbierz(); for (const f of pliki) { pobierzBlob(f, f.name); await zegar(350); }
    location.href = `mailto:${encodeURIComponent(v)}?subject=${encodeURIComponent(temat)}&body=${encodeURIComponent(tresc + '\n\n(Dołącz pobrane pliki PDF.)')}`;
    setTimeout(potwierdz, 800);
  });
}
function cofnijWyslanie() { M.wyslane = false; zapiszRekord(); odswiezHero(); pokazToast('Przywrócono stan przed wysyłką'); }
async function klikGlowny() {
  const e = etapMiesiaca();
  if (e === 'ustaw') return generuj();
  if (e === 'podpisz') return arkuszPodpis();
  if (e === 'wyslij') return arkuszWyslij();
  pokazToast('Dokumenty są już wysłane');
}
