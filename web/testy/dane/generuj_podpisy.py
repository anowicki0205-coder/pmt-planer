#!/usr/bin/env python3
"""Tworzy testowe podpisy elektroniczne (PAdES w PDF i XAdES obok pliku) dla testy/dane/podpisy/oryg.pdf — przypadki dobre i złe do testu js/weryfikacja.js.
Wymaga:  pip install pyhanko lxml cryptography      Uruchom:  python generuj_podpisy.py [nazwy plików]      (wyniki w testy/dane/podpisy/; są też zapisane w repozytorium, więc test ich nie wymaga;
z nazwami plików zapisuje tylko te pliki — reszta zostaje bez zmian, bo każde uruchomienie losuje nowe klucze)"""
import io, os, re, shutil, sys, zlib
from podpisy_lib import *
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.writer import copy_into_new_writer

KAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'podpisy'); os.makedirs(KAT, exist_ok=True)
ORYG = open(os.path.join(KAT, 'oryg.pdf'), 'rb').read()
TYLKO = set(sys.argv[1:])
def zapisz(nazwa, dane):
    if TYLKO and nazwa not in TYLKO: return
    open(os.path.join(KAT, nazwa), 'wb').write(dane); print('  ', nazwa, len(dane), 'B')

def aktualizacja(dane, obiekty, w_strumieniu=None):
    """Dopisuje do PDF-u aktualizację przyrostową (tak zapisuje zmiany np. Acrobat): obiekty = {nr: słownik albo (słownik, treść strumienia)};
    w_strumieniu = {nr: słownik} — obiekty spakowane w skompresowany strumień obiektów (/ObjStm); wtedy tablica xref też jest strumieniem."""
    tr = dane[dane.rindex(b'trailer'):]; prev = int(re.findall(rb'startxref\s+(\d+)', dane)[-1]); rozmiar = int(re.search(rb'/Size\s+(\d+)', tr).group(1))
    root = re.search(rb'/Root\s+\d+\s+\d+\s+R', tr).group(0); info = (re.search(rb'/Info\s+\d+\s+\d+\s+R', tr) or re.search(rb'^', tr)).group(0); idd = (re.search(rb'/ID\s*\[[^\]]*\]', tr) or re.search(rb'^', tr)).group(0)
    wyj, poz = bytearray(dane if dane.endswith(b'\n') else dane + b'\n'), {}
    nowy = max([rozmiar - 1, *obiekty, *(w_strumieniu or {})]) + 1
    def dodaj(nr, sl, strumien=None):
        poz[nr] = len(wyj)
        if strumien is None: wyj.extend(b'%d 0 obj\n%s\nendobj\n' % (nr, sl))
        else: wyj.extend(b'%d 0 obj\n%s /Length %d >>\nstream\n%s\nendstream\nendobj\n' % (nr, sl.rstrip()[:-2], len(strumien), strumien))
    for nr, o in obiekty.items(): dodaj(nr, *(o if isinstance(o, tuple) else (o,)))
    if not w_strumieniu:
        xref = len(wyj); wyj.extend(b'xref\n' + b''.join(b'%d 1\n%010d 00000 n \n' % (nr, poz[nr]) for nr in sorted(poz)))
        wyj.extend(b'trailer\n<< /Size %d %s %s %s /Prev %d >>\nstartxref\n%d\n%%%%EOF\n' % (max(rozmiar, nowy), root, info, idd, prev, xref)); return bytes(wyj)
    nr_s, nr_x = nowy, nowy + 1; nag = tresc = b''
    for nr, sl in w_strumieniu.items(): nag += b'%d %d ' % (nr, len(tresc)); tresc += sl + b'\n'
    dodaj(nr_s, b'<< /Type /ObjStm /N %d /First %d /Filter /FlateDecode >>' % (len(w_strumieniu), len(nag)), zlib.compress(nag + tresc))
    wiersze = {nr: b'\x01' + poz[nr].to_bytes(4, 'big') + b'\0\0' for nr in poz}
    for j, nr in enumerate(w_strumieniu): wiersze[nr] = b'\x02' + nr_s.to_bytes(4, 'big') + j.to_bytes(2, 'big')
    xref = len(wyj); wiersze[nr_x] = b'\x01' + xref.to_bytes(4, 'big') + b'\0\0'
    dodaj(nr_x, b'<< /Type /XRef /Size %d /W [1 4 2] /Index [%s] %s %s %s /Prev %d >>' % (nr_x + 1, b' '.join(b'%d 1' % nr for nr in sorted(wiersze)), root, info, idd, prev), b''.join(wiersze[nr] for nr in sorted(wiersze)))
    wyj.extend(b'startxref\n%d\n%%%%EOF\n' % xref); return bytes(wyj)

jan, k_jan, c_jan = podpisujacy('Jan', 'Testowy', '90010112349')
anna, _, _ = podpisujacy('Anna', 'Kowalska', '85010100000')
jan_inny_pesel, _, _ = podpisujacy('Jan', 'Testowy', '85010100000')
jan_bez_pesel, _, _ = podpisujacy('Jan', 'Testowy', None)
jan_ec, _, _ = podpisujacy('Jan', 'Testowy', '90010112349', ec_klucz=True)
jan_sam, k_sam, c_sam = podpisujacy('Jan', 'Testowy', '90010112349', samopodpisany=True)

