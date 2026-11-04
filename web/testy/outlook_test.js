// Szkic wiadomości w Outlooku (js/outlook.js): identyfikator aplikacji z pliku, PKCE, adres logowania, wymiana kodu na token, szkic z małym i dużym załącznikiem (granice kawałków), komunikaty błędów.
// Microsoft jest atrapą (wstrzykiwany fetch) — przeglądarkowy przebieg z oknem logowania sprawdza podpis_offline_app.js. Uruchom: node outlook_test.js
(async () => {
  const m = await import('../js/outlook.js'); const crypto = require('crypto');
  let kod = 0; const ok = (opis, w, szcz = '') => { console.log((w ? '  OK   ' : '  BŁĄD ') + opis + (szcz ? ' — ' + szcz : '')); if (!w) kod = 1; };
  const GUID = '12345678-abcd-4ef0-9876-0123456789ab';

  /* ---- identyfikator aplikacji z pliku ---- */
  ok('plik z samym komentarzem → wyłączone', m.odczytajKlienta('# opis\n# jeszcze opis\n') === '' && m.odczytajKlienta('') === '' && m.odczytajKlienta(undefined) === '');
  ok('komentarze pomijane, GUID przycięty i zapisany małymi literami', m.odczytajKlienta(`# a\r\n\r\n  ${GUID.toUpperCase()}  \r\n`) === GUID);
  ok('coś, co nie jest GUID-em (literówka, dopisek, za krótkie), nie włącza funkcji', ['12345678-abcd-4ef0-9876-0123456789a', GUID + 'x', 'nie-guid', GUID.replace(/-/g, '')].every(x => m.odczytajKlienta(x) === ''));
  ok('wczytajKlienta: 200 → GUID, 404 → pusto, błąd sieci → pusto (bez wyjątku)', await m.wczytajKlienta(async () => ({ ok: true, text: async () => GUID })) === GUID && await m.wczytajKlienta(async () => ({ ok: false })) === '' && await m.wczytajKlienta(async () => { throw new TypeError('Failed to fetch'); }) === '');

  /* ---- PKCE i adres logowania ---- */
  const k1 = await m.pkce(), k2 = await m.pkce();
  ok('PKCE: „verifier” 64 znaki base64url, „challenge” = SHA-256(verifier) w base64url, każdy raz inne', /^[A-Za-z0-9_-]{64}$/.test(k1.verifier) && k1.challenge === crypto.createHash('sha256').update(k1.verifier).digest('base64url') && k1.verifier !== k2.verifier);
  let blad = ''; try { await m.pkce(null); } catch (e) { blad = e.message; }
  ok('bez Web Crypto (strona bez https) PKCE zgłasza błąd zamiast cichego słabego klucza', /Web Crypto/.test(blad), blad);
  const url = new URL(m.adresLogowania({ klient: GUID, powrot: 'https://x.example/app/ms_powrot.html', state: 'ST', challenge: k1.challenge }));
  ok('adres logowania: wspólny punkt Microsoft, kod + PKCE S256, jedyne uprawnienie Mail.ReadWrite (bez offline_access), adres powrotu i state przekazane',
    url.origin === 'https://login.microsoftonline.com' && url.pathname === '/common/oauth2/v2.0/authorize' && url.searchParams.get('response_type') === 'code' && url.searchParams.get('code_challenge_method') === 'S256'
    && url.searchParams.get('code_challenge') === k1.challenge && url.searchParams.get('scope') === 'https://graph.microsoft.com/Mail.ReadWrite' && url.searchParams.get('redirect_uri') === 'https://x.example/app/ms_powrot.html' && url.searchParams.get('state') === 'ST' && url.searchParams.get('client_id') === GUID);

  /* ---- wymiana kodu na token ---- */
  let zad;
  const tokenOk = async (u, o) => { zad = { u, o }; return { ok: true, status: 200, json: async () => ({ access_token: 'TOK', token_type: 'Bearer' }) }; };
  const tok = await m.wymienKod({ klient: GUID, powrot: 'https://x.example/ms_powrot.html', kod: 'KOD', verifier: k1.verifier, fetchFn: tokenOk });
  const ciało = new URLSearchParams(String(zad.o.body));
  ok('wymiana kodu: POST na punkt tokenu, grant authorization_code, kod, code_verifier, adres powrotu; bez ciasteczek; zwraca sam token', tok === 'TOK' && zad.u === 'https://login.microsoftonline.com/common/oauth2/v2.0/token' && zad.o.method === 'POST' && zad.o.credentials === 'omit'
    && ciało.get('grant_type') === 'authorization_code' && ciało.get('code') === 'KOD' && ciało.get('code_verifier') === k1.verifier && ciało.get('redirect_uri') === 'https://x.example/ms_powrot.html' && !/offline_access/.test(String(zad.o.body)));
  blad = ''; try { await m.wymienKod({ klient: GUID, powrot: 'p', kod: 'K', verifier: 'v', fetchFn: async () => ({ ok: false, status: 400, text: async () => JSON.stringify({ error: 'invalid_grant', error_description: 'AADSTS70008: kod wygasł' }) }) }); } catch (e) { blad = e.message; }
  ok('błąd tokenu niesie opis z Microsoft (AADSTS…)', /AADSTS70008/.test(blad) && /HTTP 400/.test(blad), blad);

  /* ---- szkic: mały załącznik jednym zapytaniem ---- */
  const graf = (opcje = {}) => { const log = []; const f = async (u, o = {}) => {
    log.push({ u, m: o.method, h: o.headers || {}, b: o.body, c: o.credentials });
    if (/\/me\/messages$/.test(u)) return opcje.bladSzkicu ? { ok: false, status: opcje.bladSzkicu, text: async () => JSON.stringify({ error: { code: 'InvalidAuthenticationToken', message: 'zły token' } }) } : { ok: true, status: 201, json: async () => ({ id: 'ID/+=1', webLink: 'https://outlook.office365.com/owa/?x=1' }) };
    if (/\/attachments$/.test(u)) return opcje.bladZalacznika ? { ok: false, status: opcje.bladZalacznika, text: async () => 'za duże' } : { ok: true, status: 201, json: async () => ({}) };
    if (/createUploadSession$/.test(u)) return { ok: true, status: 201, json: async () => ({ uploadUrl: 'https://outlook.office.com/api/upload/S1' }) };
    if (/upload\/S1$/.test(u)) return { ok: true, status: o.headers['Content-Range'].endsWith(`/${opcje.razem}`) && /-(\d+)\//.exec(o.headers['Content-Range'])[1] === String(opcje.razem - 1) ? 201 : 200, json: async () => ({}) };
    return { ok: false, status: 404, text: async () => '' }; }; return { f, log }; };
  const male = new Uint8Array(1000).map((_, i) => i % 251), { f: f1, log: l1 } = graf(); const postep1 = [];
  const w1 = await m.utworzSzkic({ token: 'TOK', adres: 'odbiorca@example.com', temat: '[PMT] Test — ąęść', tresc: 'Treść\nz polskimi znakami', zalacznik: { nazwa: 'Dokumenty.zip', bajty: male, typ: 'application/zip' }, fetchFn: f1, postep: p => postep1.push(p) });
  const draft = JSON.parse(l1[0].b), zal = JSON.parse(l1[1].b);
  ok('mały załącznik: dwa zapytania (szkic, załącznik), token w nagłówku, bez ciasteczek; zwraca identyfikator i odnośnik do szkicu', l1.length === 2 && l1[0].h.Authorization === 'Bearer TOK' && l1.every(x => x.c === 'omit') && w1.id === 'ID/+=1' && w1.webLink === 'https://outlook.office365.com/owa/?x=1' && postep1.join() === '100');
  ok('szkic: adresat, temat i treść (zwykły tekst) bez zmian, polskie znaki całe', draft.toRecipients[0].emailAddress.address === 'odbiorca@example.com' && draft.subject === '[PMT] Test — ąęść' && draft.body.contentType === 'text' && draft.body.content === 'Treść\nz polskimi znakami');
  ok('załącznik: typ fileAttachment, nazwa, typ ZIP i zawartość base64 identyczna z oryginałem; identyfikator wiadomości w adresie zakodowany', zal['@odata.type'] === '#microsoft.graph.fileAttachment' && zal.name === 'Dokumenty.zip' && zal.contentType === 'application/zip' && Buffer.from(zal.contentBytes, 'base64').equals(Buffer.from(male)) && l1[1].u.includes(encodeURIComponent('ID/+=1')));
  const granica = new Uint8Array(3 * 1024 * 1024), { f: fg, log: lg } = graf(); await m.utworzSzkic({ token: 'T', adres: 'a@b.pl', temat: 't', tresc: 'x', zalacznik: { nazwa: 'g.zip', bajty: granica }, fetchFn: fg });
  ok('dokładnie 3 MB jeszcze idzie jednym zapytaniem (bez sesji wysyłania)', lg.length === 2 && /\/attachments$/.test(lg[1].u));

  /* ---- szkic: duży załącznik przez sesję wysyłania ---- */
  const N = 9000000, duzy = new Uint8Array(N).map((_, i) => (i * 7) % 256), { f: f2, log: l2 } = graf({ razem: N }); const postep2 = [];
  const w2 = await m.utworzSzkic({ token: 'TOK', adres: 'a@b.pl', temat: 't', tresc: 'x', zalacznik: { nazwa: 'Duza.zip', bajty: duzy, typ: 'application/zip' }, fetchFn: f2, postep: p => postep2.push(p) });
  const sesja = JSON.parse(l2[1].b).AttachmentItem, put = l2.filter(x => x.m === 'PUT'), zakresy = put.map(x => /^bytes (\d+)-(\d+)\/(\d+)$/.exec(x.h['Content-Range']).slice(1).map(Number));
  ok('duży załącznik (9 MB): szkic, sesja wysyłania z rozmiarem i nazwą, potem kawałki PUT', l2[0].m === 'POST' && /createUploadSession$/.test(l2[1].u) && sesja.attachmentType === 'file' && sesja.size === N && sesja.name === 'Duza.zip' && sesja.contentType === 'application/zip' && w2.id === 'ID/+=1');
  ok('kawałki: po 3 932 160 B (wielokrotność 320 KiB), bez dziur i nakładania, ostatni kończy się na N−1, wszystkie z tym samym „razem”', put.length === 3 && zakresy.every((z, i) => z[0] === (i ? zakresy[i - 1][1] + 1 : 0) && z[2] === N) && zakresy[0][1] - zakresy[0][0] + 1 === 3932160 && zakresy[2][1] === N - 1, JSON.stringify(zakresy));
  ok('treść kawałków sklejona = oryginał, a wysyłanie NIE niesie nagłówka Authorization (adres sesji ma własne uwierzytelnienie)', Buffer.concat(put.map(x => Buffer.from(x.b))).equals(Buffer.from(duzy)) && put.every(x => !x.h.Authorization && x.h['Content-Type'] === 'application/octet-stream' && x.c === 'omit'));
  ok('postęp rośnie do 100 po każdym kawałku', postep2.length === 3 && postep2.every((p, i, w) => !i || p > w[i - 1]) && postep2[2] === 100, postep2.join());

  /* ---- błędy ---- */
  const zle = async (opcje, zalacznik = { nazwa: 'a.zip', bajty: male }) => { try { await m.utworzSzkic({ token: 'T', adres: 'a@b.pl', temat: 't', tresc: 'x', zalacznik, fetchFn: graf(opcje).f }); return ''; } catch (e) { return e.message; } };
  const e401 = await zle({ bladSzkicu: 401 }), e413 = await zle({ bladZalacznika: 413 });
  ok('błąd tworzenia szkicu (401) i załącznika (413) przerywa z komunikatem technicznym', /szkic: HTTP 401/.test(e401) && /InvalidAuthenticationToken|zły token/.test(e401) && /załącznik: HTTP 413/.test(e413), e401 + ' | ' + e413);
  ok('komunikaty dla użytkownika po polsku: zgoda administratora, zła rejestracja, odmowa, 401, 413, sieć, nieznany błąd', [
    [new Error('token: HTTP 400 AADSTS65001: The user has not consented'), /zgody administratora/], [new Error('x AADSTS700016: Application not found'), /nie jest poprawnie zarejestrowana/], [new Error('access_denied: AADSTS65004: odmowa'), /Odmówiono zgody/],
    [new Error('szkic: HTTP 401 InvalidAuthenticationToken'), /odrzuciła dostęp/], [new Error('wysyłanie paczki: HTTP 413 RequestEntityTooLarge'), /za duża/], [new TypeError('Failed to fetch'), /Brak połączenia/], [new Error('coś dziwnego'), /Nie udało się przygotować szkicu/],
  ].every(([e, re]) => re.test(m.komunikatBledu(e))));
  ok('każdy komunikat błędu podpowiada wyjście („Inna poczta”) albo poprawkę, a nie zostawia bez drogi', ['AADSTS65001', 'access_denied', 'HTTP 401', 'RequestEntityTooLarge'].every(t => /Inna poczta|Zrób mniejsze|Spróbuj/.test(m.komunikatBledu(new Error(t)))));

  console.log(kod ? 'WYNIK: są błędy' : 'WYNIK: wszystko dobrze'); process.exit(kod);
})().catch(e => { console.error('PRZERWANO:', e.stack); process.exit(2); });
