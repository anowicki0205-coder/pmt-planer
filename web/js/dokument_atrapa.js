// PMT Planer (web) — atrapa dokumentu: miniatura i podgląd polecenia wyjazdu oraz rozliczenia, zbudowane z DANYCH wyniku generowania (silnik oddaje je razem z plikami PDF).
// Aplikacja nie ma rysownika PDF, więc to wierna replika układu z silnika (nagłówek firmy, dane pracownika, tabela WYJAZD / PRZYJAZD, koszty, pole AKCEPTACJA z trzema podpisami),
// a nie zdjęcie pliku. Służy do podglądu w karuzeli 3D; prawdziwy plik otwiera przycisk „Otwórz”. Czyste funkcje — bez dostępu do interfejsu.

const ZNAKI = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ZNAKI[c]);
export const kwotaPdf = x => Number(x || 0).toFixed(2);                 // tak jak w PDF: „805.70”
export const dataPdf = iso => /^\d{4}-\d{2}-\d{2}/.test(String(iso)) ? `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}` : String(iso || '');
export const maskaPesel = p => { p = String(p || '').replace(/\D/g, ''); return p ? '•'.repeat(Math.max(0, p.length - 3)) + p.slice(-3) : ''; };

/** Stawka za km tak, jak stoi na dokumencie („1,15”, „0,89”, „0,6000” → „0,60”) — jak tekst_stawki w silniku. */
export function tekstStawki(stawka) {
  const [calosc, u] = Number(stawka || 0).toFixed(4).split('.'); const ulamek = u.replace(/0+$/, '');
  return `${calosc},${(ulamek + '00').slice(0, Math.max(2, ulamek.length))}`;
}
/** Kilometry za kwotą dokumentu (kwota / stawka), z 1–3 miejscami po przecinku tak, by km × stawka dały DOKŁADNIE kwotę — jak kilometry_dokumentu w silniku. */
export function kilometryDokumentu(kwota, stawka) {
  if (!(stawka > 0) || !(kwota > 0)) return '';
  const km = kwota / stawka;
  for (const m of [1, 2, 3]) { const t = km.toFixed(m); if (Math.round(Number(t) * stawka * 100) === Math.round(kwota * 100)) return t.replace('.', ','); }
  return km.toFixed(3).replace('.', ',');
}
const firma = stanowisko => stanowisko === 'KR' ? { nazwa: 'PMT HR SP. Z O.O. SP. K.', nipDlugi: 'NIP 779-24-86-133', nipKrotki: 'NIP 779-248-61-33' } : { nazwa: 'PMT SERVICES SP. Z O.O. SP. K.', nipDlugi: 'NIP 779-24-86-127', nipKrotki: 'NIP 779-248-61-27' };

/** Dane polecenia wyjazdu nr `nr` z wyniku generowania: wiersze trasy (etapy dni należących do dokumentu), suma, kilometry, sieci. ctx: { imie, pesel, adres, stanowisko, przelozony }. */
export function daneDelegacji(wynik, nr, ctx) {
  const dok = (wynik.dokumenty || []).find(x => x.nr === nr); if (!dok) return null;
  const dni = (wynik.dni || []).filter(d => Number(d.dokument) === nr).sort((a, b) => String(a.data).localeCompare(String(b.data)));
  const rzedy = []; for (const d of dni) for (const e of (d.etapy || [])) rzedy.push({ skad: e.skad, data: dataPdf(d.data), wyj: e.wyjazd, dokad: e.dokad, przyj: e.przyjazd, kwota: kwotaPdf(e.kwota) });
  const suma = dni.reduce((s, d) => s + Number(d.suma || 0), 0) || Number(dok.kw || 0);
  return { typ: 'delegacja', nr, ...ctx, firma: firma(ctx.stanowisko), sieci: (dok.sieci || []).join(', '), rzedy, suma: kwotaPdf(suma), km: kilometryDokumentu(suma, wynik.stawka), stawka: tekstStawki(wynik.stawka) };
}
/** Dane rozliczenia zbiorczego: lista poleceń z kwotami, miesiąc i rok. ctx jak wyżej + { miesiac (nazwa), rok }. */
export function daneRozliczenia(wynik, ctx) {
  const wiersze = (wynik.dokumenty || []).map(x => ({ lp: x.nr, dokument: `delegacja ${String(x.nr).padStart(2, '0')} ${ctx.imie}`, opis: 'Koszty dojazdów', kwota: kwotaPdf(x.kw) }));
  return { typ: 'rozliczenie', nr: 0, ...ctx, firma: firma(ctx.stanowisko), wiersze, suma: kwotaPdf((wynik.dokumenty || []).reduce((s, x) => s + Number(x.kw || 0), 0)) };
}

