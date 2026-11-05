// PMT Planer (web) — szkic wiadomości w skrzynce Outlook (Microsoft Graph): adres, temat, treść i zahasłowana paczka już w szkicu, użytkownik tylko klika „Wyślij” w swojej poczcie.
// Strona internetowa nie może dołączyć pliku do programu pocztowego na komputerze, więc robi to przez konto Microsoft użytkownika (Outlook.com / Microsoft 365): logowanie w osobnym oknie
// (OAuth 2.0, kod autoryzacji z PKCE — bez hasła i bez sekretu aplikacji w stronie), potem Graph: nowa wiadomość w „Wersjach roboczych” + załącznik (duży przez sesję wysyłania).
//   • Uprawnienie „Mail.ReadWrite” (delegowane): aplikacja tworzy szkic i dokłada do niego plik; NIE czyta skrzynki. Token żyje tylko w pamięci strony (bez „offline_access”, bez zapisu na dysku).
//   • Identyfikator aplikacji (client ID) nie jest tajemnicą; wpisuje go administrator w pliku poczta_microsoft.txt (wdrożenie z repozytoryjnej zmiennej PMT_MS_KLIENT). Bez niego wszystko działa jak dotąd (plik .eml).
// Czyste funkcje z wstrzykiwanym fetch — testowalne bez przeglądarki (testy/outlook_test.js); część z oknem logowania (pobierzKod) wymaga przeglądarki.
import { b64, losowe } from './sejf.js';