ok = podpisz_pdf(ORYG, jan); zapisz('ok_jan.pdf', ok)
zapisz('inna_osoba.pdf', podpisz_pdf(ORYG, anna))
zapisz('inny_pesel.pdf', podpisz_pdf(ORYG, jan_inny_pesel))
zapisz('bez_pesela_w_certyfikacie.pdf', podpisz_pdf(ORYG, jan_bez_pesel))
zapisz('ecdsa_jan.pdf', podpisz_pdf(ORYG, jan_ec))
# zmieniony po podpisaniu: jeden bajt wewnątrz podpisanego zakresu (w treści oryginału)
z = bytearray(ok); z[len(ORYG) // 2] ^= 1; zapisz('zmieniony_po_podpisie.pdf', bytes(z))
# dopisek po podpisie (aktualizacja przyrostowa) — podpis nie obejmuje już całego pliku
zapisz('dopisek_po_podpisie.pdf', ok + b'\n% dopisek po podpisaniu\n')
# dwa podpisy: Jan, potem Anna (drugi obejmuje pierwszy)
zapisz('dwa_podpisy.pdf', podpisz_pdf(podpisz_pdf(ORYG, jan, 'Podpis1'), anna, 'Podpis2'))
# PDF zapisany na nowo przy podpisywaniu (bajty oryginału nie są początkiem pliku) — nowy plik z tymi samymi strumieniami
nowy = io.BytesIO(); copy_into_new_writer(PdfFileReader(io.BytesIO(ORYG))).write(nowy)
zapisz('przepisany.pdf', podpisz_pdf(nowy.getvalue(), jan))
# zmiany zapisane w pliku PRZED podpisaniem (np. „Zapisz” w Acrobacie po dopisaniu tekstu, potem podpis na gov.pl): podpis je obejmuje, więc skrót się zgadza,
# ale to już nie jest wygenerowany dokument — strona zamalowana na biało z inną kwotą, podmieniony strumień treści, adnotacja z tekstem (też schowana w skompresowanym strumieniu obiektów)
ZAMALOWANA = b'q 1 1 1 rg 0 0 595 842 re f Q BT /F1 40 Tf 1 0 0 1 60 400 Tm (KWOTA 9999.00 zl) Tj ET'
STRONA = b'<< /Contents %s /Parent 1 0 R /Resources 19 0 R /Type /Page%s >>'
ADNOTACJA = b'<< /Type /Annot /Subtype /FreeText /Rect [300 700 560 740] /Contents (KWOTA 9999.00 zl) /DA (/Helv 14 Tf 0 g) /P 3 0 R >>'
zapisz('zmieniony_przed_podpisem.pdf', podpisz_pdf(aktualizacja(ORYG, {21: (b'<< >>', ZAMALOWANA), 3: STRONA % (b'[4 0 R 21 0 R]', b'')}), jan))
zapisz('podmieniona_tresc_przed_podpisem.pdf', podpisz_pdf(aktualizacja(ORYG, {4: (b'<< >>', ZAMALOWANA)}), jan))
zapisz('adnotacja_przed_podpisem.pdf', podpisz_pdf(aktualizacja(ORYG, {21: ADNOTACJA, 3: STRONA % (b'4 0 R', b' /Annots [21 0 R]')}), jan))
zapisz('adnotacja_w_strumieniu_obiektow.pdf', podpisz_pdf(aktualizacja(ORYG, {}, {3: STRONA % (b'4 0 R', b' /Annots [21 0 R]'), 21: ADNOTACJA}), jan))
zapisz('strumien_obiektow_bez_zmian.pdf', podpisz_pdf(aktualizacja(ORYG, {}, {20: b'<< /CreationDate (D:20261027132020Z) /Producer (Acrobat) >>'}), jan))
# po podpisie Jana ktoś zmienia treść strony i podpisuje całość (Anna): podpis Jana tych zmian nie obejmuje
p1 = podpisz_pdf(ORYG, jan, 'Podpis1'); annots = re.findall(rb'/Annots\s*\[[^\]]*\]', p1)[-1]
zapisz('zmiana_miedzy_podpisami.pdf', podpisz_pdf(aktualizacja(p1, {30: (b'<< >>', ZAMALOWANA), 3: STRONA % (b'[4 0 R 30 0 R]', b' ' + annots)}), anna, 'Podpis2'))
# certyfikat samopodpisany (wystawca = podpisujący, jak „cyfrowy identyfikator” z Acrobata) — imię i PESEL się zgadzają, ale to nie jest podpis zaufany ani kwalifikowany
zapisz('samopodpisany.pdf', podpisz_pdf(ORYG, jan_sam))
# podpis z pustym znacznikiem (pole bez podpisu)
w = IncrementalPdfFileWriter(io.BytesIO(ORYG)); fields.append_signature_field(w, fields.SigFieldSpec('Puste')); o = io.BytesIO(); w.write(o); zapisz('pole_bez_podpisu.pdf', o.getvalue())

# ---- XAdES (osobny plik podpisu): wartość SignedInfo kanonizujemy lxml-em, więc to niezależna kontrola naszej kanonizacji ----
zapisz('ok.xades', xades(ORYG, k_jan, c_jan))
zapisz('ok_c14n_klasyczna.xades', xades(ORYG, k_jan, c_jan, c14n='http://www.w3.org/TR/2001/REC-xml-c14n-20010315'))
zapisz('zly_skrot.xades', xades(ORYG, k_jan, c_jan, zly_skrot=True))
zapisz('zepsuty_podpis.xades', xades(ORYG, k_jan, c_jan, psuj_podpis=True))
zapisz('samopodpisany.xades', xades(ORYG, k_sam, c_sam))
import shutil; shutil.rmtree(os.path.join(KAT, '_tmp'), ignore_errors=True)
print('gotowe')
