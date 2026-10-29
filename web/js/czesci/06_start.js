/* ====================== powiadomienia (dzwonek) ====================== */
function odswiezPowiadomienia() {
  const box = $('#powiadomienia'), bad = $('#dzwonek b'); if (!M) return;
  const poz = [];
  if (!M.wyslane) {
    const t = terminMiesiaca(), dzis = new Date(); dzis.setHours(12, 0, 0, 0);
    const dni = Math.round((t - dzis) / 86400000);
    poz.push({ c: false, t: 'Termin podpisu i wysyłki', s: `${DN[(t.getDay() + 6) % 7]} ${dwa(t.getDate())}.${dwa(t.getMonth() + 1)}.${t.getFullYear()} · ${dni > 1 ? `za ${dni} dni` : dni === 1 ? 'jutro' : dni === 0 ? 'dziś' : 'po terminie'}` });
  }
  if (M.stan === 'gotowe') poz.push({ c: true, t: `Dokumenty za ${MIES[M.mies - 1]} gotowe`, s: `${M.polecenia.length} ${M.polecenia.length === 1 ? 'polecenie' : 'polecenia'} i rozliczenie · ${fmt(M.suma)} zł` });
  box.innerHTML = poz.length ? poz.map(p => `<div class="pow"><i class="${p.c ? 'c' : ''}"></i><div><b>${p.t}</b><span>${p.s}</span></div></div>`).join('') : '<div class="pow"><i class="c"></i><div><b>Wszystko załatwione</b><span>Nic nie czeka na Ciebie.</span></div></div>';
  if (poz.length) { if (bad) bad.textContent = String(poz.length); else $('#dzwonek').insertAdjacentHTML('beforeend', `<b>${poz.length}</b>`); } else if (bad) bad.remove();
  $('#dzwonek').setAttribute('aria-label', poz.length ? `Powiadomienia: ${poz.length}` : 'Powiadomienia');
}

