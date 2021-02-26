#pylint: disable=missing-module-docstring
import sys
import signal
import logging
import argparse
import configparser
import pdb

from taky import __version__
from taky.cot import COTServer
from taky.config import load_config

def handle_pdb(sig, frame): # pylint: disable=unused-argument
    ''' Signal handler '''
    pdb.Pdb().set_trace(frame)

def arg_parse():
    ''' Handle arguments '''
    argp = argparse.ArgumentParser(description="Start the taky server")
    argp.add_argument('-l', action='store', dest='log_level', default='info',
                      choices=['debug', 'info', 'warning', 'error', 'critical'],
                      help="Log verbosity")
    argp.add_argument('-c', action='store', dest='cfg_file', default=None,
                      help="Path to configuration file")
    argp.add_argument('-d', action='store_true', dest='debug', default=False,
                      help="Allow attaching to PDB")
    argp.add_argument('--version', action='version', version='%%(prog)s version %s' % __version__)

    args = argp.parse_args()

    return (argp, args)

def main():
    ''' taky COT server '''
    ret = 0

    (argp, args) = arg_parse()
    logging.basicConfig(level=args.log_level.upper(), stream=sys.stderr)
    logging.info("taky v%s", __version__)

    try:
        config = load_config(args.cfg_file)
    except (OSError, configparser.ParsingError) as exc:
        argp.error(exc)
        sys.exit(1)

    # TODO: Check for ipv6 support

    try:
        cot_srv = COTServer(config)
    except Exception as exc: # pylint: disable=broad-except
        logging.error("Unable to start COTServer: %s", exc)
        sys.exit(1)

    if args.debug:
        signal.signal(signal.SIGUSR1, handle_pdb)

    try:
        while True:
            cot_srv.loop()
    except KeyboardInterrupt:
        pass
    except Exception as exc: # pylint: disable=broad-except
        logging.critical("Unhandled exception", exc_info=exc)
        ret = 1

    try:
        cot_srv.shutdown()
    except Exception as exc: # pylint: disable=broad-except
        logging.critical("Exception during shutdown", exc_info=exc)

    sys.exit(ret)

if __name__ == '__main__':
    main()
