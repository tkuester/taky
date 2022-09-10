from taky.dps import app, requires_auth


@app.route("/")
def hello_world():
    return "Hello, world!"


@app.route("/Marti/api/clientEndPoints")
@requires_auth
def marti_api_client_endpoints():
    return {
        "Matcher": "com.bbn.marti.remote.ClientEndpoint",
        "BaseUrl": "",
        "ServerConnectString": app.config["COT_CONN_STR"],
        "NotificationId": "",
        "type": "com.bbn.marti.remote.ClientEndpoint",
        "data": [
            # {
            #    'lastEventTime': '2020-01-31T15:30:00.000Z',
            #    'lastStatus': 'Connected',
            #    'uid': 'TAKY-lolol',
            #    'callsign': 'TAKKY'
            # }
        ],
    }
