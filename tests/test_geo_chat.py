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


XML_GEOCHAT_UIDS = """
<event version="2.0" uid="GeoChat.S-1-5-21-deadbeef.4ef822b6-6b70-405a-b059-997a3c1a8103.3937e268-10eb-4c60-8b5a-6c58df80cd87" type="b-t-f" how="h-g-i-g-o" time="2023-02-05T00:44:32.750Z" start="2023-02-05T00:44:32.750Z" stale="2023-02-06T00:44:32.750Z">
  <point lat="0.000000" lon="0.000000" hae="9999999.0" ce="9999999.0" le="9999999.0"/>
  <detail>
    <__chat id="4ef822b6-6b70-405a-b059-997a3c1a8103" chatroom="testgroup" senderCallsign="MAXIE" groupOwner="true" messageId="3937e268-10eb-4c60-8b5a-6c58df80cd87">
      <chatgrp id="4ef822b6-6b70-405a-b059-997a3c1a8103" uid0="S-1-5-21-deadbeef" uid1="ASN-TAK-BOT-FAKE-UID" uid2="ANDROID-deadbeef"/>
      <hierarchy>
        <group uid="UserGroups" name="Groups">
          <group uid="4ef822b6-6b70-405a-b059-997a3c1a8103" name="testgroup">
            <contact uid="ASN-TAK-BOT-FAKE-UID" name="ASN-TAK-BOT"/>
            <contact uid="ANDROID-deadbeef" name="FM05"/>
            <contact uid="S-1-5-21-deadbeef" name="MAXIE"/>
          </group>
        </group>
      </hierarchy>
    </__chat>
    <link uid="S-1-5-21-deadbeef" type="a-f-G-U-C-I" relation="p-p"/>
    <remarks source="BAO.F.WinTAK.S-1-5-21-deadbeef" sourceID="S-1-5-21-deadbeef" to="4ef822b6-6b70-405a-b059-997a3c1a8103" time="2023-02-05T00:44:32.75Z">test</remarks>
    <marti>
      <dest callsign="FM05"/>
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
        self.assertListEqual(chat.dst_group_uids, [])

        self.assertEqual(chat.dst_uid, "ANDROID-cafebabe")

    def test_group_uids(self):
        elm = etree.fromstring(XML_GEOCHAT_UIDS)
        event = models.Event.from_elm(elm)
        chat = event.detail

        expected = ["ASN-TAK-BOT-FAKE-UID", "ANDROID-deadbeef", "S-1-5-21-deadbeef"]

        self.assertCountEqual(chat.dst_group_uids, expected)
