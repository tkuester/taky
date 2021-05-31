import os
import sys
import time
import socket
import json
from collections import namedtuple

from taky.util import pprinttable, seconds_to_human
from taky.config import app_config as config


def status_reg(subp):
    argp = subp.add_parser("status", help="Check the status of the taky server")

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


def print_status(stat):
    print("Uptime:", seconds_to_human(stat.get("uptime", -1)))
    print("Num Clients: %d" % stat.get("num_clients", -1))
    print()

    clients = stat.get("clients")
    if len(clients) == 0:
        return

    Row = namedtuple("Row", ["Callsign", "UID", "Connected"])
    table = []
    now = time.time()
    for client in clients:
        conn_len = now - client.get("connected", 0)
        if client.get("anonymous") is True:
            cs = "(anonymous)"
            uid = "(anonymous)"
        else:
            cs = client.get("callsign")
            uid = client.get("uid")

        table.append(Row(Callsign=cs, UID=uid, Connected=seconds_to_human(conn_len)))

    pprinttable(table)


def status(args):
    if args.socket is None:
        args.socket = os.path.join(config.get("taky", "root_dir"), "taky-mgmt.sock")

    start = time.time()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(args.socket)
        cmd = json.dumps({"cmd": "status"}).encode()
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
            print_status(stat)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print("ERROR: Invalid data in response", file=sys.stderr)
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
