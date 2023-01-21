from datetime import datetime as dt

from lxml import etree
from dateutil.parser import isoparse

from .errors import UnmarshalError
from .point import Point
from .detail import Detail
from .geochat import GeoChat
from .takuser import TAKUser


class Event:
    def __init__(
        self,
        uid=None,
        etype=None,
        how=None,
        time=None,
        start=None,
        stale=None,
        version="2.0",
    ):
        self.version = version
        self.uid = uid
        self.etype = etype
        self.how = how
        self.time = time
        self.start = start
        self.stale = stale

        self.point = Point()
        self.detail = None

    def __repr__(self):
        return '<Event uid="%s" etype="%s" time="%s">' % (
            self.uid,
            self.etype,
            self.time,
        )

    @property
    def persist_ttl(self):
        return round((self.stale - dt.utcnow()).total_seconds())

    @staticmethod
    def from_elm(elm):
        if elm.tag != "event":
            raise UnmarshalError("Cannot create Event from %s" % elm.tag)

        try:
            time = isoparse(elm.get("time")).replace(tzinfo=None)
            start = isoparse(elm.get("start")).replace(tzinfo=None)
            stale = isoparse(elm.get("stale")).replace(tzinfo=None)
        except (TypeError, ValueError) as exc:
            raise UnmarshalError("Date parsing error") from exc

        ret = Event(
            version=elm.get("version"),
            uid=elm.get("uid"),
            etype=elm.get("type"),
            how=elm.get("how"),
            time=time,
            start=start,
            stale=stale,
        )

        if ret.uid is None:
            raise UnmarshalError("Event must have 'uid' attribute")
        if ret.etype is None:
            raise UnmarshalError("Event must have 'type' attribute")

        child = None
        try:
            for child in elm.iterchildren():
                if child.tag == "point":
                    ret.point = Point.from_elm(child)
                elif child.tag == "detail":
                    d_tags = set([d_elm.tag for d_elm in child.iterchildren()])
                    if TAKUser.is_type(d_tags):
                        ret.detail = TAKUser.from_elm(child, uid=ret.uid)
                    elif GeoChat.is_type(d_tags):
                        ret.detail = GeoChat.from_elm(child)
                    else:
                        ret.detail = Detail.from_elm(child)
        except (TypeError, ValueError, AttributeError) as exc:
            if child is not None:
                raise UnmarshalError(f"Issue parsing {child.tag}") from exc
            else:
                raise UnmarshalError("Issue parsing children") from exc

        return ret

    @property
    def as_element(self):
        ret = etree.Element("event")
        ret.set("version", self.version)
        ret.set("uid", self.uid)
        ret.set("type", self.etype)
        ret.set("how", self.how)
        ret.set("time", self.time.isoformat(timespec="milliseconds") + "Z")
        ret.set("start", self.start.isoformat(timespec="milliseconds") + "Z")
        ret.set("stale", self.stale.isoformat(timespec="milliseconds") + "Z")
        ret.append(self.point.as_element)
        if self.detail is not None:
            ret.append(self.detail.as_element)

        return ret
