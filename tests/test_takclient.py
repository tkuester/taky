import os
import unittest as ut
import mock

from taky import cot
from taky.config import load_config, app_config

from .test_cot_event import XML_S


class TAKClientTest(ut.TestCase):
    def setUp(self):
        load_config(os.devnull)
        app_config.set("taky", "redis", "false")
        router = cot.COTRouter()
        self.tk = cot.TAKClient(cbs={"route": router.route})

    def test_ident(self):
        self.tk.feed(XML_S)

        self.assertEqual(self.tk.user.callsign, "JENNY")
        self.assertEqual(self.tk.user.uid, "ANDROID-deadbeef")
        self.assertEqual(self.tk.user.device.os, "29")
        self.assertEqual(self.tk.user.device.device, "Some Android Device")
        self.assertEqual(self.tk.user.group, cot.Teams.CYAN)
        self.assertEqual(self.tk.user.battery, "78")
        self.assertEqual(self.tk.user.role, "Team Member")


class SocketTAKClientTest(ut.TestCase):
    def setUp(self):
        load_config(os.devnull)
        app_config.set("taky", "redis", "false")
        router = cot.COTRouter()

        self.mock_sock = mock.patch("socket.socket")
        self.sock = self.mock_sock.start()
        self.sock.recv.return_value = b"</invalid>"
        self.sock.getpeername.return_value = (
            "127.0.0.1",
            12345,
        )

        self.tk = cot.SocketTAKClient(sock=self.sock, use_ssl=False, router=router)

    def test_invalid_xml(self):
        self.tk.socket_rx()
        self.sock.close.assert_called()

    def tearDown(self):
        self.mock_sock.stop()
