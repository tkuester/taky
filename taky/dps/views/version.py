from taky import __version__
from taky.dps import app


@app.route("/Marti/api/version")
def marti_api_version():
    return f"taky-{__version__}"


@app.route("/Marti/api/version/config")
def marti_api_version_config():
    return {
        "version": "2",
        "type": "ServerConfig",
        "data": {
            "version": f"taky-{__version__}",
            "api": "2",
            "hostname": app.config["COT_ADDRESS"],
        },
        "nodeId": app.config["NODEID"],
    }
