import os
import json

from flask import request, send_file
from werkzeug.utils import secure_filename

from taky.dps import app

@app.route('/Marti/sync/search')
def marti_sync_search():
    # Arguments: keywords=missionpackage
    #            tool=public
    #keywords = request.args.get('keywords')
    ret = []
    for item in os.listdir(app.config['UPLOAD_PATH']):
        path = os.path.join(app.config['UPLOAD_PATH'], item)
        meta = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{item}.json')

        if not os.path.isfile(path):
            continue

        if not os.path.isfile(meta):
            continue

        try:
            with open(meta, 'r') as fp:
                meta = json.load(fp)
        except OSError:
            continue
        except json.JSONDecodeError:
            continue

        # TODO: Check if keywords are in meta['Keywords'] or meta['UID']
        ret.append(meta)

    return {
        'resultCount': len(ret),
        'results': ret
    }

@app.route('/Marti/sync/content')
def marti_get_content():
    try:
        f_hash = request.args['hash']
    except:
        return "Must supply hash", 400

    print("Request for f_hash: %s" % f_hash, flush=True)
    meta = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{f_hash}.json')
    try:
        with open(meta, 'r') as fp:
            meta = json.load(fp)
    except (OSError, json.JSONDecodeError) as e:
        print(e)
        abort(404)

    name = os.path.join(app.config['UPLOAD_PATH'], meta['UID'])

    if not os.path.exists(name):
        print("Can't find %s", name)
        abort(404)

    print(name)

    return send_file(name, as_attachment=True, attachment_filename=meta['Name'])

@app.route('/Marti/sync/missionupload', methods=['POST'])
def marti_sync_missionupload():
    # Args:
    # hash=...
    # filename=... (lacking extension)
    # creatorUid=ANDROID-43...

    try:
        fp = request.files['assetfile']
        creator_uid = request.args['creatorUid']
        f_hash = request.args['hash']
    except:
        abort(400, 'Invalid Arguments')

    filename = secure_filename(f'{creator_uid}_{fp.filename}')
    file_path = os.path.join(app.config['UPLOAD_PATH'], filename)
    meta_path = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{filename}.json')
    meta_hash_path = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{f_hash}.json')

    try:
        meta = {}
        with open(meta_path, 'r') as jfp:
            meta = json.load(jfp)

        if meta['Hash'] != f_hash:
            old_meta_hash_path = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{meta.get("Hash")}.json')
            os.unlink(old_meta_hash_path)
    except:
        meta = {}

    meta = {
        'UID': filename, # What the file will be saved as
        'Name': fp.filename, # File name on the server
        'Hash': request.args['hash'], # SHA-256, checked
        'PrimaryKey': 1, # Not used, must be >= 0
        'SubmissionDateTime': dt.utcnow().isoformat() + 'Z',
        'SubmissionUser': 'SubUser', # TODO: SSL Certificate Identity (MissionPackageQueryResult.java#37)
        'CreatorUid': request.args['creatorUid'],
        'Keywords': 'kw',
        'MIMEType': fp.mimetype,
        'Size': 0 # Checked, do not fake
    }

    fp.save(file_path)

    meta['Size'] = os.path.getsize(file_path)

    with open(meta_path, 'w') as fp:
        json.dump(meta, fp)

    try:
        os.symlink(f'{filename}.json', meta_hash_path)
    except FileExistsError:
        pass

    ip = app.config['PUBLIC_IP']
    port = app.config['DPS_PORT']

    # src/main/java/com/atakmap/android/missionpackage/http/MissionPackageDownloader.java:539
    # This is needed for client-to-client data package transmission
    ret = f'{app.config["PROTO"]}{ip}:{port}/Marti/sync/content?hash={request.args["hash"]}'
    print(ret)
    return ret

@app.route('/Marti/api/sync/metadata/<f_hash>/tool', methods=['PUT'])
def marti_api_sync_metadata_put(f_hash):
    meta = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{f_hash}.json')
    try:
        with open(meta, 'r') as fp:
            meta = json.load(fp)
    except:
        meta = {}

    print('sync/metadata/../tool', request.args)
    print('/sync/metadata/../tool', meta)
    print('sync/metadata: hash', f_hash) # Relevant
    print('sync/metadata: data', request.get_data()) # Returns b'public' or private
    print('', flush=True)

    return ''

@app.route('/Marti/sync/missionquery')
def marti_sync_missionquery():
    try:
        f_hash = request.args['hash']
    except:
        return 'Must supply hash', 400

    meta_hash_path = os.path.join(app.config['UPLOAD_PATH'], 'meta', f'{f_hash}.json')
    print(meta_hash_path)
    try:
        with open(meta_hash_path, 'r') as fp:
            meta = json.load(fp)

        print(meta)
        file_path = os.path.join(app.config['UPLOAD_PATH'], meta['UID'])
        if os.path.exists(file_path):
            return 'OK'
    except:
        pass

    return 'File not found', 404
