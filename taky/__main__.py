import os
import sys
import logging
import argparse
import configparser

from taky import __version__, DEFAULT_CFG
from taky.cot import COTServer

def arg_parse():
    argp = argparse.ArgumentParser(description="Start the taky server")
    argp.add_argument('-l', action='store', dest='log_level', default='info',
                      choices=['debug', 'info', 'warning', 'error', 'critical'],
                      help="Log verbosity")
    argp.add_argument('-c', action='store', dest='cfg_file', default=None,
                      help="Path to configuration file")
    argp.add_argument('--version', action='version', version='%%(prog)s version %s' % __version__)

    args = argp.parse_args()

    return (argp, args)

def main():
    (argp, args) = arg_parse()
    config = configparser.ConfigParser(allow_no_value=True)
    config.read_dict(DEFAULT_CFG)

    # TODO: Check for ipv6 support

    logging.basicConfig(level=args.log_level.upper(), stream=sys.stderr)

    if args.cfg_file is None:
        if os.path.exists('taky.conf'):
            args.cfg_file = os.path.abspath('taky.conf')
        elif os.path.exists('/etc/taky/taky.conf'):
            args.cfg_file = '/etc/taky/taky.conf'

    if args.cfg_file:
        logging.info("Loading config from '%s'", args.cfg_file)
        try:
            fp = open(args.cfg_file, 'r')
            config.read_file(fp, source=args.cfg_file)
            fp.close()
        except configparser.ParsingError as e:
            logging.error(e)
            sys.exit(1)
        except OSError as e:
            logging.error(e)
            sys.exit(1)

    try:
        cs = COTServer(config)
    except Exception as e:
        logging.error("Unable to start COTServer: %s", e)
        sys.exit(1)

    cs.start()

    try:
        cs.join()
    except KeyboardInterrupt:
        cs.stop()

    cs.join()

if __name__ == '__main__':
    main()
