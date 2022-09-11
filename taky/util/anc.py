"""
TAK Wars: Episode IV - A New Cert

Borrowed heavily from mitmproxy
https://github.com/mitmproxy/mitmproxy
"""

import os
from datetime import datetime as dt, timedelta
import ipaddress

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12, PrivateFormat

from taky.config import app_config


def load_certificate(crt_path, key_path, password=None):
    """
    Utility method to load a certificate in PEM format

    @param crt_path Where to load the certificate
    @param key_path Where to load the key
    @param password The password for the key (default as None)
    @return A tuple of (crt, key)
    """
    with open(crt_path, "rb") as crt_fp:
        ca_crt_bytes = crt_fp.read()
    with open(key_path, "rb") as key_fp:
        ca_key_bytes = key_fp.read()

    ca_crt = x509.load_pem_x509_certificate(ca_crt_bytes)
    ca_key = serialization.load_pem_private_key(ca_key_bytes, password)

    return (ca_crt, ca_key)


def write_certificate(crt_path, key_path, crt, key):
    """
    Utility method to write a certificate in unencrypted PEM format

    @param crt_path Where to write the certificate
    @param key_path Where to write the key
    @param crt      The certificate
    @param key      The key
    """
    old = os.umask(0o077)
    try:
        privkey_bytes = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(key_path, "wb") as key_fp:
            key_fp.write(privkey_bytes)
    except Exception as exc:
        raise exc
    finally:
        os.umask(old)

    with open(crt_path, "wb") as crt_fp:
        pubkey_bytes = crt.public_bytes(serialization.Encoding.PEM)
        crt_fp.write(pubkey_bytes)


def make_ca(crt_path, key_path, n_years=10):
    """
    Build a certificate authority

    @param crt_path  Where to write the ca certificate
    @param key_path  Where to write the ca key
    @param n_years   How many years the CA should be valid for
    """
    now = dt.now()

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "taky"),
        ]
    )

    builder = x509.CertificateBuilder()
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.subject_name(name)
    builder = builder.not_valid_before(now - timedelta(days=1))
    builder = builder.not_valid_after(now + timedelta(days=(365 * n_years)))
    builder = builder.issuer_name(name)
    builder = builder.public_key(private_key.public_key())
    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
        critical=False,
    )

    builder = builder.add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True
    )
    builder = builder.add_extension(
        x509.ExtendedKeyUsage(
            [ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]
        ),
        critical=False,
    )
    builder = builder.add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    )

    cert = builder.sign(private_key=private_key, algorithm=hashes.SHA256())  # type: ignore

    write_certificate(crt_path, key_path, cert, private_key)


