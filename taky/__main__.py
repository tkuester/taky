import sys
import logging
import argparse
from ipaddress import ip_address

from taky import __version__
from taky.cot import COTServer

def main():
    argp = argparse.ArgumentParser(description="Start the taky server")
    argp.add_argument('-l', action='store', dest='log_level', default='info',
                      choices=['debug', 'info', 'warning', 'error', 'critical'],
                      help="Specify log level")
    argp.add_argument('-n', '--ip', action='store', dest='ip', type=ip_address, default='::',
                      help="IP Address to listen on (v4 or v6)")
    argp.add_argument('-p', '--port', action='store', dest='port', type=int, default=None,
                      help="Port to listen on")
    argp.add_argument('--ssl-cert', action='store', dest='ssl_cert', type=str, default=None,
                      help="Path to the server certificate")
    argp.add_argument('--ssl-key', action='store', dest='ssl_key', type=str, default=None,
                      help="Path to the server certificate key")
    argp.add_argument('--cacert', action='store', dest='ca_cert', type=str, default=None,
                      help="Path to the CA for verifying client certs")
    argp.add_argument('--no-verify-client', action='store_false', dest='verify_client', default=True,
                      help="Do not verify client certificates")
    argp.add_argument('--version', action='version', version='%%(prog)s version %s' % __version__)

    args = argp.parse_args()

    if args.ssl_cert or args.ssl_key:
        if (args.ssl_cert is None or args.ssl_key is None):
            argp.error('SSL requires both --ssl-cert and --ssl-key')
        if args.port is None:
            args.port = 8089
    else:
        if args.port is None:
            args.port = 8087

    logging.basicConfig(level=args.log_level.upper(), stream=sys.stdout)

    try:
        cs = COTServer(ip=args.ip, port=args.port,
                       ca_cert=args.ca_cert,
                       ssl_cert=args.ssl_cert,
                       ssl_key=args.ssl_key,
                       verify_client=args.verify_client)
    except Exception as e:
        logging.error("Unable to start COTServer")
        sys.exit(1)

    cs.start()

    try:
        cs.join()
    except KeyboardInterrupt:
        cs.stop()

    cs.join()

if __name__ == '__main__':
    main()
