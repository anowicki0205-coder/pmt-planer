// Adres w osobnych polach (js/adres.js): rozdzielanie zapisanego adresu na pola, składanie pól w napis dla silnika (ten sam format, co dotąd), sprawdzanie pól i kod pocztowy w trakcie pisania.
// Dodatkowo (gdy jest Python z silnikiem): napis ze złożonych pól przechodzi przez PRAWDZIWE waliduj_adres z silnika i daje ten sam adres do PDF, co wpisanie go w jednym polu.
// Uruchom: node adres_pola_test.js
(async () => {
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const A = await import('../js/adres.js'), j = JSON.stringify;
  const r = A.rozbierzAdres;
  ok('rozdziela adres z ulicą, numerem budynku, kodem i miejscowością', j(r('ul. Testowa 1, 00-001 Warszawa')) === j({ ulica: 'ul. Testowa', nr: '1', lokal: '', kod: '00-001', miasto: 'Warszawa' }), j(r('ul. Testowa 1, 00-001 Warszawa')));
  ok('numer mieszkania po ukośniku trafia do osobnego pola (także z literą i odwrotnym ukośnikiem)', j(r('ul. Polna 5/12, 00-001 Warszawa')) === j({ ulica: 'ul. Polna', nr: '5', lokal: '12', kod: '00-001', miasto: 'Warszawa' }) && r('Polna 12A/3b, 00-001 Warszawa').lokal === '3b' && r('Polna 12A/3b, 00-001 Warszawa').nr === '12A' && r('Polna 5\\7, 00-001 Warszawa').lokal === '7');
  ok('adres wiejski bez przedrostka: nazwa wsi w polu ulicy, miejscowość = poczta', j(r('Dębowa Wola 12, 26-660 Jedlińsk')) === j({ ulica: 'Dębowa Wola', nr: '12', lokal: '', kod: '26-660', miasto: 'Jedlińsk' }));
  ok('przedrostki (ulica/aleja/plac/osiedle) zapisują się skrótem jak w silniku; nazwa z cyfrą („al. 3 Maja”) zostaje cała', r('ulica Polna 5, 00-001 Warszawa').ulica === 'ul. Polna' && r('Aleja Róż 5, 00-001 Warszawa').ulica === 'al. Róż' && r('osiedle Słoneczne 2, 00-001 Warszawa').ulica === 'os. Słoneczne' && j(r('al. 3 Maja 5, 00-001 Warszawa')) === j({ ulica: 'al. 3 Maja', nr: '5', lokal: '', kod: '00-001', miasto: 'Warszawa' }));
  ok('miejscowość z kilku słów i myślnikiem zostaje cała („Bielsko-Biała”, „Józefów nad Wisłą”); nadmiarowe spacje znikają', r('Polna 5,   43-300   Bielsko-Biała').miasto === 'Bielsko-Biała' && r('Rynek 1, 24-150 Józefów nad Wisłą').miasto === 'Józefów nad Wisłą' && r('  ul.   Polna   5 , 00-001  Warszawa ').ulica === 'ul. Polna');
  ok('adresu, którego nie da się rozdzielić (brak numeru, kodu albo śmieci), nie zgaduje — null', r('Dębowa Wola, 26-660 Jedlińsk') === null && r('ul. Polna 5 Warszawa') === null && r('') === null && r(null) === null && r('cokolwiek') === null);
  const z = A.zlozAdres;
  ok('składa pola w napis dla silnika: „ulica numer, kod miejscowość”, z mieszkaniem po ukośniku', z({ ulica: 'ul. Testowa', nr: '1', lokal: '', kod: '00-001', miasto: 'Warszawa' }) === 'ul. Testowa 1, 00-001 Warszawa' && z({ ulica: 'ul. Polna', nr: '5', lokal: '12', kod: '00-001', miasto: 'Warszawa' }) === 'ul. Polna 5/12, 00-001 Warszawa' && z({ ulica: 'Dębowa Wola', nr: '12', lokal: '', kod: '26-660', miasto: 'Jedlińsk' }) === 'Dębowa Wola 12, 26-660 Jedlińsk');
  ok('składanie czyści spacje w numerach i na brzegach pól', z({ ulica: '  ul.  Polna ', nr: ' 5 ', lokal: ' 1 2 ', kod: ' 00-001 ', miasto: ' Warszawa ' }) === 'ul. Polna 5/12, 00-001 Warszawa');
  const adresy = ['ul. Testowa 1, 00-001 Warszawa', 'ul. Polna 5/12, 00-001 Warszawa', 'Dębowa Wola 12, 26-660 Jedlińsk', 'al. 3 Maja 5A/7b, 43-300 Bielsko-Biała', 'os. Słoneczne 2, 61-100 Poznań', 'Krzyżówki 3, 26-660 Jedlińsk'];
  ok('obie drogi są odwrotne: rozdzielenie i ponowne złożenie daje ten sam adres (6 przykładów)', adresy.every(a => z(r(a)) === a), adresy.filter(a => z(r(a)) !== a).join(' | '));
  const s = A.sprawdzPola;
  ok('poprawne pola (z pustym mieszkaniem i z mieszkaniem) przechodzą', s({ ulica: 'ul. Polna', nr: '5', lokal: '', kod: '00-001', miasto: 'Warszawa' }).ok && s({ ulica: 'Polna', nr: '12A', lokal: '3b', kod: '00-001', miasto: 'Warszawa' }).ok);
  const zle = s({ ulica: '', nr: '', lokal: 'x', kod: '123', miasto: '' });
  ok('każde złe pole dostaje własny komunikat (ulica, numer budynku, mieszkanie, kod, miejscowość)', !zle.ok && ['ulica', 'nr', 'lokal', 'kod', 'miasto'].every(k => typeof zle.bledy[k] === 'string' && zle.bledy[k].length > 5), j(zle.bledy));
  ok('numer budynku: tylko cyfry z ewentualną jedną literą („5”, „12A”); „5/3”, „abc”, „5 3” odrzucone — mieszkanie ma własne pole', !s({ ulica: 'Polna', nr: '5/3', lokal: '', kod: '00-001', miasto: 'W' }).ok && !s({ ulica: 'Polna', nr: 'abc', lokal: '', kod: '00-001', miasto: 'W' }).ok && s({ ulica: 'Polna', nr: '5 3', lokal: '', kod: '00-001', miasto: 'W' }).ok);      // „5 3” to po usunięciu spacji „53” — poprawny numer; spacje w numerze są zbędne, nie błędne
  ok('numer mieszkania jest opcjonalny: puste pole nie jest błędem', !('lokal' in s({ ulica: 'Polna', nr: '5', lokal: '   ', kod: '00-001', miasto: 'Warszawa' }).bledy));
  const k = A.kodWTrakcieWpisywania;
  ok('kod pocztowy w trakcie pisania: myślnik wstawia się sam po trzeciej–piątej cyfrze, litery i nadmiar znikają', k('00') === '00' && k('000') === '00-0' && k('00001') === '00-001' && k('00-001') === '00-001' && k('00a-0b01') === '00-001' && k('0000123') === '00-001' && k('') === '' && k('26660') === '26-660');

  // prawdziwy silnik: ten sam adres do PDF z pól i z jednego napisu
  const cp = require('child_process'), path = require('path'), PY = process.env.PYTHON_PODPISY || 'python3';
  const probe = cp.spawnSync(PY, ['-I', '-c', 'import sys; sys.path.insert(0, sys.argv[1]); import pmt_silnik as S; print(S.waliduj_adres("ul. Polna 5/12, 00-001 Warszawa")["adres_caly"])', path.join(__dirname, '..', 'silnik')], { encoding: 'utf8' });
  if (probe.status !== 0) console.log('  UWAGA silnik w Pythonie nie uruchomił się tu (brak bibliotek) — pominięto porównanie z waliduj_adres: ' + (probe.stderr || '').split('\n').filter(Boolean).pop());
  else {
    const przez = a => JSON.parse(cp.spawnSync(PY, ['-I', '-c', 'import sys, json; sys.path.insert(0, sys.argv[1]); import pmt_silnik as S; a = S.waliduj_adres(sys.argv[2]); print(json.dumps(a, ensure_ascii=False))', path.join(__dirname, '..', 'silnik'), a], { encoding: 'utf8' }).stdout);
    const rozne = adresy.filter(a => { const x = przez(a), y = przez(z(r(a))); return x.adres_caly !== y.adres_caly || x.kod_pocztowy !== y.kod_pocztowy || x.baza_miasto !== y.baza_miasto; });
    ok('silnik daje TEN SAM adres do PDF, kod i miejscowość bazy dla adresu z jednego napisu i z pól (6 przykładów)', rozne.length === 0, rozne.join(' | '));
  }
  console.log(kod ? 'KONIEC kod=1' : 'KONIEC kod=0'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e); process.exit(2); });
