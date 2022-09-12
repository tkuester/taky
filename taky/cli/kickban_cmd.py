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

    argp.add_argument(
        "-j",
        "--json",
        dest="json",
        default=False,
        action="store_true",
        help="Output the status in JSON",
    )

    argp.add_argument("name", help="Name for client")


def kickban(args):
    try:
        load_config(args.cfg_file)
    except (OSError, configparser.ParsingError) as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    if args.socket is None:
        args.socket = os.path.join(config.get("taky", "root_dir"), "taky-mgmt.sock")

    start = time.time()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        sock.connect(args.socket)
        cmd = json.dumps({"cmd": "kickban", "user": args.name}).encode()
        sock.sendall(cmd + b"\0")

        sock.settimeout(1)
        data = b""
        done = False
        while (time.time() - start) < 5:
            try:
                recv = sock.recv(4096)
            except socket.timeout:
                continue

            if len(recv) == 0:
                break
            data += recv

            try:
                data.index(b"\0")
                done = True
                break
            except ValueError:
                continue

        sock.shutdown(socket.SHUT_RDWR)

        if not done:
            print("ERROR: No response from server", file=sys.stderr)
            return 1

        data = data[:-1].decode()
        stat = json.loads(data)

        if args.json:
            print(json.dumps(stat))
        else:
            revoked_sns = stat.get("revoked_sns", [])
            if len(revoked_sns) == 0:
                print(f"Unable to find certificates for user {args.name}")
                return 0

            print(f"Revoked certificate SNs for {args.name}:")
            for revoked_sn in revoked_sns:
                print(f" - {revoked_sn:040x}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: Invalid data in response: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(
            f"ERROR: Unable to connect to mgmt socket: {args.socket}", file=sys.stderr
        )
        print("       Is taky running?", file=sys.stderr)
        return 1
    except socket.error as exc:
        print("ERROR: Socket error:", exc)
        if exc.errno in [2, 111]:
            print("       Is taky running?", file=sys.stderr)
        return 1
    finally:
        sock.close()
        sock = None

    return 0