/* ====================== zdarzenia ====================== */
function zdarzenia() {
  const siatka = $('#siatka');
  siatka.addEventListener('click', e => {
    const b = e.target.closest('button.dz'); if (!b) return;
    const d = Number(b.dataset.d);
    if (b.classList.contains('trasa')) wybierzDzien(d); else przelaczWolne(d);
  });
  siatka.addEventListener('pointerover', e => {
    const c = e.target.closest('.dz.trasa, .dz.bez, .dz.urlop');
    if (!c || !M) { ukryjPodp(); podswietlPolecenie(0, false); return; }
    const d = Number(c.dataset.d), r = c.getBoundingClientRect();
    pokazPodp(opisDnia(d), r.left + r.width / 2, r.top - 2);
    const p = polDla(d); if (c.classList.contains('trasa') && p) podswietlPolecenie(p.nr, true, true);
  });
  siatka.addEventListener('pointerleave', () => { ukryjPodp(); podswietlPolecenie(0, false); });
  siatka.addEventListener('focusin', e => { const c = e.target.closest('.dz.trasa'); if (c) { const r = c.getBoundingClientRect(); pokazPodp(opisDnia(Number(c.dataset.d)), r.left + r.width / 2, r.top - 2); } });
  siatka.addEventListener('focusout', ukryjPodp);
  $('#fiolki').addEventListener('pointerover', e => { const w = e.target.closest('.fiolka[data-pol]'); if (w) podswietlPolecenie(Number(w.dataset.pol), true); else podswietlPolecenie(0, false); });
  $('#fiolki').addEventListener('pointerleave', () => podswietlPolecenie(0, false));
  $('#fiolki').addEventListener('click', e => { if (M && M.stan === 'gotowe' && e.target.closest('.fiolka')) arkuszPodpis(); });
  $('#ku-pol').addEventListener('pointerover', e => { const s = e.target.closest('[data-pol]'); if (s) podswietlPolecenie(Number(s.dataset.pol), true); });
  $('#ku-pol').addEventListener('pointerleave', () => podswietlPolecenie(0, false));
  $('#e-wstecz').addEventListener('click', () => { const i = M.dniT.indexOf(wybrany); if (i > 0) wybierzDzien(M.dniT[i - 1], -1); });
  $('#e-dalej').addEventListener('click', () => { const i = M.dniT.indexOf(wybrany); if (i < M.dniT.length - 1) wybierzDzien(M.dniT[i + 1], 1); });
  $$('.rozwin').forEach(b => { b.dataset.etykieta = b.getAttribute('aria-label'); b.setAttribute('aria-expanded', 'false'); b.addEventListener('click', e => { e.stopPropagation(); const k = b.closest('.kafel'); skupienie(k === skupiony ? null : k); }); });
  bento.addEventListener('click', e => { if (skupiony && !skupiony.contains(e.target)) skupienie(null); });
  btn.addEventListener('click', klikGlowny);
  $('#cofnij').addEventListener('click', cofnijWyslanie);
  $('#parametry').addEventListener('click', e => {
    const t = e.target.closest('[data-tryb]'); if (t) { przelaczTryb(t.dataset.tryb); return; }
    const s = e.target.closest('[data-silnik]'); if (s && M.stan === 'plan') { M.silnik = s.dataset.silnik === '1'; if (PROFIL) { PROFIL.silnik_powyzej_900 = M.silnik; magProfil.zapisz(PROFIL); odswiezProfilWNaglowku(); } odswiezParametry(); }
  });
  let tK = 0;
  const wej = $('#kwota-in');
  wej.addEventListener('input', () => { M.kwota = parsujKwote(wej.value); clearTimeout(tK); tK = setTimeout(odswiezParametry, 250); });
  wej.addEventListener('blur', () => { M.kwota = parsujKwote(wej.value); wej.value = M.kwota ? fmt(M.kwota).replace(/ /g, '') : ''; magUst.ustaw('kwota-' + magMiesiace.klucz(M.rok, M.mies), M.kwota); odswiezParametry(); });
  wej.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); wej.blur(); } });
  $('#przystanki').addEventListener('scroll', sprawdzListe, { passive: true });
  $('#przystanki').addEventListener('click', e => {
    const nav = e.target.closest('.nawiguj');
    if (nav) { const i = Number(nav.dataset.i), on = nawigacja !== i; nawigacja = on ? i : -1; nav.classList.toggle('prowadzi', on); nav.setAttribute('aria-pressed', String(on)); $('span', nav).textContent = on ? 'Prowadzę' : 'Nawiguj'; if (on) zorza && zorza.flara(.18); return; }
    const b = e.target.closest('.p-znak'); if (!b) return;
    const i = Number(b.dataset.i); PLAN_DZIS[i].ok = !PLAN_DZIS[i].ok;
    przejscie(rysujDzis, () => { const nb = $(`.p-znak[data-i="${i}"]`); nb && nb.focus({ preventScroll: true }); }, 'dzis');
    if (PLAN_DZIS[i].ok) zorza && zorza.flara(.2);
  });
  for (const [b, d] of dymki) {
    b.addEventListener('click', e => {
      e.stopPropagation(); const o = !d.classList.contains('otwarty'); zamknijDymki(d);
      d.classList.toggle('otwarty', o); b.setAttribute('aria-expanded', String(o));
    });
  }
  doc.addEventListener('click', e => { if (!e.target.closest('.dymek')) zamknijDymki(null); });
  $('#moje-dane').addEventListener('click', () => { zamknijDymki(null); otworzMojeDane(false); });
  $$('.przel button').forEach(b => b.addEventListener('click', () => { ustawMotyw(b.dataset.motyw, b); zegar(700).then(() => zamknijDymki(null)); }));
  $('#motyw').addEventListener('click', e => ustawMotyw(motywTeraz() === 'light' ? 'dark' : 'light', e.currentTarget));
  const zmienMiesiac = k => { let r = M.rok, m = M.mies + k; if (m < 1) { m = 12; r--; } if (m > 12) { m = 1; r++; } przeladujMiesiac(r, m); };
  $('#m-wstecz').addEventListener('click', () => zmienMiesiac(-1));
  $('#m-dalej').addEventListener('click', () => zmienMiesiac(1));
  $('#termin').addEventListener('pointerenter', () => { ustawCelCiepla(); zorza && zorza.cieplo(1); });
  $$('.zakladka').forEach(b => b.addEventListener('click', () => ustawZakladke(b.dataset.tab)));
  $('#zakladki').addEventListener('keydown', e => {
    const z = $$('.zakladka'), i = z.indexOf(doc.activeElement); if (i < 0) return;
    const j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: z.length - 1 }[e.key]; if (j === undefined) return;
    e.preventDefault(); const c = z[(j + z.length) % z.length]; c.focus(); ustawZakladke(c.dataset.tab);
  });
  try { JASNY.addEventListener('change', () => { if (!root.dataset.theme) poMotywie(); }); } catch (e) {}
  try { RM.addEventListener('change', e => { spokoj = e.matches; zorza && zorza.tryb(); kurtyna && kurtyna.tryb(); }); } catch (e) {}
  addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if (arkuszOtwarty) { zamknijArkusz(); return; }
    for (const [b, d] of dymki) if (d.classList.contains('otwarty')) { zamknijDymki(null); b.focus(); return; }
    if (skupiony) { const k = skupiony; skupienie(null); const b = $('.rozwin', k); b && b.focus({ preventScroll: true }); }
  });
  let rt = 0;
  addEventListener('resize', () => {
    clearTimeout(rt);
    rt = setTimeout(() => { zorza && zorza.rozmiar(); kurtyna && kurtyna.rozmiar(); rysujGwiazdy(); rysujHoryzont(); domyslne(); mierz(); ustawCelCiepla(); budz(); sprawdzListe(); }, 120);
  });
}

