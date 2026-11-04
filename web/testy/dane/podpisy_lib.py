"""Wspólne funkcje do tworzenia testowych podpisów elektronicznych (PAdES i XAdES). Używane przez generuj_podpisy.py i podpisz_pliki.py.
Wymaga: pip install pyhanko lxml cryptography. Certyfikaty są testowe, podpisane własnym kluczem pod nazwą testowego centrum certyfikacji (samopodpisany=True: wystawca = podmiot); imiona, nazwiska i PESEL-e wymyślone."""
import base64, datetime, hashlib, io, os, tempfile
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from lxml import etree
from asn1crypto import cms as acms
from pyhanko.sign import signers, fields
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.signers.pdf_signer import PdfSigner, PdfSignatureMetadata

def certyfikat(imie, nazwisko, pesel, klucz, nazwa_poz=None, samopodpisany=False):
    """samopodpisany=True: wystawca = podmiot (jak „cyfrowy identyfikator” utworzony w Acrobacie), zamiast testowego centrum certyfikacji."""
    pod = [x509.NameAttribute(NameOID.COMMON_NAME, f'{imie} {nazwisko}'), x509.NameAttribute(NameOID.GIVEN_NAME, imie), x509.NameAttribute(NameOID.SURNAME, nazwisko),
           x509.NameAttribute(NameOID.COUNTRY_NAME, 'PL')]
    if pesel: pod.insert(3, x509.NameAttribute(NameOID.SERIAL_NUMBER, f'PNOPL-{pesel}'))
    n = x509.Name(pod); wyst = n if samopodpisany else x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Testowe Centrum Certyfikacji (nie do użytku)'), x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'PMT Planer testy')])
    t0 = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    b = (x509.CertificateBuilder().subject_name(n).issuer_name(wyst).public_key(klucz.public_key()).serial_number(x509.random_serial_number())
         .not_valid_before(t0).not_valid_after(t0 + datetime.timedelta(days=3650))
         .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=True, key_encipherment=False, data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
         .add_extension(x509.SubjectKeyIdentifier.from_public_key(klucz.public_key()), critical=False))
    if samopodpisany: b = b.add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(klucz.public_key()), critical=False)
    h = hashes.SHA256()
    return b.sign(klucz, h)

def podpisujacy(imie, nazwisko, pesel, ec_klucz=False, samopodpisany=False):
    klucz = ec.generate_private_key(ec.SECP256R1()) if ec_klucz else rsa.generate_private_key(65537, 2048)
    cert = certyfikat(imie, nazwisko, pesel, klucz, samopodpisany=samopodpisany)
    sciezka = tempfile.mkdtemp(prefix='podpisy_')
    kf, cf = os.path.join(sciezka, 'k.pem'), os.path.join(sciezka, 'c.pem')
    open(kf, 'wb').write(klucz.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    open(cf, 'wb').write(cert.public_bytes(serialization.Encoding.PEM))
    return signers.SimpleSigner.load(kf, cf), klucz, cert

def podpisz_pdf(dane, sig, nazwa_pola='Podpis', md='sha256', name='Jan Testowy', reason=None):
    w = IncrementalPdfFileWriter(io.BytesIO(dane))
    out = io.BytesIO()
    PdfSigner(PdfSignatureMetadata(field_name=nazwa_pola, md_algorithm=md, name=name, reason=reason), signer=sig, new_field_spec=fields.SigFieldSpec(sig_field_name=nazwa_pola)).sign_pdf(w, output=out)
    return out.getvalue()

# ---- podpis zaufany z gov.pl: PIECZĘĆ Ministra (certyfikat Ministerstwa Cyfryzacji, osoba tylko w słowniku podpisu), RSA PKCS#1 v1.5 z DigestInfo BEZ pola NULL, bez atrybutu czasu ----
# Tak wygląda prawdziwy plik z gov.pl (sprawdzony ręcznie: Poppler i OpenSSL odrzucają go jako „bad signature”, bo są ścisłe, a podpis jest poprawny). Tu: tylko wymyślone dane i testowe klucze.
PREFIKS_SHA256_BEZ_NULL = bytes.fromhex('302f300b06096086480165030402010420')
ORG_ID = x509.ObjectIdentifier('2.5.4.97')
def certyfikat_pieczec(klucz, samopodpisany=False, cn='Minister do spraw informatyzacji - pieczęć podpisu zaufanego', org='Ministerstwo Cyfryzacji', nip='VATPL-5252955037'):
    n = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn), x509.NameAttribute(NameOID.ORGANIZATION_NAME, org), x509.NameAttribute(ORG_ID, nip), x509.NameAttribute(NameOID.COUNTRY_NAME, 'PL')])
    wyst = n if samopodpisany else x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Testowe Centrum Kwalifikowane (nie do użytku)'), x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'PMT Planer testy')])
    t0 = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    b = (x509.CertificateBuilder().subject_name(n).issuer_name(wyst).public_key(klucz.public_key()).serial_number(x509.random_serial_number())
         .not_valid_before(t0).not_valid_after(t0 + datetime.timedelta(days=3650))
         .add_extension(x509.SubjectKeyIdentifier.from_public_key(klucz.public_key()), critical=False))
    if samopodpisany: b = b.add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(klucz.public_key()), critical=False)
    return b.sign(klucz, hashes.SHA256())

