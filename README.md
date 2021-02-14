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

# Run taky within the folder (ie: if you can't install it)
~/taky $ python3 -m taky
```

`taky`, if no configuration file is specified, will check the current directory
for `taky.conf` and then `/etc/taky/taky.conf`.

With no (or an empty) configuration file, taky will start a tcp server on
`0.0.0.0`. A sample configuration file is located in the project root.