/* ====================== start ====================== */
const pierwszaKlatka = () => new Promise(res => {
  let gotowe = false; const ok = () => { if (!gotowe) { gotowe = true; res(); } };
  requestAnimationFrame(() => requestAnimationFrame(ok)); setTimeout(ok, 1200);
});
function ladowanie(widoczne, tekst, p) {
  const l = $('#ladowanie'); l.classList.toggle('widoczny', widoczne);
  if (tekst) $('#lad-tekst').textContent = tekst;
  if (p != null) $('#lad-pasek').style.setProperty('--p', Math.round(p * 100) + '%');
}
async function start() {
  app.classList.add('czeka');
  ladowanie(true, 'Uruchamianie…', .03);
  PROFIL = magProfil.wczytaj();
  try {
    await silnik.start((t, v) => ladowanie(true, t, v));
    const st = await silnik.stale(); LIMIT_DZIEN = st.limit_dnia; LIMIT_POL = st.limit_dokumentu; MIN_KWOTA = st.min_kwota;
  } catch (e) {
    $('#lad-tekst').innerHTML = `Nie udało się uruchomić silnika delegacji.<br><small>${bezZnacznikow(e.message)}</small><br><br><button class="przycisk" type="button" onclick="location.reload()">Spróbuj ponownie</button>`;
    return;
  }
  /* start na miesiącu, który minął (jak w programie): w październiku — wrzesień */
  const dzis = new Date(); let r = dzis.getFullYear(), m = dzis.getMonth(); if (m === 0) { r--; m = 12; }
  const ost = magUst.daj('ostatni-miesiac', null);
  if (ost) { r = ost.rok; m = ost.mies; }
  await przeladujMiesiac(r, m, true);
  const zak = pamiec.get('zakladka');
  if (zak && ['dzis', 'miesiac', 'dokumenty'].includes(zak)) ustawZakladke(zak, false);
  odswiezProfilWNaglowku();
  rysujGwiazdy(); rysujHoryzont();
  zorza = startZorza();
  kurtyna = startKurtyna();
  szkla.forEach(el => { ro && ro.observe(el); });
  mierz(); ustawSwiatlo(); poMotywieUI();
  zdarzenia();
  kurtyna && kurtyna.dane && kurtyna.dane();
  ladowanie(false);
  await pierwszaKlatka();
  app.classList.remove('czeka');
  zorza && zorza.restart(); kurtyna && kurtyna.restart();
  if (czyChromium) { root.classList.add('soczewka'); szkla.forEach(budujSoczewke); }
  if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(() => { mierz(); ustawSwiatlo(); sprawdzListe(); kurtyna && kurtyna.rozmiar(); }).catch(() => {});
  await zegar(700);
  let licznikiGotowe = false;
  $$('[data-licz]').forEach(el => { const cel = Number(el.dataset.licz); tween(1300, p => { if (!licznikiGotowe) el.textContent = String(Math.round(cel * p)); }); });
  zegar(2700).then(() => { licznikiGotowe = true; $$('[data-licz]').forEach(el => { el.textContent = el.dataset.licz; }); });
  await zegar(1500);
  ustawCelCiepla();
  zorza && zorza.cieplo(.55);
  await zegar(2000);
  app.classList.remove('wejscie');
  mierz(); ustawSwiatlo();
  strazKlatek();
  if (!PROFIL) otworzMojeDane(true);
}
