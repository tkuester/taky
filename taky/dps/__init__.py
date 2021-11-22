import os

from flask import Flask

from taky.config import load_config
from taky.config import app_config as config

load_config(os.environ.get("TAKY_CONFIG"))

application = app = Flask(__name__)
app.config["HOSTNAME"] = config.get("taky", "hostname")
app.config["NODEID"] = config.get("taky", "node_id")
app.config["UPLOAD_PATH"] = os.path.realpath(config.get("dp_server", "upload_path"))

app.config["COT_PORT"] = config.getint("cot_server", "port")
if config.getboolean("ssl", "enabled"):
    app.config["COT_CONN_STR"] = 'ssl:{app.config["HOSTNAME"]}:{app.config["COT_PORT"]}'
else:
    app.config["COT_CONN_STR"] = 'tcp:{app.config["HOSTNAME"]}:{app.config["COT_PORT"]}'
    # TODO: Configurable?

from taky.dps import views  # pylint: disable=wrong-import-position