class _PodpisBezNull(signers.SimpleSigner):
    klucz_rsa = None; bez_czasu = False; psuj = False; z_null = False
    def sign_raw(self, data, digest_algorithm):
        t = hashlib.new(digest_algorithm, data).digest()
        if self.z_null: t = bytes.fromhex('3031300d060960864801650304020105000420') + t       # zwykły zapis (z NULL) — do porównania
        else: t = PREFIKS_SHA256_BEZ_NULL + t
        liczby = self.klucz_rsa.private_numbers(); n, k = liczby.public_numbers.n, (liczby.public_numbers.n.bit_length() + 7) // 8
        em = b'\x00\x01' + b'\xff' * (k - len(t) - 3) + b'\x00' + t
        s = bytearray(pow(int.from_bytes(em, 'big'), liczby.d, n).to_bytes(k, 'big'))
        if self.psuj: s[100] ^= 1
        return bytes(s)
    async def signed_attrs(self, *a, **kw):
        attrs = await super().signed_attrs(*a, **kw)
        if self.bez_czasu and attrs is not None: attrs = acms.CMSAttributes([x for x in attrs if x['type'].native != 'signing_time'])
        return attrs

def podpisujacy_bez_null(imie=None, nazwisko=None, pesel=None, pieczec=False, samopodpisany=False, bez_czasu=False, psuj=False, z_null=False):
    """Podpisujący RSA, który zapisuje DigestInfo bez NULL: zwykły certyfikat osoby (imie, nazwisko, pesel) albo pieczęć podpisu zaufanego (pieczec=True)."""
    klucz = rsa.generate_private_key(65537, 2048)
    cert = certyfikat_pieczec(klucz, samopodpisany) if pieczec else certyfikat(imie, nazwisko, pesel, klucz, samopodpisany=samopodpisany)
    sciezka = tempfile.mkdtemp(prefix='podpisy_'); kf, cf = os.path.join(sciezka, 'k.pem'), os.path.join(sciezka, 'c.pem')
    open(kf, 'wb').write(klucz.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    open(cf, 'wb').write(cert.public_bytes(serialization.Encoding.PEM))
    sig = signers.SimpleSigner.load(kf, cf); sig.__class__ = _PodpisBezNull
    sig.klucz_rsa, sig.bez_czasu, sig.psuj, sig.z_null = klucz, bez_czasu, psuj, z_null
    return sig

def powod_pieczeci(imie_nazwisko, pesel, pz_id='20200430135451'):
    """Tekst pola /Reason, jaki wpisuje gov.pl (po polsku, z imieniem WIELKIMI LITERAMI)."""
    return f'Opatrzono pieczęcią ministra właściwego do spraw informatyzacji w imieniu: {imie_nazwisko.upper()}, PESEL: {pesel}, PZ ID: {pz_id}'

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

