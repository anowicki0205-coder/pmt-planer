"""Wspólne funkcje do tworzenia testowych podpisów elektronicznych (PAdES i XAdES). Używane przez generuj_podpisy.py i podpisz_pliki.py.
Wymaga: pip install pyhanko lxml cryptography. Certyfikaty są testowe, samopodpisane; imiona, nazwiska i PESEL-e wymyślone."""
import base64, datetime, hashlib, io, os, tempfile
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from lxml import etree
from pyhanko.sign import signers, fields
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.signers.pdf_signer import PdfSigner, PdfSignatureMetadata

def certyfikat(imie, nazwisko, pesel, klucz, nazwa_poz=None):
    pod = [x509.NameAttribute(NameOID.COMMON_NAME, f'{imie} {nazwisko}'), x509.NameAttribute(NameOID.GIVEN_NAME, imie), x509.NameAttribute(NameOID.SURNAME, nazwisko),
           x509.NameAttribute(NameOID.COUNTRY_NAME, 'PL')]
    if pesel: pod.insert(3, x509.NameAttribute(NameOID.SERIAL_NUMBER, f'PNOPL-{pesel}'))
    n = x509.Name(pod); wyst = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Testowe Centrum Certyfikacji (nie do użytku)'), x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'PMT Planer testy')])
    t0 = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    b = (x509.CertificateBuilder().subject_name(n).issuer_name(wyst).public_key(klucz.public_key()).serial_number(x509.random_serial_number())
         .not_valid_before(t0).not_valid_after(t0 + datetime.timedelta(days=3650))
         .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=True, key_encipherment=False, data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
         .add_extension(x509.SubjectKeyIdentifier.from_public_key(klucz.public_key()), critical=False))
    h = hashes.SHA256()
    return b.sign(klucz, h)

def podpisujacy(imie, nazwisko, pesel, ec_klucz=False):
    klucz = ec.generate_private_key(ec.SECP256R1()) if ec_klucz else rsa.generate_private_key(65537, 2048)
    cert = certyfikat(imie, nazwisko, pesel, klucz)
    sciezka = tempfile.mkdtemp(prefix='podpisy_')
    kf, cf = os.path.join(sciezka, 'k.pem'), os.path.join(sciezka, 'c.pem')
    open(kf, 'wb').write(klucz.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    open(cf, 'wb').write(cert.public_bytes(serialization.Encoding.PEM))
    return signers.SimpleSigner.load(kf, cf), klucz, cert

def podpisz_pdf(dane, sig, nazwa_pola='Podpis', md='sha256'):
    w = IncrementalPdfFileWriter(io.BytesIO(dane))
    out = io.BytesIO()
    PdfSigner(PdfSignatureMetadata(field_name=nazwa_pola, md_algorithm=md, name='Jan Testowy'), signer=sig, new_field_spec=fields.SigFieldSpec(sig_field_name=nazwa_pola)).sign_pdf(w, output=out)
    return out.getvalue()

DS = 'http://www.w3.org/2000/09/xmldsig#'
def xades(dokument, klucz, cert, c14n='http://www.w3.org/2001/10/xml-exc-c14n#', nazwa='dokument.pdf', zly_skrot=False, psuj_podpis=False):
    skrot = hashlib.sha256(dokument).digest()
    if zly_skrot: skrot = hashlib.sha256(b'inny dokument').digest()
    cert_b64 = base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode()
    xml = f'''<ds:Signature xmlns:ds="{DS}" Id="Sig1"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="{c14n}"/><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
<ds:Reference URI="{nazwa}"><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>{base64.b64encode(skrot).decode()}</ds:DigestValue></ds:Reference></ds:SignedInfo>
<ds:SignatureValue>PODPIS</ds:SignatureValue><ds:KeyInfo><ds:X509Data><ds:X509Certificate>{cert_b64}</ds:X509Certificate></ds:X509Data></ds:KeyInfo>
<ds:Object><xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Target="#Sig1"><xades:SignedProperties Id="SP"><xades:SignedSignatureProperties><xades:SigningTime>2026-09-30T10:15:00Z</xades:SigningTime></xades:SignedSignatureProperties></xades:SignedProperties></xades:QualifyingProperties></ds:Object></ds:Signature>'''
    # kanonizacja SignedInfo w kontekście całego dokumentu (przestrzeń ds dziedziczona od Signature)
    korzen = etree.fromstring(xml.encode()); si = korzen.find('{%s}SignedInfo' % DS)
    kan = etree.tostring(si, method='c14n', exclusive=('exc-c14n' in c14n))
    podpis = klucz.sign(kan, padding.PKCS1v15(), hashes.SHA256())
    if psuj_podpis: podpis = bytes([podpis[0] ^ 1]) + podpis[1:]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + xml.replace('PODPIS', base64.b64encode(podpis).decode())).encode()

