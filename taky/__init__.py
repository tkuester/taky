from pkg_resources import get_distribution, DistributionNotFound

from . import cot

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    __version__ = 'unknown'
