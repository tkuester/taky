import os
import logging
import configparser
import socket

app_config = configparser.ConfigParser(allow_no_value=True)

DEFAULT_CFG = {
    "taky": {
        "node_id": "TAKY",  # TAK Server nodeId
        "bind_ip": None,  # Defaults to all (0.0.0.0)
        "redis": None,  # If Redis is enabled. True for localhost,
        # or a redis:// connect string
        "root_dir": "/var/taky",  # Where the root taky directory lies
    },
    "cot_server": {
        "port": None,  # Defaults to 8087 (or 8089 if SSL)
        "mon_ip": None,
        "mon_port": None,
        "log_cot": None,  # Path to log COT files to
    },
    "dp_server": {
        "upload_path": "/var/taky/dp-user",
    },
    "ssl": {
        "enabled": False,
        "client_cert_required": True,
        "ca": "/etc/taky/ssl/ca.crt",
        "ca_key": "/etc/taky/ssl/ca.key",
        "server_p12": "/etc/taky/ssl/server.p12",
        "server_p12_pw": "atakatak",
        "cert": "/etc/taky/ssl/server.crt",
        "key": "/etc/taky/ssl/server.key",
        "key_pw": None,
    },
}


def load_config(path=None, explicit=False):
    """
    Loads a config file from the specified path into the global config. If no
    path is specified, the file is inferred by checking local and global paths.

    @param path     The path of the configuration file to load
    @param explicit Don't return a default
    """
    if path is None:
        if os.path.exists("taky.conf"):
            path = os.path.abspath("taky.conf")
        elif os.path.exists("/etc/taky/taky.conf"):
            path = "/etc/taky/taky.conf"

    if explicit and not (path and os.path.exists(path)):
        raise FileNotFoundError("Config file required, but not present")

    ret_config = configparser.ConfigParser(allow_no_value=True)
    ret_config.read_dict(DEFAULT_CFG)

    lgr = logging.getLogger("load_config")

    if path and os.path.exists(path):
        lgr.info("Loading config file from %s", path)
        with open(path, "r") as cfg_fp:
            ret_config.read_file(cfg_fp, source=path)

    # TODO: Deprecate
    if ret_config.has_option("taky", "hostname") or ret_config.has_option(
        "taky", "public_ip"
    ):
        lgr.warning(
            "The config options 'hostname' and 'server_ip' have been deprecated\n"
            "since version 0.9, please update your config file to use server_address\n"
            "instead."
        )

    if ret_config.has_option("taky", "hostname"):  # TODO: Deprecate
        hostname = ret_config.get("taky", "hostname")
    elif ret_config.has_option("taky", "server_address"):
        hostname = ret_config.get("taky", "server_address")
    else:
        hostname = socket.getfqdn()
    ret_config.set("taky", "server_address", hostname)

    port = ret_config.get("cot_server", "port")
    if port in [None, ""]:
        port = 8089 if ret_config.getboolean("ssl", "enabled") else 8087
    else:
        try:
            port = int(port)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid port: {port}") from exc

        if port <= 0 or port >= 65535:
            raise ValueError(f"Invalid port: {port}")
    ret_config.set("cot_server", "port", str(port))

    if not ret_config.getboolean("ssl", "enabled"):
        # Disable monitor port
        ret_config.set("cot_server", "mon_ip", None)
    else:
        port = ret_config.get("cot_server", "mon_port")
        if port in [None, ""]:
            port = 8087 if ret_config.getboolean("ssl", "enabled") else None
        else:
            try:
                port = int(port)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid port: {port}") from exc

            if port <= 0 or port >= 65535:
                raise ValueError(f"Invalid port: {port}")
        ret_config.set("cot_server", "mon_port", str(port))

    if explicit:
        ret_config.set("taky", "cfg_path", path)

    app_config.clear()
    app_config.update(ret_config)
