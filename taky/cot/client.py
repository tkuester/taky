import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from lxml import etree

from taky import cot

class TAKClient(object):
    def __init__(self, sock, event_q=None):
        self.sock = sock
        self.event_q = event_q
        self.parser = etree.XMLPullParser(tag='event')
        self.user = cot.TAKUser()

        self.lgr = logging.getLogger()

    def __repr__(self):
        return '<TAKClient uid=%s device=%s sock=%s>' % (self.user.uid, repr(self.user.device), repr(self.sock))

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
        if evt.detail is None:
            return

        if evt.detail.find('takv') is not None:
            self.user.update_from_evt(evt)
            if self.event_q:
                self.event_q.put((self, self.user.as_element))

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
        self.sock.sendall(etree.tostring(pong.as_element))

