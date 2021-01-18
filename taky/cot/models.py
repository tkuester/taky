from dataclasses import dataclass
from datetime import datetime

from lxml import etree

@dataclass
class Point(object):
    lat: float = 0.0
    lon: float = 0.0
    hae: float = 0.0
    ce: float = 9999999.0

    @property
    def coords(self):
        return (self.lat, self.lon)

    def __repr__(self):
        return "<Point coords=(%.6f, %.6f), hae=%.1f m, ce=%.1f m>" % (
                self.lat, self.lon, self.hae, self.ce)

    @staticmethod
    def from_elm(elm):
        if elm.tag != 'point':
            raise TypeError("Cannot create Point from %s" % type(elm))

        return Point(
            lat=float(elm.get('lat')),
            lon=float(elm.get('lon')),
            hae=float(elm.get('hae')),
            ce=float(elm.get('ce'))
        )

    @property
    def as_element(self):
        ret = etree.Element('point')
        ret.set('lat', '%.6f' % self.lat)
        ret.set('lon', '%.6f' % self.lon)
        ret.set('hae', '%.1f' % self.hae)
        ret.set('ce', '%.1f' % self.ce)

        return ret

    @property
    def as_xml(self):
        return etree.tostring(self.as_element)

class Event(object):

    def __init__(self, uid=None, etype=None, how=None,
                    time=None, start=None, stale=None,
                    version="2.0"):
        self.version = version
        self.uid = uid
        self.etype = etype
        self.how = how
        self.time = time
        self.start = start
        self.stale = stale

        self.point = Point()
        self.detail = None

    @property
    def as_element(self):
        ret = etree.Element('event')
        ret.set('version', self.version)
        ret.set('uid', self.uid)
        ret.set('type', self.etype)
        ret.set('how', self.how)
        ret.set('time', self.time.strftime('%Y-%m-%dT%H:%M:%S.000Z'))
        ret.set('start', self.start.strftime('%Y-%m-%dT%H:%M:%S.000Z'))
        ret.set('stale', self.stale.strftime('%Y-%m-%dT%H:%M:%S.000Z'))
        ret.append(self.point.as_element)
        if self.detail:
            ret.append(self.detail)

        return ret

    @property
    def as_xml(self):
        return etree.tostring(self.as_element)
