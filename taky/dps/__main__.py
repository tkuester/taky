import os
import sys
import multiprocessing
import argparse
import configparser
import ssl

from gunicorn.app.base import BaseApplication
from gunicorn.workers.sync import SyncWorker

from taky import __version__
from taky.config import load_config
from taky.config import app_config
from taky.dps import app as taky_dps


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

    def handle_request(self, listener, req, client, addr):
        subject = dict(
            [i for subtuple in client.getpeercert().get("subject") for i in subtuple]
        )
        issuer = dict(
            [i for subtuple in client.getpeercert().get("issuer") for i in subtuple]
        )
        headers = dict(req.headers)
        headers["X-USER"] = subject["commonName"]
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

    try:
        load_config(args.cfg_file)
    except (OSError, configparser.ParsingError) as exc:
        argp.error(exc)

    bind_ip = app_config.get("taky", "bind_ip")
    if bind_ip is None:
        bind_ip = ""

    try:
        port = app_config.getint("dp_server", "port")
        if port <= 0 or port > 65535:
            raise ValueError("Invalid port")
    except ValueError:
        print(
            "[ ERROR ] Invalid port specified for dp_server.port, must be (0,65535]",
            file=sys.stderr,
        )
    except (configparser.NoOptionError, configparser.NoSectionError):
        port = 8443 if app_config.getboolean("ssl", "enabled") else 8080

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
        options["cert_reqs"] = ssl.CERT_REQUIRED
        options["do_handshake_on_connect"] = True
        options["worker_class"] = "taky.dps.__main__.ClientCertificateWorker"

    StandaloneApplication(taky_dps, options).run()
    print("DONE")


if __name__ == "__main__":
    main()
