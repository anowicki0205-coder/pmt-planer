/* ====================== dziś: plan wizyt ====================== */
let nawigacja = -1;
const wizyt = k => k === 1 ? 'wizyta' : (k % 10 >= 2 && k % 10 <= 4 && (k % 100 < 10 || k % 100 >= 20)) ? 'wizyty' : 'wizyt';
function rysujDzis() {
  const teraz = new Date();
  $('#d-data').textContent = `· ${DK[(teraz.getDay() + 6) % 7]} ${dwa(teraz.getDate())}.${dwa(teraz.getMonth() + 1)}`;
  const lista = $('#przystanki'), plan = $('#d-plan'), os = $('#d-os');
  if (!PLAN_DZIS.length) {
    $('#d-pier-t').textContent = '–'; $('#d-pier').style.setProperty('--p', '0');
    $('#d-meta').innerHTML = '<span>brak planu wizyt</span>';
    lista.innerHTML = '<li class="pusty-stan"><b>Nie ma planu na dziś</b><span>Tu pojawi się lista sklepów na dzisiejszą trasę, z przyciskiem „Nawiguj" do następnego.</span></li>';
    plan.innerHTML = ''; os.innerHTML = '';
    return;
  }
  const ile = PLAN_DZIS.filter(s => s.ok).length, n = PLAN_DZIS.findIndex(s => !s.ok);
  $('#d-pier-t').textContent = `${ile}/${PLAN_DZIS.length}`; $('#d-pier').style.setProperty('--p', (ile / PLAN_DZIS.length).toFixed(4));
  $('#d-meta').innerHTML = `<span><b>${ile} z ${PLAN_DZIS.length}</b> ${wizyt(PLAN_DZIS.length)}</span>`;
  if (nawigacja !== n) nawigacja = -1;
  lista.innerHTML = PLAN_DZIS.map((s, i) => {
    const teraz = i === n, pr = nawigacja === i;
    return `<li class="przystanek${s.ok ? ' ok' : ''}${teraz ? ' teraz' : ''}" style="view-transition-name:p${i}">` +
      `<span class="p-godz num">${s.g}</span>` +
      `<button class="p-znak" type="button" data-i="${i}" aria-pressed="${s.ok}" aria-label="${s.ok ? 'Cofnij odhaczenie' : 'Odhacz wizytę'}: ${s.s}, ${s.m}">${ik('i-ok')}</button>` +
      (teraz ? `<p class="p-etyk brew">Następny · jedziesz teraz</p>` : '') +
      `<p class="p-nazwa"><i style="--c:var(${s.c || '--cyan'})"></i>${s.s} <span>· ${s.m}</span></p><p class="p-adres">${s.a}</p>` +
      (teraz ? `<button class="nawiguj${pr ? ' prowadzi' : ''}" type="button" id="nawiguj" data-i="${i}" aria-pressed="${pr}">${ik('i-nawi')}<span>${pr ? 'Prowadzę' : 'Nawiguj'}</span></button>` : '') + `</li>`;
  }).join('');
  const zost = PLAN_DZIS.length - ile;
  plan.innerHTML = `<div class="dp-k dp-glowny"><span class="dp-et">Przed Tobą</span><b class="num">${zost}</b><span class="dp-op">${zost ? `${wizyt(zost)} · następna ${PLAN_DZIS[n].g}` : 'komplet — trasa zakończona'}</span></div>` +
    `<div class="dp-k"><span class="dp-et">Ostatnia wizyta</span><b class="num">${PLAN_DZIS[PLAN_DZIS.length - 1].g}</b><span class="dp-op">${PLAN_DZIS[PLAN_DZIS.length - 1].s} · ${PLAN_DZIS[PLAN_DZIS.length - 1].m}</span></div>`;
  const A = 16 * 60, Z = 21 * 60, pc = v => ((v - A) / (Z - A) * 100).toFixed(2) + '%';
  const t = i => minuty(PLAN_DZIS[i].g), ost = PLAN_DZIS.reduce((m, x, i) => x.ok ? i : m, -1);
  let h = `<div class="dos-tor">`;
  if (ost >= 0) h += `<span class="dos-zrob" style="left:${pc(t(0))};width:calc(${pc(t(ost))} - ${pc(t(0))})"></span>`;
  if (n >= 0) { const a = n > 0 ? t(n - 1) : A + 24; h += `<span class="dos-jazda" style="left:${pc(a)};width:calc(${pc(t(n))} - ${pc(a)})"></span>`; }
  h += PLAN_DZIS.map((x, i) => `<span class="dos-p${x.ok ? ' ok' : ''}${i === n ? ' teraz' : ''}" style="left:${pc(t(i))}"><i></i><b>${x.s}</b><small class="num">${x.g}</small></span>`).join('');
  os.innerHTML = h + `</div><div class="dos-skala num"><span>16:00</span><span>21:00</span></div>`;
  requestAnimationFrame(sprawdzListe);
}
function sprawdzListe() {
  const l = $('#przystanki'); if (!l) return;
  l.classList.toggle('przewijana', l.scrollHeight > l.clientHeight + 2 && l.scrollTop + l.clientHeight < l.scrollHeight - 2);
}

