import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from lxml import etree

from taky import cot
from taky.util import XMLDeclStrip

class TAKClient(object):
    def __init__(self, sock, router=None):
        self.sock = sock
        self.router = router
        self.user = cot.TAKUser()

        self.xdc = XMLDeclStrip()
        self.parser = etree.XMLPullParser(tag='event', resolve_entities=False)
        self.parser.feed(b'<root>')

        self.lgr = logging.getLogger()

    def __repr__(self):
        # IPv6 returns a 4 element tuple
        (ip, port) = self.sock.getpeername()[:2]
        return f'<TAKClient uid={self.user.uid} callsign={self.user.callsign} client={ip}:{port}>'

    def feed(self, data):
        data = self.xdc.feed(data)
        try:
            self.parser.feed(self.xdc.feed(data))
        except etree.XMLSyntaxError as e:
            self.lgr.warn("XML Parsing Error: %s", e)

        for (etype, elm) in self.parser.read_events():
            #self.lgr.debug(etree.tostring(elm))
            evt = cot.Event.from_elm(elm)
            self.lgr.debug(evt)
            if evt.etype.startswith('a'):
                self.handle_atom(evt)
            elif evt.etype.startswith('b'):
                self.handle_bits(evt)
            elif evt.etype.startswith('t'):
                self.handle_tasking(evt)
            else:
                self.lgr.warn("Unhandled event: %s", evt)
            elm.clear(keep_tail=True)

    def handle_atom(self, evt):
        if evt.detail is None:
            return

        if evt.detail.find('takv') is not None:
            self.user.update_from_evt(evt)
            self.router.push_event(self, self.user.as_element)

    def handle_bits(self, evt):
        if evt.etype == 'b-t-f':
            gc = cot.GeoChat.from_elm(evt)
        self.router.push_event(self, evt)

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
        self.router.push_event(self, pong, dst=self)
