import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

from lxml import etree

from taky import cot

class XMLDeclStrip(object):
    def __init__(self):
        self.tail = b''
        self.in_decl = False

    def feed(self, data):
        start_tag = b'<?xml '
        end_tag = b'?>'

        ret = bytes()
        data = (self.tail + data)
        while len(data) > 0:
            if not self.in_decl:
                try:
                    pos = data.index(start_tag)
                    self.in_decl = True
                    ret += data[:pos]
                    data = data[pos + len(start_tag):]
                except ValueError:
                    dlen = len(data)
                    pos = data.rfind(b'<')
                    if pos < 0:
                        self.tail = b''
                        ret += data
                    elif len(data) - pos >= len(start_tag):
                        self.tail = b''
                        ret += data
                    else:
                        self.tail = data[pos:]
                        ret += data[:pos]

                    return ret

            else:
                if len(data) < len(end_tag):
                    self.tail = b''
                    return ret

                try:
                    pos = data.index(end_tag)
                    # We found the end tag, skip to it
                    self.in_decl = False
                    data = data[pos + len(end_tag):]
                    self.tail = b''
                    continue
                except ValueError:
                    # data might end with a '?'
                    self.tail = data[-1:]
                    return ret

        return ret

class TAKClient(object):
    def __init__(self, sock, event_q=None):
        self.sock = sock
        self.event_q = event_q
        self.parser = etree.XMLPullParser(tag='event')
        self.parser.feed(b'<root>')
        self.user = cot.TAKUser()
        self.xdc = XMLDeclStrip()

        self.lgr = logging.getLogger()

    def __repr__(self):
        return '<TAKClient uid=%s device=%s sock=%s>' % (self.user.uid, repr(self.user.device), repr(self.sock))

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
            if self.event_q:
                self.event_q.put((self, self.user.as_element))

    def handle_bits(self, evt):
        if self.event_q:
            self.event_q.put((self, evt))

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