/* ====================== dokumenty: fiolki poleceń wobec limitu ====================== */
function budujFiolki() {
  const box = $('#fiolki'), n = M ? M.polecenia.length : 0;
  if (!M || M.stan !== 'gotowe') {
    box.style.gridTemplateColumns = '1fr';
    box.innerHTML = '<div class="pusty-stan"><b>Dokumenty pojawią się po wygenerowaniu</b><span>Każde polecenie wyjazdu ma limit; zobaczysz, jak bardzo je wykorzystano.</span></div>';
    $('#dok-kolka').innerHTML = ''; $('#podp-ile').textContent = '0'; $('#podp-ile-z').textContent = '–'; $('#lim-pol').textContent = `limit polecenia ${fmt(LIMIT_POL)} zł`;
    return;
  }
  box.style.gridTemplateColumns = `repeat(${n},minmax(0,1fr)) minmax(0,1.15fr)`;
  const h = M.polecenia.map((p, i) => {
    const u = p.kw / LIMIT_POL, pr = Math.round(u * 100);
    return `<div class="fiolka${u >= .85 ? ' blisko' : ''}" data-pol="${p.nr}" data-dok="${i}" style="--p:${Math.min(1, u).toFixed(4)};--s:${i}" aria-label="Polecenie ${p.nr}, ${dwa(p.od)}–${dwa(p.do)}.${dwa(M.mies)}: ${fmt(p.kw)} zł, ${pr} % limitu ${fmt(LIMIT_POL)} zł">` +
      `<div class="f-rurka"><span class="f-limit" aria-hidden="true"></span><span class="f-ciecz" aria-hidden="true"></span>` +
      `<span class="f-pieczec" data-dok="${i}" role="img" aria-label="Polecenie ${p.nr}: niepodpisane">${ik('i-ok')}</span></div>` +
      `<p class="f-op num" aria-hidden="true"><b>P${p.nr}<em>${pr}&nbsp;%</em></b><span>${fmt(p.kw)}</span><small>${dwa(p.od)}–${dwa(p.do)}.${dwa(M.mies)}</small></p></div>`;
  }).join('');
  const r = `<div class="fiolka rozl" data-dok="${n}" style="--p:1;--s:${n}" aria-label="Rozliczenie: ${fmt(M.suma)} zł, ${n} poleceń">` +
    `<div class="f-rurka"><span class="f-ciecz" aria-hidden="true"></span><span class="f-pieczec" data-dok="${n}" role="img" aria-label="Rozliczenie: niepodpisane">${ik('i-ok')}</span></div>` +
    `<p class="f-op num" aria-hidden="true"><b>R</b><span>${fmt(M.suma).replace(' ', NBSP)}</span><small>${n} ${n === 1 ? 'polecenie' : n < 5 ? 'polecenia' : 'poleceń'}</small></p></div>`;
  box.innerHTML = h + r;
  $('#dok-kolka').innerHTML = Array.from({ length: n + 1 }, () => '<i></i>').join('');
  $('#podp-ile-z').textContent = String(n + 1);
  $('#lim-pol').textContent = `limit polecenia ${fmt(LIMIT_POL)} zł`;
  odswiezPodpisy();
}
function odswiezPodpisy() {
  if (!M) return;
  const razem = razemDok();
  $$('.f-pieczec').forEach(st => {
    const i = Number(st.dataset.dok), ok = !!M.podpisane[i];
    st.classList.toggle('ok', ok);
    st.setAttribute('aria-label', (i < M.polecenia.length ? `Polecenie ${i + 1}` : 'Rozliczenie') + (ok ? ': podpisane' : ': niepodpisane'));
  });
  $$('.fiolka').forEach(f => f.classList.toggle('podp-ok', !!M.podpisane[Number(f.dataset.dok)]));
  $$('#dok-kolka i').forEach((k, i) => k.classList.toggle('ok', !!M.podpisane[i]));
  $('#podp-ile').textContent = String(ilePodpisanych());
  const k3 = $('#k3-ile'); if (k3) k3.textContent = `${ilePodpisanych()} z ${razem}`;
  btn.style.setProperty('--pk', String(razem ? ilePodpisanych() / razem * 100 : 0));
}
function podswietlPolecenie(nr, on, tylkoKurtyna) {
  $$('#siatka .swiec, .fiolka.swiec, #ku-pol .swiec').forEach(c => c.classList.remove('swiec'));
  if (!on || !nr || !M) return;
  const p = M.polecenia.find(x => x.nr === nr); if (!p) return;
  const s = $(`#ku-pol [data-pol="${nr}"]`); s && s.classList.add('swiec');
  const w = $(`.fiolka[data-pol="${nr}"]`); w && w.classList.add('swiec');
  if (!tylkoKurtyna) $$('#siatka .dz.trasa').forEach(c => { const d = Number(c.dataset.d); if (d >= p.od && d <= p.do) c.classList.add('swiec'); });
}

