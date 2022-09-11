import os
import queue
import unittest as ut
from unittest import mock
from datetime import datetime as dt
from datetime import timedelta

from lxml import etree

from taky import cot
from taky.config import load_config, app_config
from taky.cot import models
from taky.config import load_config
from . import XML_S, UnittestTAKClient


class RouterMaxTTLTestcase(ut.TestCase):
    def setUp(self):
        self.max_ttl_s = 10
        load_config(os.devnull)
        app_config.set("taky", "redis", "false")
        app_config.set("cot_server", "log_cot", None)
        app_config.set("cot_server", "max_persist_ttl", str(self.max_ttl_s))

        self.router = cot.COTRouter()
        self.tk1 = UnittestTAKClient(
            cbs={"route": self.router.route, "connect": self.router.send_persist}
        )
        self.tk2 = UnittestTAKClient(
            cbs={"route": self.router.route, "connect": self.router.send_persist}
        )

        elm = etree.fromstring(XML_S)
        self.now = now = dt(2022, 1, 1)
        td = timedelta(days=10)

        elm.set("time", now.isoformat())
        elm.set("start", now.isoformat())
        elm.set("stale", (now + td).isoformat())

        self.tk1_ident_msg = etree.tostring(elm)

    @mock.patch("taky.cot.persistence.dt")
    @mock.patch("taky.cot.models.event.dt")
    @mock.patch("taky.cot.router.dt")
    def test_max_ttl(self, mock_dt1, mock_dt2, mock_dt3):
        mock_dt1.utcnow = mock.Mock(return_value=self.now)
        mock_dt2.utcnow = mock.Mock(return_value=self.now)
        mock_dt3.utcnow = mock.Mock(return_value=self.now)

        # TK1 connects, and identifies
        self.router.client_connect(self.tk1)
        self.router.send_persist(self.tk2)
        self.tk1.feed(self.tk1_ident_msg)

        # TK2 connets, and mock identifies. It should receive info about TK1
        self.router.client_connect(self.tk2)
        self.router.send_persist(self.tk2)
        ret = self.tk2.queue.get_nowait()
        self.assertTrue(ret.uid == "ANDROID-deadbeef")
        self.assertTrue(ret.persist_ttl == self.max_ttl_s)
