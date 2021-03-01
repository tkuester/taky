import unittest as ut

from taky import cot
from taky.config import load_config

from .test_cot_event import XML_S

class TAKClientTest(ut.TestCase):
    def test_load(self):
        cfg = load_config()
        cfg.set('taky', 'redis', 'false')
        router = cot.COTRouter(cfg)
        tk = cot.TAKClient(router)
        
        tk.feed(XML_S)

        self.assertEqual(tk.user.callsign, "JENNY")
        self.assertEqual(tk.user.uid, "ANDROID-deadbeef")
        self.assertEqual(tk.user.device.os, "29")
        self.assertEqual(tk.user.device.device, "Some Android Device")
        self.assertEqual(tk.user.group, cot.Teams.CYAN)
        self.assertEqual(tk.user.battery, '78')
        self.assertEqual(tk.user.role, 'Team Member')
