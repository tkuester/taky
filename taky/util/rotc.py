"""
Revenge of the Certs

Borrowed heavily from ATAK-Certs
https://github.com/lennisthemenace/ATAK-Certs
"""

import os
import random

from OpenSSL import crypto


def make_ca(crt_path, key_path, n_years=10):
    """
    Build a certificate authority

    @param crt_path  Where to write the ca certificate
    @param key_path  Where to write the ca key
    @param n_years   How many years the CA should be valid for
    """
    ca_key = crypto.PKey()
    ca_key.generate_key(crypto.TYPE_RSA, 2048)

    cert = crypto.X509()
    cert.get_subject().CN = "CA"
    cert.set_serial_number(0)
    cert.set_version(2)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(31536000 * n_years)
    cert.set_issuer(cert.get_subject())
    cert.add_extensions(
        [
            crypto.X509Extension(b"basicConstraints", False, b"CA:TRUE"),
            crypto.X509Extension(b"keyUsage", False, b"keyCertSign, cRLSign"),
        ]
    )
    cert.set_pubkey(ca_key)
    cert.sign(ca_key, "sha256")

    old = os.umask(0o077)
    try:
        with open(key_path, "wb") as key_fp:
            key_fp.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, ca_key))
    except Exception as exc:
        raise exc
    finally:
        os.umask(old)

    with open(crt_path, "wb") as crt_fp:
        crt_fp.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    os.umask(old)


def make_cert(path, f_name, hostname, cert_pw, cert_auth, n_years=10, dump_pem=False):
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
    (ca_crt, ca_key) = cert_auth
    with open(ca_key, "r") as ca_key_fp:
        cakey = crypto.load_privatekey(crypto.FILETYPE_PEM, ca_key_fp.read())

    with open(ca_crt, "r") as ca_crt_fp:
        capem = crypto.load_certificate(crypto.FILETYPE_PEM, ca_crt_fp.read())

    serialnumber = random.getrandbits(64)
    chain = (capem,)

    cli_key = crypto.PKey()
    cli_key.generate_key(crypto.TYPE_RSA, 2048)

    cert = crypto.X509()
    cert.get_subject().CN = hostname
    cert.set_serial_number(serialnumber)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(31536000 * n_years)
    cert.set_issuer(capem.get_subject())
    cert.set_pubkey(cli_key)
    cert.set_version(2)
    cert.sign(cakey, "sha256")

    p12 = crypto.PKCS12()
    p12.set_privatekey(cli_key)
    p12.set_certificate(cert)
    p12.set_ca_certificates(chain)
    p12data = p12.export(passphrase=bytes(cert_pw, encoding="UTF-8"))

    with open(os.path.join(path, f"{f_name}.p12"), "wb") as p12_fp:
        p12_fp.write(p12data)

    if not dump_pem:
        return

    old = os.umask(0o077)
    try:
        with open(os.path.join(path, f"{f_name}.key"), "wb") as cli_key_fp:
            cli_key_fp.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, cli_key))
    except Exception as exc:
        raise exc
    finally:
        os.umask(old)

    with open(os.path.join(path, f"{f_name}.crt"), "wb") as cli_crt_fp:
        cli_crt_fp.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
