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
        if app.config["SSL"]:
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
    app.config["COT_PORT"] = config.getint("cot_server", "port")
    app.config["SSL"] = config.getboolean("ssl", "enabled")


try:
    load_config(os.environ.get("TAKY_CONFIG"))
except FileNotFoundError:
    pass
configure_app(app_config)

from taky.dps import views  # pylint: disable=wrong-import-position
