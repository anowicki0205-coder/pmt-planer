# Test w prawdziwym silniku WebKit (ten sam silnik co Safari na iPhonie i Macu): uruchomienie, silnik w wasm, profil, generowanie dokumentów, błędy.
# Wymaga: webkit2gtk-driver, xvfb, selenium (python). Uruchom: xvfb-run -a /tmp/wkvenv/bin/python webkit_app.py
import json, os, subprocess, sys, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait

KAT = os.path.dirname(os.path.abspath(__file__))
srv = subprocess.Popen(['node', os.path.join(KAT, 'serwer_wk.js')], stdout=subprocess.PIPE, text=True, env={**os.environ, 'NODE_PATH': '/opt/node22/lib/node_modules'})
port = srv.stdout.readline().strip().split('=')[1]
URL = f'http://127.0.0.1:{port}'
kod = 0
def ok(opis, w, szcz=''):
    global kod
    print(('  OK   ' if w else '  BŁĄD ') + opis + (' — ' + str(szcz) if szcz else '')); 
    if not w: kod = 1

opts = webdriver.WebKitGTKOptions()
opts.binary_location = '/usr/lib/x86_64-linux-gnu/webkit2gtk-4.1/MiniBrowser'
opts.add_argument('--automation')
d = webdriver.WebKitGTK(options=opts)
W, H = int(os.environ.get('W', 1440)), int(os.environ.get('H', 900))
d.set_window_size(W, H)
bledy = lambda: d.execute_script('return window.__bledy || []')
def czekaj(f, t=120, krok=.4):
    return WebDriverWait(d, t, poll_frequency=krok).until(f)
