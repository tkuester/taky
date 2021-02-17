"""
Revenge of the Certs

Borrowed heavily from ATAK-Certs
https://github.com/lennisthemenace/ATAK-Certs
"""

import os
import random

from OpenSSL import crypto

def make_ca(crt_path, key_path, n_years=10):
    ca_key = crypto.PKey()
    ca_key.generate_key(crypto.TYPE_RSA, 2048)

    cert = crypto.X509()
    cert.get_subject().CN = "CA"
    cert.set_serial_number(0)
    cert.set_version(2)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(31536000 * n_years)
    cert.set_issuer(cert.get_subject())
    cert.add_extensions([crypto.X509Extension(b'basicConstraints', False, b'CA:TRUE'),
                         crypto.X509Extension(b'keyUsage', False, b'keyCertSign, cRLSign')])
    cert.set_pubkey(ca_key)
    cert.sign(ca_key, "sha256")

    p12 = crypto.PKCS12()

    old = os.umask(0o077)
    try:
        with open(key_path, "wb") as fp:
            fp.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, ca_key))
    except Exception as e:
        raise e
    finally:
        os.umask(old)

    with open(crt_path, "wb") as fp:
        fp.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    os.umask(old)

def make_cert(path, f_name, hostname, cert_pw, ca, n_years=10, dump_pem=False):
    (ca_crt, ca_key) = ca
    with open(ca_key, "r") as fp:
        cakey = crypto.load_privatekey(crypto.FILETYPE_PEM, fp.read())

    with open(ca_crt, "r") as fp:
        capem = crypto.load_certificate(crypto.FILETYPE_PEM, fp.read())

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
    p12data = p12.export(passphrase=bytes(cert_pw, encoding='UTF-8'))

    with open(os.path.join(path, f"{f_name}.p12"), "wb") as fp:
        fp.write(p12data)

    if not dump_pem:
        return

    old = os.umask(0o077)
    try:
        with open(os.path.join(path, f"{f_name}.key"), "wb") as fp:
            fp.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, cli_key))
    except Exception as e:
        raise e
    finally:
        os.umask(old)

    with open(os.path.join(path, f"{f_name}.crt"), "wb") as fp:
        fp.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
