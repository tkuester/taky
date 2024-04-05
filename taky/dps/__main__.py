import os
import sys
import multiprocessing
import argparse
import configparser
import ssl
import logging

from gunicorn.app.base import BaseApplication
from gunicorn.workers.sync import SyncWorker

from taky import __version__
from taky.config import load_config
from taky.config import app_config
from taky.util import anc
from taky.dps import app as taky_dps
from taky.dps import configure_app


class StandaloneApplication(BaseApplication):
    # 'init' and 'load' methods are implemented by WSGIApplication.
    # pylint: disable=abstract-method

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


# Based on code from
# https://eugene.kovalev.systems/blog/flask_client_auth
class ClientCertificateWorker(SyncWorker):
    """Worker for putting certificate information into the X-USER header variable of the request."""

    cert_db = None

    def handle_request(self, listener, req, client, addr):
        if self.cert_db is None:
            self.cert_db = anc.CertificateDatabase()

        headers = dict(req.headers)
        peer_cert = client.getpeercert()

        # Don't let users specify these header values
        forbidden_keys = [
            "X-USER",
            "X-SERIAL_NUMBER",
            "X-ISSUER",
            "X-REVOKED",
            "X-NOT_BEFORE",
            "X-NOT_AFTER",
        ]
        for keyname in forbidden_keys:
            if keyname in headers:
                headers.pop(keyname)

        if peer_cert:
            subject = dict(
                [i for subtuple in peer_cert.get("subject") for i in subtuple]
            )
            issuer = dict([i for subtuple in peer_cert.get("issuer") for i in subtuple])
            headers["X-USER"] = subject["commonName"]
            headers["X-SERIAL_NUMBER"] = peer_cert.get("serialNumber")

            cert = self.cert_db.get_certificate_by_serial(peer_cert.get("serialNumber"))
            if cert and cert.get("status") == "R":
                headers["X-REVOKED"] = 1

            headers["X-ISSUER"] = issuer["commonName"]
            headers["X-NOT_BEFORE"] = ssl.cert_time_to_seconds(
                client.getpeercert().get("notBefore")
            )
            headers["X-NOT_AFTER"] = ssl.cert_time_to_seconds(
                client.getpeercert().get("notAfter")
            )

        req.headers = list(headers.items())
        super().handle_request(listener, req, client, addr)


def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1


def arg_parse():
    argp = argparse.ArgumentParser(description="Taky command line utility")
    argp.add_argument(
        "-c",
        action="store",
        dest="cfg_file",
        default=None,
        help="Path to configuration file",
    )
    argp.add_argument(
        "-l",
        action="store",
        dest="log_level",
        default="INFO",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Path to configuration file",
    )
    argp.add_argument(
        "--version", action="version", version="%%(prog)s version %s" % __version__
    )

    args = argp.parse_args()

    return (argp, args)


def main():
    """
    Runs the DPS, handy for avoiding a specific gunicorn setup
    """
    (argp, args) = arg_parse()
    logging.basicConfig(level=args.log_level.upper(), stream=sys.stderr)

    try:
        if os.environ.get("TAKY_CONFIG"):
            load_config(os.environ.get("TAKY_CONFIG"), explicit=True)
        elif args.cfg_file:
            load_config(args.cfg_file, explicit=True)
        else:
            load_config()
    except (OSError, configparser.ParsingError) as exc:
        argp.error(str(exc))

    configure_app(app_config)

    bind_ip = app_config.get("taky", "bind_ip")
    port = 8443 if app_config.getboolean("ssl", "enabled") else 8080

    if bind_ip is None:
        bind_ip = ""

    dp_path = app_config.get("dp_server", "upload_path")
    if not os.path.exists(dp_path):
        print("-" * 30, file=sys.stderr)
        print("[ WARNING ] Datapackage directory does not exist!", file=sys.stderr)
        print("            Please create it, or check permissions.", file=sys.stderr)
        print("Current Settings:", file=sys.stderr)
        print("  [dp_server]", file=sys.stderr)
        print(f"  upload_path = {dp_path}", file=sys.stderr)
        print("-" * 30, file=sys.stderr)

    options = {
        "bind": f"{bind_ip}:{port}",
        "workers": number_of_workers(),
        "loglevel": args.log_level,
        "accesslog": "-",
        "access_log_format": '%(t)s "%(r)s" %(s)s %(b)s "%(a)s"',
    }

    if app_config.getboolean("ssl", "enabled"):
        options["ca_certs"] = app_config.get("ssl", "ca")
        options["certfile"] = app_config.get("ssl", "cert")
        options["keyfile"] = app_config.get("ssl", "key")
        options["cert_reqs"] = ssl.CERT_OPTIONAL
        options["do_handshake_on_connect"] = True
        options["worker_class"] = "taky.dps.__main__.ClientCertificateWorker"

    StandaloneApplication(taky_dps, options).run()
    print("DONE")


if __name__ == "__main__":
    main()
