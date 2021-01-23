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
 * Thread safety? Why would you need thread safety?

## Requirements

 * Python 3.7 or greater
 * lxml
 * dateutil

This application was developed with Python 3.8, and tested with ATAK v4.2.0.4.
It is slowly progressing towards a beta state, and should work for playing
around.

But, really. Using this is for anything important is probably a very-bad-idea (TM).

## Installation

Inside the taky folder, run

```bash
$ git clone https://github.com/tkuester/taky
$ cd taky
$ python3 setup.py install
```

Alternatively, you can use pip!

```bash
$ python3 -m pip install taky
```

## Usage

```bash
$ taky -h
usage: taky [-h] [-l {debug,info,warning,error,critical}] [-n IP] [-p PORT] [--ssl-cert SSL_CERT]
            [--ssl-key SSL_KEY] [--cacert CA_CERT] [--no-verify-client] [--version]

Start the taky server

optional arguments:
  -h, --help            show this help message and exit
  -l {debug,info,warning,error,critical}
                        Specify log level
  -n IP, --ip IP        IP Address to listen on (v4 or v6)
  -p PORT, --port PORT  Port to listen on
  --ssl-cert SSL_CERT   Path to the server certificate
  --ssl-key SSL_KEY     Path to the server certificate key
  --cacert CA_CERT      Path to the CA for verifying client certs
  --no-verify-client    Do not verify client certificates
  --version             show program's version number and exit

# Run taky on :::8087
$ taky

# Run taky on 127.0.0.1:58087 with debugging enabled
$ taky --ip 127.0.0.1 --port 58087 -l debug

# Run taky within the folder (ie: if you can't install it)
~/taky $ python3 -m taky

# Run taky with SSL and client certificates on 8089 (default)
$ taky --ssl-cert ./server.crt --ssl-key ./server.key --cacert ./ca.crt
```
