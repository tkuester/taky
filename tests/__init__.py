import queue

from taky import cot

XML_S = b"""<event version="2.0" uid="ANDROID-deadbeef" type="a-f-G-U-C" how="m-g" time="2021-02-27T20:32:24.771Z" start="2021-02-27T20:32:24.771Z" stale="2021-02-27T20:38:39.771Z"><point lat="1.234567" lon="-3.141592" hae="-25.7" ce="9.9" le="9999999.0"/><detail><takv os="29" version="4.0.0.0 (deadbeef).1234567890-CIV" device="Some Android Device" platform="ATAK-CIV"/><contact xmppUsername="xmpp@host.com" endpoint="*:-1:stcp" callsign="JENNY"/><uid Droid="JENNY"/><precisionlocation altsrc="GPS" geopointsrc="GPS"/><__group role="Team Member" name="Cyan"/><status battery="78"/><track course="80.24833892285461" speed="0.0"/></detail></event>"""


class UnittestTAKClient(cot.TAKClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue.Queue()

    def send_event(self, msg):
        self.queue.put(msg)


def elements_equal(e1, e2):
    """
    Returns True if two elements are identical
    """
    if e1.tag != e2.tag:
        raise ValueError(f"Tags differ: {e1.tag} != {e2.tag}")
    if e1.text != e2.text:
        raise ValueError(f"Text differs: '{e1.text}' != '{e2.text}'")
    if e1.tail != e2.tail:
        raise ValueError(f"Tail differs: '{e1.tail}' != '{e2.tail}'")
    if e1.attrib != e2.attrib:
        raise ValueError(f"Attrib differs {e1.tag}.attrib != {e2.tag}.attrib")
    if len(e1) != len(e2):
        raise ValueError(
            f"Length differs: len({e1.tag})({len(e1)}) != len({e2.tag})({len(e2)})"
        )
    return all(elements_equal(c1, c2) for c1, c2 in zip(e1, e2))
