import os
import logging
from datetime import datetime as dt
from datetime import timedelta

from lxml import etree

from . import models
from ..util import XMLDeclStrip

class TAKClient:
    def __init__(self, ip, port, router=None, cot_log_dir=None):
        self.ip = ip
        self.port = port
        self.router = router
        self.user = models.TAKUser()

        self.cot_log_dir = cot_log_dir
        self.cot_fp = None

        self.xdc = XMLDeclStrip()
        self.parser = etree.XMLPullParser(tag='event', resolve_entities=False)
        self.parser.feed(b'<root>')

        self.out_buff = b''

        self.lgr = logging.getLogger(TAKClient.__name__)

    def __repr__(self):
        return f'<TAKClient uid={self.user.uid} callsign={self.user.callsign} client={self.ip}:{self.port}>'
    def send(self, data):
        if isinstance(data, models.Event):
            data = data.as_element

        if etree.iselement(data):
            self.out_buff += etree.tostring(data)
        elif isinstance(data, bytes):
            self.out_buff += data
        else:
            raise ValueError("Can only send Event / XML to TAKClient!")

    @property
    def has_data(self):
        return len(self.out_buff) > 0

    def close(self):
        if self.cot_fp:
            try:
                self.cot_fp.close()
            except:
                pass

    def log_event(self, evt):
        '''
        Writes the COT XML to the logfile, if configured.

        @param evt The COT Event to log
        '''
        # Skip if we're not configured to log
        if not self.cot_log_dir:
            return
        # Skip logging of pings
        if evt.uid.endswith('-ping'):
            return
        # Don't log if we don't have a user yet
        if not self.user.uid:
            return

        # Open the COT file if it's the first run
        if not self.cot_fp:
            # TODO: Multiple clients with same name will fight over file
            #     : Could happen on WiFi -> LTE handoff
            name = os.path.join(self.cot_log_dir, f'{self.user.uid}.cot')
            try:
                self.lgr.info("Opening logfile %s", name)
                self.cot_fp = open(name, 'a+')
            except OSError as e:
                self.lgr.warning("Unable to open COT log: %s", e)
                self.cot_fp = None
                self.cot_log_dir = None
                return

        try:
            elm = evt.as_element
            self.cot_fp.write(etree.tostring(elm, pretty_print=True).decode())
            self.cot_fp.flush()
        except (IOError, OSError) as e:
            self.lgr.warning("Unable to write to COT log: %s", e)
            try:
                self.cot_fp.close()
            except:
                pass
            self.cot_fp = None
            self.cot_log_dir = None

    def feed(self, data):
        data = self.xdc.feed(data)
        try:
            self.parser.feed(self.xdc.feed(data))
        except etree.XMLSyntaxError as e:
            self.lgr.warning("XML Parsing Error: %s", e)

        for (_, elm) in self.parser.read_events():
            try:
                evt = models.Event.from_elm(elm)
            except (ValueError, TypeError) as e:
                self.lgr.warning("Unable to parse element: %s", e)
                self.log_event(evt)
                elm.clear(keep_tail=True)
                continue

            self.lgr.debug(evt)
            if evt.etype.startswith('a'):
                self.handle_atom(evt)
            elif evt.etype.startswith('b'):
                self.handle_bits(evt)
            elif evt.etype.startswith('t'):
                self.handle_tasking(evt)

            self.handle_marti(evt)
            self.log_event(evt)

            elm.clear(keep_tail=True)

    def handle_atom(self, evt):
        if evt.detail is None:
            return

        if evt.detail.find('takv') is not None:
            first_ident = self.user.update_from_evt(evt)
            if first_ident:
                self.router.client_ident(self)

    def handle_bits(self, evt):
        if evt.etype == 'b-t-f':
            # Currently, ATAK 4.2.0.4 does not properly set MARTI for chat
            # messages sent to teams. In any case, setting the destination as a
            # Team prevents queue-ing multiple messages in the routing
            # engine

            chat = models.GeoChat.from_elm(evt)
            if chat.src is None:
                chat.src = self.router.find_client(uid=chat.src_uid)
            if chat.dst is None:
                chat.dst = self.router.find_client(uid=chat.dst_uid)

            if self.user is not chat.src:
                self.lgr.warning("%s is sending messages for user %s", self.user, chat.src)
            if isinstance(chat.dst, models.Teams) and self.user.group != chat.dst:
                self.lgr.warning("%s is sending messages for group %s", self.user, chat.src)

            if chat.src is not None and chat.dst is not None:
                self.router.push_event(src=chat.src, evt=chat.event, dst=chat.dst)

    def handle_tasking(self, elm):
        if elm.etype == 't-x-c-t':
            self.pong()

    def handle_marti(self, evt):
        if evt.detail is None:
            return

        marti = evt.detail.find('marti')
        if marti is not None:
            for dest in marti.iterfind('dest'):
                callsign = dest.get('callsign')
                dst = self.router.find_client(callsign=callsign)
                if dst:
                    self.router.push_event(self, evt, dst)
        else:
            self.router.push_event(self, evt)

    def pong(self):
        now = dt.utcnow()
        pong = models.Event(
            uid='takPong',
            etype='t-x-c-t-r',
            how='h-g-i-g-o',
            time=now,
            start=now,
            stale=now + timedelta(seconds=20)
        )
        self.router.push_event(self, pong, dst=self)