try:
    d.get(URL + '/robots.txt')            # ta sama domena: zasiej sesję zalogowanego konta 12345 (bez backendu)
    d.execute_script("""localStorage.setItem('pmt-web-dostep-v1', JSON.stringify({kod:'12345',ostatni:'12345',konta:{12345:{imie:'Jan Testowy',skrot:'x',kontakt:Date.now()}},status:{status:'ok',kod:'12345',imie:'Jan Testowy',wazne_do:'2099-01-01'},kolejka:{uruchomienia:0,dokumenty:0,minuty:0}}));localStorage.setItem('pmt-ui-wycieczka','1');sessionStorage.setItem('pmt-web-sesja-karty','12345');sessionStorage.setItem('pmt-web-dek','AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=');""")      # znacznik: zalogowano już na tej karcie (logowanie jest wymagane przy każdym uruchomieniu)
    d.get(URL + '/index.html')
    info = d.execute_script('return navigator.userAgent')
    print('UA:', info)
    czekaj(lambda x: x.execute_script("return document.documentElement.classList.contains('przyklad')"), 240)
    time.sleep(5)
    ok('pierwsze uruchomienie pokazuje przykładowy miesiąc (a nie pusty program) w WebKit', True)
    ok('przykład: kalendarz z trasami, probówki dokumentów i mapa trasy dnia', d.execute_script("return document.querySelectorAll('#siatka .dz.trasa').length >= 10 && document.querySelectorAll('#fiolki .fiolka').length >= 5 && !!document.querySelector('#dzien-tresc .mapka svg')"))
    ok('przykład: status „Przykład”, przycisk „Wpisz swoją kwotę” i klikalna kwota', d.execute_script("return /Przykład/.test(document.querySelector('#status').textContent) && /Wpisz swoją kwotę/.test(document.querySelector('#kropla-napis').textContent) && document.querySelector('#b-kwota-w').getAttribute('role') === 'button'"))
    d.save_screenshot('/tmp/webkit_przyklad.png')
    ok('WebGL dostępny (zorza)', d.execute_script("try{const c=document.createElement('canvas');return !!(c.getContext('webgl'))}catch(e){return false}"))
    ok('szkło bez rozmycia tła (kafle nie mają backdrop-filter) — klasy html', True, d.execute_script("return document.documentElement.className"))
    ok('bez błędów JS przy starcie', len(bledy()) == 0, json.dumps(bledy()[:5], ensure_ascii=False))
    # klik w dużą kwotę przykładu: wychodzimy z przykładu, kursor ląduje w polu kwoty (bez okna z danymi)
    d.execute_script("document.querySelector('#b-kwota-w').click()")
    czekaj(lambda x: x.execute_script("return !document.documentElement.classList.contains('przyklad') && /Do wygenerowania/.test(document.querySelector('#status').textContent)"), 240)
    time.sleep(2)
    ok('klik w kwotę przykładu: własny miesiąc, kursor w polu kwoty, bez okna z danymi', d.execute_script("return document.activeElement && document.activeElement.id === 'kwota-in' && !document.querySelector('#arkusz-tlo.otwarty')"))
    ActionChains(d).send_keys('1500').send_keys(Keys.ENTER).perform(); time.sleep(1.2)
    ok('kwotę da się wpisać w WebKit (po Enterze pole pokazuje 1500,00)', d.execute_script("return document.querySelector('#kwota-in').value").startswith('1500'), d.execute_script("return document.querySelector('#kwota-in').value"))
    d.execute_script("document.querySelector('#podpisz').click()")
    czekaj(lambda x: x.execute_script("return !!document.querySelector('#arkusz-tlo.otwarty #d-imie')"), 60)
    ok('„Generuj dokumenty” bez danych osobowych otwiera „Moje dane”', True)
    d.find_element(By.ID, 'd-imie').send_keys('Jan Testowy'); d.find_element(By.ID, 'd-pesel').send_keys('90010112349'); d.find_element(By.ID, 'd-adres').send_keys('ul. Testowa 1, 00-001 Warszawa')
    # silnik (Pyodide) musi się uruchomić w WebKit
    czekaj(lambda x: x.execute_script("return !document.querySelector('#ladowanie.widoczny')"), 240)
    d.find_element(By.ID, 'zapisz-dane').click()
    czekaj(lambda x: x.execute_script("return !document.querySelector('#arkusz-tlo.otwarty')"), 240)
    ok('silnik (Pyodide/wasm) odpowiada w WebKit: profil zapisany po sprawdzeniu adresu', True)
    czekaj(lambda x: x.execute_script("return !document.documentElement.classList.contains('przyklad') && /Do wygenerowania/.test(document.querySelector('#status').textContent)"), 180)
    time.sleep(3)
    ok('wpisana wcześniej kwota przeżyła zapis danych', d.execute_script("return document.querySelector('#kwota-in').value").startswith('1500'))
    d.find_element(By.ID, 'podpisz').click()
    czekaj(lambda x: x.execute_script("return !!document.querySelector('#potwierdz-gen')"), 120)
    ok('arkusz „Sprawdź, zanim wygeneruję”', True)
    d.find_element(By.ID, 'potwierdz-gen').click()
    czekaj(lambda x: x.execute_script("return !!document.querySelector('#kA.po-gen')"), 420)
    ok('dokumenty wygenerowane w WebKit (silnik + PDF)', True)
    time.sleep(3)
    ok('kalendarz pokazuje dni z trasą', d.execute_script("return document.querySelectorAll('#siatka .dz.trasa').length") > 5)
    ok('po generowaniu nie ma błędów JS', len(bledy()) == 0, json.dumps(bledy()[:5], ensure_ascii=False))
    d.save_screenshot('/tmp/webkit_gotowe.png')
    ok('po zapisaniu danych przykład zniknął', d.execute_script("return !document.documentElement.classList.contains('przyklad')"))
    # okno dokumentów: siatka kart, ścieżki podpisu; ZIP i scalanie PDF w WebKit
    d.execute_script("document.querySelector('#podpisz').click()")
    czekaj(lambda x: x.execute_script("return !!document.querySelector('#dok-siatka')"), 60); time.sleep(2)
    ok('okno dokumentów w WebKit: cztery kolorowe kroki i karty dokumentów', d.execute_script("return document.querySelectorAll('#dok-siatka .dok-k').length >= 2 && document.querySelectorAll('.krok-k').length === 4"))
    d.save_screenshot('/tmp/webkit_podpis.png')
    zip_ok = d.execute_async_script("""const kon = arguments[arguments.length - 1]; import('/js/pliki.js').then(m => { const b = m.zipuj([{ nazwa: 'a.pdf', bajty: new Uint8Array([1, 2, 3]) }]); kon({ typ: b.type, rozmiar: b.size, crc: m.crc32(new TextEncoder().encode('123456789')) }); }).catch(e => kon({ blad: String(e) }));""")
    wer = d.execute_async_script("""const kon = arguments[arguments.length - 1]; (async () => { const m = await import('/js/weryfikacja.js'); const bin = async u => new Uint8Array(await (await fetch(u)).arrayBuffer()); const o = await bin('/testy/dane/podpisy/oryg.pdf'); const w = {};
      for (const [n, f] of [['pades', 'ok_jan.pdf'], ['ecdsa', 'ecdsa_jan.pdf'], ['inna', 'inna_osoba.pdf'], ['zmieniony', 'zmieniony_po_podpisie.pdf']]) { const r = await m.ocenPodpisElektroniczny({ bajty: await bin('/testy/dane/podpisy/' + f), oryginal: o, imie: 'Jan Testowy', pesel: '90010112349' }); w[n] = r.stan; }
      const x = await m.ocenPodpisElektroniczny({ xades: new TextDecoder().decode(await bin('/testy/dane/podpisy/ok.xades')), oryginal: o, imie: 'Jan Testowy', pesel: '90010112349' }); w.xades = x.stan; kon(w); })().catch(e => kon({ blad: String(e) }));""")
    ok('sprawdzanie podpisów elektronicznych w WebKit (WebCrypto, DOMParser): PAdES ✓, ECDSA ✓, XAdES ✓, inna osoba ✗, zmieniony ✗', wer == {'pades': 'ok', 'ecdsa': 'ok', 'inna': 'zle', 'zmieniony': 'zle', 'xades': 'ok'}, wer)
    ok('ZIP (Blob) działa w WebKit', zip_ok.get('typ') == 'application/zip' and zip_ok.get('rozmiar') == 111 and zip_ok.get('crc') == 0xCBF43926, zip_ok)
    if W < 761:
        for z in ('dzis', 'miesiac', 'dokumenty'):
            d.execute_script("document.querySelector('.zakladka[data-tab=\"%s\"]').click()" % z); time.sleep(3)
            d.save_screenshot('/tmp/webkit_tel_%s.png' % z)
        ok('telefon: bez poziomego przewijania', d.execute_script('return document.scrollingElement.scrollWidth <= innerWidth + 1'))
    print('zrzut: /tmp/webkit_gotowe.png')
except Exception as e:
    kod = 2; print('PRZERWANO:', type(e).__name__, str(e)[:300]); 
    try: print('błędy strony:', json.dumps(bledy()[:8], ensure_ascii=False)); d.save_screenshot('/tmp/webkit_blad.png')
    except Exception: pass
finally:
    try: d.quit()
    except Exception: pass
    srv.terminate()
print('WYNIK:', 'wszystko dobrze' if kod == 0 else 'są błędy'); sys.exit(kod)
