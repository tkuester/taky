import os
import queue
import unittest as ut
from datetime import datetime as dt
from datetime import timedelta

from lxml import etree

from taky import cot
from taky.config import load_config, app_config
from taky.cot import models
from taky.config import load_config
from . import XML_S, XML_EMPTY_MARTI_BC, UnittestTAKClient


class RouterTestcase(ut.TestCase):
    def setUp(self):
        load_config(os.devnull)
        app_config.set("taky", "redis", "false")
        app_config.set("cot_server", "log_cot", None)
        self.router = cot.COTRouter()
        self.tk1 = UnittestTAKClient(
            cbs={"route": self.router.route, "connect": self.router.send_persist}
        )
        self.tk2 = UnittestTAKClient(
            cbs={"route": self.router.route, "connect": self.router.send_persist}
        )

        elm = etree.fromstring(XML_S)
        now = dt.utcnow()
        td = timedelta(days=10)

        elm.set("time", now.isoformat())
        elm.set("start", now.isoformat())
        elm.set("stale", (now + td).isoformat())

        self.tk1_ident_msg = etree.tostring(elm)

    def test_route_packet(self):
        """
        This integration test sets up two clients, one which remains anonymous,
        and the other which identifies itself.

        We check to make sure that the router tracks the user, and that the
        anonymous user receives the packet.
        """
        # Both clients connect simultaneously
        self.router.client_connect(self.tk1)
        self.router.client_connect(self.tk2)

        # tk1 identifies self, tk2 should get message
        self.tk1.feed(self.tk1_ident_msg)
        ret = self.tk2.queue.get_nowait()
        self.assertTrue(ret.uid == "ANDROID-deadbeef")

        # The router should now have the client in it's routing table
        self.assertEqual(len(list(self.router.find_clients(uid="ANDROID-deadbeef"))), 1)
        self.assertEqual(len(list(self.router.find_clients(callsign="JENNY"))), 1)

        # And this client should not exist
        self.assertEqual(len(list(self.router.find_clients(callsign="FOOBAR"))), 0)

    def test_persist_announce(self):
        # TK1 connects, and identifies
        self.router.client_connect(self.tk1)
        self.tk1.feed(self.tk1_ident_msg)

        # TK2 connets, and mock identifies. It should receive info about TK1
        self.router.client_connect(self.tk2)
        self.router.send_persist(self.tk2)
        ret = self.tk2.queue.get_nowait()
        self.assertTrue(ret.uid == "ANDROID-deadbeef")

        # TK1 should not have any packets yet...
        self.assertRaises(queue.Empty, self.tk1.queue.get_nowait)

        # ...even if it re-mock identifies!
        self.router.send_persist(self.tk1)
        self.assertRaises(queue.Empty, self.tk1.queue.get_nowait)

    def test_geochat(self):
        # TK1 connects, and identifies
        self.router.client_connect(self.tk1)
        self.tk1.feed(self.tk1_ident_msg)

        gc = models.GeoChat(None)
        gc.src_cs = "TESTCASE"
        gc.src_uid = "ANDROID-cafebabe"
        gc.src_marker = "a-f-G-U-C"

        gc.dst_uid = "ANDROID-deadbeef"
        gc.chatroom = "JENNY"
        gc.chat_parent = "RootContactGroup"

        gc.message = "Hello world!"
        gc.message_ts = dt.utcnow()

        evt = models.Event(
            uid="GeoChat.ANDROID-deadbeef.TESTCASE.563040b9-2ac9-4af3-9e01-4cb2b05d98ea",
            etype="b-t-f",
            how="h-g-i-g-o",
            time=dt.utcnow(),
            start=dt.utcnow(),
            stale=dt.utcnow() + timedelta(1000),
        )
        evt.detail = gc

        self.router.route(None, evt)

        # TK1 should not have any packets yet...
        try:
            evt = self.tk1.queue.get_nowait()
            self.assertIsInstance(evt.detail, models.GeoChat)
            self.assertEqual(evt.detail.message, gc.message)
        except queue.Empty:
            self.fail("Message not routed to user")

    def test_empty_marti(self):
        """
        This integration test sets up two clients, and ensures that packets with
        empty <Marti> tags get routed.
        """
        # Both clients connect simultaneously
        self.router.client_connect(self.tk1)
        self.router.client_connect(self.tk2)

        elm = etree.fromstring(XML_EMPTY_MARTI_BC)
        # TODO: Mock time, instead of using real time
        now = dt.utcnow()
        td = timedelta(days=10)

        elm.set("time", now.isoformat())
        elm.set("start", now.isoformat())
        elm.set("stale", (now + td).isoformat())

        msg = etree.tostring(elm)

        # tk1 identifies self, tk2 should get message
        self.tk1.feed(msg)
        ret = self.tk2.queue.get_nowait()
        self.assertTrue(ret.uid == "EB77220E-6299-4CA3-95FC-0200BD9FE78A")