const PODPIS_SVG = '<svg class="da-podpis" viewBox="0 0 60 30" fill="none" stroke="#1d2f8a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path pathLength="1" d="M3 22C8 6 12 4 14 14S18 26 24 12 30 6 32 16s4 8 9-6 6 6 14-4"/><path pathLength="1" d="M6 26c14-3 30-3 50-6" stroke-width="1"/></svg>';
const ZNAK = { czeka: '✎', trwa: '…', uwaga: '?', zle: '×', ok: '' };
/** Pole „podpis pracownika”. Na ROZLICZENIU WYDATKÓW podpis nie jest wymagany (wymagają go tylko polecenia wyjazdu), więc tam pole nie czeka na podpis: bez kreskowanej ramki, znaczków stanu (✎ ? ×)
 *  i bez „rysującego się” podpisu — tylko cichy napis „niewymagany”. */
const polePodpisu = (stan, wymagany = true) => wymagany
  ? `<div class="da-pole da-moj">podpis pracownika${stan === 'ok' ? PODPIS_SVG : ''}${stan === 'ok' ? '' : `<span class="da-znak">${ZNAK[stan] ?? ''}</span>`}</div>`
  : '<div class="da-pole da-niewym">podpis pracownika<span class="da-nie">niewymagany</span></div>';
const blokAkceptacji = stan => `<div class="da-akc"><div class="da-v">AKCEPTACJA</div><div class="da-pole">podpis Księgowej</div><div class="da-pole">podpis Dyrektora Zarządzającego</div>${polePodpisu(stan)}</div>`;

