from dataclasses import dataclass

from lxml import etree

@dataclass
class Point:
    ''' An object representing the CoT Point

    All the fields are required. If circular error (ce) or linear error (le)
    are omitted, they should be set to arbitrarily large values. (Regrettably,
    this makes a CoT Point rather large in XML.)

    (lat, lon) refers to WGS84 coordinates

    All other units are in meters.
    '''

    lat: float = 0.0
    lon: float = 0.0
    hae: float = 0.0
    ce: float = 9999999.0
    le: float = 9999999.0

    @property
    def coords(self):
        return (self.lat, self.lon)

    def __repr__(self):
        return "<Point coords=(%.6f, %.6f), hae=%.1f m, ce=%.1f m>" % (
                self.lat, self.lon, self.hae, self.ce)

    @staticmethod
    def from_elm(elm):
        if elm.tag != 'point':
            raise TypeError("Cannot create Point from %s" % elm.tag)

        return Point(
            lat=float(elm.get('lat')),
            lon=float(elm.get('lon')),
            hae=float(elm.get('hae')),
            ce=float(elm.get('ce')),
            le=float(elm.get('le'))
        )

    @property
    def as_element(self):
        ret = etree.Element('point')
        ret.set('lat', '%.6f' % self.lat)
        ret.set('lon', '%.6f' % self.lon)
        ret.set('hae', '%.1f' % self.hae)
        ret.set('ce', '%.1f' % self.ce)
        ret.set('le', '%.1f' % self.le)

        return ret
