import sys
import logging
import argparse
from ipaddress import ip_address

from taky import __version__
from taky.cot import COTServer

def main():
    argp = argparse.ArgumentParser(description="Start the taky server")
    argp.add_argument('-l', action='store', dest='log_level', default='INFO',
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      help="Specify log level")
    argp.add_argument('-n', '--ip', action='store', dest='ip', type=ip_address, default='::')
    argp.add_argument('-p', '--port', action='store', dest='port', type=int, default=8087)
    argp.add_argument('--ssl-cert', action='store', dest='ssl_cert', type=str, default=None)
    argp.add_argument('--ssl-key', action='store', dest='ssl_key', type=str, default=None)
    argp.add_argument('--version', action='version', version='%%(prog)s version %s' % __version__)

    args = argp.parse_args()

    logging.basicConfig(level=args.log_level, stream=sys.stdout)

    cs = COTServer(ip=args.ip, port=args.port,
                   ssl_cert=args.ssl_cert, ssl_key=args.ssl_key)
    cs.start()

    try:
        cs.join()
    except KeyboardInterrupt:
        cs.stop()

    cs.join()

if __name__ == '__main__':
    main()
