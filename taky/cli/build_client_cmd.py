import os
import shutil
import tempfile
import uuid
import zipfile

from taky.util import datapackage, rotc
from taky.config import app_config as config


def build_client_reg(subp):
    bld_cl = subp.add_parser("build_client", help="Build client file")
    bld_cl.add_argument("name", help="Name for client")
    bld_cl.add_argument(
        "--p12_pw",
        dest="p12_pw",
        default="atakatak",
        help="Password for server .p12 [%(default)s]",
    )
    bld_cl.add_argument(
        "--dump_pem",
        dest="dump_pem",
        default=False,
        action="store_true",
        help="Save the .crt/.key files",
    )


def build_client(args):
    tdir = tempfile.mkdtemp(prefix="taky-cert-")

    # Build zip file structure
    mdir = os.path.join(tdir, "MANIFEST")
    os.mkdir(mdir)
    cdir = os.path.join(tdir, "certs")
    os.mkdir(cdir)

    # Copy over server p12 file
    server_p12 = config.get("ssl", "server_p12")
    shutil.copy(server_p12, cdir)

    # Build client certificates
    rotc.make_cert(
        path=cdir,
        f_name=args.name,
        hostname=args.name,
        cert_pw=args.p12_pw,  # TODO: OS environ? -p is bad
        cert_auth=(config.get("ssl", "ca"), config.get("ssl", "ca_key")),
        dump_pem=args.dump_pem,
    )

    # Build .pref file
    hostname = config.get("taky", "hostname")
    public_ip = config.get("taky", "public_ip")
    port = config.getint("cot_server", "port")
    method = "ssl" if config.getboolean("ssl", "enabled") else "tcp"

    prefs = {
        "cot_streams": {
            "count": 1,
            "description0": hostname,
            "enabled0": False,
            "connectString0": f"{public_ip}:{port}:{method}",
        },
        "com.atakmap.app_preferences": {
            "displayServerConnectionWidget": True,
            "caLocation": f"/storage/emulated/0/atak/cert/{os.path.basename(server_p12)}",
            "caPassword": config.get("ssl", "server_p12_pw"),
            "clientPassword": args.p12_pw,
            "certificateLocation": f"/storage/emulated/0/atak/cert/{args.name}.p12",
        },
    }

    with open(os.path.join(cdir, "taky.pref"), "wb") as pref_fp:
        datapackage.build_pref(pref_fp, prefs)

    # Build Mission Package Manifest
    cfg_params = {
        "uid": str(uuid.uuid4()),
        "name": f"{hostname}_DP",
        "onReceiveDelete": "true",
    }
    man_cts = ["taky.pref", os.path.basename(server_p12), f"{args.name}.p12"]

    with open(os.path.join(mdir, "manifest.xml"), "wb") as man_fp:
        datapackage.build_manifest(man_fp, cfg_params, man_cts)

    cwd = os.getcwd()

    # Save PEM files
    if args.dump_pem:
        shutil.copy(os.path.join(cdir, f"{args.name}.p12"), cwd)
        shutil.copy(os.path.join(cdir, f"{args.name}.crt"), cwd)
        shutil.copy(os.path.join(cdir, f"{args.name}.key"), cwd)

        os.unlink(os.path.join(cdir, f"{args.name}.crt"))
        os.unlink(os.path.join(cdir, f"{args.name}.key"))

    # Save temporary directory, and build ZIP file
    os.chdir(tdir)
    zip_path = os.path.join(cwd, f"{args.name}.zip")
    zip_fp = zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(tdir):  # pylint: disable=unused-variable
        root = os.path.relpath(root, tdir)
        for file in files:
            zip_fp.write(os.path.join(root, file))

    zip_fp.close()

    # Cleanup temporary directory
    shutil.rmtree(tdir)

    return 0
