import os
import logging
import configparser

DEFAULT_CFG = {
    'taky': {
        'hostname': 'taky.local', # Servers FQDN
        'node_id': 'TAKY',        # TAK Server nodeId
        'bind_ip': None,          # Defaults to all (0.0.0.0)
        'public_ip': None,        # Server's public IP address
    },

    'cot_server': {
        'port': None,    # Defaults to 8087 (or 8089 if SSL)
        'log_cot': None  # Path to log COT files to
    },

    'dp_server': {
        'upload_path': '/var/taky/dp-user',
    },

    'ssl': {
        'enabled': False,
        'client_cert_required': True,
        'ca': '/etc/taky/ssl/ca.crt',
        'ca_key': '/etc/taky/ssl/ca.key',
        'server_p12': '/etc/taky/ssl/server.p12',
        'server_p12_pw': 'atakatak',
        'cert': '/etc/taky/ssl/server.crt',
        'key': '/etc/taky/ssl/server.key',
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

    if path:
        lgr = logging.getLogger('load_config')
        lgr.info("Loading config file from %s", path)
        with open(path, 'r') as fp:
            config.read_file(fp, source=path)

    port = config.get('cot_server', 'port')
    if port in [None, '']:
        port = 8089 if config.getboolean('ssl', 'enabled') else 8087
    else:
        try:
            port = int(port)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid port: {port}") from e

        if port <= 0 or port >= 65535:
            raise ValueError(f"Invalid port: {port}") from e
    config.set('cot_server', 'port', str(port))

    return config