/* ====================== kontrola, termin, bohater ====================== */
function kontrola() {
  if (!M || M.stan !== 'gotowe') return null;
  const w = M.wynik, dni = M.dniT.map(d => M.trasy[d]);
  const zam = Number(M.kwota || 0);
  return [
    { t: 'Suma dni = kwota', ok: !w.niepelna && Math.abs(M.suma - zam) < 0.005 },
    { t: `Dzień ≤ ${fmt(LIMIT_DZIEN)} zł`, ik: 'i-le', ok: dni.every(d => d.suma <= LIMIT_DZIEN + 0.005) },
    { t: `Polecenie ≤ ${fmt(LIMIT_POL)} zł`, ik: 'i-le', ok: M.polecenia.every(p => p.kw <= LIMIT_POL + 0.005) },
    { t: 'Bez tras w dniach wolnych', ok: M.dniT.every(d => !M.wolne.has(d)) },
    { t: 'Bez tras w niedziele i święta', ok: M.dniT.every(d => M.robocze0.has(d)) },
  ];
}
function odswiezKontrole() {
  const lista = $('#ko-lista'), pier = $('#ko-luk'), licz = $('#ko-licz'), pod = $('#ko-podtyt');
  const k = kontrola();
  if (!k) { lista.innerHTML = '<li style="grid-column:1/-1">Po wygenerowaniu sprawdzę limity i dni wolne</li>'; pier.style.strokeDasharray = '0 100'; licz.textContent = '–'; pod.textContent = ''; return; }
  const dobre = k.filter(x => x.ok).length;
  lista.innerHTML = k.map(x => {
    const t = x.t.replace(/≤/, '<svg class="zn" aria-label="nie więcej niż" role="img"><use href="#i-le"/></svg>').replace(' zł', NBSP + 'zł');
    return `<li${x.ok ? '' : ' style="color:var(--a-blad)"'}>${ik(x.ok ? 'i-ok' : 'i-zamknij')}${t}</li>`;
  }).join('');
  pier.style.strokeDasharray = `${dobre / k.length * 100} 100`;
  licz.textContent = `${dobre}/${k.length}`;
  pod.textContent = dobre === k.length ? `${k.length} z ${k.length} w porządku` : `${dobre} z ${k.length} w porządku`;
}
/** Termin wysyłki: 10. dzień następnego miesiąca (jak w programie: „do 10.10" dla września). */
function terminMiesiaca() { return new Date(M.mies === 12 ? M.rok + 1 : M.rok, M.mies === 12 ? 0 : M.mies, 10, 12); }
function odswiezTermin() {
  if (!M) return;
  const t = terminMiesiaca(), dzis = new Date(); dzis.setHours(12, 0, 0, 0);
  const dni = Math.round((t - dzis) / 86400000), dt = `${DN[(t.getDay() + 6) % 7]} ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}.${t.getFullYear()}`;
  const gdy = dni > 1 ? `za ${dni} dni` : dni === 1 ? 'jutro' : dni === 0 ? 'dziś' : `${-dni} ${-dni === 1 ? 'dzień' : 'dni'} po terminie`;
  $('#t-op').innerHTML = `<b>${gdy}</b><span>termin wysyłki · ${dt}</span>`;
  $('#t-tel').innerHTML = `<b>${gdy}</b><span>${DK[(t.getDay() + 6) % 7]}. ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}</span>`;
  const chipy = [];
  for (let i = Math.min(3, Math.max(0, dni)); i >= 0; i--) { const x = new Date(t); x.setDate(x.getDate() - i); chipy.push({ x, cel: i === 0, dzis: i === dni }); }
  $('#t-dni').innerHTML = chipy.map(c => `<li class="${c.cel ? 'cel' : ''}${c.dzis ? ' dzis' : ''}">${DK[(c.x.getDay() + 6) % 7]}<b>${dwa(c.x.getDate())}</b></li>`).join('');
  const luk = $('#t-luk'), dobre = Math.max(0, Math.min(7, dni));
  luk.setAttribute('stroke-dasharray', `${dobre} 7`); $('#t-pier').textContent = String(Math.max(0, dni));
}
const tekstSilnika = () => M && M.silnik ? 'powyżej 900 cm³' : 'poniżej 900 cm³';
function odswiezHero() {
  const kA = $('#kA'); if (!M) return;
  const gotowe = M.stan === 'gotowe';
  kA.classList.toggle('przed', !gotowe); kA.classList.toggle('po-gen', gotowe);
  const mn = `${MIES[M.mies - 1]} ${M.rok}`;
  $('#b-etyk').textContent = gotowe ? `Do zwrotu · ${mn}` : `Kwota do rozliczenia · ${mn}`;
  $('#m-nazwa').textContent = cap(mn);
  const kmRazem = M.dniT.reduce((a, d) => a + M.trasy[d].km, 0), wizytRazem = M.dniT.reduce((a, d) => a + M.trasy[d].etapy.length - 1, 0);
  if (gotowe) {
    $('#b-kwota-w').setAttribute('aria-label', `${fmt(M.suma)} zł`);
    przygotujCyfry($('#kwota'), fmt(M.suma).replace(/ /g, NBSP));
    $('#b-wzor').innerHTML = `<b>${fmt(kmRazem, 1).replace(' ', NBSP)} km</b> × <b>${fmt(M.stawka)} zł/km</b><span class="znaczek">auto ${tekstSilnika()}</span>`;
    $('#b-staty').innerHTML = `<li><b>${M.dniT.length}</b>${M.dniT.length === 1 ? 'dzień' : 'dni'} z trasą</li><li><b>${wizytRazem}</b>${wizyt(wizytRazem)}</li>`;
    $('#ku-st').innerHTML = `<b>${M.dniT.length}</b>${M.dniT.length === 1 ? 'dzień' : 'dni'} z trasą · <b>${wizytRazem}</b>${wizyt(wizytRazem)}`;
    $('#ku-limit').textContent = `limit dnia ${fmt(LIMIT_DZIEN)} zł`;
  }
  const wolneTxt = [...M.wolne].sort((a, b) => a - b);
  $('#k1-op').innerHTML = `<span>${tekstSilnika()}</span><span>${M.tryb === 'wieczory' ? 'Wieczory 16:30–22:00 · sb' : 'Tydzień, dni robocze'}</span>` + (wolneTxt.length ? `<span>wolne: ${wolneTxt.join(', ')}.${dwa(M.mies)}</span>` : '');
  $('#k2-op').innerHTML = gotowe ? `<span>${M.polecenia.length} ${M.polecenia.length === 1 ? 'polecenie' : M.polecenia.length < 5 ? 'polecenia' : 'poleceń'}</span><span>${M.dniT.length} ${M.dniT.length === 1 ? 'dzień' : 'dni'} z trasą</span><span>${wizytRazem} ${wizyt(wizytRazem)}</span>` : '<span>do wygenerowania</span>';
  const razem = razemDok(), t = terminMiesiaca();
  $('#k3-op').innerHTML = gotowe ? `<span><b id="k3-ile">${ilePodpisanych()} z ${razem}</b> dokumentów · Profil Zaufany</span>` : '<span>Profil Zaufany</span>';
  $('#k4-op').innerHTML = `<span>Kierownik regionu · do ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}</span>`;
  const e = etapMiesiaca(), nr = { ustaw: 1, podpisz: 3, wyslij: 4, wyslane: 5 }[e];
  [1, 2, 3, 4].forEach(i => {
    const kr = $('#krok' + i), zrob = i < nr || e === 'wyslane';
    kr.className = 'krok' + (zrob ? ' zrobiony' : i === nr ? ' aktywny' : '');
    $('.wezel', kr).innerHTML = zrob ? ik('i-ok') : String(i);
    kr.style.setProperty('--k', String(i - 1));
  });
  const nap = { ustaw: ['Generuj dokumenty', 'i-pioro'], podpisz: [`Podpisz ${razem} ${razem === 1 ? 'dokument' : razem < 5 ? 'dokumenty' : 'dokumentów'}`, 'i-pioro'], wyslij: ['Wyślij do Kierownika regionu', 'i-nawi'], wyslane: ['Wysłano do Kierownika regionu', 'i-ok'] }[e];
  napis.textContent = nap[0]; $('.kropla-tresc use', btn).setAttribute('href', '#' + nap[1]);
  btn.classList.toggle('wyslij', e === 'wyslij'); btn.classList.toggle('gotowe', e === 'wyslane');
  $('#kA').classList.toggle('po', e === 'wyslij' || e === 'wyslane');
  ustawStatus({ ustaw: 'Do wygenerowania', podpisz: 'Wygenerowane', wyslij: 'Podpisane', wyslane: 'Wysłane' }[e], e === 'wyslij' || e === 'wyslane');
  odswiezTermin();
  const stat = $('#kropla-napis'); if (stat) btn.setAttribute('aria-label', nap[0]);
}
function odswiezWszystko(opcje = {}) {
  tytulKalendarza(); budujKalendarz(); budujKurtyneDOM(); budujFiolki(); rysujDzien(!!opcje.start); odswiezKontrole(); odswiezHero(); rysujDzis();
  odswiezParametry(); odswiezPowiadomienia();
  kurtyna && kurtyna.dane && kurtyna.dane();
  zaznaczKomorke();
  requestAnimationFrame(() => { kurtyna && kurtyna.rozmiar(); mierz(); ustawSwiatlo(); szkla.forEach(budujSoczewke); skalaMapki(); });
}
