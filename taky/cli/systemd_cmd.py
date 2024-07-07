import os
import sys
import configparser
import subprocess

from taky.config import load_config
from taky.config import app_config as config


def systemd_reg(subp):
    """Register the systemd command"""
    argp = subp.add_parser("systemd", help="Generate systemd service scripts")
    argp.add_argument(
        "--path",
        dest="path",
        default="/etc/systemd/system",
        help="Where to store the systemd scripts",
    )
    argp.add_argument(
        "--no-install",
        dest="install",
        default=True,
        action="store_false",
        help="Only write service files, do not activate",
    )
    argp.add_argument(
        "--no-dps",
        dest="dps",
        default=True,
        action="store_false",
        help="Do not enable the Data Package Server",
    )
    argp.add_argument(
        "-u", "--user", dest="user", default=None, help="Specify a user to run as"
    )


def write_cot_svc(names, args, using_venv=False, site_path=None):
    """Build the cot server service"""
    cot_svc = [
        "[Unit]",
        "Description=taky CoT Server",
        f"PartOf={names['taky']}",
        "",
        "[Service]",
        'Environment="LOG_LEVEL=info"',
        "Restart=always",
        "RestartSec=3",
    ]
    if site_path:
        host = config.get("taky", "hostname")
        cot_svc.append(f"EnvironmentFile=-/etc/default/taky-{host}")
    else:
        cot_svc.append("EnvironmentFile=-/etc/default/taky")

    if args.user:
        cot_svc.append(f"User={args.user}")
    if site_path:
        cot_svc.append(f"WorkingDirectory={site_path}")

    if using_venv:
        taky_path = os.path.join(sys.prefix, "bin", "taky")
    else:
        taky_path = "taky"

    cot_svc.append(f'ExecStart={taky_path} -l "${{LOG_LEVEL}}"')

    cot_svc.extend(["", "[Install]", "WantedBy=multi-user.target"])

    with open(os.path.join(args.path, names["cot"]), "w", encoding="utf8") as svc_fp:
        svc_fp.write("\n".join(cot_svc))
        svc_fp.write("\n")


def write_dps_svc(names, args, using_venv=False, site_path=None):
    """Build the data package server service"""
    dps_svc = [
        "[Unit]",
        "Description=taky Data Package Server",
        f"PartOf={names['taky']}",
        "",
        "[Service]",
        "Type=simple",
        "Restart=always",
        "RestartSec=3",
    ]
    if args.user:
        dps_svc.append(f"User={args.user}")
    if site_path:
        dps_svc.append(f"WorkingDirectory={site_path}")

    if using_venv:
        taky_path = os.path.join(sys.prefix, "bin", "taky_dps")
    else:
        taky_path = "taky_dps"

    dps_svc.append(f"ExecStart={taky_path}")

    dps_svc.extend(
        [
            "",
            "[Install]",
            "WantedBy=multi-user.target",
        ]
    )

    with open(os.path.join(args.path, names["dps"]), "w", encoding="utf8") as svc_fp:
        svc_fp.write("\n".join(dps_svc))
        svc_fp.write("\n")


def write_uni_svc(names, args):
    """Build the service that unites the COT and DPS services"""
    uni_svc = [
        "[Unit]",
        "Description=taky Server",
        f"Wants={names['cot']}",
    ]
    if args.dps:
        uni_svc.append(f"Wants={names['dps']}")

    uni_svc.extend(
        [
            "After=network.target",
            "",
            "[Service]",
            "Type=oneshot",
            "ExecStart=/bin/true",
            "RemainAfterExit=yes",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
        ]
    )

    with open(os.path.join(args.path, names["taky"]), "w", encoding="utf8") as svc_fp:
        svc_fp.write("\n".join(uni_svc))
        svc_fp.write("\n")


def systemd(args):
    """Build and install systemd scripts for the server"""
    try:
        load_config(args.cfg_file, explicit=True)
    except (FileNotFoundError, configparser.ParsingError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print("Building systemd services")

    using_venv = sys.prefix != sys.base_prefix
    if using_venv:
        print(f" - Detected virtualenv: {sys.prefix}")
        print("   Service files will be built for this virutalenv")

    site_path = None
    global_site = config.get("taky", "cfg_path") == "/etc/taky/taky.conf"
    if global_site:
        print(" - Detected system-wide site install")
        svcs = {
            "taky": "taky.service",
            "cot": "taky-cot.service",
            "dps": "taky-dps.service",
        }
    else:
        site_path = os.path.dirname(str(config.get("taky", "cfg_path")))
        hostname = config.get("taky", "hostname")
        print(f" - Detected site install: {site_path}")
        svcs = {
            "taky": f"taky-{hostname}.service",
            "cot": f"taky-{hostname}-cot.service",
            "dps": f"taky-{hostname}-dps.service",
        }

    if not args.user:
        print(
            " - WARNING: taky will run as root! It's strongly recommended",
            file=sys.stderr,
        )
        print("            to create a system user for taky!", file=sys.stderr)

    # Do not overwrite files if they exist
    for svc in svcs:
        path = os.path.join(args.path, svcs[svc])
        if os.path.exists(path):
            print(f"ERROR: Refusing to overwite service file: {path}", file=sys.stderr)
            return 1

    print(f" - Writing services to {args.path}")
    try:
        print(f"   - Writing {svcs['cot']}")
        write_cot_svc(svcs, args, using_venv, site_path)
        if args.dps:
            print(f"   - Writing {svcs['dps']}")
            write_dps_svc(svcs, args, using_venv, site_path)
        print(f"   - Writing {svcs['taky']}")
        write_uni_svc(svcs, args)
    except PermissionError:
        print(
            f"ERROR: Unable to write service files to {args.path}, permission denied",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.install:
        try:
            print(" - Reloading systemctl services")
            subprocess.check_output(["systemctl", "daemon-reload"])
            print(" - Enabling service")
            subprocess.check_output(["systemctl", "enable", svcs["taky"]])
            print(" - Starting service")
            subprocess.check_output(["systemctl", "start", svcs["taky"]])
        except subprocess.CalledProcessError as exc:
            print(f"ERROR: systemctl calls failed: {exc}")
            return 1

    return 0
