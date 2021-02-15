import os
import logging
import configparser

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
        'client_cert_required': False,
        'ca': None,
        'cert': '/etc/taky/ssl/server.pem',
        'key': None,
        'key_pw': None,
    }
}

def load_config(path=None):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read_dict(DEFAULT_CFG)

    if path is None:
        if os.path.exists('taky.conf'):
            path = os.path.abspath('taky.conf')
        elif os.path.exists('/etc/taky/taky.conf'):
            path = '/etc/taky/taky.conf'

        lgr = logging.getLogger('load_config')
        lgr.info("Loading config file from %s", path)

    if path:
        fp = open(path, 'r')
        config.read_file(fp, source=path)
        fp.close()

    return config
