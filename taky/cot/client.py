import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from lxml import etree

from taky import cot

class TAKClient(object):
    def __init__(self, sock, server):
        self.sock = sock
        # FIXME: This is so bad
        self.server = server

        self.uid = None
        self.callsign = None
        self.phone = None
        self.marker = None
        self.group = None
        self.role = None

        self.point = None
        self.course = None
        self.speed = None

        self.device = None
        self.parser = etree.XMLPullParser(tag='event')
        self.lgr = logging.getLogger()

    def __repr__(self):
        return '<TAKClient device=%s sock=%s>' % (repr(self.device), repr(self.sock))

    def from_elm(self, elm):
        if elm.tag == 'takv':
            self.device = TAKDevice.from_elm(elm)
        elif elm.tag == 'contact':
            self.callsign = elm.get('callsign')
            self.phone = elm.get('phone')
        elif elm.tag == '__group':
            self.group = elm.get('group')
            self.role = elm.get('role')
        elif elm.tag == 'status':
            self.device.battery = elm.get('battery')
        elif elm.tag == 'track':
            self.course = float(elm.get('course'))
            self.speed = float(elm.get('speed'))
        elif elm.tag == 'uid':
            pass
        elif elm.tag == 'precisionlocation':
            pass
        else:
            self.lgr.warn("Unhandled TAKClient detail: %s", elm.tag)

    def feed(self, data):
        # XXX: This is the ugliest way to handle multiple <?xml> tags
        for ch in data:
            try:
                # FIXME: Safer XML input handling
                self.parser.feed(chr(ch))
            except etree.XMLSyntaxError as e:
                continue

        for (etype, elm) in self.parser.read_events():
            evt = cot.Event.from_elm(elm)
            self.lgr.debug(str(evt))
            if evt.etype.startswith('a'):
                self.handle_atom(evt)
            elif evt.etype.startswith('t'):
                self.handle_tasking(evt)
            else:
                self.lgr.warn("Unhandled event: %s", evt)
            elm.clear(keep_tail=True)

    def handle_atom(self, evt):
        if evt.detail is not None and evt.detail.find('takv') is not None:
            if self.uid is None:
                self.uid = evt.uid

            if self.uid == evt.uid:
                self.marker = evt.etype
                self.point = evt.point
                for child in evt.detail.iterchildren():
                    self.from_elm(child)

                if self.server is None:
                    return

                out = etree.tostring(self.as_element)
                for client in self.server.clients.values():
                    if client is self:
                        continue

                    self.lgr.info("Broadcasting update from %s to %s", self, client)
                    self.lgr.info(out)
                    client.sock.sendall(out)

    def handle_tasking(self, elm):
        if elm.etype == 't-x-c-t':
            self.pong()

    def pong(self):
        now = datetime.utcnow()
        pong = cot.Event(
            uid='takPong',
            etype='t-x-c-t-r',
            how='h-g-i-g-o',
            time=now,
            start=now,
            stale=now + timedelta(seconds=20)
        )
        self.sock.sendall(pong.as_xml)

    @property
    def as_element(self, stale_s=20):
        now = datetime.utcnow()
        stale = now + timedelta(seconds=stale_s)
        evt = cot.Event(
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
                'battery': self.device.battery or '100',
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
class TAKDevice(object):
    os: str = None
    version: str = None
    device: str = None
    platform: str = None
    battery: str = None

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