const WLADZA = 'https://login.microsoftonline.com/common/oauth2/v2.0';
const GRAPH = 'https://graph.microsoft.com/v1.0';
export const ZAKRES = 'https://graph.microsoft.com/Mail.ReadWrite';
export const KANAL = 'pmt-ms-odpowiedz';
const PROG_MALEGO = 3 * 1024 * 1024;          // do 3 MB załącznik idzie jednym zapytaniem; większy przez sesję wysyłania (do 150 MB)
const KAWALEK = 12 * 327680;                   // 3 932 160 B: wielokrotność 320 KiB, poniżej limitu 4 MB na jedno PUT
const GUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Identyfikator aplikacji z pliku poczta_microsoft.txt (wiersze zaczynające się od # pomijamy): poprawny GUID albo '' (funkcja wyłączona). */
export function odczytajKlienta(tekst) {
  const w = String(tekst || '').split(/\r?\n/).map(x => x.trim()).find(x => x && !x.startsWith('#')) || '';
  return GUID.test(w) ? w.toLowerCase() : '';
}
export async function wczytajKlienta(fetchFn = globalThis.fetch, adres = 'poczta_microsoft.txt') {
  try { const r = await fetchFn(adres, { cache: 'no-store' }); return r.ok ? odczytajKlienta(await r.text()) : ''; } catch (e) { return ''; }
}

export const b64url = b => b64(b).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
/** PKCE (RFC 7636): losowy „verifier” (64 znaki) i jego skrót SHA-256 jako „challenge”. Wymaga Web Crypto (https) — na stronie bez https wysyłka tą drogą jest wyłączona. */
export async function pkce(subtle = globalThis.crypto && globalThis.crypto.subtle) {
  if (!subtle) throw new Error('brak Web Crypto (strona bez https)');
  const verifier = b64url(losowe(48)), challenge = b64url(new Uint8Array(await subtle.digest('SHA-256', new TextEncoder().encode(verifier))));
  return { verifier, challenge };
}
export const losowyStan = () => b64url(losowe(24));

export function adresLogowania({ klient, powrot, state, challenge }) {
  const q = new URLSearchParams({ client_id: klient, response_type: 'code', redirect_uri: powrot, response_mode: 'query', scope: ZAKRES, state, code_challenge: challenge, code_challenge_method: 'S256' });
  return `${WLADZA}/authorize?${q}`;
}

/** Komunikat po polsku z błędu Microsoft (token lub Graph); szczegół techniczny zostaje w nawiasie na końcu. */
export function komunikatBledu(e) {
  const t = String((e && e.message) || e || ''), kod = (t.match(/AADSTS\d+/) || [])[0] || '';
  if (/AADSTS65001|consent_required|interaction_required|AADSTS90094/.test(t)) return 'Poczta wymaga zgody administratora Twojej firmy na tę aplikację (uprawnienie do tworzenia szkiców). Poproś go o zgodę albo użyj „Zmień sposób”.';
  if (/AADSTS700016|AADSTS50011|AADSTS900971/.test(t)) return `Aplikacja nie jest poprawnie zarejestrowana w Microsoft (identyfikator albo adres powrotu) — zgłoś to administratorowi (${kod}).`;
  if (/AADSTS50020|AADSTS500200|AADSTS90072|personal.*accounts/i.test(t)) return `To konto Microsoft nie jest dozwolone dla tej aplikacji (${kod}). Użyj „Zmień sposób”.`;
  if (/access_denied|AADSTS65004/.test(t)) return 'Odmówiono zgody na dostęp do poczty — bez niej nie przygotuję szkicu. Spróbuj jeszcze raz albo użyj „Zmień sposób”.';
  if (/MailboxNotEnabledForRESTAPI|MailboxNotSupportedForRESTAPI|ResourceNotFound.*mailbox|REST API is not yet supported/i.test(t)) return 'To konto nie ma skrzynki Outlook obsługiwanej przez aplikację (np. skrzynka lokalna). Użyj „Zmień sposób”.';
  if (/\b401\b|InvalidAuthenticationToken|\b403\b|ErrorAccessDenied/i.test(t)) return 'Poczta odrzuciła dostęp (brak uprawnień do tworzenia szkiców). Spróbuj jeszcze raz albo użyj „Zmień sposób”.';
  if (/\b413\b|RequestEntityTooLarge|ErrorMessageSizeExceeded|too large/i.test(t)) return 'Paczka jest za duża dla Twojej skrzynki. Zrób mniejsze skany albo użyj „Zmień sposób”.';
  if (/Failed to fetch|NetworkError|Load failed/i.test(t)) return 'Brak połączenia z pocztą Microsoft. Sprawdź internet i spróbuj jeszcze raz.';
  return 'Nie udało się przygotować szkicu w Outlooku (' + t.slice(0, 160) + ').';
}

async function json(r, co) {
  if (r.ok) return r.status === 204 ? {} : r.json();
  let t = ''; try { t = await r.text(); } catch (e) { /* bez treści */ }
  let m = t; try { const j = JSON.parse(t); m = (j.error_description || (j.error && (j.error.message || j.error.code)) || j.error || t); } catch (e) { /* nie JSON */ }
  throw new Error(`${co}: HTTP ${r.status} ${String(m).replace(/\s+/g, ' ').slice(0, 220)}`);
}

/** Kod autoryzacji → token dostępu (tylko w pamięci). Punkt końcowy tokenu przyjmuje zapytania z przeglądarki tylko dla aplikacji zarejestrowanej jako „Aplikacja jednostronicowa (SPA)”. */
export async function wymienKod({ klient, powrot, kod, verifier, fetchFn = globalThis.fetch }) {
  const cialo = new URLSearchParams({ client_id: klient, grant_type: 'authorization_code', code: kod, redirect_uri: powrot, code_verifier: verifier, scope: ZAKRES });
  const j = await json(await fetchFn(`${WLADZA}/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: cialo, credentials: 'omit' }), 'token');
  if (!j.access_token) throw new Error('token: brak access_token w odpowiedzi');
  return j.access_token;
}

/** Szkic w „Wersjach roboczych”: adresat, temat, treść (zwykły tekst) i załącznik; zwraca { id, webLink }. postep(0..100) — dla dużych plików. */
export async function utworzSzkic({ token, adres, temat, tresc, zalacznik, fetchFn = globalThis.fetch, postep = () => {} }) {
  const naglowki = { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' };
  const wiad = await json(await fetchFn(`${GRAPH}/me/messages`, { method: 'POST', headers: naglowki, credentials: 'omit',
    body: JSON.stringify({ subject: temat, body: { contentType: 'text', content: tresc }, toRecipients: [{ emailAddress: { address: adres } }] }) }), 'szkic');
  if (!wiad.id) throw new Error('szkic: brak identyfikatora wiadomości');
  const id = encodeURIComponent(wiad.id), bajty = zalacznik.bajty, typ = zalacznik.typ || 'application/octet-stream';
  if (bajty.length <= PROG_MALEGO) {
    await json(await fetchFn(`${GRAPH}/me/messages/${id}/attachments`, { method: 'POST', headers: naglowki, credentials: 'omit',
      body: JSON.stringify({ '@odata.type': '#microsoft.graph.fileAttachment', name: zalacznik.nazwa, contentType: typ, contentBytes: b64(bajty) }) }), 'załącznik');
    postep(100);
  } else {
    const s = await json(await fetchFn(`${GRAPH}/me/messages/${id}/attachments/createUploadSession`, { method: 'POST', headers: naglowki, credentials: 'omit',
      body: JSON.stringify({ AttachmentItem: { attachmentType: 'file', name: zalacznik.nazwa, size: bajty.length, contentType: typ } }) }), 'sesja wysyłania');
    if (!s.uploadUrl) throw new Error('sesja wysyłania: brak uploadUrl');
    for (let od = 0; od < bajty.length; od += KAWALEK) {
      const koniec = Math.min(od + KAWALEK, bajty.length), kawalek = bajty.subarray(od, koniec);
      // adres sesji niesie własne uwierzytelnienie — bez nagłówka Authorization
      await json(await fetchFn(s.uploadUrl, { method: 'PUT', headers: { 'Content-Type': 'application/octet-stream', 'Content-Range': `bytes ${od}-${koniec - 1}/${bajty.length}` }, body: kawalek, credentials: 'omit' }), 'wysyłanie paczki');
      postep(Math.round(koniec / bajty.length * 100));
    }
  }
  return { id: wiad.id, webLink: wiad.webLink || '' };
}

/** Logowanie w otwartym już oknie (okno otwiera się od razu po kliknięciu, inaczej przeglądarka je zablokuje): zwraca { kod, verifier }.
 *  Odpowiedź wraca ze strony ms_powrot.html kanałem BroadcastChannel (działa także gdy okno logowania zerwało powiązanie z oknem aplikacji) albo przez postMessage. */
export function pobierzKod({ okno, klient, powrot, limitMs = 300000 }) {
  return new Promise(async (rozwiaz, odrzuc) => {
    let kanal = null, zegar = null, kontrola = null, koniec = false;
    const sprzatnij = () => { koniec = true; clearTimeout(zegar); clearInterval(kontrola); try { kanal && kanal.close(); } catch (e) { /* zamknięty */ } removeEventListener('message', naWiadomosc); };
    const gotowe = (blad, wynik) => { if (koniec) return; sprzatnij(); blad ? odrzuc(blad) : rozwiaz(wynik); };
    let verifier = '', state = '';
    const przyjmij = d => {
      if (!d || koniec) return;
      if (d.error) return gotowe(new Error(`${d.error}: ${d.error_description || ''}`));
      if (d.state !== state) return;           // odpowiedź na inne logowanie — ignoruję
      if (!d.code) return gotowe(new Error('logowanie: brak kodu w odpowiedzi'));
      gotowe(null, { kod: d.code, verifier });
    };
    const naWiadomosc = e => { if (e.origin === location.origin && e.data && e.data.pmtMs) przyjmij(e.data.pmtMs); };
    try {
      const k = await pkce(); verifier = k.verifier; state = losowyStan();
      addEventListener('message', naWiadomosc);
      if (typeof BroadcastChannel === 'function') { kanal = new BroadcastChannel(KANAL); kanal.onmessage = e => przyjmij(e.data); }
      zegar = setTimeout(() => gotowe(new Error('logowanie: minął czas na zalogowanie')), limitMs);
      kontrola = setInterval(() => { try { if (okno.closed) gotowe(new Error('logowanie: okno zostało zamknięte')); } catch (e) { /* okno z innego źródła — nie sprawdzam */ } }, 700);
      okno.location.href = adresLogowania({ klient, powrot, state, challenge: k.challenge });
    } catch (e) { gotowe(e); }
  });
}
