// PMT Planer (web) — folder roboczy na dysku użytkownika (File System Access API: Chrome, Edge na komputerze).
// Po co: dokumenty do podpisu zapisują się w folderze „delegacje” (jak w programie na komputerze), w podfolderze miesiąca, użytkownik podpisuje je na gov.pl i zapisuje podpisane pliki w TYM SAMYM folderze,
// a aplikacja sama zauważa nowe pliki, wczytuje je i sprawdza (zamiast ręcznego „Wgraj podpisane pliki”). Przeglądarka pozwala na to wyłącznie za zgodą użytkownika: miejsce wskazuje się RAZ w oknie
// systemowym, a folder „delegacje” aplikacja tworzy sama w wskazanym miejscu (albo używa wskazanego, jeśli tak się już nazywa). Przeglądarka nie pozwala wskazać samego Pulpitu, Dokumentów ani Pobranych
// (dopiero ich podfolder) — wtedy w oknie wyboru trzeba kliknąć „Nowy folder”, nazwać go „delegacje” i wskazać. Zgoda dotyczy tylko tego folderu. Uchwyt do folderu pamiętamy w IndexedDB
// (to nie jest ścieżka ani dane — przeglądarka sama pyta o ponowne pozwolenie, gdy trzeba). Bez tego API (Firefox, Safari, telefon) aplikacja działa po staremu: pobieranie plików i ręczne wgrywanie.
// Moduł nie robi nic przy samym imporcie; wszystkie funkcje przyjmują uchwyty, więc w testach można podstawić folder z prywatnej pamięci przeglądarki (OPFS) zamiast okna systemowego.

const BAZA = 'pmt-folder-roboczy', SKLEP = 'uchwyty', KLUCZ = 'glowny';
const DOZWOLONE = /\.(pdf|xades|xml|zip|png|jpe?g|heic|heif|webp|tiff?)$/i;      // rodzaje plików, które aplikacja umie wczytać jako podpisane/zeskanowane dokumenty

/** Czy ta przeglądarka umie wskazać folder i w nim zapisywać (Chrome, Edge na komputerze; strona musi być bezpieczna: https albo localhost). */
export const obslugiwany = () => typeof window !== 'undefined' && typeof window.showDirectoryPicker === 'function' && window.isSecureContext !== false && !(window.matchMedia && matchMedia('(pointer:coarse)').matches);

function otworzBaze() {
  return new Promise((ok, err) => {
    let q; try { q = indexedDB.open(BAZA, 1); } catch (e) { return err(e); }
    q.onupgradeneeded = () => { q.result.createObjectStore(SKLEP); };
    q.onsuccess = () => ok(q.result); q.onerror = () => err(q.error);
  });
}
const transakcja = async (tryb, f) => { const b = await otworzBaze(); try { return await new Promise((ok, err) => { const t = b.transaction(SKLEP, tryb), r = f(t.objectStore(SKLEP)); t.oncomplete = () => ok(r && r.result); t.onerror = () => err(t.error); t.onabort = () => err(t.error); }); } finally { b.close(); } };

/** Zapamiętany uchwyt folderu roboczego albo null (nic nie zapisano, IndexedDB niedostępne). */
export async function wczytajFolder() { try { return (await transakcja('readonly', s => s.get(KLUCZ))) || null; } catch (e) { return null; } }
export async function zapamietajFolder(uchwyt) { try { await transakcja('readwrite', s => s.put(uchwyt, KLUCZ)); return true; } catch (e) { return false; } }
export async function zapomnijFolder() { try { await transakcja('readwrite', s => s.delete(KLUCZ)); } catch (e) { /* nie ma czego zapominać */ } }

/** Okno systemowe „Wybierz folder” (tylko z kliknięcia). Zwraca uchwyt albo null, gdy użytkownik zrezygnował; błąd bezpieczeństwa (folder niedozwolony) rzuca dalej z czytelnym kodem. */
export async function wskazFolder() {
  try { return await window.showDirectoryPicker({ id: 'pmt-dokumenty', mode: 'readwrite', startIn: 'desktop' }); }
  catch (e) { if (e && e.name === 'AbortError') return null; throw e; }
}
/** Zgoda na zapis w folderze: 'granted' | 'prompt' | 'denied'. Z kliknięcia (zadaj = true) pyta użytkownika, jeśli przeglądarka zgody jeszcze nie pamięta. */
export async function zgoda(uchwyt, zadaj = false) {
  const opcje = { mode: 'readwrite' };
  if (typeof uchwyt.queryPermission !== 'function') return 'granted';      // uchwyt bez pytania o zgodę (np. prywatna pamięć przeglądarki w testach): dostęp jest zawsze
  try {
    let s = await uchwyt.queryPermission(opcje);
    if (s !== 'granted' && zadaj) s = await uchwyt.requestPermission(opcje);
    return s;
  } catch (e) { return 'denied'; }
}

/** Nazwa folderu głównego z dokumentami. */
export const NAZWA_FOLDERU = 'delegacje';
/** Folder „delegacje”: gdy wskazany folder już tak się nazywa (wielkość liter bez znaczenia), używamy go; inaczej tworzymy „delegacje” w jego środku (albo otwieramy, jeśli już tam jest). */
export const korzenDelegacji = async uchwyt => String(uchwyt.name || '').toLowerCase() === NAZWA_FOLDERU ? uchwyt : uchwyt.getDirectoryHandle(NAZWA_FOLDERU, { create: true });

/** Podfolder (tworzy, jeśli go nie ma) — tu leżą dokumenty jednego miesiąca. */
export const podfolder = (uchwyt, nazwa) => uchwyt.getDirectoryHandle(nazwa, { create: true });

/** Zapisuje plik w folderze (nadpisuje istniejący) i zwraca jego odcisk { nazwa, rozmiar, zmiana } do porównań. */
export async function zapiszPlik(folder, nazwa, bajty) {
  const u = await folder.getFileHandle(nazwa, { create: true }), w = await u.createWritable();
  try { await w.write(bajty); } finally { await w.close(); }
  const p = await u.getFile(); return { nazwa, rozmiar: p.size, zmiana: p.lastModified };
}

/** Odcisk pliku — nazwa, rozmiar i czas zmiany: nowy albo zmieniony plik ma inny odcisk niż poprzednio. */
export const odcisk = p => `${p.name}|${p.size}|${p.lastModified}`;

/** Pliki w folderze (bez podfolderów), które aplikacja umie wczytać: [{ nazwa, rozmiar, zmiana, odcisk, uchwyt }]. Pliki tymczasowe przeglądarki (.crdownload, .tmp, ~$…) pomijamy. */
export async function wypisz(folder) {
  const wyn = [];
  for await (const [nazwa, uchwyt] of folder.entries()) {
    if (uchwyt.kind !== 'file' || !DOZWOLONE.test(nazwa) || /^(~\$|\.)/.test(nazwa)) continue;
    let p; try { p = await uchwyt.getFile(); } catch (e) { continue; }      // plik zniknął albo jest zablokowany przez inny program
    wyn.push({ nazwa, rozmiar: p.size, zmiana: p.lastModified, odcisk: odcisk(p), uchwyt });
  }
  return wyn;
}
