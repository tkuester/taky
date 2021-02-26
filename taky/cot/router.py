# pylint: disable=missing-module-docstring
import enum
import logging

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

    def route(self, src, evt):
        '''
        Push an event to the router
        '''
        if not isinstance(evt, models.Event):
            raise ValueError(f"Unable to route {type(evt)}")

        # Special handling for chat messages
        if isinstance(evt.detail, models.GeoChat):
            chat = evt.detail
            if chat.broadcast:
                self.broadcast(src, evt)
            elif chat.dst_team:
                self.group_broadcast(src, evt, group=chat.dst_team)
            else:
                client = self.find_client(uid=chat.dst_uid)
                if client:
                    client.send(evt)
                else:
                    self.lgr.warning("No destination for %s", chat)
            return

        # Check for Marti, use first
        if evt.detail and evt.detail.marti_cs:
            for cs in evt.detail.marti_cs:
                client = self.find_client(callsign=cs)
                if client:
                    client.send(evt)
            return

        # Assume broadcast
        self.broadcast(src, evt)