def make_cert(
    path,
    f_name,
    hostname,
    cert_pw,
    cert_auth,
    n_years=2,
    dump_pem=False,
    key_in_pem=True,
    is_server_cert=True,
):
    """
    Make an SSL certificate and p12 file

    @param path      The directory to create the certificate in
    @param f_name    The base name to write the certificate to
    @param hostname  The certificate hostname to use (often equal to f_name)
    @param cert_pw   The password to use for the P12 file
    @param cert_auth A tuple of paths to (ca_crt, ca_key)
    @param n_years   How many years the certificate should be valid for
    @param dump_pem  True if you wish to keep the .crt/.key file
    """
    now = dt.now()

    # Load CA
    (ca_crt_path, ca_key_path) = cert_auth
    (ca_crt, ca_key) = load_certificate(ca_crt_path, ca_key_path)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    builder = x509.CertificateBuilder()
    builder = builder.issuer_name(ca_crt.subject)
    builder = builder.public_key(private_key.public_key())
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.not_valid_before(now - timedelta(days=2))
    builder = builder.not_valid_after(now + timedelta(days=(365 * n_years)))
    builder = builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True
    )
    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
        critical=False,
    )
    builder = builder.add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(
            ca_crt.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value
        ),
        critical=False,
    )

    # Add Server / Client Auth
    if is_server_cert:
        builder = builder.add_extension(
            x509.ExtendedKeyUsage(
                [ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]
            ),
            critical=False,
        )
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
    else:
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False
        )
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

    commonname = hostname
    organization = None
    subject = []
    is_valid_commonname = commonname is not None and len(commonname) < 64
    if is_valid_commonname:
        subject.append(x509.NameAttribute(NameOID.COMMON_NAME, commonname))
    if organization is not None:
        subject.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization))
    builder = builder.subject_name(x509.Name(subject))

    # Add SubjectAltName (if server)
    if is_server_cert:
        sans = [hostname]
        ss: list[x509.GeneralName] = []
        for x in sans:
            try:
                ip = ipaddress.ip_address(x)
            except ValueError:
                ss.append(x509.DNSName(x))
            else:
                ss.append(x509.IPAddress(ip))
        # RFC 5280 §4.2.1.6: subjectAltName is critical if subject is empty.
        builder = builder.add_extension(
            x509.SubjectAlternativeName(ss), critical=not is_valid_commonname
        )

    cert = builder.sign(private_key=ca_key, algorithm=hashes.SHA256())  # type: ignore

    if dump_pem:
        key_path = os.path.join(path, f"{f_name}.key")
        crt_path = os.path.join(path, f"{f_name}.crt")

        write_certificate(crt_path, key_path, cert, private_key)

    ca_p12 = pkcs12.PKCS12Certificate(cert=ca_crt, friendly_name="CA".encode())

    kseb = PrivateFormat.PKCS12.encryption_builder()
    kseb = kseb.kdf_rounds(1)
    kseb = kseb.hmac_hash(hashes.SHA1())
    kseb = kseb.key_cert_algorithm(pkcs12.PBES.PBESv1SHA1And3KeyTripleDESCBC)

    p12_dat = pkcs12.serialize_key_and_certificates(  # type: ignore
        name=hostname.encode(),
        key=private_key if key_in_pem else None,
        cert=cert,
        cas=[ca_p12],
        encryption_algorithm=kseb.build(cert_pw.encode()),
    )

    p12_path = os.path.join(path, f"{f_name}.p12")
    with open(p12_path, "wb") as p12_fp:
        p12_fp.write(p12_dat)

    return cert


class CertificateDatabase:
    def __init__(self):
        self.cert_db_path = app_config.get("ssl", "cert_db")

        self.cert_db_sn = {}
        self.read_cert_db()

    def read_cert_db(self):
        self.cert_db_sn = {}

        if not os.path.exists(self.cert_db_path):
            return

        with open(self.cert_db_path, "r", encoding="utf8") as fp:
            for line in fp.readlines():
                line = line.strip().split("\t")
                if len(line) != 5:
                    continue

                (status, issued, expires, serial_num, name) = line
                issued = dt.fromisoformat(issued)
                expires = dt.fromisoformat(expires)
                serial_num = int(serial_num, 16)

                cert = {
                    "status": status,
                    "issued": issued,
                    "expires": expires,
                    "serial_num": serial_num,
                    "name": name,
                }

                self.cert_db_sn[serial_num] = cert

    def revoke_certificate(self, serial_num, revocation_date=None):
        if serial_num not in self.cert_db_sn:
            raise IndexError("Unable to find certificate")

        now = dt.now()
        if revocation_date is None:
            revocation_date = now

        self.cert_db_sn[serial_num]["status"] = "R"
        self.cert_db_sn[serial_num]["expires"] = revocation_date

        self.write_cert_db()

    def add_certificate(self, cert):
        names = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if len(names) != 1:
            raise ValueError("Certificate must have exactly one CommonName")
        common_name = names[0].value

        self.cert_db_sn[cert.serial_number] = {
            "status": "V",
            "issued": cert.not_valid_before,
            "expires": cert.not_valid_after,
            "serial_num": cert.serial_number,
            "name": common_name,
        }

        self.write_cert_db()

    def get_certificates_by_name(self, name):
        for record in self.cert_db_sn.values():
            if record["name"] == name:
                yield record

    def get_certificate_by_serial(self, serial_num):
        if isinstance(serial_num, str):
            try:
                serial_num = int(serial_num, 16)
            except:
                return None

        return self.cert_db_sn.get(serial_num)

    def write_cert_db(self):
        with open(self.cert_db_path, "w", encoding="utf8") as fp:
            for record in self.cert_db_sn.values():
                line = [
                    record["status"],
                    record["issued"].isoformat(),
                    record["expires"].isoformat(),
                    f"{record['serial_num']:040x}",
                    record["name"],
                ]
                line = "\t".join(line) + "\n"
                fp.write(line)
