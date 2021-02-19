import sys
import logging
import argparse
import configparser

from taky import __version__
from taky.cot import COTServer
from taky.config import load_config

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
    logging.basicConfig(level=args.log_level.upper(), stream=sys.stderr)

    try:
        config = load_config(args.cfg_file)
    except (OSError, configparser.ParsingError) as e:
        logging.error(e)
        sys.exit(1)

    # TODO: Check for ipv6 support

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
