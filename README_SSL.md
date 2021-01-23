# Configuring taky for SSL support

There are a few ways of generating certificates for the server and various
clients. Since `openssl` is tricky to use, this guide will focus on
[easyrsa](https://github.com/OpenVPN/easy-rsa).

Whenever I get around to writing the certificate enrollment and data package
server, this process should get a ton easier. But until then!

Note: I'm not really an expert in the intracacies of SSL. If you are, and see
something that could be improved, please drop me a note!

## Step 1. Generating the Certificate Authority

Self-signed certificates are no good. Let's make a certificate authority so
that our certificates are somewhat legitimate!

I'll be making my CA with a password. This prevents someone from generating
their own certificates with your CA if they come across it. (If this feels
a bit overkill for you, run `easyrsa build-ca nopass`!)

```bash
$ git clone --depth 1 https://github.com/OpenVPN/easy-rsa
Cloning into 'easy-rsa'...

$ cd easy-rsa
$ ./easyrsa3/easyrsa init-pki

init-pki complete; you may now create a CA or requests.
Your newly created PKI dir is: ...

$ ./easyrsa3/easyrsa build-ca
Using SSL: openssl OpenSSL 1.1.1f  31 Mar 2020

Enter New CA Key Passphrase: 
Re-Enter New CA Key Passphrase: 
Generating RSA private key, 2048 bit long modulus (2 primes)
.......................................................+++++
...........................+++++
e is 65537 (0x010001)
[ ... output truncated ]
```

You can find your CA certificate in `pki/ca.crt`.

## Step 2. Generating the Server Certificate

We now have a CA, which is considered the "authority" on if a certificate is
valid. Let's now make the certificate which `taky` will use to encrypt
communication with clients.

I like using `nopass` here, because I don't want to have to enter a passphrase
to startup the server -- only for generating certificates.

```bash
$ ./easyrsa3/easyrsa build-server-full taky-server nopass
Using SSL: openssl OpenSSL 1.1.1f  31 Mar 2020
Generating a RSA private key
.........+++++
....................................+++++
writing new private key to '...'
[ ... output truncated ]
```

Now we have the minimal items required to run `taky` in SSL.

1. taky-server.crt - The public part of the server certificate
2. taky-server.key - The private key of the server certificate
3. ca.crt - The public part of the Certificate Authority

To start up taky, we can run

```bash
$ taky --ssl-cert ./pki/issued/taky-server.crt \
     --ssl-key ./pki/private/taky-server.key \
     --cacert ./pki/ca.crt
INFO:COTServer:Loading CA certificate from ./pki/ca.crt
INFO:COTServer:Listening for SSL on :::8089
```

## Step 3. Generating the Server .p12 TrustStore for ATAK

Most SSL applications use a public certificate authority, like Let's Encrypt.
However, we're "flying under the radar", and made our own. We need to tell
ATAK what our CA and server certificate are, so it can verify the connection.

This is where my knowledge starts to get a little thin. PCKS12 (or .p12 files)
bundle together certificates and keys, and secures them with a passphrase so
they can be transmitted over the internet.

Given that we're only sharing the public side of the keys, I don't
particularly understand why we need a passphrase... but oh well!

ATAK wants two .p12 files -- one for the server certificate, and one for the
client. Let's build the Server bundle:

```bash
$ ./easyrsa3/easyrsa export-p12 taky-server nokey
Using SSL: openssl OpenSSL 1.1.1f  31 Mar 2020
Enter Export Password:
Verifying - Enter Export Password:

Successful export of p12 file. Your exported file is at the following
location: .../pki/private/taky-server.p12
```

Now we can copy that file over to your Android device. I put mine in
`/sdcard/atak/cert/taky-server.p12`. To configure ATAK to use this certificate,
go into "Settings > Show All Preferences > Network Preferences > Network
Connection Preferences > Default SSL/TLS TrustStore Location" and click the
file. Don't forget to set the TrustStore Password here, too!

Alternatively, you can specify this on a per connection basis, by going to
"Settings > TAK Servers", clicking the pencil icon by your server, checking
"Advanced Options", and unchecking "Use default SSL/TLS Certificates". Then
select the `taky-server.p12` file, and put the password in the nearby entry.

At this point, theoretically, you can run `taky` with `--no-verify-client`, and
everything should be fine. SSL connections don't require client certificates,
but ATAK might not work without them. But to complete the setup...

## Step 4. Generating the Client Certificate Store for ATAK

Alright, home stretch.

Unlike the server TrustStore, which doesn't require the private key, the
Client Certificate Store does need the private key. (But we'll generate it
without a password, all the same.)

```bash
$ ./easyrsa3/easyrsa build-client-full android-client nopass
Using SSL: openssl OpenSSL 1.1.1f  31 Mar 2020
Generating a RSA private key
...+++++
....................................+++++
writing new private key to '...'
[ ... output truncated ]

$ ./easyrsa3/easyrsa export-p12 android-client
Using SSL: openssl OpenSSL 1.1.1f  31 Mar 2020
Enter Export Password:
Verifying - Enter Export Password:

Successful export of p12 file. Your exported file is at the following
location: ./pki/private/android-client.p12
```

Copy this file over onto your Android device, and follow the setup procedure
from Step 3 with one slight modification: instead of using "TrustStore
Location", you want "Default SSL/TLS Client Certificate Store" and password.

All done! You should now be able to see your Android client connect to `taky`!

## Future Work

ATAK allows you to bundle server settings and certificates together in a single
importable zip archive. Also, there's apparently a certificate enrollment API.
But that will be for a later version!
