import os
import sys
import shutil
import argparse
import configparser
import socket

from taky import __version__
from taky.config import load_config
import taky.rotc as rotc

def arg_parse():
    argp = argparse.ArgumentParser(description="Taky command line utility")
    argp.add_argument('-c', action='store', dest='cfg_file', default=None,
                      help="Path to configuration file")
    argp.add_argument('--version', action='version', version='%%(prog)s version %s' % __version__)

    subp = argp.add_subparsers(dest='command')

    try:
        default_hostname = socket.gethostname()
    except:
        default_hostname = 'taky'
    setup = subp.add_parser('setup', help="Setup the taky server")
    setup.add_argument('--p12_pw', dest='p12_pw', default="atakatak",
                       help="Password for server .p12 [%(default)s]")
    setup.add_argument('--host', dest='hostname', default=default_hostname,
                       help="Server hostname [%(default)s]")
    setup.add_argument('--ip', dest='ip', default="0.0.0.0",
                       help="Bind Address [%(default)s]")
    setup.add_argument('--user', dest='user', default=None,
                       help="User/group for file permissions")
    setup.add_argument('path', nargs='?', help="Optional path for taky install")

    setup = subp.add_parser('build_client', help="Build client file")
    setup.add_argument('name', help="Name for client")

    args = argp.parse_args()

    return (argp, args)

def build_client(config, args):
    pass

def setup(config, args):
    config = load_config('/dev/null')
    if args.path:
        if os.path.exists(args.path):
            print("ERROR: Directory exists, refusing to run setup", file=sys.stderr)
            sys.exit(1)

        args.path = os.path.abspath(args.path)

        dirs = [
            args.path,
            os.path.join(args.path, 'ssl')
        ]
        for dir_name in dirs:
            if not os.path.exists(dir_name):
                os.mkdir(dir_name)
                if args.user:
                    shutil.chown(dir_name, user=args.user, group=args.user)

        os.chdir(args.path)

        ssl_path = 'ssl'
        config_path = 'taky.conf'

        config.set('ssl', 'ca', os.path.join('.', 'ssl', 'ca.crt'))
        config.set('ssl', 'ca_key', os.path.join('.', 'ssl', 'ca.key'))
        config.set('ssl', 'cert', os.path.join('.', 'ssl', 'server.crt'))
        config.set('ssl', 'key', os.path.join('.', 'ssl', 'server.key'))

        config.set('dp_server', 'upload_path', os.path.join('.', 'dp-user'))
    else:
        args.path = '/'

        dirs = [
            os.path.join(args.path, 'etc', 'taky'),
            os.path.join(args.path, 'etc', 'taky', 'ssl'),
            os.path.join(args.path, 'var', 'taky'),
        ]
        
        for dir_name in dirs:
            if not os.path.exists(dir_name):
                os.mkdir(dir_name)
                if args.user:
                    shutil.chown(dir_name, user=args.user, group=args.user)

        ssl_path = os.path.join(args.path, 'etc', 'taky', 'ssl')
        config_path = os.path.join(args.path, 'etc', 'taky', 'taky.conf')

    config.set('taky', 'bind_ip', args.ip)
    config.set('taky', 'hostname', args.hostname)
    config.set('cot_server', 'port', '8089')
    config.set('ssl', 'enabled', 'true')

    with open(config_path, 'w') as fp:
        config.write(fp)

    if args.user:
        shutil.chown(config_path, user=args.user, group=args.user)

    dirs = [
        config.get('dp_server', 'upload_path'),
        os.path.join(config.get('dp_server', 'upload_path'), 'meta'),
    ]

    for dir_name in dirs:
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
            if args.user:
                shutil.chown(dir_name, user=args.user, group=args.user)
    
    if config.getboolean('ssl', 'enabled'):
        if os.path.exists(config.get('ssl', 'ca')):
            print("ERROR: CA exists at %s, refusing to run setup" % config.get('ssl', 'ca'), file=sys.stderr)
            sys.exit(1)

        rotc.make_ca(crt_path=config.get('ssl', 'ca'),
                     key_path=config.get('ssl', 'ca_key'))

        if args.user:
            shutil.chown(config.get('ssl', 'ca'),
                         user=args.user,
                         group=args.user)
            shutil.chown(config.get('ssl', 'ca_key'),
                         user=args.user,
                         group=args.user)

        rotc.make_cert(
            path=ssl_path,
            name='server',
            cert_pw=args.p12_pw, # TODO: OS environ? -p is bad
            ca=(config.get('ssl', 'ca'), config.get('ssl', 'ca_key')),
            dump_pem=True
        )

        if args.user:
            shutil.chown(config.get('ssl', 'cert'),
                         user=args.user,
                         group=args.user)
            shutil.chown(config.get('ssl', 'key'),
                         user=args.user,
                         group=args.user)
            shutil.chown(os.path.join(ssl_path, 'server.p12'),
                         user=args.user,
                         group=args.user)

def main():
    (argp, args) = arg_parse()

    try:
        config = load_config(args.cfg_file)
    except (OSError, configparser.ParsingError) as e:
        print(e)
        sys.exit(1)

    commands = {
        'setup': setup,
        'build_client': build_client
    }

    if not args.command:
        argp.print_usage()
        sys.exit(1)

    commands[args.command](config, args)

if __name__ == '__main__':
    main()
