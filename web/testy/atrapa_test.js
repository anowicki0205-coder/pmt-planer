// Atrapa dokumentu (js/dokument_atrapa.js): dane z wyniku generowania → HTML kartki. Czyste funkcje, test w samym Node (bez przeglądarki).
// node atrapa_test.js
(async () => {
  const A = await import('../js/dokument_atrapa.js'); let kod = 0;
  const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const wynik = {
    stawka: 1.15, zrodlo: { etykieta: 'szacunek' },
    dokumenty: [{ nr: 1, plik: 'delegacja_01.pdf', od: '2026-09-01', do: '2026-09-04', kw: 805.7, sieci: ['Biedronka', 'Żabka'] }, { nr: 2, plik: 'delegacja_02.pdf', od: '2026-09-07', do: '2026-09-10', kw: 798.95, sieci: ['Carrefour'] }],
    dni: [
      { data: '2026-09-02', suma: 100.5, km: 87, dokument: 1, etapy: [{ skad: 'Warszawa', dokad: 'Brwinów', wyjazd: '07:59', przyjazd: '08:26', kwota: 33.97, km: 29 }, { skad: 'Brwinów', dokad: 'Warszawa', wyjazd: '08:43', przyjazd: '09:10', kwota: 66.53, km: 58 }] },
      { data: '2026-09-01', suma: 705.2, km: 613, dokument: 1, etapy: [{ skad: 'Warszawa', dokad: 'Milanówek', wyjazd: '07:00', przyjazd: '07:40', kwota: 705.2, km: 613 }] },
      { data: '2026-09-07', suma: 798.95, km: 695, dokument: 2, etapy: [{ skad: 'Warszawa', dokad: 'Zduny', wyjazd: '07:17', przyjazd: '09:20', kwota: 798.95, km: 695 }] }],
  };
  const ctx = { imie: 'Jan Testowy', pesel: '90010112349', adres: 'ul. Testowa 1, 00-001 Warszawa', stanowisko: 'merchandiser', przelozony: 'Kierownik Testowy' };
  const sam = h => h.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ');

  ok('stawka jak na dokumencie: 1,15 / 0,89 / 0,60 / 1,00', A.tekstStawki(1.15) === '1,15' && A.tekstStawki(0.89) === '0,89' && A.tekstStawki(0.6) === '0,60' && A.tekstStawki(1) === '1,00', [1.15, 0.89, 0.6, 1].map(A.tekstStawki).join(' '));
  ok('kilometry za kwotą: km × stawka dają dokładnie kwotę (805,70 zł / 1,15 → 700,6 → 805,69 ≠ → 700,61)', A.kilometryDokumentu(805.7, 1.15) === '700,61', A.kilometryDokumentu(805.7, 1.15));
  ok('kilometry: brak stawki lub kwoty → pusto', A.kilometryDokumentu(0, 1.15) === '' && A.kilometryDokumentu(100, 0) === '');
  ok('data jak w PDF (DD.MM.RRRR), PESEL zamaskowany (ostatnie 3 cyfry)', A.dataPdf('2026-09-07') === '07.09.2026' && A.maskaPesel('90010112349') === '••••••••349' && A.maskaPesel('') === '');

  const d1 = A.daneDelegacji(wynik, 1, ctx);
  ok('polecenie 1: wiersze trasy tylko z dni tego dokumentu, w kolejności dat (3 odcinki)', d1.rzedy.length === 3 && d1.rzedy[0].skad === 'Warszawa' && d1.rzedy[0].dokad === 'Milanówek' && d1.rzedy[0].data === '01.09.2026' && d1.rzedy[2].dokad === 'Warszawa', JSON.stringify(d1.rzedy.map(r => r.data + ' ' + r.dokad)));
  ok('polecenie 1: suma = suma dni (805.70), cel wyjazdu z sieci dokumentu, stawka i kilometry', d1.suma === '805.70' && d1.sieci === 'Biedronka, Żabka' && d1.stawka === '1,15' && d1.km === '700,61', JSON.stringify({ s: d1.suma, k: d1.km, st: d1.stawka }));
  ok('nieistniejący numer dokumentu → null', A.daneDelegacji(wynik, 9, ctx) === null);
  const dR = A.daneRozliczenia(wynik, { ...ctx, miesiac: 'wrzesień', rok: 2026 });
  ok('rozliczenie: wiersz na każde polecenie, suma wszystkich', dR.wiersze.length === 2 && dR.wiersze[0].dokument === 'delegacja 01 Jan Testowy' && dR.suma === '1604.65', JSON.stringify(dR.wiersze[1]) + ' ' + dR.suma);

  const h1 = A.atrapaHtml(d1, { stan: 'czeka', maks: 6 }), t1 = sam(h1);
  ok('miniatura: firma usługowa, imię i nazwisko, adres, przełożony, kwota', /PMT SERVICES SP\. Z O\.O\. SP\. K\./.test(t1) && t1.includes('Jan Testowy') && t1.includes('ul. Testowa 1') && t1.includes('Kierownik Testowy') && t1.includes('805.70'));
  ok('miniatura: PESEL zasłonięty, pełnego numeru nie ma w kodzie', !h1.includes('90010112349') && h1.includes('349'));
  const hP = A.atrapaHtml(d1, { stan: 'czeka', pelnyPesel: true });
  ok('podgląd: pełny PESEL, wszystkie 3 wiersze trasy i trzy pola podpisów (Księgowa, Dyrektor, pracownik)', hP.includes('90010112349') && (hP.match(/class="c">\d\d\.\d\d\.\d{4}</g) || []).length === 6 && /podpis Księgowej/.test(hP) && /podpis Dyrektora Zarządzającego/.test(hP) && /podpis pracownika/.test(hP));
  const dDuze = { ...d1, rzedy: Array.from({ length: 20 }, (_, i) => ({ skad: 'A' + i, dokad: 'B' + i, data: '01.09.2026', wyj: '07:00', przyj: '08:00', kwota: '1.00' })) };
  const hM = A.atrapaHtml(dDuze, { stan: 'czeka', maks: 6 });
  ok('miniatura skraca długą trasę do 6 linii (5 odcinków + dopisek „jeszcze 15 odcinków”), podgląd pokazuje wszystkie 20', (hM.match(/class="c">01\.09\.2026</g) || []).length === 10 && /jeszcze 15 odcinków/.test(hM) && (A.atrapaHtml(dDuze, { stan: 'czeka' }).match(/class="c">01\.09\.2026</g) || []).length === 40);
  ok('rozliczenie: tytuł „Rozliczenie wydatków za miesiąc”, spółka HR dla KR, 13 wierszy w podglądzie', (() => { const r = A.atrapaHtml(A.daneRozliczenia(wynik, { ...ctx, stanowisko: 'KR', miesiac: 'wrzesień', rok: 2026 }), { stan: 'czeka' }); return /Rozliczenie wydatków za miesiąc: wrzesień 2026r\./.test(r) && r.includes('PMT HR SP. Z O.O. SP. K.') && /Suma wydatków/.test(r) && (r.match(/class="c">\d+\.</g) || []).length === 13; })());
  ok('stany: czeka/trwa/ok/uwaga/zle dają własną klasę, „ok” ma podpis, pozostałe znak; wysłano → pieczęć', ['czeka', 'trwa', 'ok', 'uwaga', 'zle'].every(s => A.atrapaHtml(d1, { stan: s }).includes('da-' + s)) && A.atrapaHtml(d1, { stan: 'ok' }).includes('da-podpis') && !A.atrapaHtml(d1, { stan: 'czeka' }).includes('da-podpis') && A.atrapaHtml(d1, { stan: 'ok', wyslano: true }).includes('da-wyslano'));
  const zly = { ...d1, imie: '<img src=x onerror=alert(1)>', adres: '"><script>alert(2)</script>', przelozony: "'; DROP", sieci: '<b>x</b>', rzedy: [{ skad: '<i>', dokad: '&', data: '01.09.2026', wyj: '<', przyj: '>', kwota: '"' }] };
  const hZ = A.atrapaHtml(zly, { stan: 'czeka' });
  ok('dane z pliku/profilu nie wstrzykują znaczników (XSS): brak <img, <script, <b>, <i>', !/<img|<script|<b>x|<i>/.test(hZ) && hZ.includes('&lt;img') && hZ.includes('&lt;script&gt;'));
  process.exit(kod);
})();
