import os

from lxml import etree
from flask import request
from flask.wrappers import Response
from werkzeug.utils import secure_filename

from taky.dps import app, requires_auth


@app.route("/Marti/vcm", methods=["POST"])
@requires_auth
def marti_video_upload():
    """
    Accepts an XML document of video feeds, and saves them
    to the video feed directory
    """
    parser = etree.XMLParser(resolve_entities=True)
    try:
        parser.feed(request.data)
        elm = parser.close()
    except etree.XMLSyntaxError:
        return "Malformed XML", 400

    if elm.tag != "videoConnections":
        return "Invalid XML document", 400

    feeds_dir = os.path.join(app.config["UPLOAD_PATH"], "video_feed")
    if not os.path.exists(feeds_dir):
        try:
            os.mkdir(feeds_dir)
        except OSError:
            return "Sever error", 500

    for feed in elm.iterchildren():
        if feed.tag != "feed":
            return "Invalid XML document", 400

        uid = feed.find("uid")
        if uid is None:
            continue
        uid = uid.text.strip()
        path = secure_filename(f"{uid}.xml")

        try:
            with open(os.path.join(feeds_dir, path), "wb") as feed_fp:
                feed_fp.write(etree.tostring(feed, xml_declaration=True))
        except OSError:
            return "Server error", 500

    return ""


@app.route("/Marti/vcm", methods=["GET"])
@requires_auth
def marti_video_index():
    """
    Returns an XML document of all the feeds on the server
    """
    # Create root element
    doc = etree.Element("videoConnections")

    # If the directory doesn't exist, return empty
    feeds_dir = os.path.join(app.config["UPLOAD_PATH"], "video_feed")
    if not os.path.exists(feeds_dir):
        return etree.tostring(doc, xml_declaration=True)

    # Get ready to parse XML files
    parser = etree.XMLParser(resolve_entities=True)
    for fname in os.listdir(feeds_dir):
        fname = os.path.join(feeds_dir, fname)
        if not os.path.isfile(fname):
            continue
        if not fname.endswith(".xml"):
            continue

        # Read and parse the file
        try:
            with open(fname, "rb") as feed_fp:
                xml = feed_fp.read()
                parser.feed(xml)
                elm = parser.close()

                # Basic sanity check
                if elm.tag != "feed":
                    continue

                doc.append(elm)
        except etree.XMLSyntaxError as exc:
            print(exc)
            continue
        except OSError as exc:
            print(exc)
            continue

    # Return the XML document
    return Response(etree.tostring(doc, xml_declaration=True), mimetype="text/xml")
