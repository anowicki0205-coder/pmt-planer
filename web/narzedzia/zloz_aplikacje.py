#!/usr/bin/env python3
"""Składa js/aplikacja.js z makiety (zrodlo_makiety/skrypt_makiety.js — wygląd i ruch) i z js/czesci/ (dane z silnika).
Uruchomione raz; potem js/aplikacja.js edytujemy bezpośrednio. Zostawione jako zapis, skąd co pochodzi."""
import re, os
R = os.path.join(os.path.dirname(__file__), '..')
mk = open(os.path.join(R, 'zrodlo_makiety/skrypt_makiety.js'), encoding='utf-8').read().split('\n')
def L(a, b): return '\n'.join(mk[a - 1:b])           # linie makiety, 1-based, włącznie
def czesc(n): return open(os.path.join(R, 'js/czesci', n), encoding='utf-8').read()
def miedzy(tekst, od, do_=None, wlacznie_do=False):
    i = tekst.index(od); j = tekst.index(do_, i) if do_ else len(tekst)
    return tekst[i:j + (len(do_) if (do_ and wlacznie_do) else 0)]
mk_all = '\n'.join(mk)

# --- patche kurtyny (liczba dni z modelu zamiast stałych 30) ---
fs_i_kurtyna = L(198, 347)
def zam(s, a, b, ile=1):
    assert s.count(a) >= 1, 'brak: ' + a[:60]
    return s.replace(a, b) if ile == 0 else s.replace(a, b, ile)
k = fs_i_kurtyna
k = zam(k, 'uniform float uT,uS,uHv,uWz,uFl,uSw,uDzien,uB;', 'uniform float uT,uS,uHv,uWz,uFl,uSw,uDzien,uB,uN;')
k = zam(k, 'float colW=uR.x/30.;', 'float colW=uR.x/uN;')
k = zam(k, 'if(fi<0.||fi>29.)continue;', 'if(fi<0.||fi>uN-1.)continue;')
k = zam(k, "'uDzien', 'uB', 'uD',", "'uDzien', 'uB', 'uN', 'uD',")
# dane: tekstura wgrywana osobno (zmienia się z miesiącem)
a = k.index('    const dane = new Uint8Array(32 * 4);'); b = k.index('    gl.uniform1i(U.uD, 0);') + len('    gl.uniform1i(U.uD, 0);')
k = k[:a] + '''    tex = gl.createTexture(); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.uniform1i(U.uD, 0);
    wgrajDane();''' + k[b:]
k = zam(k, '  function init() {', '''  let tex = null;
  /* dane miesiąca do tekstury: wysokość promienia = kwota dnia / limit dnia; rodzaj: trasa / dzień bez trasy */
  function wgrajDane() {
    if (zgubiony || !prog || !tex) return;
    const N = M ? M.N : 30, dane = new Uint8Array(32 * 4);
    for (let d = 1; d <= N; d++) {
      const t = M ? typDnia(d) : 'nd', o = (d - 1) * 4;
      dane[o] = t === 'trasa' ? Math.round(Math.min(1, M.trasy[d].suma / LIMIT_DZIEN) * 255) : 0;
      dane[o + 1] = t === 'trasa' ? 255 : t === 'bez' ? 170 : 0; dane[o + 3] = 255;
    }
    gl.useProgram(prog); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 32, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, dane);
    gl.uniform1f(U.uN, N);
  }
  function init() {''')
k = zam(k, 'const dzienZ = e => { const r = pole.getBoundingClientRect(); return Math.min(30, Math.max(1, Math.floor((e.clientX - r.left) / r.width * 30) + 1)); };',
        'const dzienZ = e => { const r = pole.getBoundingClientRect(), N = M ? M.N : 30; return Math.min(N, Math.max(1, Math.floor((e.clientX - r.left) / r.width * N) + 1)); };')
k = zam(k, 'const h = t === \'trasa\' ? TRASY[d][1] / LIMIT_DZIEN : 0;', 'const h = t === \'trasa\' ? Math.min(1, M.trasy[d].suma / LIMIT_DZIEN) : 0;')
k = zam(k, "r.left + (d - .5) / 30 * r.width", "r.left + (d - .5) / M.N * r.width")
k = zam(k, "if (TRASY[d]) wybierzDzien(d);", "if (M && M.trasy[d]) wybierzDzien(d);")
k = zam(k, "tryb, kolory() { kolory(); rysuj(); },", "tryb, dane() { wgrajDane(); rysuj(); }, kolory() { kolory(); rysuj(); },")
for a_ in ('TRASY[', ' 30 ', '/ 30'):
    pass
assert 'TRASY' not in k, [m.start() for m in re.finditer('TRASY', k)]

sign_a = miedzy(mk_all, "const btn = $('#podpisz'), napis = $('#kropla-napis');", 'function ustawLicznik()')
sign_b = miedzy(mk_all, 'function lot(i, x0, y0, cel) {', 'function podpiszDok(i)')
sign_c = miedzy(mk_all, 'function ustawStatus(t, kl) {', 'async function podpisz()')
straz = miedzy(mk_all, '/* adaptacyjna jakość szkła', 'start();')

wyj = [czesc('00_naglowek.js'),
       "\n/* ====================== czas, pomocnicze ====================== */\n" + L(5, 52).replace("'pmt-final-'", "'pmt-ui-'"),
       czesc('01_model.js'),
       L(96, 156),
       czesc('02_kalendarz.js'),
       k,
       czesc('03_dzien.js'),
       czesc('04_widoki.js'),
       L(558, 960),
       "\n/* ====================== przycisk główny: kropla ciekłego szkła ====================== */\n" + sign_a + sign_b + sign_c,
       czesc('05_przeplyw.js'),
       L(1079, 1100),
       czesc('06_start.js'),
       straz,
       'start();']
src = '\n'.join(wyj)
src = src.replace("$('#kA').classList.toggle('po', e === 'wyslij' || e === 'wyslane');", "$('#kA').classList.toggle('po', e === 'wyslane');")
open(os.path.join(R, 'js/aplikacja.js'), 'w', encoding='utf-8').write(src)
print('js/aplikacja.js', len(src), 'znaków,', src.count('\n'), 'linii')
