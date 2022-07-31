import os

from flask import Flask

from taky.config import load_config, app_config

application = app = Flask(__name__)


def configure_app(config):
    app.config["HOSTNAME"] = config.get("taky", "hostname")
    app.config["NODEID"] = config.get("taky", "node_id")
    app.config["UPLOAD_PATH"] = os.path.realpath(config.get("dp_server", "upload_path"))

    app.config["PUBLIC_IP"] = config.get("taky", "public_ip")
    app.config["COT_PORT"] = config.getint("cot_server", "port")
    if config.getboolean("ssl", "enabled"):
        app.config["PREFERRED_URL_SCHEME"] = "https"
        app.config[
            "COT_CONN_STR"
        ] = f'ssl:{app.config["HOSTNAME"]}:{app.config["COT_PORT"]}'
        app.config["DPS_PORT"] = 8443
    else:
        app.config["PREFERRED_URL_SCHEME"] = "http"
        app.config[
            "COT_CONN_STR"
        ] = f'tcp:{app.config["HOSTNAME"]}:{app.config["COT_PORT"]}'
        app.config["DPS_PORT"] = 8080
        # TODO: Configurable?


try:
    load_config(os.environ.get("TAKY_CONFIG"))
except FileNotFoundError:
    pass
configure_app(app_config)

from taky.dps import views  # pylint: disable=wrong-import-position
