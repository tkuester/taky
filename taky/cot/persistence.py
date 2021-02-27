from datetime import datetime as dt
import logging

from lxml import etree
import redis

from .models.event import Event

KEPT_EVENTS = [
    'a-',
    'b-m-p',
    'b-r-f-h-c',
    'u-d-c',
    'u-d-r',
    'u-d-f',
]

class Persistence:
    def __init__(self, config=None):
        self.events = {}
        self.rds = None
        self.rds_ks = None
        self.rds_ok = True
        self.lgr = logging.getLogger(self.__class__.__name__)

        use_redis = config.get('taky', 'redis')
        if config.get('taky', 'redis'):
            try:
                if config.getboolean('taky', 'redis'):
                    self.lgr.info("Connecting to default redis")
                    self.rds = redis.StrictRedis()
            except ValueError:
                pass

            if not self.rds:
                self.lgr.info("Connecting to %s", config.get('taky', 'redis'))
                self.rds = redis.StrictRedis.from_url(config.get('taky', 'redis'))

            self.rds_ks = f'taky:{config.get("taky", "hostname")}'

            try:
                self.rds.ping()
                self._redis_result(True)
            except redis.ConnectionError:
                self._redis_result(False)

    def update(self, event):
        # Log all Atoms
        # a-f-G-U-C / User Update (f-G-U-C) points
        # a-u-G / Marker

        # Log some bits
        # b-m-p-w-GOTO # Go to this thing
        # b-m-p-s-p-i # Digital Pointer (cuepoint)
        # b-m-p (Generic point prefix, log all)
        # b-f-t-r / Picture / File download request (Don't log)
        # b-r-f-h-c / EVAC
        # b-t-f / GeoChat
        # b-a-o-tbl / Emergency
        # b-a-o-can / Emergency canceled

        # ???
        # u-d-c-c / Rectangle + Circle
        # u-d-f-m / Drawing (polygon)
        # u-d-f-m / Drawing (line)

        # Ignore tasking - Seems like UDP
        # t-x-c-t / Ping

        # c - Capability
        # r - Reply
        for etype in KEPT_EVENTS:
            if event.etype.startswith(etype):
                self.track(event)
                return

    def _redis_result(self, result):
        if self.rds_ok and not result:
            self.lgr.warning("Lost connection to redis")
        elif not self.rds_ok and result:
            self.lgr.warning("Connection to redis restored")

        self.rds_ok = result

    def track(self, event):
        ttl = round((event.stale - dt.utcnow()).total_seconds())
        if ttl <= 0:
            return

        if self.rds:
            try:
                key = f'{self.rds_ks}:{event.uid}'
                if self.rds.exists(key):
                    self.lgr.info("Updating tracking for: %s (ttl: %d)", key, ttl)
                else:
                    self.lgr.info("New item to track: %s (ttl: %d)", key, ttl)

                self.rds.set(key, etree.tostring(event.as_element))
                self.rds.expire(key, ttl)
                self._redis_result(True)
            except redis.ConnectionError:
                self._redis_result(False)
        else:
            if event.uid in self.events:
                self.lgr.info("Updating tracking for: %s", event)
            else:
                self.lgr.info("New item to track: %s", event)
            self.events[event.uid] = event
            self.prune()

    def get_all(self):
        ret = []
        if self.rds:
            try:
                for key in self.rds.keys(f'{self.rds_ks}:*'):
                    try:
                        xml = self.rds.get(key)
                        self._redis_result(True)
                        elm = etree.fromstring(xml)
                        evt = Event.from_elm(elm)
                    except etree.XMLSyntaxError as e:
                        self.lgr.warning("Unable to parse XML from persistence store: %s", e)
                        self.lgr.warning("Purging key %s", key)
                        self.rds.delete(key)
                        continue
                    except redis.ResponseError as e:
                        self.lgr.warning("Unable to get Event from persistence store: %s", e)
                        self.lgr.warning("Purging key %s", key)
                        self.rds.delete(key)
                    except StandardError:
                        self.lgr.warning("Unable to parse Event from persistence store: %s", e)
                        self.lgr.warning("Purging key %s", key)
                        self.rds.delete(key)
                        continue

                    ret.append(evt)
            except redis.ConnectionError:
                self._redis_result(False)
        else:
            self.prune()
            ret = self.events.values()

        return ret

    def prune(self):
        uids = []
        now = dt.utcnow()

        for item in self.events.values():
            if now > item.stale:
                self.lgr.info("Pruning %s, stale is %s", item, item.stale)
                uids.append(item.uid)

        for uid in uids:
            self.events.pop(uid)
