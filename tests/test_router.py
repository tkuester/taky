import queue
import unittest as ut
from datetime import datetime as dt
from datetime import timedelta

from lxml import etree

from taky import cot
from taky.config import load_config
from .test_cot_event import XML_S


class UnittestTAKClient(cot.TAKClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue.Queue()

    def send(self, msg):
        self.queue.put(msg)


class RouterTestcase(ut.TestCase):
    def setUp(self):
        cfg = load_config("/dev/null")
        cfg.set("taky", "redis", "false")
        cfg.set("cot_server", "cot_log", None)
        self.router = cot.COTRouter(cfg)
        self.tk1 = UnittestTAKClient(self.router)
        self.tk2 = UnittestTAKClient(self.router)

        elm = etree.fromstring(XML_S)
        now = dt.utcnow()
        td = timedelta(days=10)

        elm.set("time", now.isoformat())
        elm.set("start", now.isoformat())
        elm.set("stale", (now + td).isoformat())

        self.msg = etree.tostring(elm)

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
        self.tk1.feed(self.msg)
        ret = self.tk2.queue.get_nowait()
        self.assertTrue(ret.uid == "ANDROID-deadbeef")

        # The router should now have the client in it's routing table
        self.assertIsNot(self.router.find_client(uid="ANDROID-deadbeef"), None)
        self.assertIsNot(self.router.find_client(callsign="JENNY"), None)

        # And this client should not exist
        self.assertIs(self.router.find_client(callsign="FOOBAR"), None)

    def test_persist_announce(self):
        # TK1 connects, and identifies
        self.router.client_connect(self.tk1)
        self.tk1.feed(self.msg)

        # TK2 connets, and mock identifies. It should receive info about TK1
        self.router.client_connect(self.tk2)
        self.router.client_ident(self.tk2)
        ret = self.tk2.queue.get_nowait()
        self.assertTrue(ret.uid == "ANDROID-deadbeef")

        # TK1 should not have any packets yet...
        self.assertRaises(queue.Empty, self.tk1.queue.get_nowait)

        # ...even if it re-mock identifies!
        self.router.client_ident(self.tk1)
        self.assertRaises(queue.Empty, self.tk1.queue.get_nowait)
