import unittest as ut

from lxml import etree

from taky.cot import models
from . import elements_equal

XML_S = b"""<event version="2.0" uid="ANDROID-deadbeef" type="a-f-G-U-C" how="m-g" time="2021-02-27T20:32:24.771Z" start="2021-02-27T20:32:24.771Z" stale="2021-02-27T20:38:39.771Z"><point lat="1.234567" lon="-3.141592" hae="-25.7" ce="9.9" le="9999999.0"/><detail><takv os="29" version="4.0.0.0 (deadbeef).1234567890-CIV" device="Some Android Device" platform="ATAK-CIV"/><contact xmppUsername="xmpp@host.com" endpoint="*:-1:stcp" callsign="JENNY"/><uid Droid="JENNY"/><precisionlocation altsrc="GPS" geopointsrc="GPS"/><__group role="Team Member" name="Cyan"/><status battery="78"/><track course="80.24833892285461" speed="0.0"/></detail></event>"""


class COTTestcase(ut.TestCase):
    def setUp(self):
        self.elm = etree.fromstring(XML_S)

    def test_unmarshall(self):
        event = models.Event.from_elm(self.elm)

        # Event
        self.assertEqual(event.version, "2.0")
        self.assertEqual(event.uid, "ANDROID-deadbeef")
        self.assertEqual(event.etype, "a-f-G-U-C")
        self.assertEqual(event.how, "m-g")
        self.assertEqual(event.time, event.start)

        # Point
        self.assertAlmostEqual(event.point.lat, 1.234567, places=6)
        self.assertAlmostEqual(event.point.lon, -3.141592, places=6)
        self.assertAlmostEqual(event.point.hae, -25.7, places=1)
        self.assertAlmostEqual(event.point.ce, 9.9, places=1)
        self.assertAlmostEqual(event.point.le, 9999999.0, places=1)

        self.assertFalse(event.has_marti)
        self.assertEqual(len(list(event.detail.marti_cs)), 0)

    def test_marshall(self):
        event = models.Event.from_elm(self.elm)

        # FIXME: from_elm seems to be modifying the elm!?
        elm = etree.fromstring(XML_S)

        self.assertTrue(elements_equal(elm, event.as_element))

    def test_marshall_err_tagname(self):
        self.elm.tag = "xxx"
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, self.elm)

    def test_marshall_err_ts_failure(self):
        self.elm.set("start", "xxx")
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, self.elm)

    def test_marshall_err_invalid_point(self):
        self.elm[0].set("lat", "xxx")
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, self.elm)

    def test_marshall_err_no_uid(self):
        self.elm.attrib.pop("uid")
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, self.elm)

    def test_marshall_err_no_type(self):
        # An element with no type
        self.elm.attrib.pop("type")
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, self.elm)

    def test_marti_exceptions(self):
        # An element with no detail/marti
        del self.elm[1]
        evt = models.Event.from_elm(self.elm)
        self.assertFalse(evt.has_marti)
