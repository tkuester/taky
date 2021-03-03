from flask import request

from taky.dps import app


@app.route("/Marti/TracksKML", methods=["POST"])
def marti_tracks_kml():
    print(request.args)
    print(request.data)
    return ""


@app.route("/Marti/ExportMissionKML")
def marti_mission_kml():
    """
    [
        ('startTime', '2021-02-12T00:00:00.0Z'),
        ('endTime', '2021-02-19T23:59:59.9Z'),
        ('uid', 'ANDROID-43fa2bcefa93135a'),
        ('multiTrackThreshold', '10'),
        ('extendedData', 'true'),
        ('format', 'kmz'),
        ('optimizeExport', 'true')
    ]
    """

    ret = "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>"
    ret += '<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">'
    ret += "</kml>"
    return ret
