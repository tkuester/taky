import os
import sys
import time
import socket
import json
from collections import namedtuple
import configparser

from taky.util import pprinttable, seconds_to_human, anc
from taky.config import load_config
from taky.config import app_config as config


def kickban_reg(subp):
    argp = subp.add_parser("kickban", help="Kick and banish a user")

    argp.add_argument(
        "-U",
        dest="socket",
        default=None,
        help="Explicitly specify a socket to connect to",
    )

    argp.add_argument("name", help="Name for client")


def kickban(args):
    try:
        load_config(args.cfg_file)
    except (OSError, configparser.ParsingError) as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    cdb = anc.CertificateDatabase()

    cert = cdb.get_certificate_by_name(args.name)
    if cert is None:
        print(f"ERROR: Unable to find client certificate for {args.name}")
        return 1

    cdb.revoke_certificate(cert["serial_num"])
    print(f"Revoked certificate for {args.name}")

    return 0
