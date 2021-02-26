# taky

taky - A simple COT server for ATAK

## Features (and anti-Features!)

 * Should support multiple ATAK clients simultaneously! You can see them on the
   map!
 * GeoChats are routed to appropriate groups / UIDs, unless broadcast!
 * SSL support with optional client keys!
 * Some design consideration for XML security!
 * Actually somewhat decent CoT routing uses Marti for other items. If
   unspecified, packets are considered broadcast.
 * A hacked up XML parser written by someone who barely understands XML!
 * Advanced Pythonic implementation of CoT model, with only 5 hours of combined
   industry experience in implementing CoT technology!
 * Server shuts down with only one Ctrl+C!
 * Does not require root to run!
 * Thread safety? Where we're going, we don't need threads!
 * Slightly less-than-broken Data Package Server
 * Requires no SQlite / databases! (For now!)
 * Only one version away from having systemd scripts!
 * Tools spit backtraces out instead of giving a nice error message!
 * Stupid fast for no good reason! Routes 1000 packets / second on an old
   Core i5-2500k!

## Requirements

 * Python 3.6 or greater (strongly recommend 3.7+)
 * lxml
 * dateutil
 * flask
 * pyopenssl
 * gunicorn

This application was developed with Python 3.8 on Ubuntu 20.04, and tested with
ATAK v4.2.0.4. It is slowly progressing towards a beta state, and should work
for playing around.

But, really. Using this is for anything important is probably a very-bad-idea (TM).

## Installation

Open a shell, and run:

```
$ git clone https://github.com/tkuester/taky
$ cd taky
taky $ python3 setup.py install
```

Alternatively, you can use pip!

```
$ python3 -m pip install taky
```

## Usage

```
$ taky -h
usage: taky [-h] [-l {debug,info,warning,error,critical}] [-c CFG_FILE] [--version]

Start the taky server

optional arguments:
  -h, --help            show this help message and exit
  -l {debug,info,warning,error,critical}
                        Log verbosity
  -c CFG_FILE           Path to configuration file
  --version             show program's version number and exit

# Run taky on 0.0.0.0:8087
$ taky
```

## More Complicated Setup

While `taky` can run as a standalone CoT server, there are more advanced
features that are available if the server is fully setup. Fortunately, there
is a simple tool to make this easy! You don't even need root!

The only thing needed is your public IP address. The rest is configured
automatically for your convenience.

```
$ takyctl setup -h
usage: takyctl setup [-h] [--p12_pw P12_PW] [--host HOSTNAME] [--bind-ip IP] --public-ip PUBLIC_IP
                     [--user USER] [--no-ssl]
                     [path]

positional arguments:
  path                  Optional path for taky install

optional arguments:
  -h, --help            show this help message and exit
  --p12_pw P12_PW       Password for server .p12 [atakatak]
  --host HOSTNAME       Server hostname [devbox]
  --bind-ip IP          Bind Address [0.0.0.0]
  --public-ip PUBLIC_IP
                        Public IP address
  --user USER           User/group for file permissions
  --no-ssl              Disable SSL for the server

$ takyctl setup --public-ip 192.168.1.100 my_install
$ cd my_install
my_install $ taky

# (in another window, we'll start the data package server)
my_install $ taky_dps
```

Taky will automatically find the config file located in `my_install`, load the
SSL certificates, and start running. You can find user uploaded data packages
in `my_install/dp-user`.

If you are using SSL (highly recommended!), it is simple to generate client
certificates in a zip file for the import manager. You can also run this
through the CLI tool.

```
my_install $ takyctl build_client -h
usage: takyctl build_client [-h] [--p12_pw P12_PW] name

positional arguments:
  name             Name for client

optional arguments:
  -h, --help       show this help message and exit
  --p12_pw P12_PW  Password for server .p12 [atakatak]

my_install $ takyctl build_client JENNY
```

Transferring the .zip file to your device is an exercise left to the reader.
(Although, we hope to have this as a feature eventually!)

This "installation" is local, and can be edited to your hearts content. When
you are done, you can simply delete the folder and start again.
