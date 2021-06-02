import logging
import configparser

from taky.config import app_config as config
from taky.cot.router_plugins.baseplugin import RoutingPlugin


class GPSNoise(RoutingPlugin):
    name = "gps_noise"

    def config(self):
        self.lgr = logging.getLogger(self.__class__.__name__)
        self.precision = 4
        if not config.has_section("gps_noise"):
            return

        try:
            self.precision = config.getint("gps_noise", "precision")
        except configparser.Error:
            pass

        self.lgr.debug("Setting precision to: %s", self.precision)

    def process(self, src, dst, event):
        self.lgr.info("Truncating")
        event.point.lat = round(event.point.lat, self.precision)
        event.point.lon = round(event.point.lat, self.precision)

        return False


plugin = GPSNoise
