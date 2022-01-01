# pylint: disable=missing-module-docstring
import time
import enum
import logging

from . import models
from .client import TAKClient
from .persistence import build_persistence


class Destination(enum.Enum):
    """
    Indicate where this packet is routed
    """

    BROADCAST = 1
    GROUP = 2


class COTRouter:
    """
    A class to keep track of clients, and ensure packets get routed properly.
    """

    def __init__(self):
        # TODO: self.clients as dictionary, with UID as keys?
        #     : should prohibit multiple sockets sharing a client
        self.clients = set()
        self.persist = build_persistence()
        self.last_prune = 0
        self.lgr = logging.getLogger(self.__class__.__name__)

    def prune(self):
        now = time.time()
        if (now - self.last_prune) > 10:
            self.last_prune = now
            self.persist.prune()

    def client_connect(self, client):
        """
        Add a client to the router
        """
        self.clients.add(client)
        self.send_persist(client)

    def client_disconnect(self, client):
        """
        Remove a client from the router
        """
        self.clients.discard(client)

    def send_persist(self, client):
        """
        Sends persistence objects to the client
        """
        self.lgr.debug("Sending persistence objects to %s", client)
        for event in self.persist.get_all():
            if client.user and event.uid == client.user.uid:
                continue

            client.send_event(event)

    def find_clients(self, uid=None, callsign=None):
        """
        Returns an iterator of objects matching the criteria
        """
        for client in self.clients:
            if not client.user:
                continue

            if uid and client.user.uid == uid:
                yield client
            if callsign and client.user.callsign == callsign:
                yield client

    def broadcast(self, src, msg):
        """
        Broadcast a message from source to all clients
        """
        if src.user:
            self.lgr.debug("%s -> Broadcast: %s", src.user.callsign, msg)
        else:
            self.lgr.debug("Anonymous Broadcast: %s", msg)

        self.persist.track(msg)
        for client in self.clients:
            if client is src:
                continue

            client.send_event(msg)

    def group_broadcast(self, src, msg, group=None):
        """
        Broadcast a message from source to all members to a group.

        If group is not specified, the source's group is used.
        """
        if isinstance(src, TAKClient):
            src = src.user

        if group is None:
            if src is None:
                raise ValueError("Unable to determine group to send to")
            group = src.group

        if not isinstance(group, models.Teams):
            raise ValueError("group must be models.Teams")

        if src:
            self.lgr.debug("%s -> %s: %s", src.callsign, group, msg)
        else:
            self.lgr.debug("Anonymous -> %s: %s", group, msg)

        for client in self.clients:
            if not client.user or (client.user is src):
                continue

            if client.user.group == group:
                client.send_event(msg)

    def send_user(self, src, msg, dst_cs=None, dst_uid=None):
        """
        Send a message to a destination by callsign or UID
        """
        for client in self.find_clients(uid=dst_uid, callsign=dst_cs):
            client.send_event(msg)

    def route(self, src, evt):
        """
        Push an event to the router
        """
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
                self.send_user(src, evt, dst_uid=chat.dst_uid)
            return

        # Check for Marti, use first
        if evt.has_marti:
            self.lgr.debug("Handling marti")
            for callsign in evt.detail.marti_cs:
                self.send_user(src, evt, dst_cs=callsign)
            return

        # Assume broadcast
        self.broadcast(src, evt)
