#!/usr/bin/env python3
"""Tworzy testowe podpisy elektroniczne (PAdES w PDF i XAdES obok pliku) dla testy/dane/podpisy/oryg.pdf — przypadki dobre i złe do testu js/weryfikacja.js.
Wymaga:  pip install pyhanko lxml cryptography      Uruchom:  python generuj_podpisy.py      (wyniki w testy/dane/podpisy/; są też zapisane w repozytorium, więc test ich nie wymaga)"""
import io, os, shutil
from podpisy_lib import *
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.writer import copy_into_new_writer

KAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'podpisy'); os.makedirs(KAT, exist_ok=True)
ORYG = open(os.path.join(KAT, 'oryg.pdf'), 'rb').read()
def zapisz(nazwa, dane): open(os.path.join(KAT, nazwa), 'wb').write(dane); print('  ', nazwa, len(dane), 'B')

jan, k_jan, c_jan = podpisujacy('Jan', 'Testowy', '90010112349')
anna, _, _ = podpisujacy('Anna', 'Kowalska', '85010100000')
jan_inny_pesel, _, _ = podpisujacy('Jan', 'Testowy', '85010100000')
jan_bez_pesel, _, _ = podpisujacy('Jan', 'Testowy', None)
jan_ec, _, _ = podpisujacy('Jan', 'Testowy', '90010112349', ec_klucz=True)

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
# podpis z pustym znacznikiem (pole bez podpisu)
w = IncrementalPdfFileWriter(io.BytesIO(ORYG)); fields.append_signature_field(w, fields.SigFieldSpec('Puste')); o = io.BytesIO(); w.write(o); zapisz('pole_bez_podpisu.pdf', o.getvalue())

# ---- XAdES (osobny plik podpisu): wartość SignedInfo kanonizujemy lxml-em, więc to niezależna kontrola naszej kanonizacji ----
zapisz('ok.xades', xades(ORYG, k_jan, c_jan))
zapisz('ok_c14n_klasyczna.xades', xades(ORYG, k_jan, c_jan, c14n='http://www.w3.org/TR/2001/REC-xml-c14n-20010315'))
zapisz('zly_skrot.xades', xades(ORYG, k_jan, c_jan, zly_skrot=True))
zapisz('zepsuty_podpis.xades', xades(ORYG, k_jan, c_jan, psuj_podpis=True))
import shutil; shutil.rmtree(os.path.join(KAT, '_tmp'), ignore_errors=True)
print('gotowe')