/** HTML kartki. o: { stan: 'czeka'|'trwa'|'ok'|'uwaga'|'zle', maks: najwyżej tyle wierszy (miniatura), pelnyPesel, wyslano, nowy (stan zmienił się przed chwilą: podpis „rysuje się”, zły dokument drży) }. Wszystkie teksty są oczyszczane — dane z pliku/profilu nie wstrzykną znaczników. */
export function atrapaHtml(d, o = {}) {
  const stan = o.stan || 'czeka', maks = o.maks ?? Infinity, pesel = o.pelnyPesel ? String(d.pesel || '') : maskaPesel(d.pesel);
  const klasa = `da-papier da-${stan}${o.nowy ? ' da-nowy' : ''}${o.wyslano ? ' da-wyslano' : ''}${d.typ === 'rozliczenie' ? ' da-rozl' : ''}`;
  let tresc;
  if (d.typ === 'rozliczenie') {
    const wiersze = d.wiersze.slice(0, Math.max(1, maks)), reszta = d.wiersze.length - wiersze.length;
    const pelne = wiersze.map(w => `<span class="c">${esc(w.lp)}.</span><span>${esc(w.dokument)}</span><span>${esc(w.opis)}</span><span class="r">${esc(w.kwota)}</span>`).join('');
    const puste = o.maks === undefined || o.maks === Infinity ? Array.from({ length: Math.max(0, 13 - d.wiersze.length) }, (_, i) => `<span class="c">${d.wiersze.length + i + 1}.</span><span>&nbsp;</span><span></span><span></span>`).join('') : '';
    tresc = `<div class="da-firma">${esc(d.firma.nazwa)}</div><div class="da-adr">ul. Ptasia 10, 60-319 Poznań</div><div class="da-adr">${esc(d.firma.nipKrotki)}</div>
      <div class="da-tyt2">Rozliczenie wydatków za miesiąc: ${esc(d.miesiac)} ${esc(d.rok)}r.</div>
      <div class="da-nagl"><b>Imię i Nazwisko:</b><span>${esc(d.imie)}</span><b>Projekt/Stanowisko:</b><span>${esc(d.stanowisko)}</span><b>MENEDŻER:</b><span>${esc(d.przelozony || '—')}</span><b>Liczba dokumentów:</b><span>${esc(d.wiersze.length)}</span></div>
      <div class="da-tab da-tab4"><span class="h">Lp.</span><span class="h">Dokument</span><span class="h">Opis</span><span class="h">Kwota brutto</span>${pelne}${reszta > 0 ? `<span class="c">…</span><span class="szary" style="grid-column:span 3">jeszcze ${reszta} ${reszta === 1 ? 'dokument' : 'dokumenty'}</span>` : ''}${puste}</div>
      <div class="da-sumy"><span>zaliczka:</span><span class="r">&nbsp;</span><b>Suma wydatków global:</b><span class="r b">${esc(d.suma)}</span></div>
      <div class="da-akc da-akc1"><div class="da-pole">&nbsp;</div>${polePodpisu(stan, false)}</div>`;
  } else {
    const rzedy = d.rzedy.slice(0, maks === Infinity ? undefined : Math.max(1, maks - (d.rzedy.length > maks ? 1 : 0))), reszta = d.rzedy.length - rzedy.length;
    const wiersze = rzedy.map(r => `<span>${esc(r.skad)}</span><span class="c">${esc(r.data)}</span><span class="c">${esc(r.wyj)}</span><span>${esc(r.dokad)}</span><span class="c">${esc(r.data)}</span><span class="c">${esc(r.przyj)}</span><span class="c">samochód osobowy</span><span class="r">${esc(r.kwota)}</span>`).join('')
      + (reszta > 0 ? `<span class="szary" style="grid-column:1/-1;text-align:center">… jeszcze ${reszta} ${reszta === 1 ? 'odcinek' : 'odcinków'} (pełna lista po powiększeniu)</span>` : '');
    tresc = `<div class="da-firma">${esc(d.firma.nazwa)}</div><div class="da-adr">ul. Ptasia 10, 60-319 Poznań</div><div class="da-adr">${esc(d.firma.nipDlugi)}</div>
      <div class="da-tyt">Rozliczenie delegacji<span class="n">6</span></div><div class="da-centrum">Centrum</div>
      <div><div class="da-box"><div>${esc(d.imie)} ${esc(pesel)}</div><div>${esc(d.stanowisko)}</div></div><div class="da-pod"><span>imię i nazwisko oraz PESEL</span><span>stanowisko</span></div></div>
      <div><div class="da-box"><div>${esc(d.adres)}</div><div>${esc(d.przelozony || '—')}</div></div><div class="da-pod"><span>adres zamieszkania</span><span>przełożony</span></div></div>
      <div><div class="da-proj">projekt: ${esc(d.sieci || '—')}</div><div class="da-pod1">cel wyjazdu - Projekt</div></div>
      <div class="da-sek"><b>Rozliczenie kosztów podróży</b></div>
      <div class="da-tab"><span class="h sp3">WYJAZD</span><span class="h sp3">PRZYJAZD</span><span class="h">Środki lokomocji</span><span class="h">Koszty</span>
        <span class="h">miejscowość</span><span class="h">data</span><span class="h">godz.</span><span class="h">miejscowość</span><span class="h">data</span><span class="h">godz.</span><span class="h">&nbsp;</span><span class="h">&nbsp;</span>${wiersze}</div>
      <div class="da-koszty"><span>(1) Przejazdy</span><span>Prywatny samochód${d.km ? `: ${esc(d.km)} km × ${esc(d.stawka)} zł/km` : ''}</span><span class="r">${esc(d.suma)}</span>
        <span>(2) Noclegi</span><span>Koszt hotelu lub ryczałt 67,50 zł</span><span class="r">-</span><span>(3) Diety</span><span>22,50 zł lub 45,00 zł</span><span class="r">-</span>
        <span>(4) Inne</span><span>Autostrada, parking, reprezentacja</span><span class="r">-</span>
        <span class="b" style="grid-column:span 2;text-align:right">Suma wydatków</span><span class="r b">${esc(d.suma)}</span></div>
      ${blokAkceptacji(stan)}`;
  }
  return `<div class="${klasa}"><div class="da-pin">${tresc}</div><div class="da-pieczec">WYSŁANO</div></div>`;
}
