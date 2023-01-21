# Feature Comparison

It may be useful to have a side by side comparison of competing TAK servers
to help pick the right tool for your application. We will look at several
metrics.

If you are writing a TAK server, and want to have it listed here, please let
me know!

## Programming Language

| Servers           | taky (0.9)          | Free TAK Server (1.9.9)      |
| ---               | ---                 | ---                          |
| Application       | Light Weight        | Feature Full                 |
| Language          | Python 3.6+         | Python 3.6+                  |
| SLOC              | ~3000               | ~11200                       |
| Unit Testing      | Yes (~35%, passing) | Yes (~38%, failing)          |
| Pylint            | 9.3/10              | 2.2/10                       |
| Development Model | GitHub              | Private (mirrored to GitHub) |
| First Commit      | 2021/01/18          | 2020/02/05                   |
| License           | MIT                 | Eclipse                      |

taky and FTS have both been developed in the same language. FTS has many more
bells and whistles that make it easy for non-tech folks to help administrate.
As such, it's code base nearly 5x larger! However, users can easily browse
data packages and register new clients in a web browser with FTS. In taky,
this must be done on the command line.

taky is much more bare bones, and geared towards hackers and devlopers. An
emphasis was put on code hygeine, and pythonic development practices,
resulting in a pleasing pylint score!

FTS is developed and maintained by several developers, and appears to be
maintained on a private repository. When the developers are ready for a
release, they sync the code to a public git. In contrast, taky is developed on
a public git, and users are able to run the bleeding edge (if they so desire).

Both software packages come with extremely permissive licenses, allowing both
private and commercial use.

## Features and Functionality

| Servers             | taky (0.8.4)                   | Free TAK Server (1.8.1)      |
| ---                 | ---                            | ---                          |
| Interactive Web UI  | No                             | Yes                          |
| DPS Endpoints       | Data Package, Video            | Data Package, Video, ExCheck |
| DPS Security        | Client Certs, Public / Private | N/A                          |
| Dual TCP/SSL Server | Monitor socket                 | Yes                          |
| COT Model           | Naive                          | Strict                       |
| Persistence Backend | Filesystem, Redis              | SQlite                       |
| Requires root?      | No                             | Yes                          |
| Service Management  | Systemd                        | Docker                       |
| Logging             | Server, COT                    | Misc debug                   |

As previously mentioned, FTS is the heavy weight in the room, implementing
the ExCheck utility, and supporting both SSL and TCP clients. But this comes
with a performance cost, requiring more memory.

taky was originally developed with a security focus. As such, SSL was expected
to work out of the box, doing away with a need for TCP. However, many users
also use some homebrew scripts for integration -- and setting up client
certificates is burdensome. taky allows for a TCP monitoring port to be opened
that receives all routed packets.

As an added bonus though, taky's Data Package Server has several security
benefits not yet found in FTS. First, taky's DPS enforces client certificates.
This means that anonymous users can't abuse the server by uploading spam files
with `curl`, removing the need for a VPN. Additionally, if a user sends a file
to another user, it is marked "private" and hidden from being listed in public
search. The DPS also uses the client certs to keep track of who uploaded what.

One downside of FTS is that it currently requires root to run. In general, it
is considered best practice to run services as a non-priviliged user, to
help contain someone who is able to exploit the server. taky was written to
be run as a regular user.

A significant design difference between taky and FTS is how they handles COT
packets. FTS interprets the XML, decides which type of event the packet is most
similar to, and then forces it to match the schema. However, taky does not
attempt to understand what is in the packet, only where it should go.

If you are developing a custom application that does not have a schema in FTS
yet, you may be interested in taky, as taky will simply forward the packets as
received. taky is much less picky about what is inside the `<detail>` block!

To ease deployment, taky has been written to work with systemd as a service
manager. This means when your system reboots, taky will boot and run. Should
the software crash, a detailed log is kept in the journal, and systemd restarts
restarts the COT server in 3 seconds.

Another feature of taky is logging COT messages. If enabled, all valid XML
messages are sent to individual user [log](log) files. This can be extremely handy for
debugging custom applications.

Finally, both taky and FTS have a persistence backend to store and notify users
of historical COT messages. FTS stores the messages in a database, which
persists across reboots. taky stores the objects in memory -- so restarting the
server clears the database. As a tradeoff, redis can optionally be used to
expose the internal persistence state.

## Performance

| Servers                         | taky (0.8) | Free TAK Server (1.8.1) |
| ---                             | ---        | ---                     |
| Memory Usage (COT, Idle)        | ~20 MB     | ~80 MB                  |
| Memory Usage (COT, 10 Clients)  | ???        | ???                     |
| Memory Usage (COT, 100 Clients) | ???        | ???                     |
| Packets / second                | 1000+      | ???                     |

Regrettably, this section has the least amount of information. I would love
some help better expanding this section.

One part that taky excells at is the speed at which it can route packets. The
main loop was written using `select()` calls to ensure that no one client can
block the server. This results in extremely efficient packet routing. On an old
Intel i5-2500k, taky was able to route over 1k pps.Coupled with the naive
packet routing, this also makes the server extremely robust to a wide range of
clients.

## Conclusion

Hopefully, this helps you make a more informed decision on which server
software is right for your application!
