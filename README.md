# taky

taky - A simple COT server for ATAK

![python](https://img.shields.io/badge/python-3.6%7C3.7%7C3.8-black)
![pylint](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/tkuester/b8b273c056ed05901cfc671070e875ed/raw/taky-pylint-shieldsio.json)
![coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/tkuester/c7e215b2645a1b63b07f12eff8f13fdb/raw/taky-coverage-shieldsio.json)
![PyPI](https://img.shields.io/pypi/v/taky)

## Features (and anti-Features!)

 * Supports multiple ATAK clients simultaneously! You can see them on the map!
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
 * Slightly less-than-broken Data Package Server!
 * Handy CLI utilities for generating systemd service files and client keys!
 * Stupid fast for no good reason! Routes 1000 packets / second on an old Core
   i5-2500k!
 * Optional redis backed object persistence storage!
 * Still no requirement for SQlite / database!

## Requirements

 * Python 3.6 or greater (strongly recommend 3.7+)
 * lxml
 * dateutil
 * flask
 * pyopenssl
 * gunicorn
 * redis

This application was developed with Python 3.8 on Ubuntu 20.04, and tested with
ATAK v4.2.0.4 and WinTAK. It is now in a beta state, and should work relatively
well.

Most of the testing so far has been with "simulated" clients, instead of real
users. I still wouldn't recommend using this for an important exercise where
lives are at stake, but if you want to test it out, please let me know how it
goes!

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

Right out of the box, with no configuration, you can build a simple COT server
for you and your friends to play with over TCP!

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
INFO:root:taky v0.7
INFO:COTServer:Listening for tcp on :8087
```

## Deploying Taky

Taky has been written with ease of administration in mind. It should be easy to
install, upgrade, build (and run) multiple instances, manage with systemd
scripts, and adhere to standard Linux service organization and package
management. Additionally, there is no tie in to operating systems. This should
be just as easy to setup on Fedora as it is on Ubuntu -- though the
instructions have been written for Ubuntu.

See the deployment guide in the `/doc` folder for instructions on deploying a
server of your own!

## Development Status

As far as the "Unicorn Test Readiness Level" goes, `taky` is not a high
heritage space unicorn. We are somewhere between TRL 5 and 6. The horse is
outside, and we're tentatively calling it a unicorn.

The COT server is the most mature part of the codebase. While some of the more
esoteric configurations have not been tested, the standard SSL setup seems to
be rather solid, and performs well with heavy loads.

The Data Package server (DPS) is starting to mature, but has not been as
extensively tested. Simple client-to-client and client-to-server transfers seem
to work well, although some features like Video and posting tracks have not
been implemented yet.

Feel free to checkout the
[milestones](https://github.com/tkuester/taky/milestones) page to see what is
planned for the next version of taky! Pull requests and issues are welcome!
