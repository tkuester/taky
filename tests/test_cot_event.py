import unittest as ut

from lxml import etree

from taky.cot import models
from . import elements_equal, XML_S


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

        self.assertFalse(event.detail.has_marti)
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
        self.assertTrue(evt.detail is None)
