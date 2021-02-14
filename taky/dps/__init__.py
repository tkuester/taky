import os

from flask import Flask, request, send_file
from werkzeug.utils import secure_filename

from taky import __version__

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp'
app.config['HOSTNAME'] = '0.0.0.0'
app.config['NODEID'] = 'TAKY'

@app.route('/')
def hello_world():
    return 'Hello, world!'

@app.route('/Marti/api/version')
def marti_api_version():
    return f'taky-{__version__}'

@app.route('/Marti/api/version/config')
def marti_api_version_config():
    return {
        'version': '2',
        'type': 'ServerConfig',
        'data': {
            'version': f'taky-{__version__}',
            'api': '2',
            'hostname': app.config['HOSTNAME'],
        },
        'nodeId': app.config['NODEID']
    }

@app.route('/Marti/api/clientEndPoints')
def marti_api_client_endpoints():
    return {
        'Matcher': 'com.bbn.marti.remote.ClientEndpoint',
        'BaseUrl': '',
        'ServerConnectString': 'tcp:192.168.1.91:8087',
        'NotificationId': '',
        'type': 'com.bbn.marti.remote.ClientEndpoint',
        'data': [
            {
                'lastEventTime': '2020-01-31T15:30:00.000Z',
                'lastStatus': 'Connected',
                'uid': 'TAKY-lolol',
                'callsign': 'TAKKY'
            }
        ]
    }

@app.route('/Marti/sync/search')
def marti_sync_search():
    # Arguments: keywords=missionpackage
    #            tool=public
    results = [
        {
            'UID': 'uid-haha.zip', # What the file will be saved as
            'Name': 'haha.zip', # File name on the server
            'Hash': '78e750a5f38a794caf466e0f2fe7a302096d573899cef1869fb5a30f55d7ac4f', # SHA-256, checked
            'PrimaryKey': 1, # Not used, must be >= 0
            'SubmissionDateTime': '2021-01-31T00:11:22.000Z',
            'SubmissionUser': 'SubUser', # Not displayed
            'CreatorUid': 'cuid', # Displayed, ie: ANDROID-43fa2bcef...
            'Keywords': 'kw',
            'MIMEType': 'application/zip',
            'Size': 181 # Checked, do not fake
        },
    ]

    return {
        'resultCount': len(results),
        'results': results
    }

@app.route('/Marti/sync/content')
def marti_get_content():
    return send_file('/tmp/haha.zip', as_attachment=True)

@app.route('/Marti/sync/missionquery')
def marti_sync_missionquery():
    # Args: hash=...
    # Don't know what to do here
    return '', 404

@app.route('/Marti/sync/missionupload', methods=['POST'])
def marti_sync_missionupload():
    # Args:
    # hash=...
    # filename=... (lacking extension)
    # creatorUid=ANDROID-43...

    print(request.files)
    for (key, fp) in request.files.items():
        print((key, fp, fp.filename))

        fp.save(os.path.join('/tmp', secure_filename(fp.filename)))

    return ''

@app.route('/Marti/api/sync/metadata/<f_hash>/tool', methods=['PUT'])
def marti_api_sync_metadata(f_hash):
    print(f_hash)
    print(dir(request))
    print(request.headers)
    print(request.get_data())
    return ''

@app.route('/Marti/ErrorLog', methods=['POST'])
def marti_errorlog():
    # Args:
    # hash=...
    # filename=... (lacking extension)
    # creatorUid=ANDROID-43...

    print(request.files)
    for (key, fp) in request.files.items():
        print((key, fp, fp.filename))

        fp.save(os.path.join('/tmp', secure_filename(fp.filename)))

    return ''


# Marti/api/tls/config
# Returns... json+xml?
# xml: nameEntries, validityDays
