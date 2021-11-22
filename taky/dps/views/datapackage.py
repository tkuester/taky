import os
import json
from datetime import datetime as dt

from flask import request, send_file
from werkzeug.utils import secure_filename

from taky.dps import app


def url_for(f_hash):
    """
    Returns the URL for the given hash
    """
    return f"{request.host_url}Marti/sync/content?hash={f_hash}"


def get_meta(f_hash=None, f_name=None):
    """
    Gets the metadata for an assigned filename or hash
    """
    if f_hash:
        meta_path = os.path.join(app.config["UPLOAD_PATH"], "meta", f"{f_hash}.json")
    elif f_name:
        meta_path = os.path.join(app.config["UPLOAD_PATH"], "meta", f"{f_name}.json")
    else:
        return {}

    try:
        with open(meta_path) as meta_fp:
            return json.load(meta_fp)
    except (json.JSONDecodeError, OSError):
        return {}


def put_meta(meta):
    """
    Updates the metadata - the supplied hash/UID is used to find the target file
    """
    filename = meta.get("UID")
    f_hash = meta.get("Hash")

    # Save the file's meta/{filename}.json
    meta_path = os.path.join(app.config["UPLOAD_PATH"], "meta", f"{filename}.json")
    with open(meta_path, "w") as meta_fp:
        json.dump(meta, meta_fp)

    # Symlink the meta/{f_hash}.json to {filename}.json
    meta_hash_path = os.path.join(app.config["UPLOAD_PATH"], "meta", f"{f_hash}.json")
    try:
        os.symlink(f"{filename}.json", meta_hash_path)
    except FileExistsError:
        pass


@app.route("/Marti/sync/search")
def datapackage_search():
    """
    Search for a datapackage
    Arguments:
        keywords=missionpackage
        tool=public
        keywords=request.args.get('keywords')
    """
    ret = []
    for item in os.listdir(app.config["UPLOAD_PATH"]):
        path = os.path.join(app.config["UPLOAD_PATH"], item)
        if not os.path.isfile(path):
            continue

        # TODO: Check if keywords are in meta['Keywords'] or meta['UID']
        meta = get_meta(f_name=item)
        if meta and meta.get("Visibility", "public") == "public":
            ret.append(meta)

    return {"resultCount": len(ret), "results": ret}


@app.route("/Marti/sync/content")
def datapackage_get():
    """
    Download a datapackage
    Arguments:
        hash:     The file hash
        receiver: The client downloading the file
    """
    try:
        f_hash = request.args["hash"]
    except KeyError:
        return "Must supply hash", 400

    meta = get_meta(f_hash=f_hash)
    name = os.path.join(app.config["UPLOAD_PATH"], meta["UID"])

    if not os.path.exists(name):
        return f"Can't find {name}", 404

    return send_file(name, as_attachment=True, attachment_filename=meta["Name"])


@app.route("/Marti/sync/missionupload", methods=["POST"])
def datapackage_upload():
    """
    Upload a datapackage to the server

    Arguments:
        hash=...
        filename=... (lacking extension)
        creatorUid=ANDROID-43...

    Return:
        The URL where the file can be downloaded
    """

    try:
        asset_fp = request.files["assetfile"]
        creator_uid = request.args["creatorUid"]
        f_hash = request.args["hash"]
    except KeyError:
        return "Invalid arguments", 400

    filename = secure_filename(f"{creator_uid}_{asset_fp.filename}")

    # Delete / unlink old files
    meta = get_meta(f_name=filename)
    if meta.get("Hash") != f_hash:
        old_meta_hash_path = os.path.join(
            app.config["UPLOAD_PATH"], "meta", f'{meta.get("Hash")}.json'
        )
        try:
            os.unlink(old_meta_hash_path)
        except:  # pylint: disable=bare-except
            pass

    # Save the uploaded file
    file_path = os.path.join(app.config["UPLOAD_PATH"], filename)
    asset_fp.save(file_path)

    sub_user = request.headers.get("X-USER", "Anonymous")
    meta = {
        "UID": filename,  # What the file will be saved as
        "Name": asset_fp.filename,  # File name on the server
        "Hash": f_hash,  # SHA-256, checked
        "PrimaryKey": 1,  # Not used, must be >= 0
        "SubmissionDateTime": dt.utcnow().isoformat() + "Z",
        "SubmissionUser": sub_user,
        "CreatorUid": creator_uid,
        "Keywords": "kw",
        "MIMEType": asset_fp.mimetype,
        "Size": os.path.getsize(file_path),  # Checked, do not fake
        "Visibility": "private",
    }

    put_meta(meta)

    # src/main/java/com/atakmap/android/missionpackage/http/MissionPackageDownloader.java:539
    # This is needed for client-to-client data package transmission
    return url_for(f_hash)


@app.route("/Marti/api/sync/metadata/<f_hash>/tool", methods=["PUT"])
def datapackage_metadata_tool(f_hash):
    """
    Update the "tool" for the datapackage (ie: public / private)
    """
    meta = get_meta(f_hash=f_hash)
    if not meta:
        return f"Could not find file matching {f_hash}", 404

    visibility = (
        "public" if request.get_data().decode("utf-8") == "public" else "private"
    )

    if meta.get("Visibility", "private") != visibility:
        meta["Visibility"] = visibility
        put_meta(meta)

    return url_for(f_hash)


@app.route("/Marti/sync/missionquery")
def datapackage_exists():
    """
    Called when trying to determine if the file exists on the server

    Arguments:
        hash: The file hash
    """
    try:
        f_hash = request.args["hash"]
    except KeyError:
        return "Must supply hash", 400

    meta = get_meta(f_hash)
    if not meta:
        return "File not found", 404

    return url_for(f_hash)
