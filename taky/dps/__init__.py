import os

from flask import Flask

from taky.config import load_config

config = load_config(os.environ.get("TAKY_CONFIG"))

application = app = Flask(__name__)
app.config["HOSTNAME"] = config.get("taky", "hostname")
app.config["NODEID"] = config.get("taky", "node_id")
app.config["UPLOAD_PATH"] = os.path.realpath(config.get("dp_server", "upload_path"))

app.config["PUBLIC_IP"] = config.get("taky", "public_ip")
app.config["COT_PORT"] = config.getint("cot_server", "port")
if config.getboolean("ssl", "enabled"):
    app.config["PROTO"] = "https://"
    app.config["COT_CONN_STR"] = 'ssl:{app.config["HOSTNAME"]}:{app.config["COT_PORT"]}'
    app.config["DPS_PORT"] = 8443
else:
    app.config["PROTO"] = "http://"
    app.config["COT_CONN_STR"] = 'tcp:{app.config["HOSTNAME"]}:{app.config["COT_PORT"]}'
    app.config["DPS_PORT"] = 8080
    # TODO: Configurable?

from taky.dps import views  # pylint: disable=wrong-import-position

# /Marti/vcm - Videos on Server
