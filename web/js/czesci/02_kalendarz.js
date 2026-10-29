/* ====================== kalendarz miesiąca ====================== */
function budujKalendarz() {
  const siatka = $('#siatka'); if (!M) { siatka.innerHTML = ''; return; }
  const off = dzienTyg(1), N = M.N, plan = M.stan === 'plan';
  siatka.style.setProperty('--wiersze', Math.ceil((off + N) / 7));
  let h = '';
  for (let i = 0; i < off; i++) h += '<div class="dz pusty" aria-hidden="true"></div>';
  const nazwaM = MIES_D[M.mies - 1];
  for (let d = 1, k = 0; d <= N; d++, k++) {
    const t = typDnia(d), wd = dzienTyg(d), tr = M.trasy[d];
    if (t === 'trasa') {
      /* poziom cieczy = kwota dnia / limit dnia */
      h += `<button type="button" class="dz trasa" data-d="${d}" style="--poziom:${Math.min(1, tr.suma / LIMIT_DZIEN).toFixed(3)};--k:${k}" aria-pressed="false" aria-label="${DN[wd]} ${d} ${nazwaM}: ${fmt(tr.km, 1)} km, ${fmt(tr.suma)} zł, ${Math.round(tr.suma / LIMIT_DZIEN * 100)} % limitu dnia">` +
        `<span class="pl-w" aria-hidden="true"><span class="pl"></span></span><span class="nr">${d}</span><span class="dane num"><span class="km">${fmt(tr.km, 1)} km</span><span class="zl">${fmt(tr.suma)}</span></span></button>`;
    } else if (t === 'urlop') {
      if (plan) {
        h += `<button type="button" class="dz urlop" data-d="${d}" aria-pressed="true" aria-label="${DN[wd]} ${d} ${nazwaM}: wolne — kliknij, aby przywrócić"><span class="nr">${d}</span><span class="etyk">wolne</span></button>`;
      } else {
        let r = 1; while (M.wolne.has(d + r) && d + r <= N && dzienTyg(d + r) !== 0) r++;
        h += `<div class="urlop-pas" role="img" aria-label="${d}–${d + r - 1} ${nazwaM}: bez pracy" style="--k:${k};grid-column:span ${r}"><span class="u-dni" style="grid-template-columns:repeat(${r},minmax(0,1fr))" aria-hidden="true">${Array.from({ length: r }, (_, i) => `<span>${d + i}</span>`).join('')}</span>` +
          (r >= 3 ? `<span class="u-et" aria-hidden="true">bez pracy · ${d}–${d + r - 1}.${dwaCyfry(M.mies)}</span>` : '') + `</div>`;
        d += r - 1; k += r - 1;
      }
    } else if (t === 'nd') {
      h += `<div class="dz nd" data-d="${d}"><span class="nr">${d}</span></div>`;
    } else if (plan) {
      h += `<button type="button" class="dz bez przelacz" data-d="${d}" aria-pressed="false" aria-label="${DN[wd]} ${d} ${nazwaM}: dzień roboczy — kliknij, aby oznaczyć jako wolny"><span class="nr">${d}</span><span class="etyk">roboczy</span></button>`;
    } else {
      h += `<div class="dz bez" data-d="${d}" aria-label="${DN[wd]} ${d} ${nazwaM}: dzień pracy bez wyjazdu"><span class="nr">${d}</span><span class="etyk">bez trasy</span></div>`;
    }
  }
  siatka.innerHTML = h;
  const pozaMiesiacem = (7 - (off + N) % 7) % 7;
  for (let i = 0; i < pozaMiesiacem; i++) siatka.insertAdjacentHTML('beforeend', '<div class="dz pusty" aria-hidden="true"></div>');
  zaznaczKomorke();
}
function zaznaczKomorke() {
  $$('#siatka .dz.trasa').forEach(b => {
    const on = Number(b.dataset.d) === wybrany;
    b.classList.toggle('wybrany', on); b.setAttribute('aria-pressed', String(on));
    const p = $('.pierscien', b);
    if (on && !p) b.insertAdjacentHTML('beforeend', '<span class="pierscien" aria-hidden="true"></span>');
    if (!on && p) p.remove();
  });
  $$('#ku-os span[data-d]').forEach(s => s.classList.toggle('wyb', Number(s.dataset.d) === wybrany));
}
function tytulKalendarza() {
  const el = $('#c-tyt'); if (!M) return;
  el.innerHTML = `${cap(MIES[M.mies - 1])} <span>${M.stan === 'gotowe' ? '· ' + M.dniT.length + ' ' + (M.dniT.length === 1 ? 'dzień' : 'dni') + ' z trasą' : '· ' + M.robocze.size + ' dni roboczych'}</span>`;
}

/* ====================== kurtyna miesiąca (WebGL, promienie danych) ====================== */
function budujKurtyneDOM() {
  if (!M || M.stan !== 'gotowe') { $('#ku-os').innerHTML = ''; $('#ku-pol').innerHTML = ''; $('#ku-zapas').innerHTML = ''; return; }
  const N = M.N, pc = d => ((d - .5) / N * 100).toFixed(2) + '%';
  const os = [...new Set([1, 5, 10, 15, 20, 25, N].filter(d => d <= N && (d === N || N - d >= 3 || d === 1)))];
  let h = os.map(d => `<span data-d="${d}" style="left:${pc(d)}">${d}</span>`).join('');
  /* pas „bez pracy" nad najdłuższym ciągiem dni wolnych (od 3 dni) */
  let najd = null, i = 1;
  while (i <= N) { if (M.wolne.has(i)) { let j = i; while (M.wolne.has(j + 1)) j++; if (j - i + 1 >= 3 && (!najd || j - i > najd[1] - najd[0])) najd = [i, j]; i = j + 1; } else i++; }
  if (najd) h += `<span class="urlop" style="left:${((najd[0] - 1) / N * 100).toFixed(2)}%;width:${((najd[1] - najd[0] + 1) / N * 100).toFixed(2)}%">bez pracy</span>`;
  $('#ku-os').innerHTML = h;
  $('#ku-pol').style.gridTemplateColumns = `repeat(${N},minmax(0,1fr))`;
  $('#ku-pol').innerHTML = M.polecenia.map(p => `<span data-pol="${p.nr}" style="grid-column:${p.od}/${p.do + 1}" title="Polecenie ${p.nr}: ${dwa(p.od)}–${dwa(p.do)}.${dwa(M.mies)}, ${fmt(p.kw)} zł"><b>P${p.nr}</b><span class="dl">${fmt(p.kw)}</span><span class="kr">${Math.round(p.kw / LIMIT_POL * 100)}&nbsp;%</span></span>`).join('');
  $('#ku-zapas').innerHTML = Array.from({ length: N }, (_, i) => { const d = i + 1; return `<i style="--h:${M.trasy[d] ? Math.min(1, M.trasy[d].suma / LIMIT_DZIEN).toFixed(3) : 0}"></i>`; }).join('');
  const pole = $('#ku-pole'); if (pole) pole.setAttribute('aria-label', `Kwoty dni miesiąca: najwyższa ${fmt(Math.max(...M.dniT.map(d => M.trasy[d].suma)))} zł, najniższa ${fmt(Math.min(...M.dniT.map(d => M.trasy[d].suma)))} zł`);
}
