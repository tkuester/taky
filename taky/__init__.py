try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    # Python < 3.8
    from importlib_metadata import version, PackageNotFoundError

from . import cot

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    __version__ = "unknown"
