import os
import json
from datetime import datetime as dt

from flask import request, send_file
from werkzeug.utils import secure_filename

from taky.dps import app, requires_auth


def url_for(f_hash):
    """
    Returns the URL for the given hash
    """
    return f"{request.host_url}/Marti/sync/content?hash={f_hash}"


def get_meta(f_hash=None, f_name=None):
    """
    Gets the metadata for an assigned filename or hash. If no file is found, then an empty
    dictionary is returned to the user.

    @param f_hash The file hash to index on
    @param f_name The name of the file
    @return A dictionary of the JSON metadata, or an empty dictionary on error.
    """
    if f_hash:
        meta_path = os.path.join(app.config["UPLOAD_PATH"], "meta", f"{f_hash}.json")
    elif f_name:
        meta_path = os.path.join(app.config["UPLOAD_PATH"], "meta", f"{f_name}.json")
    else:
        return {}

    try:
        with open(meta_path, encoding="utf8") as meta_fp:
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
    with open(meta_path, "w", encoding="utf8") as meta_fp:
        json.dump(meta, meta_fp)

    # Symlink the meta/{f_hash}.json to {filename}.json
    meta_hash_path = os.path.join(app.config["UPLOAD_PATH"], "meta", f"{f_hash}.json")
    try:
        os.symlink(f"{filename}.json", meta_hash_path)
    except FileExistsError:
        pass


@app.route("/Marti/sync/search")
@requires_auth
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
@requires_auth
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
    uid = meta.get("UID")
    if uid is None:
        return f"Can't find metadata for {f_hash}", 404

    f_name = meta.get("Name", f"{uid}.bin")
    f_path = os.path.join(app.config["UPLOAD_PATH"], uid)

    if not os.path.exists(f_path):
        return f"Can't find {f_path}", 404

    return send_file(f_path, as_attachment=True, download_name=f_name)


@app.route("/Marti/sync/missionupload", methods=["POST"])
@requires_auth
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
@requires_auth
def datapackage_metadata_tool(f_hash):
    """
    Update the "tool" for the datapackage (ie: public / private)
    """
    meta = get_meta(f_hash=f_hash)
    if not meta:
        return f"Could not find file matching {f_hash}", 404

    max_content_length = 4096
    data_len = request.content_length
    if data_len > max_content_length:
        return "Content length must be <= f{max_content_length}", 400

    try:
        r_data = request.get_data().decode().strip()
    except UnicodeDecodeError:
        return "Invalid data, unable to decode", 400

    if r_data not in ["public", "private"]:
        return f"Unexpected value: {r_data}", 400

    visibility = "public" if r_data == "public" else "private"

    if meta.get("Visibility", "private") != visibility:
        meta["Visibility"] = visibility
        put_meta(meta)

    return url_for(f_hash)


@app.route("/Marti/sync/missionquery")
@requires_auth
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
