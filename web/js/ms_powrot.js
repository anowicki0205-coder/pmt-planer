// PMT Planer (web) — strona powrotu po logowaniu do konta Microsoft (adres „…/ms_powrot.html” zarejestrowany w aplikacji Microsoft Entra jako „Adres URI przekierowania”).
// Odczytuje kod autoryzacji (albo błąd) z adresu i oddaje go oknu aplikacji — kanałem BroadcastChannel (tylko to samo źródło) oraz przez postMessage do okna, które otworzyło to okno.
// Kodu nie zapisuje nigdzie i od razu usuwa go z paska adresu. Samo okno zostaje otwarte: aplikacja przekieruje je potem na gotowy szkic wiadomości.
(() => {
  const q = new URLSearchParams(location.search), d = { code: q.get('code') || '', state: q.get('state') || '', error: q.get('error') || '', error_description: (q.get('error_description') || '').slice(0, 300) };
  try { history.replaceState(null, '', location.pathname); } catch (e) { /* bez historii */ }
  const tytul = document.getElementById('tytul'), opis = document.getElementById('opis');
  if (!d.code && !d.error) { tytul.textContent = 'Nic tu do zrobienia'; opis.textContent = 'To okno służy tylko do powrotu po zalogowaniu z aplikacji PMT Planer. Możesz je zamknąć.'; return; }
  let dostarczono = false;
  try { const k = new BroadcastChannel('pmt-ms-odpowiedz'); k.postMessage(d); dostarczono = true; setTimeout(() => k.close(), 1500); } catch (e) { /* brak BroadcastChannel */ }
  try { if (window.opener) { window.opener.postMessage({ pmtMs: d }, location.origin); dostarczono = true; } } catch (e) { /* okno aplikacji niedostępne */ }
  if (d.error) { tytul.textContent = 'Logowanie nie powiodło się'; opis.textContent = 'Wróć do aplikacji PMT Planer — pokaże, co poszło nie tak. Możesz zamknąć to okno.'; return; }
  if (!dostarczono) { tytul.textContent = 'Wróć do aplikacji'; opis.textContent = 'Nie udało się przekazać logowania do aplikacji. Zamknij to okno i spróbuj jeszcze raz.'; return; }
  tytul.textContent = 'Zalogowano — przygotowuję szkic wiadomości…';
})();
