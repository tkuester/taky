import os
import sys
import shutil
import argparse
import configparser
import socket
import tempfile
import uuid
import zipfile

from lxml import etree

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
    setup.add_argument('--bind-ip', dest='ip', default="0.0.0.0",
                       help="Bind Address [%(default)s]")
    setup.add_argument('--public-ip', dest='public_ip', required=True,
                       help="Public IP address")
    setup.add_argument('--user', dest='user', default=None,
                       help="User/group for file permissions")
    setup.add_argument('--no-ssl', dest='use_ssl', action='store_false',
                       help="Disable SSL for the server")
    setup.add_argument('path', nargs='?', help="Optional path for taky install")

    bld_cl = subp.add_parser('build_client', help="Build client file")
    bld_cl.add_argument('name', help="Name for client")
    bld_cl.add_argument('--p12_pw', dest='p12_pw', default="atakatak",
                       help="Password for server .p12 [%(default)s]")

    args = argp.parse_args()

    return (argp, args)

def build_client(config, args):
    tdir = tempfile.mkdtemp(prefix='taky-cert-')

    mdir = os.path.join(tdir, 'MANIFEST')
    os.mkdir(mdir)
    cdir = os.path.join(tdir, 'certs')
    os.mkdir(cdir)

    server_p12 = config.get('ssl', 'server_p12')
    shutil.copy(server_p12, cdir)

    rotc.make_cert(
        path=cdir,
        f_name=args.name,
        hostname=args.name,
        cert_pw=args.p12_pw, # TODO: OS environ? -p is bad
        ca=(config.get('ssl', 'ca'), config.get('ssl', 'ca_key')),
        dump_pem=False
    )

    hostname = config.get('taky', 'hostname')
    public_ip = config.get('taky', 'public_ip')
    port = config.getint('cot_server', 'port')
    method = 'ssl' if config.getboolean('ssl', 'enabled') else 'tcp'

    prefs = {
        'cot_streams': {
            'count': 1,
            'description0': hostname,
            'enabled0': False,
            'connectString0': f'{public_ip}:{port}:{method}'
        },
        'com.atakmap.app_preferences': {
            'displayServerConnectionWidget': True,
            'caLocation': f'/storage/emulated/0/atak/cert/{os.path.basename(server_p12)}',
            'caPassword': config.get('ssl', 'server_p12_pw'),
            'clientPassword': args.p12_pw,
            'certificateLocation': f'/storage/emulated/0/atak/cert/{args.name}.p12'
        }
    }

    prefs_xml = etree.Element('preferences')
    for (name, pref) in prefs.items():
        pref_xml = etree.Element('preference', attrib={
            'version': '1',
            'name': name,
        })

        for (key, val) in pref.items():
            if isinstance(val, bool):
                v_type = 'Boolean'
            elif isinstance(val, int):
                v_type = 'Integer'
            elif isinstance(val, str):
                v_type = 'String'

            entry = etree.Element('entry', attrib={
                'key': key,
                'class': f'class java.lang.{v_type}'
            })

            if isinstance(val, bool):
                entry.text = str(val).lower()
            else:
                entry.text = str(val)

            pref_xml.append(entry)

        prefs_xml.append(pref_xml)

    with open(os.path.join(cdir, 'fts.pref'), 'wb') as fp:
        fp.write(etree.tostring(prefs_xml,
                                pretty_print=True,
                                xml_declaration=True,
                                standalone=True))

    cfg_params = {
        'uid': str(uuid.uuid4()),
        'name': f'{hostname}_DP',
        'onReceiveDelete': 'true'
    }
    mpm = etree.Element('MissionPackageManifest', attrib={'version': '2'})
    cfg_xml = etree.Element('Configuration')

    for (name, value) in cfg_params.items():
        cfg_xml.append(
            etree.Element(
                'Parameter', attrib={
                    'name': name,
                    'value': value,
                }
            )
        )
    mpm.append(cfg_xml)

    cts = etree.Element('Contents')
    for name in ['fts.pref', os.path.basename(server_p12), f'{args.name}.p12']:
        cts.append(
            etree.Element('Content', attrib={
                'ignore': 'false',
                'zipEntry': os.path.join('certs', name)
            })
        )
    mpm.append(cts)

    with open(os.path.join(mdir, 'manifest.xml'), 'wb') as fp:
        fp.write(etree.tostring(mpm, pretty_print=True))

    cwd = os.getcwd()
    os.chdir(tdir)

    zip_path = os.path.join(cwd, f"{args.name}.zip")
    fp = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(tdir):
        root = os.path.relpath(root, tdir)
        for file in files:
            fp.write(os.path.join(root, file))

    fp.close()
    
    shutil.rmtree(tdir)

def setup_taky(config, args):
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
        config.set('ssl', 'server_p12', os.path.join('.', 'ssl', 'server.p12'))
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
    config.set('taky', 'public_ip', args.public_ip)
    config.set('taky', 'hostname', args.hostname)
    config.set('cot_server', 'port', '8089' if args.use_ssl else '8087')
    config.set('ssl', 'enabled', 'true' if args.use_ssl else 'false')
    config.set('ssl', 'server_p12_pw', args.p12_pw)

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
            f_name='server',
            hostname=args.hostname,
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
            shutil.chown(config.get('ssl', 'server_p12'),
                         user=args.user,
                         group=args.user)

def main():
    (argp, args) = arg_parse()

    try:
        config = load_config(args.cfg_file)
    except (OSError, configparser.ParsingError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    commands = {
        'setup': setup_taky,
        'build_client': build_client
    }

    if not args.command:
        argp.print_usage()
        sys.exit(1)

    commands[args.command](config, args)

if __name__ == '__main__':
    main()
