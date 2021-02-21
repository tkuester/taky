import queue
import enum
import logging

from lxml import etree

from . import models
from .client import TAKClient

class Destination(enum.Enum):
    BROADCAST=1
    GROUP=2

class COTRouter:
    def __init__(self):
        self.clients = set()
        self.lgr = logging.getLogger(self.__class__.__name__)

    def client_connect(self, client):
        self.clients.add(client)

    def client_disconnect(self, client):
        self.clients.discard(client)

    def client_ident(self, client):
        self.lgr.debug("Sending active clients to %s", client)
        for _client in self.clients:
            if _client is client:
                continue
            if _client.user.uid is None:
                continue

            client.send(_client.user.as_element)

    def find_client(self, uid=None, callsign=None):
        for client in self.clients:
            if uid and client.user.uid == uid:
                return client
            if callsign and client.user.callsign == callsign:
                return client

        return None

    def broadcast(self, src, msg):
        for client in self.clients:
            if client is src:
                continue

            # TODO: Timeouts? select() on writable sockets
            client.send(msg)

    def group_broadcast(self, src, msg, group=None):
        if group is None:
            if isinstance(src, models.TAKUser):
                group = src.group
            elif isinstance(src, TAKClient):
                group = src.user.group
            else:
                raise ValueError("Unable to determine group to send to")

        if not isinstance(group, models.Teams):
            raise ValueError("group must be models.Teams")

        for client in self.clients:
            if client.user is src:
                continue

            if client.user.group == group:
                client.send(msg)

    def push_event(self, src, evt, dst=None):
        if not isinstance(evt, (models.Event, etree._Element)):
            raise ValueError("Must be models.Event or lxml Element")

        if dst is None:
            dst = Destination.BROADCAST

        if isinstance(evt, models.Event):
            xml = etree.tostring(evt.as_element)
        elif etree.iselement(evt) and evt.tag == 'event':
            xml = etree.tostring(evt)
        else:
            raise ValueError("Unable to handle event of type %s", type(evt))

        if dst is Destination.BROADCAST:
            self.broadcast(src, xml)
        elif dst is Destination.GROUP:
            self.group_broadcast(src, xml)
        elif isinstance(dst, models.Teams):
            self.group_broadcast(src, xml, dst)
        elif isinstance(dst, TAKClient):
            dst.send(xml)
        elif isinstance(dst, models.TAKUser):
            client = self.find_client(uid=dst.uid)
            if client is None:
                self.lgr.warning("Can't find client for %s to deliver message", dst)
            else:
                client.send(xml)
        else:
            self.lgr.warning("Don't know what to do with %s", evt)
