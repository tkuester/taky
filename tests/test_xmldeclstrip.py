import unittest as ut

from lxml.etree import XMLPullParser

from taky.util import XMLDeclStrip


class XDCTest(ut.TestCase):
    def setUp(self):
        parser = XMLPullParser(tag="event")
        parser.feed(b"<root>")
        self.xdc = XMLDeclStrip(parser)

    def test_valid_xml(self):
        self.xdc.feed(b"<?xml version='1.0' encoding='utf-8'?>")
        self.xdc.feed(b'<event data="stuff here" />')

        evts = list(self.xdc.read_events())
        self.assertEqual(len(evts), 1)

    def test_split_decl(self):
        self.xdc.feed(b"<?xm")
        self.xdc.feed(b"l version='1.0' encoding='utf-8'?>")
        self.xdc.feed(b'<event data="stuff here" />')

        evts = list(self.xdc.read_events())
        self.assertEqual(len(evts), 1)

    def test_split_decl2(self):
        self.xdc.feed(b"<?xml version='1.0' encoding='utf-8'?")
        self.xdc.feed(b">")
        self.xdc.feed(b'<event data="stuff here" />')

        evts = list(self.xdc.read_events())
        self.assertEqual(len(evts), 1)

    def test_split_decl3(self):
        self.xdc.feed(b"<?xml version='1.0' encoding='utf-8'?>")
        self.xdc.feed(b'<event data="stuff here" /><')
        self.xdc.feed(b"?xml version='1.0' encoding='utf-8'?>")
        self.xdc.feed(b'<event data="stuff here" />')

        evts = list(self.xdc.read_events())
        self.assertEqual(len(evts), 2)

    def test_split_data(self):
        self.xdc.feed(b"<?xml version='1.0' encoding='utf-8'?>")
        self.xdc.feed(b'<event data="stuff')
        self.xdc.feed(b' here" />')

        evts = list(self.xdc.read_events())
        self.assertEqual(len(evts), 1)
