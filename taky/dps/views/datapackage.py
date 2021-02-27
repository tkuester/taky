import os
import json
from datetime import datetime as dt

from flask import request, send_file
from werkzeug.utils import secure_filename

from taky.dps import app

@app.route('/Marti/sync/search')
def datapackage_search():
    '''
    Search for a datapackage
    Arguments:
        keywords=missionpackage
        tool=public
        keywords=request.args.get('keywords')
    '''
    ret = []
    for item in os.listdir(app.config['UPLOAD_PATH']):
        path = os.path.join(app.config['UPLOAD_PATH'], item)
        meta = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{item}.json')

        if not os.path.isfile(path):
            continue
        if not os.path.isfile(meta):
            continue

        try:
            with open(meta, 'r') as meta_fp:
                meta = json.load(meta_fp)
        except json.JSONDecodeError:
            # TODO: Purge files
            continue
        except OSError:
            continue

        # TODO: Check "tool" for public / private
        # TODO: Check if keywords are in meta['Keywords'] or meta['UID']
        ret.append(meta)

    return {
        'resultCount': len(ret),
        'results': ret
    }

@app.route('/Marti/sync/content')
def datapackage_get():
    '''
    Download a datapackage
    Arguments:
        hash:     The file hash
        receiver: The client downloading the file
    '''
    try:
        f_hash = request.args['hash']
    except KeyError:
        return "Must supply hash", 400

    meta = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{f_hash}.json')
    try:
        with open(meta, 'r') as meta_fp:
            meta = json.load(meta_fp)
    except (OSError, json.JSONDecodeError) as exc:
        return str(exc), 404

    name = os.path.join(app.config['UPLOAD_PATH'], meta['UID'])

    if not os.path.exists(name):
        return f"Can't find {name}", 404

    return send_file(name, as_attachment=True, attachment_filename=meta['Name'])

@app.route('/Marti/sync/missionupload', methods=['POST'])
def datapackage_upload():
    '''
    Upload a datapackage to the server

    Arguments:
        hash=...
        filename=... (lacking extension)
        creatorUid=ANDROID-43...

    Return:
        The URL where the file can be downloaded
    '''

    try:
        asset_fp = request.files['assetfile']
        creator_uid = request.args['creatorUid']
        f_hash = request.args['hash']
    except KeyError:
        return 'Invalid arguments', 400

    filename = secure_filename(f'{creator_uid}_{asset_fp.filename}')
    file_path = os.path.join(app.config['UPLOAD_PATH'], filename)
    meta_path = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{filename}.json')
    meta_hash_path = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{f_hash}.json')

    # Delete / unlink old files
    try:
        meta = {}
        with open(meta_path, 'r') as meta_fp:
            meta = json.load(meta_fp)

        if meta['Hash'] != f_hash:
            old_meta_hash_path = os.path.join(
                app.config['UPLOAD_PATH'], 'meta', f'{meta.get("Hash")}.json'
            )
            os.unlink(old_meta_hash_path)
    except:
        meta = {}

    # TODO: Use SSL Certificate Identity to set SubmissionUser
    #       (see MissionPackageQueryResult.java#37)
    meta = {
        'UID': filename, # What the file will be saved as
        'Name': asset_fp.filename, # File name on the server
        'Hash': request.args['hash'], # SHA-256, checked
        'PrimaryKey': 1, # Not used, must be >= 0
        'SubmissionDateTime': dt.utcnow().isoformat() + 'Z',
        'SubmissionUser': 'SubUser',
        'CreatorUid': request.args['creatorUid'],
        'Keywords': 'kw',
        'MIMEType': asset_fp.mimetype,
        'Size': 0 # Checked, do not fake
    }

    asset_fp.save(file_path)

    meta['Size'] = os.path.getsize(file_path)

    with open(meta_path, 'w') as meta_fp:
        json.dump(meta, meta_fp)

    try:
        os.symlink(f'{filename}.json', meta_hash_path)
    except FileExistsError:
        pass

    ip_addr = app.config['PUBLIC_IP']
    port = app.config['DPS_PORT']

    # src/main/java/com/atakmap/android/missionpackage/http/MissionPackageDownloader.java:539
    # This is needed for client-to-client data package transmission
    ret = f'{app.config["PROTO"]}{ip_addr}:{port}/Marti/sync/content?hash={request.args["hash"]}'
    return ret

@app.route('/Marti/api/sync/metadata/<f_hash>/tool', methods=['PUT'])
def datapackage_metadata_tool(f_hash):
    '''
    Update the "tool" for the datapackage (ie: public / private)
    '''
    meta = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{f_hash}.json')
    try:
        with open(meta, 'r') as meta_fp:
            meta = json.load(meta_fp)
    except FileNotFoundError:
        return f'Could not find file matching {f_hash}', 404
    except (json.JSONDecodeError, OSError):
        meta = {}

    ip_addr = app.config['PUBLIC_IP']
    port = app.config['DPS_PORT']

    ret = f'{app.config["PROTO"]}{ip_addr}:{port}/Marti/sync/content?hash={f_hash}'
    return ret

@app.route('/Marti/sync/missionquery')
def datapackage_exists():
    '''
    Called when trying to determine if the file exists on the server

    Arguments:
        hash: The file hash
    '''
    try:
        f_hash = request.args['hash']
    except:
        return 'Must supply hash', 400

    meta_hash_path = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{f_hash}.json')
    try:
        with open(meta_hash_path, 'r') as meta_fp:
            meta = json.load(meta_fp)

        file_path = os.path.join(app.config['UPLOAD_PATH'], meta['UID'])
        if os.path.exists(file_path):
            ip_addr = app.config['PUBLIC_IP']
            port = app.config['DPS_PORT']

            ret = f'{app.config["PROTO"]}{ip_addr}:{port}/Marti/sync/content?hash={request.args["hash"]}'
            return ret
    except:
        pass

    return 'File not found', 404
