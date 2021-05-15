import os
import sys
import shutil
import socket

from taky.config import load_config
import taky.util.rotc as rotc


def setup_taky_reg(subp):
    try:
        default_hostname = socket.gethostname()
    except:
        default_hostname = "taky"

    setup = subp.add_parser("setup", help="Setup the taky server")
    setup.add_argument(
        "--p12_pw",
        dest="p12_pw",
        default="atakatak",
        help="Password for server .p12 [%(default)s]",
    )
    setup.add_argument(
        "--host",
        dest="hostname",
        default=default_hostname,
        help="Server hostname [%(default)s]",
    )
    setup.add_argument(
        "--bind-ip", dest="ip", default="0.0.0.0", help="Bind Address [%(default)s]"
    )
    setup.add_argument(
        "--public-ip", dest="public_ip", required=True, help="Public IP address"
    )
    setup.add_argument(
        "--user", dest="user", default=None, help="User/group for file permissions"
    )
    setup.add_argument(
        "--no-ssl",
        dest="use_ssl",
        action="store_false",
        help="Disable SSL for the server",
    )
    setup.add_argument("path", nargs="?", help="Optional path for taky install")


def setup_taky(config, args):
    config = load_config(os.devnull)
    if args.path:
        if os.path.exists(args.path):
            print("ERROR: Directory exists, refusing to run setup", file=sys.stderr)
            return 1

        args.path = os.path.abspath(args.path)
        print(f"Installing site to {args.path}")

        dirs = [args.path, os.path.join(args.path, "ssl")]
        for dir_name in dirs:
            if not os.path.exists(dir_name):
                os.mkdir(dir_name)
                if args.user:
                    shutil.chown(dir_name, user=args.user, group=args.user)

        os.chdir(args.path)

        ssl_path = "ssl"
        config_path = "taky.conf"

        config.set("ssl", "ca", os.path.join(args.path, "ssl", "ca.crt"))
        config.set("ssl", "ca_key", os.path.join(args.path, "ssl", "ca.key"))
        config.set("ssl", "server_p12", os.path.join(args.path, "ssl", "server.p12"))
        config.set("ssl", "cert", os.path.join(args.path, "ssl", "server.crt"))
        config.set("ssl", "key", os.path.join(args.path, "ssl", "server.key"))

        config.set("dp_server", "upload_path", os.path.join(args.path, "dp-user"))
    else:
        print("Installing site to system")
        args.path = "/"

        dirs = [
            os.path.join(args.path, "etc", "taky"),
            os.path.join(args.path, "etc", "taky", "ssl"),
            os.path.join(args.path, "var", "taky"),
        ]

        for dir_name in dirs:
            if not os.path.exists(dir_name):
                os.mkdir(dir_name)
                if args.user:
                    shutil.chown(dir_name, user=args.user, group=args.user)

        ssl_path = os.path.join(args.path, "etc", "taky", "ssl")
        config_path = os.path.join(args.path, "etc", "taky", "taky.conf")

    config.set("taky", "bind_ip", args.ip)
    config.set("taky", "public_ip", args.public_ip)
    config.set("taky", "hostname", args.hostname)
    config.set("cot_server", "port", "8089" if args.use_ssl else "8087")
    config.set("ssl", "enabled", "true" if args.use_ssl else "false")
    config.set("ssl", "server_p12_pw", args.p12_pw)

    if os.path.exists(config_path):
        print(f"ERROR: Config already exists at {config_path}, refusing to setup")
        return 1

    with open(config_path, "w") as cfg_fp:
        config.write(cfg_fp)

    print(f" - Wrote {config_path}")

    if args.user:
        shutil.chown(config_path, user=args.user, group=args.user)

    dirs = [
        config.get("dp_server", "upload_path"),
        os.path.join(config.get("dp_server", "upload_path"), "meta"),
    ]

    for dir_name in dirs:
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
            if args.user:
                shutil.chown(dir_name, user=args.user, group=args.user)

    if config.getboolean("ssl", "enabled"):
        if os.path.exists(config.get("ssl", "ca")):
            ca_path = config.get("ssl", "ca")
            print(f"ERROR: CA exists at {ca_path}, stopping here", file=sys.stderr)
            return 1

        print(" - Generating certificate authority")
        rotc.make_ca(
            crt_path=config.get("ssl", "ca"), key_path=config.get("ssl", "ca_key")
        )

        if args.user:
            shutil.chown(config.get("ssl", "ca"), user=args.user, group=args.user)
            shutil.chown(config.get("ssl", "ca_key"), user=args.user, group=args.user)

        print(" - Generating server certificate")
        rotc.make_cert(
            path=ssl_path,
            f_name="server",
            hostname=args.hostname,
            cert_pw=args.p12_pw,  # TODO: OS environ? -p is bad
            cert_auth=(config.get("ssl", "ca"), config.get("ssl", "ca_key")),
            dump_pem=True,
        )

        if args.user:
            print(f" - Changing ownership to {args.user}")
            shutil.chown(config.get("ssl", "cert"), user=args.user, group=args.user)
            shutil.chown(config.get("ssl", "key"), user=args.user, group=args.user)
            shutil.chown(
                config.get("ssl", "server_p12"), user=args.user, group=args.user
            )

    return 0
