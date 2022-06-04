"""
A collection of classes that implement persistence

Currently, this class is only designed to track broadcast items, like markers,
atom locations, and map drawings. A brief description of some event types
follows.

Atoms:
  a-f-G-U-C / User Update (f-G-U-C) points
  a-u-G / Marker

Bits:
  b-m-p-w-GOTO # Go to this thing
  b-m-p-s-p-i # Digital Pointer (cuepoint)
  b-m-p (Generic point prefix, log all)
  b-f-t-r / Picture / File download request (Don't log)
  b-r-f-h-c / EVAC
  b-t-f / GeoChat
  b-a-o-tbl / Emergency
  b-a-o-can / Emergency canceled

User (?) Drawings
  u-d-c / Drawing (circle)
  u-d-r / Drawing (rectangle)
  u-d-f / Drawing (line / polygon)

UDP Like Commands
  t-x-c-t / Ping
  c - Capability
  r - Reply
"""

from datetime import datetime as dt
import logging

from lxml import etree
import redis

from taky.config import app_config as config
from . import models

KEPT_EVENTS = [
    "a-",
    "b-m-p",
    "b-r-f-h-c",
    "u-d-c",
    "u-d-r",
    "u-d-f",
]


def build_persistence():
    """
    Factory method to build a Persistence object from the given config
    """
    try:
        if config.getboolean("taky", "redis"):
            return RedisPersistence(config.get("taky", "hostname"))

        return Persistence()
    except (AttributeError, ValueError):
        pass

    conn_str = config.get("taky", "redis")
    if conn_str:
        return RedisPersistence(config.get("taky", "hostname"), conn_str)

    return Persistence()


class BasePersistence:
    def __init__(self):
        self.lgr = logging.getLogger(self.__class__.__name__)

    def track(self, event):
        """
        @return False if the item should not be tracked, otherwise the TTL
        """
        ttl = False
        # TODO: Regex probably faster?
        for etype in KEPT_EVENTS:
            if event.etype.startswith(etype):
                ttl = event.persist_ttl
                break

        if not ttl or ttl < 0:
            return

        if self.event_exists(event.uid):
            self.lgr.debug("Updating tracking for: %s (ttl: %d)", event, ttl)
        else:
            self.lgr.debug("New item to track: %s (ttl: %d)", event, ttl)

        self.track_event(event, ttl)

    def track_event(self, event, ttl):
        """
        Add the event to the database
        """
        raise NotImplementedError()

    def get_all(self):
        """
        Return all items tracked
        """
        raise NotImplementedError()

    def get_event(self, uid):
        """
        Return a specific Event by UID. Returns None if the event does not
        exist.
        """
        raise NotImplementedError()

    def event_exists(self, uid):
        """
        Return true if the event exists
        """
        raise NotImplementedError()

    def prune(self):
        """
        Prune the collection
        """
        # In this case, assume nothing needs to be done
        return


class Persistence(BasePersistence):
    """
    A simple memory based persistence object. Events are stored as objects in a
    dictionary. Whenever the dictionary is updated or accessed, it is pruned.

    This object has no long term storage. If taky quits, all the objects are
    lost.
    """

    def __init__(self):
        super().__init__()
        self.events = {}

    def track_event(self, event, ttl):
        self.events[event.uid] = event
        self.prune()

    def event_exists(self, uid):
        return uid in self.events

    def get_event(self, uid):
        self.prune()
        return self.events.get("uid")

    def get_all(self):
        self.prune()
        ret = self.events.values()

        return ret

    def prune(self):
        """
        Go through the database, and delete items that have expired
        """
        uids = []
        now = dt.utcnow()

        for item in self.events.values():
            if now > item.stale:
                self.lgr.info("Pruning %s, stale is %s", item, item.stale)
                uids.append(item.uid)

        for uid in uids:
            self.events.pop(uid)


class RedisPersistence(BasePersistence):
    """
    A Redis backed persistence object, useful for keeping track of events,
    even if taky restarts. This also allows other systems which can
    communicate with Redis to access the events.

    Events are stored as raw XML, and makes use of Redis' EXPIRE command to
    automatically prune events.

    The events are stored under the following keyspace:
      taky:{keyspace}:persist:{event.uid} = <xml>

    In most configurations, keyspace should be the hostname.
    """

    def __init__(self, keyspace=None, conn_str=None):
        super().__init__()
        self.rds_ok = True
        if keyspace:
            self.rds_ks = f"taky:{keyspace}:persist"
        else:
            self.rds_ks = "taky:persist"

        if conn_str:
            self.lgr.info("Connecting to %s", conn_str)
            self.rds = redis.StrictRedis.from_url(conn_str)
        else:
            self.lgr.info("Connecting to default redis")
            self.rds = redis.StrictRedis()

        try:
            total = len(self.rds.keys(f"{self.rds_ks}:*"))
            self.lgr.info("Tracking %d items", total)
            self._redis_result(True)
        except redis.ConnectionError:
            self._redis_result(False)

    def _redis_result(self, result):
        """
        Simple set/reset latch to notify the user if the connection to the
        redis server is lost
        """
        if self.rds_ok and not result:
            self.lgr.warning("Lost connection to redis")
        elif not self.rds_ok and result:
            self.lgr.warning("Connection to redis restored")

        self.rds_ok = result

    def track_event(self, event, ttl):
        try:
            key = f"{self.rds_ks}:{event.uid}"
            self.rds.set(key, etree.tostring(event.as_element))
            self.rds.expire(key, ttl)
            self._redis_result(True)
        except redis.ConnectionError:
            self._redis_result(False)

    def event_exists(self, uid):
        return self._event_exists(uid)

    def _event_exists(self, uid, uid_is_redis_key=False):
        if uid_is_redis_key:
            key = uid
        else:
            key = f"{self.rds_ks}:{uid}"

        exists = False

        try:
            exists = self.rds.exists(key) > 0
            self._redis_result(True)
        except redis.ConnectionError:
            self._redis_result(False)

        return exists

    def get_event(self, uid):
        return self._get_event(uid)

    def _get_event(self, uid, uid_is_redis_key=False):
        if uid_is_redis_key:
            key = uid
        else:
            key = f"{self.rds_ks}:{uid}"

        evt = None
        purge = False
        try:
            xml = self.rds.get(key)
            self._redis_result(True)
            if xml is None:
                return None

            parser = etree.XMLParser(resolve_entities=False)
            parser.feed(xml)
            elm = parser.close()

            evt = models.Event.from_elm(elm)
        except (models.UnmarshalError, etree.XMLSyntaxError) as exc:
            self.lgr.warning("Unable to parse Event from persistence store: %s", exc)
            purge = True
        except redis.ResponseError as exc:
            self.lgr.warning("Unable to get Event from persistence store: %s", exc)
            purge = True
        except redis.ConnectionError as exc:
            self._redis_result(False)
            return None
        except Exception as exc:  # pylint: disable=broad-except
            self.lgr.error(
                "Uhandled exception parsing Event from persistence store: %s", exc
            )
            purge = True

        if purge:
            self.lgr.warning("Purging key %s", key)
            try:
                self.rds.delete(key)
            except:  # pylint: disable=bare-except
                pass
            return None

        return evt

    def get_all(self):
        try:
            for key in self.rds.keys(f"{self.rds_ks}:*"):
                evt = self._get_event(key, True)
                if evt:
                    yield evt
        except redis.ConnectionError:
            self._redis_result(False)
            return
