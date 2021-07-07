import unittest as ut

from lxml import etree

from taky.cot import models

XML_S = """<event version="2.0" uid="GeoChat.ANDROID-deadbeef.JOKER MAN.563040b9-2ac9-4af3-9e01-4cb2b05d98ea" type="b-t-f" how="h-g-i-g-o" time="2021-02-23T22:28:22.191Z" start="2021-02-23T22:28:22.191Z" stale="2021-02-24T22:28:22.191Z">
  <point lat="1.234567" lon="-3.141592" hae="-25.8" ce="9.9" le="9999999.0"/>
  <detail>
    <__chat parent="RootContactGroup" groupOwner="false" chatroom="JOKER MAN" id="ANDROID-cafebabe" senderCallsign="JENNY">
      <chatgrp uid0="ANDROID-deadbeef" uid1="ANDROID-cafebabe" id="ANDROID-cafebabe"/>
    </__chat>
    <link uid="ANDROID-deadbeef" type="a-f-G-U-C" relation="p-p"/>
    <remarks source="BAO.F.ATAK.ANDROID-deadbeef" to="ANDROID-cafebabe" time="2021-02-23T22:28:22.191Z">test</remarks>
    <__serverdestination destinations="123.45.67.89:4242:tcp:ANDROID-deadbeef"/>
    <marti>
      <dest callsign="JOKER MAN"/>
    </marti>
  </detail>
</event>
"""


class GeoChatTestcase(ut.TestCase):
    def test_unmarshall(self):
        elm = etree.fromstring(XML_S)
        event = models.Event.from_elm(elm)
        chat = event.detail

        self.assertIsInstance(chat, models.GeoChat)
        self.assertEqual(chat.chatroom, "JOKER MAN")
        self.assertEqual(chat.chat_parent, "RootContactGroup")
        self.assertFalse(chat.group_owner)
        self.assertFalse(chat.broadcast)
        self.assertEqual(chat.src_uid, "ANDROID-deadbeef")
        self.assertEqual(chat.src_cs, "JENNY")
        self.assertEqual(chat.src_marker, "a-f-G-U-C")
        self.assertEqual(chat.message, "test")

        self.assertEqual(chat.dst_uid, "ANDROID-cafebabe")
