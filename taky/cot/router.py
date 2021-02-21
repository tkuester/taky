# pylint: disable=missing-module-docstring
import enum
import logging

from lxml import etree

from . import models
from .client import TAKClient

class Destination(enum.Enum):
    '''
    Indicate where this packet is routed
    '''
    BROADCAST=1
    GROUP=2

class COTRouter:
    '''
    Simple class to route packets. A class is a bit over kill when a simple
    function would do, but currently the router needs to know what clients are
    available to send packets to.
    '''
    def __init__(self):
        # TODO: self.clients as dictionary, with UID as keys?
        #     : should prohibit multiple sockets sharing a client
        self.clients = set()
        self.lgr = logging.getLogger(self.__class__.__name__)

    def client_connect(self, client):
        '''
        Add a client to the router
        '''
        self.clients.add(client)

    def client_disconnect(self, client):
        '''
        Remove a client from the router
        '''
        self.clients.discard(client)

    def client_ident(self, client):
        '''
        Called by TAKClient when the client first identifies to the server
        '''
        self.lgr.debug("Sending active clients to %s", client)
        for _client in self.clients:
            if _client is client:
                continue
            if _client.user.uid is None:
                continue

            client.send(_client.user.as_element)

    def find_client(self, uid=None, callsign=None):
        '''
        Search the client database for a requested client
        '''
        for client in self.clients:
            if uid and client.user.uid == uid:
                return client
            if callsign and client.user.callsign == callsign:
                return client

        return None

    def broadcast(self, src, msg):
        '''
        Broadcast a message from source to all clients
        '''
        for client in self.clients:
            if client is src:
                continue

            client.send(msg)

    def group_broadcast(self, src, msg, group=None):
        '''
        Broadcast a message from source to all members to a group.

        If group is not specified, the source's group is used.
        '''
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
        '''
        Push an event to the router
        '''
        if dst is None:
            dst = Destination.BROADCAST

        if isinstance(evt, models.Event):
            xml = etree.tostring(evt.as_element)
        elif etree.iselement(evt) and evt.tag == 'event':
            xml = etree.tostring(evt)
        else:
            raise ValueError(f"Unable to handle event of type {type(evt)}")

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
