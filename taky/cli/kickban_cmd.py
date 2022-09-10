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

    count = 0
    for cert in cdb.get_certificates_by_name(args.name):
        if cert["status"] == "R":
            continue

        cdb.revoke_certificate(cert["serial_num"])
        print(f"Revoked certificate for {args.name} (SN: {cert['serial_num']:040x})")
        count += 1

    if count == 0:
        print("Unable to find valid certificate for {args.name}")

    return 0
