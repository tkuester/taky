# Security Guide

So... ATAK / COT isn't the most secure ecosystem. There are some security
measures in place, for sure! But... it's a tad like a screen door on a
submarine.

This guide contains some observations I've made about ATAK / COT security, what
can be done to secure your server, and some of the security features written
into `taky`.

## First Things First

If you want your deployment to be "secure"

1. Run your server on a VPN connection
2. Tightly control access to the VPN
3. Client certificates? Why not!

`taky` was written with SSL as a "first class feature" to help secure things,
and prevent certificate reusage. That being said? Those aren't enough to secure
your setup.

## COT Server Security

One large feature is that `taky` does not need to run as root. Should someone
discover an exploit with `taky`, this will help to limit how far they can get
into your system.

The COT Server requires client certificates. This means that if your COT server
was configured with SSL and hosted on a public network, no one can connect
unless they have a client certificate.

However, malicious and/or badly behaving clients may still be able to take down
the server, or disrupt service. While the XML parsers are run with
`resolve_entities=False` to prohibit [external entity
attacks](https://en.wikipedia.org/wiki/XML_external_entity_attack), XML is a
large attack surface.

Cursor on Target (COT) is a very "tribal" language, and most of the
implementation I gathered was from the [ATAK source
code](https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV). For this
reason, `taky` only understands as much of a COT event as is necessary for
routing. However, malformed documents may linger in Redis persistence,
poisoning all new clients that connect. This is an interesting attack vector
which I have not considered much.

Another concern is that clients may spoof their UID or Callsign. While the
server can investigate the client certificate to enforce a username, that
feature has not been implemented yet. Additionally, given how little `taky`
understands about COT, there may be some fields that slip by the username
enforcement, even if such a feature is implemented.

## Data Package Server Security

Regrettably, the data package server (DPS) is in its infancy. While I have
tried to enforce client certificates for the DPS, ATAK seems to not like this.
I've submitted an issue to ATAK, this may be resolved in the future.

As such, while all communication with the DPS is encrypted with SSL, anyone
that can open a socket to the DPS could post large files, or download files.

While ATAK seems to indicate a "public" and "private" setting for files, I
haven't had a chance to implement that feature yet. Consider all data uploaded
as accessible to anyone.

Also, there is no "virus scan" for the data packages. I have heard one story of
a malicious datapackage bricking the Android clients with a malformed image.
ATAK does not prompt the user to see if they want to accept the download, it
just downloads the datapackage in the background.

A simple solution is to not run the DPS, and disable "File Sharing" in ATAK
under "Settings / Tool Preferences / Data Package Control Preferences". You may
need to disable "Mesh Network Mode" under "Settings / Network Preferences /
Network Connection Preferences / Enable Mesh Network Mode" as well. COT will
work without it, you just have fewer features.

## Certificate / Client Security

This is a bit of an oddball for me. ATAK uses `.p12` files, which encrypt the
client certificate and key with a password. Funnily enough, the server
certificate, which is public information anyways, is also encrypted with a
`.p12` file. However, both passwords are included plaintext in the `.zip` file
that you import.

While you can distribute `.p12` files out of band and configure the unit
manually, this is extremely tedious.

`taky` allows you to specify a password, but it doesn't seem to give much more
security. If you don't specify a password, "atakatak" is used. It wouldn't be
too difficult to implement random passwords for each client certificate, but
given the plaintext password shipped with the keys, it's a bit like leaving the
key under the door mat.

Android isn't particularly known for it's system security, so consider a
malicious user stealing a user's certificate, and then attacking the COT
server.

We could implement a revocation list to lock them out of further access, but
they will still have access to the server until then. Perhaps this is a feature for
later.

## The Conclusion of the Matter?

Ooog. Use a VPN and control access tightly. Regenerate your CA and certificates
often. If you use the DPS, consider wiping the datapackage directory clean
between operations. The same if you use redis as a persistence store.
