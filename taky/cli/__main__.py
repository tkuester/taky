import sys
import argparse
import configparser

from taky import __version__
from taky.config import load_config
from taky import cli

def arg_parse():
    argp = argparse.ArgumentParser(description="Taky command line utility")
    argp.add_argument('-c', action='store', dest='cfg_file', default=None,
                      help="Path to configuration file")
    argp.add_argument('--version', action='version', version='%%(prog)s version %s' % __version__)

    subp = argp.add_subparsers(dest='command')

    cli.setup_taky_reg(subp)
    cli.build_client_reg(subp)

    args = argp.parse_args()

    return (argp, args)

def main():
    (argp, args) = arg_parse()

    try:
        config = load_config(args.cfg_file)
    except (OSError, configparser.ParsingError) as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    commands = {
        'setup': cli.setup_taky,
        'build_client': cli.build_client
    }

    if not args.command:
        argp.print_usage()
        sys.exit(1)

    commands[args.command](config, args)

if __name__ == '__main__':
    main()
