import os
import unittest as ut

from taky import cot
from taky.config import load_config, app_config

from .test_cot_event import XML_S


class TAKClientTest(ut.TestCase):
    def setUp(self):
        load_config(os.devnull)
        app_config.set("taky", "redis", "false")
        router = cot.COTRouter()
        self.tk = cot.TAKClient(router)

    def test_ident(self):
        self.tk.feed(XML_S)

        self.assertEqual(self.tk.user.callsign, "JENNY")
        self.assertEqual(self.tk.user.uid, "ANDROID-deadbeef")
        self.assertEqual(self.tk.user.device.os, "29")
        self.assertEqual(self.tk.user.device.device, "Some Android Device")
        self.assertEqual(self.tk.user.group, cot.Teams.CYAN)
        self.assertEqual(self.tk.user.battery, "78")
        self.assertEqual(self.tk.user.role, "Team Member")
