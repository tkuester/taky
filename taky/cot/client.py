# pylint: disable=missing-module-docstring
import os
import enum
from datetime import datetime as dt
from datetime import timedelta
import logging

from lxml import etree

from . import models
from ..util import XMLDeclStrip

class TAKClient:
    '''
    Holds state and information regarding a client connected to the TAK server.
    This object is designed to be somewhat agnostic as to HOW the client
    connected, and instead only focuses on what the server needs to know about
    the client.
    '''

    def __init__(self, router=None, cot_log_dir=None):
        self.router = router
        self.user = models.TAKUser()

        self.cot_log_dir = cot_log_dir
        self.cot_fp = None

        parser = etree.XMLPullParser(tag='event', resolve_entities=False)
        parser.feed(b'<root>')
        self.xdc = XMLDeclStrip(parser)

        self.lgr = logging.getLogger(TAKClient.__name__)

    def __repr__(self):
        return f'<TAKClient uid={self.user.uid} ' \
               f'callsign={self.user.callsign}>'

    def send(self, data):
        '''
        Send a CoT event to the client. Data should be a cot Event object,
        or an XML element, or a byte string.
        '''
        raise NotImplementedError()

    def close(self):
        ''' Close the COT log '''
        if self.cot_fp:
            try:
                self.cot_fp.close()
            except: # pylint: disable=bare-except
                pass
            self.cot_fp = None

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
            except OSError as exc:
                self.lgr.warning("Unable to open COT log: %s", exc)
                self.cot_fp = None
                self.cot_log_dir = None
                return

        try:
            elm = evt.as_element
            self.cot_fp.write(etree.tostring(elm, pretty_print=True).decode())
            self.cot_fp.flush()
        except (IOError, OSError) as exc:
            self.lgr.warning("Unable to write to COT log: %s", exc)
            self.close()
            self.cot_log_dir = None

    def feed(self, data):
        '''
        Feed the XML data parser with COT data
        '''
        try:
            self.xdc.feed(data)
        except etree.XMLSyntaxError as exc:
            self.lgr.warning("XML Parsing Error: %s", exc)
            # TODO: Close client? Rebuild parser?

        for (_, elm) in self.xdc.read_events():
            try:
                evt = models.Event.from_elm(elm)
            except (ValueError, TypeError) as exc:
                self.lgr.warning("Unable to parse element: %s", exc)
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
        '''
        Process a COT atom.

        Inspects the Event to see if it is a self description, and if so,
        informs the router a client has identified itself.
        '''
        if evt.detail is None:
            return

        if evt.detail.find('takv') is not None:
            first_ident = self.user.update_from_evt(evt)
            if first_ident:
                self.router.client_ident(self)

    def handle_bits(self, evt):
        '''
        Process COT bits.

        Primarily, this handles fixing Marti routing for chat messages.
        '''

        if evt.etype == 'b-t-f':
            # Currently, ATAK 4.2.0.4 does not properly set Marti for chat
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
        '''
        Process COT tasking.

        This is how the client knows it needs to send a TAK pong
        '''
        if elm.etype == 't-x-c-t':
            self.pong()

    def handle_marti(self, evt):
        '''
        Handle Marti

        For all packets, use Marti to determine how the packet should be
        routed.
        '''
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
        '''
        Generate and send a TAK pong. Clients that do not receive a pong in
        an appropriate amount of time will disconnect.
        '''
        now = dt.utcnow()
        pong = models.Event(
            uid='takPong',
            etype='t-x-c-t-r',
            how='h-g-i-g-o',
            time=now,
            start=now,
            stale=now + timedelta(seconds=20)
        )
        self.send(pong)

class SSLState(enum.Enum):
    ''' Tracks SSL state '''
    NO_SSL = 0
    SSL_WAIT = 1
    SSL_WAIT_TX = 2
    SSL_ESTAB = 4

class SocketTAKClient(TAKClient):
    '''
    A TAK client based on sockets
    '''
    def __init__(self, router, cot_log_dir=None, addr=None):
        super().__init__(router, cot_log_dir)
        self.addr = addr
        self.ssl_hs = SSLState.NO_SSL
        self.out_buff = b''

    def __repr__(self):
        return f'<SocketTAKClient uid={self.user.uid} ' \
               f'callsign={self.user.callsign} '        \
               f'addr={self.addr[0]}:{self.addr[1]}>'

    def send(self, data):
        '''
        Send a CoT event to the client. Data should be a cot Event object,
        or an XML element, or a byte string.
        '''
        if isinstance(data, models.Event):
            data = data.as_element

        # Silently drop data if the SSL handshake is not ready yet
        if self.ssl_hs in [SSLState.SSL_WAIT, SSLState.SSL_WAIT_TX]:
            return

        if etree.iselement(data):
            self.out_buff += etree.tostring(data)
        elif isinstance(data, bytes):
            self.out_buff += data
        else:
            raise ValueError("Can only send Event / XML to TAKClient!")

    @property
    def has_data(self):
        ''' Returns true if there is outbound data pending '''
        return len(self.out_buff) > 0 or self.ssl_hs == SSLState.SSL_WAIT_TX
