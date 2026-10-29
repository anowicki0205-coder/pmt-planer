// Zamiennik backendu Apps Script do testów: te same reguły co apps_script_POPRAWIONY_v2.gs (logowanie, puls, sesja, zmiana i reset hasła,
// podpis HMAC, limity prób resetu). Prawdziwego Google nie wołamy — test przechwytuje zapytania przeglądarki i odpowiada stąd.
const crypto = require('crypto');
const hash = (kod, haslo) => crypto.createHash('sha256').update(`PMT|${kod}|${haslo}`).digest('hex');
const dwa = n => String(n).padStart(2, '0');
const iso = d => `${d.getFullYear()}-${dwa(d.getMonth() + 1)}-${dwa(d.getDate())}`;

class BackendMock {
  constructor(opcje = {}) {
    this.sekrety = opcje.sekrety || ['SEKRET-TESTOWY'];
    this.podpisObowiazkowy = !!opcje.podpisObowiazkowy;
    this.opoznienieMs = opcje.opoznienieMs || 0;
    this.martwy = false;                       // symulacja braku sieci / niedostępnego serwera
    this.uzytkownicy = opcje.uzytkownicy || {
      '12345': { imie: 'Jan Testowy', telefon: '600100200', hash: hash('12345', 'haslo123'), wazne_do: '2099-12-31' },
      '22222': { imie: 'Anna Nowa', telefon: '501502503', hash: '', wazne_do: '2099-12-31' },
      '33333': { imie: 'Ewa Wygasla', telefon: '700800900', hash: hash('33333', 'haslo123'), wazne_do: '2020-01-01' },
    };
    this.log = []; this.sesje = []; this.pulsy = []; this.proby = {};
  }
  podpisPoprawny(d) {
    const czas = Number(d.klucz_czas || 0); if (!czas || Math.abs(Date.now() / 1000 - czas) > 600) return false;
    const baza = `${d.kod || ''}|${d.akcja || ''}|${czas}`, podany = String(d.podpis || ''); if (!podany) return false;
    return this.sekrety.some(s => crypto.createHmac('sha256', s).update(baza).digest('hex') === podany);
  }
  /** Jak _podpisHaslaOk w .gs: HMAC kluczem = skrót hasła konta (kolumna „Haslo hash”); konto bez hasła nie ma klucza. */
  hasloOk(d, u) {
    const czas = Number(d.klucz_czas || 0); if (!u.hash || !czas || Math.abs(Date.now() / 1000 - czas) > 600) return false;
    return crypto.createHmac('sha256', u.hash).update(`${d.kod || ''}|${d.akcja || ''}|${czas}`).digest('hex') === String(d.podpis_hasla || '');
  }
  zapisz(kod, zdarzenie, szczegoly = '') { this.log.push({ kod, zdarzenie, szczegoly }); }
  obsluz(tekst) {
    let d; try { d = JSON.parse(tekst || '{}'); } catch (e) { return { status: 'blad', opis: String(e) }; }
    if (!this.podpisPoprawny(d)) {
      if (this.podpisObowiazkowy) return { status: 'blad', opis: 'odmowa' };
      this.zapisz(String(d.kod || '?'), 'podpis_zly', `akcja ${d.akcja}`);
    }
    switch (d.akcja) {
      case 'logowanie': return this.logowanie(d);
      case 'puls': return this.puls(d);
      case 'sesja': { const u = this.uzytkownicy[String(d.kod || '')]; if (u && this.hasloOk(d, u)) this.sesje.push(d); else this.sesjeOdrzucone = (this.sesjeOdrzucone || 0) + 1; return { status: 'ok' }; }
      case 'zmien_haslo': return this.zmienHaslo(d);
      case 'reset_hasla': return this.reset(d);
      default: return { status: 'blad', opis: 'Nieznana akcja' };
    }
  }
  logowanie(d) {
    const kod = String(d.kod || '').trim(); if (!/^\d{5}$/.test(kod)) return { status: 'blad', opis: 'Kod musi miec 5 cyfr' };
    const haslo = String(d.haslo || d.telefon || '').trim(); if (!haslo) return { status: 'blad', opis: 'Podaj haslo albo numer telefonu' };
    const tel = haslo.replace(/\D/g, ''), u = this.uzytkownicy[kod]; if (!u) return { status: 'blad', opis: 'Nie znaleziono takiego kodu' };
    const telBaza = (u.telefon || '').replace(/\D/g, '');
    const haslem = u.hash && hash(kod, haslo) === u.hash, telefonem = !u.hash && telBaza && tel.length >= 9 && telBaza.slice(-9) === tel.slice(-9);
    if (!haslem && !telefonem) {
      if (u.hash && telBaza && tel.length >= 9 && telBaza.slice(-9) === tel.slice(-9)) return { status: 'blad', opis: 'To konto ma ustawione haslo — zaloguj sie haslem. Numer telefonu sluzy tylko do zmiany lub resetu hasla.' };
      return { status: 'blad', opis: u.hash ? 'Nieprawidlowe haslo' : 'Nieprawidlowy numer telefonu' };
    }
    this.zapisz(kod, 'logowanie_' + (d.zrodlo || 'www'), haslem ? 'OK (haslo)' : 'OK (telefon)');
    return { status: 'ok', imie: u.imie };
  }
  puls(d) {
    const kod = String(d.kod || '').trim(); if (!/^\d{5}$/.test(kod)) return { status: 'zly_kod' };
    const u = this.uzytkownicy[kod]; if (!u) return { status: 'zly_kod' };
    const pelne = this.hasloOk(d, u);
    if (pelne) this.pulsy.push({ kod, uruchomienia: d.uruchomienia, dokumenty: d.dokumenty, minuty: d.minuty, system: d.system }); else this.pulsyBezHasla = (this.pulsyBezHasla || 0) + 1;
    const dzis = iso(new Date()), status = u.wazne_do && u.wazne_do >= dzis ? 'ok' : 'wygasla';
    return pelne ? { status, imie: u.imie, rejon: u.rejon || '', wazne_do: u.wazne_do || '', nieobecnosci: [], pelne: true } : { status, imie: '', rejon: '', wazne_do: u.wazne_do || '', nieobecnosci: [], pelne: false };
  }
  zmienHaslo(d) {
    const kod = String(d.kod || '').trim(), stare = String(d.stare_haslo || '').trim(), nowe = String(d.nowe_haslo || '').trim();
    if (!stare) return { status: 'blad', opis: 'Podaj dotychczasowe haslo albo telefon' };
    if (nowe.length < 6) return { status: 'blad', opis: 'Nowe haslo: min. 6 znakow' };
    const u = this.uzytkownicy[kod]; if (!u) return { status: 'blad', opis: 'Nie znaleziono takiego kodu' };
    const telBaza = (u.telefon || '').replace(/\D/g, ''), st = stare.replace(/\D/g, '');
    const telPasuje = telBaza && st.length >= 9 && telBaza.slice(-9) === st.slice(-9);
    const haslem = u.hash && hash(kod, stare) === u.hash, telefonem = !u.hash && telPasuje;
    if (!haslem && !telefonem) { this.zapisz(kod, 'zmiana_hasla', 'ODRZUCONA'); return { status: 'blad', opis: u.hash ? 'Dotychczasowe haslo nie pasuje' : 'Numer telefonu nie zgadza sie z kartoteka' }; }
    u.hash = hash(kod, nowe); this.zapisz(kod, 'zmiana_hasla', 'OK'); return { status: 'ok' };
  }
  reset(d) {
    const kod = String(d.kod || '').trim(), tel = String(d.telefon || '').replace(/\D/g, '');
    this.proby[kod] = (this.proby[kod] || 0) + 1;
    if (this.proby[kod] > 5) { this.zapisz(kod, 'reset_hasla', 'ODRZUCONA (za duzo prob)'); return { status: 'blad', opis: 'Za duzo prob resetu — sprobuj za godzine' }; }
    const u = this.uzytkownicy[kod]; if (!u) return { status: 'blad', opis: 'Nie znaleziono takiego kodu' };
    const telBaza = (u.telefon || '').replace(/\D/g, '');
    if (!telBaza) return { status: 'blad', opis: 'Konto nie ma telefonu w kartotece — zglos sie do administratora' };
    if (tel.length < 9 || telBaza.slice(-9) !== tel.slice(-9)) { this.zapisz(kod, 'reset_hasla', 'ODRZUCONA (zly telefon)'); return { status: 'blad', opis: 'Numer telefonu nie zgadza sie z kartoteka' }; }
    u.hash = ''; this.zapisz(kod, 'reset_hasla', 'OK'); return { status: 'ok', opis: 'Haslo skasowane.' };
  }
  /* podpięcie do strony Playwright */
  async podepnij(kontekst) {
    await kontekst.route(/^https:\/\/script\.google\.com\//, async r => {
      const q = r.request(), cors = { 'access-control-allow-origin': '*' };
      if (this.martwy) return r.abort('internetdisconnected');
      if (this.cors && q.method() === 'POST') return r.abort('failed');            // serwer osiągalny, ale odpowiedź zablokowana (CORS)
      if (this.opoznienieMs) await new Promise(ok => setTimeout(ok, this.opoznienieMs));
      if (q.method() !== 'POST') return r.fulfill({ status: 200, headers: cors, contentType: 'application/json', body: JSON.stringify({ status: 'ok', opis: 'PMT backend dziala (mock)' }) });
      return r.fulfill({ status: 200, headers: cors, contentType: 'application/json', body: JSON.stringify(this.obsluz(q.postData())) });
    });
  }
}
module.exports = { BackendMock, hash };
