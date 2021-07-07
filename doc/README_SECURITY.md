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

Cursor on Target (COT) is a very "tribal" language, and most of the
implementation I gathered was from the [ATAK source
code](https://github.com/deptofdefense/AndroidTacticalAssaultKit-CIV). For this
reason, `taky` only understands as much of a COT event as is necessary for
routing. However, malformed documents may linger in Redis persistence,
poisoning all new clients that connect. This is an interesting attack vector
which I have not considered much.

A recent discussion in Discord showed that some TAK Servers were not relaying
custom extensions in the `<detail>` element. The servers were interpreting the
COT detail, discarding what was not understood, and only relaying what passed
through a filter. While this does result in a "safer" COT experience, it
decreases interoperability with closed source extensions.

Another concern is that clients may spoof their UID or Callsign. While the
server can investigate the client certificate to enforce a username, that
feature has not been implemented yet. Additionally, given how little `taky`
understands about COT, there may be some fields that slip by the username
enforcement, even if such a feature is implemented.

Given the tribal nature of COT and the desire for custom user extensions -- it
is an impossible task to authenticate and sanitize the COT messages. I think
the solution is to delegate this aspect of security to the user via access
control. `taky` should act as a "dumb" router, and only have a naive
understanding of the message content. The end user is responsible for ensuring
the clients

### But what about XML Security? And running as root?

If `taky` isn't going to try and enforce callsigns, UID's, and a strict data
model, why make such a big stink about not running as root, and XML security?
This is an important question to ask, and helps explain `taky`'s security
model.

`taky`'s XML parsers are run with `resolve_entities=False` to prohibit
[external entity
attacks](https://en.wikipedia.org/wiki/XML_external_entity_attack), XML is a
large attack surface, and this prevents denial of service attacks with
"XML Bombs".

However, protecting the end users against entity attacks is a beneficial side
effect. The primary security concern is not to protect the TAK network, but to
protect the server itself. Entity attacks can be used to read files on the
server, which may include sensitive information (like `/etc/shadow`). This
could lead to a compromise of the server.

From the last section, `taky` assumes that TAK network security depends on
tight access control to certificates, and well behaved clients -- due to some
design decisions made in COT. While there's no way to protect the COT network
from poorly designed protocol, the server that `taky` runs on should not have
to suffer those consequences!

## Data Package Server Security

The data package server (DPS) is in its infancy. However, as of 0.8, the DPS
only allows clients which present the certificate from the client .zip file.
This means that you can run the DPS on the public internet, and not have to
worry about anonymous users uploading malicious data packages.

Additionally, the DPS now supports "public" and "private" datapackages. This
means if you send a data package between users, it will not show up in the
search index. However, anyone with the link to the datapackage and a client
certificate will still be able to access it. The "privacy" feature is more for
convenience, than for security.

Also, there is no "virus scan" for the data packages. I have heard one story of
a malicious datapackage bricking the Android clients with a malformed image.
ATAK does not prompt the user to see if they want to accept the download, it
just downloads the datapackage in the background. In the future, we may
implement a packet filter that drops these packets.

Until then, a simple solution is to not run the DPS, and disable "File Sharing"
in ATAK under "Settings / Tool Preferences / Data Package Control Preferences".
You may need to disable "Mesh Network Mode" under "Settings / Network
Preferences / Network Connection Preferences / Enable Mesh Network Mode" as
well. COT will work without it, you just have fewer features.

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

Use SSL, and control access to who gets certificates. Until CRL's are
implemented, you'll need to regenerate your CA and certificates in the event
you want to revoke someone's keys.

If you use the DPS, consider wiping the datapackage directory clean between
operations. The same if you use redis as a persistence store.
