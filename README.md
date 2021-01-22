# taky

taky - A simple COT server for ATAK

## Features (and anti-Features!)

 * Android clients don't disconnect!
 * No design consideration for XML security!
 * Atrocious CoT routing ensures everyone (may) get your updates!
 * A hacked up XML parser written by someone who barely understands XML!
 * Advanced Pythonic implementation of CoT model, with only 5 hours of combined
   industry experience in implementing CoT technology!
 * Server shuts down in about 1 second with only one Ctrl+C!

## Requirements

 * Python 3.6 or greater
 * lxml
 * dateutil

This application was developed with Python 3.8, and tested with ATAK v4.2.0.4.
It is in an extremely alpha state, and isn't useful for anything at this point.

No, really. Using this is probably a very-bad-idea (TM).

## Installation

Inside the taky folder, run

`python3 setup.py install`

## Usage

```bash
$ taky -h
usage: taky [-h] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-n IP] [-p PORT] [--version]

Start the taky server

optional arguments:
  -h, --help            show this help message and exit
  -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Specify log level
  -n IP, --ip IP
  -p PORT, --port PORT
  --version             show program's version number and exit

# Run taky on :::8087
$ taky

# Run taky on 127.0.0.1:58087 with debugging enabled
$ taky --ip 127.0.0.1 --port 58087 -l DEBUG
```
