import os
import functools

import flask
from flask import Flask

from taky.config import load_config, app_config

application = app = Flask(__name__)


def requires_auth(func):
    """
    Function to ensure that a valid client certificate is submitted
    """

    @functools.wraps(func)
    def check_headers(*args, **kwargs):
        if not flask.request.headers.get("X-USER"):
            flask.abort(401)
        if flask.request.headers.get("X-REVOKED"):
            flask.abort(403)

        return func(*args, **kwargs)

    return check_headers


def configure_app(config):
    app.config["HOSTNAME"] = config.get("taky", "hostname")
    app.config["NODEID"] = config.get("taky", "node_id")
    app.config["UPLOAD_PATH"] = config.get("dp_server", "upload_path")

    cot_port = config.getint("cot_server", "port")
    if config.getboolean("ssl", "enabled"):
        app.config["COT_CONN_STR"] = f'ssl:{app.config["HOSTNAME"]}:{cot_port}'
    else:
        app.config["COT_CONN_STR"] = f'tcp:{app.config["HOSTNAME"]}:{cot_port}'


try:
    load_config(os.environ.get("TAKY_CONFIG"))
except FileNotFoundError:
    pass
configure_app(app_config)

from taky.dps import views  # pylint: disable=wrong-import-position
