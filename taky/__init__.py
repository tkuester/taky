from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    __version__ = 'unknown'

DEFAULT_CFG = {
    'taky': {
        'hostname': None,
    },

    'cot_server': {
        'bind_ip': None, # Defaults to all
        'port': None,    # Defaults to 8087 (or 8089 if SSL)
    },

    'ssl': {
        'enabled': False,
        'verify_client': False,
        'cert': '/etc/taky/ssl/server.pem',
        'key': None,
        'ca': None,
        'key_pw': None,
    }
}
