import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from lxml import etree
import dateutil.parser

lgr = logging.getLogger()

class GeoChat(object):
    def __init__(self):
        self.uid = None
        self.chatroom = None
        self.chat_id = None
        self.sender_cs = None
        self.remarks_to = None
        self.remarks_src = None
        self.message = None

        self.time = None
        self.point = None

    @staticmethod
    def from_elm(elm):
        # Sanity check inputs
        if elm.detail is None:
            return

        chat = elm.detail.find('__chat')
        remarks = elm.detail.find('remarks')

        if chat is None or remarks is None:
            return

        gch = GeoChat()
        gch.uid = elm.uid
        gch.time = elm.time
        gch.point = elm.point

        gch.chatroom = chat.get('chatroom')
        gch.chat_id = chat.get('id')
        gch.sender_cs = chat.get('senderCallsign')
        gch.remarks_to = remarks.get('to')
        gch.remarks_src = remarks.get('source')
        gch.message = remarks.text

        lgr.info("%s", gch)
        return gch

    def __str__(self):
        return "[ #%s ] < %s >: %s" % (self.chatroom, self.sender_cs, self.message)

@dataclass
class TAKDevice(object):
    os: str = None
    version: str = None
    device: str = None
    platform: str = None

    def __repr__(self):
        return '<TAKDevice %s (%s) on %s>' % (self.platform, self.version, self.device)

    @staticmethod
    def from_elm(elm):
        if elm.tag != 'takv':
            raise ValueError("Unable to load TAKDevice from %s" % elm.tag)

        return TAKDevice(
            os = elm.get('os'),
            device = elm.get('device'),
            version = elm.get('version'),
            platform = elm.get('platform')
        )

    @property
    def as_element(self):
        ret = etree.Element('takv')
        ret.set('os', self.os or '')
        ret.set('device', self.device or '')
        ret.set('version', self.version or '')
        ret.set('platform', self.platform or '')

        return ret

    @property
    def as_xml(self):
        return etree.tostring(self.as_element)

@dataclass
class TAKUser(object):
    def __init__(self):
        self.uid = None
        self.callsign = None
        self.phone = None
        self.marker = None
        self.group = None
        self.role = None

        self.point = Point()
        self.course = None
        self.speed = None

        self.battery = None

        self.device = None

    def update_from_evt(self, evt):
        # Sanity check inputs
        if evt.detail is None:
            return
        if evt.detail.find('takv') is None:
            return

        # Is this our first run?
        if self.uid is None:
            self.uid = evt.uid

        # Don't update the user if it's a different UID
        if self.uid != evt.uid:
            return

        self.marker = evt.etype
        self.point = evt.point

        for elm in evt.detail.iterchildren():
            if elm.tag == 'takv':
                self.device = TAKDevice.from_elm(elm)
            elif elm.tag == 'contact':
                self.callsign = elm.get('callsign')
                self.phone = elm.get('phone')
            elif elm.tag == '__group':
                self.group = elm.get('group')
                self.role = elm.get('role')
            elif elm.tag == 'status':
                self.battery = elm.get('battery')
            elif elm.tag == 'track':
                self.course = float(elm.get('course'))
                self.speed = float(elm.get('speed'))
            elif elm.tag == 'uid':
                pass
            elif elm.tag == 'precisionlocation':
                pass
            else:
                #self.lgr.warn("Unhandled TAKClient detail: %s", elm.tag)
                pass

    @property
    def as_element(self, stale_s=20):
        now = datetime.utcnow()
        stale = now + timedelta(seconds=stale_s)
        evt = Event(
            uid=self.uid,
            etype=self.marker or 'a-f',
            how='m-g',
            time=now,
            start=now,
            stale=stale
        )
        evt.point = self.point
        evt.detail = etree.Element('detail')
        if self.device:
            takv = etree.Element('takv', attrib={
                'os': self.device.os or '30',
                'version': self.device.version or 'unknown',
                'device': self.device.device or 'unknown',
                'platform': self.device.platform or 'unknown',
            })
            evt.detail.append(takv)

            status = etree.Element('status', attrib={
                'battery': self.battery or '100',
            })
            evt.detail.append(status)

        uid = etree.Element('uid', attrib={
            'Droid': self.callsign or 'JENNY'
        })
        evt.detail.append(uid)

        contact = etree.Element('contact', attrib={
            'callsign': self.callsign or 'JENNY',
            'endpoint': '*:-1:stcp',
        })
        if self.phone:
            contact.set('phone', self.phone)
        evt.detail.append(contact)

        group = etree.Element('__group', attrib={
            'role': self.role or 'Team Member',
            'name': self.group or 'Cyan',
        })
        evt.detail.append(group)

        track = etree.Element('track', attrib={
            'course': '%.1f' % (self.course or 0.0),
            'speed': '%.1f' % (self.speed or 0.0),
        })
        evt.detail.append(track)

        precisloc = etree.Element('precisionlocation', attrib={
            'altsrc': 'GPS',
            'geopointsrc': 'GPS',
        })
        evt.detail.append(precisloc)

        return evt.as_element

@dataclass
class Point(object):
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

    def __repr__(self):
        return '<Event uid="%s" type="%s" time=%s">' % (self.uid, self.etype, self.time)

    @staticmethod
    def from_elm(elm):
        if elm.tag != 'event':
            raise TypeError('Cannot create Event from %s' % elm.tag)

        time = dateutil.parser.isoparse(elm.get('time')).replace(tzinfo=None)
        start = dateutil.parser.isoparse(elm.get('start')).replace(tzinfo=None)
        stale = dateutil.parser.isoparse(elm.get('stale')).replace(tzinfo=None)

        ret = Event(
            version=elm.get('version'),
            uid=elm.get('uid'),
            etype=elm.get('type'),
            how=elm.get('how'),
            time=time,
            start=start,
            stale=stale
        )

        for child in elm.iterchildren():
            if child.tag == 'point':
                ret.point = Point.from_elm(child)
            elif child.tag == 'detail':
                ret.detail = child

        return ret

    @property
    def as_element(self):
        ret = etree.Element('event')
        ret.set('version', self.version)
        ret.set('uid', self.uid)
        ret.set('type', self.etype)
        ret.set('how', self.how)
        ret.set('time', self.time.isoformat(timespec='milliseconds') + 'Z')
        ret.set('start', self.start.isoformat(timespec='milliseconds') + 'Z')
        ret.set('stale', self.stale.isoformat(timespec='milliseconds') + 'Z')
        ret.append(self.point.as_element)
        if self.detail is not None:
            ret.append(self.detail)

        return ret
