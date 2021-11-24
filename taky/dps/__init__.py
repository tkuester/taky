import os

from flask import Flask

from taky.config import load_config
from taky.config import app_config as config

load_config(os.environ.get("TAKY_CONFIG"))

application = app = Flask(__name__)

cot_port = config.getint("cot_server", "port")
proto = "ssl" if config.getboolean("ssl", "enabled") else "tcp"

app.config["COT_ADDRESS"] = config.get("taky", "server_address")
app.config["COT_CONN_STR"] = f"{proto}:{app.config['COT_ADDRESS']}:{cot_port}"
app.config["NODEID"] = config.get("taky", "node_id")
app.config["UPLOAD_PATH"] = os.path.realpath(config.get("dp_server", "upload_path"))

from taky.dps import views  # pylint: disable=wrong-import-position
