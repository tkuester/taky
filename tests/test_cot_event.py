import unittest as ut

from lxml import etree

from taky.cot import models

XML_S = '''<event version="2.0" uid="ANDROID-deadbeef" type="a-f-G-U-C" how="m-g" time="2021-02-27T20:32:24.771Z" start="2021-02-27T20:32:24.771Z" stale="2021-02-27T20:38:39.771Z"><point lat="1.234567" lon="-3.141592" hae="-25.7" ce="9.9" le="9999999.0"/><detail><takv os="29" version="4.0.0.0 (deadbeef).1234567890-CIV" device="Some Android Device" platform="ATAK-CIV"/><contact xmppUsername="xmpp@host.com" endpoint="*:-1:stcp" callsign="JENNY"/><uid Droid="JENNY"/><precisionlocation altsrc="GPS" geopointsrc="GPS"/><__group role="Team Member" name="Cyan"/><status battery="78"/><track course="80.24833892285461" speed="0.0"/></detail></event>'''

def elements_equal(e1, e2):
    if e1.tag != e2.tag: return False
    if e1.text != e2.text: return False
    if e1.tail != e2.tail: return False
    if e1.attrib != e2.attrib: return False
    if len(e1) != len(e2): return False
    return all(elements_equal(c1, c2) for c1, c2 in zip(e1, e2))

class COTTestcase(ut.TestCase):
    def test_unmarshall(self):
        elm = etree.fromstring(XML_S)
        event = models.Event.from_elm(elm)

        # Event
        self.assertEqual(event.version, '2.0')
        self.assertEqual(event.uid, 'ANDROID-deadbeef')
        self.assertEqual(event.etype, 'a-f-G-U-C')
        self.assertEqual(event.how, 'm-g')
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
        elm = etree.fromstring(XML_S)
        event = models.Event.from_elm(elm)

        # FIXME: from_elm seems to be modifying the elm!?
        elm = etree.fromstring(XML_S)

        self.assertTrue(elements_equal(elm, event.as_element))

    def test_marshall_error(self):
        # An otherwise valid element with an incorrect tag
        elm = etree.fromstring(XML_S)
        elm.tag = 'xxx'
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, elm)

        # An otherwise valid element with an incorrect tag
        elm = etree.fromstring(XML_S)
        elm.set('start', 'xxx')
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, elm)

        # An invalid point
        elm = etree.fromstring(XML_S)
        elm[0].set('lat', 'xxx')
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, elm)

        # An element with no UID
        elm = etree.fromstring(XML_S)
        elm.attrib.pop('uid')
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, elm)

        # An element with no type
        elm = etree.fromstring(XML_S)
        elm.attrib.pop('type')
        self.assertRaises(models.UnmarshalError, models.Event.from_elm, elm)

    def test_marti_exceptions(self):
        # An element with no detail/marti
        elm = etree.fromstring(XML_S)
        del elm[1]
        evt = models.Event.from_elm(elm)
        self.assertFalse(evt.has_marti)
