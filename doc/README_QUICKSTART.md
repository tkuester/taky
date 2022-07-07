# Shut up and take my money!

Ok, geez! Hold your horses! This guide assumes:

1. You have sudo privilegs
2. You don't mind installing things globally
3. You don't want to run the server as root
4. You want SSL, and know how to get files to your end user devices
5. There are no other services runing on 8089 / 8443

In this case, we will pretend your username is "bluetack".

```
# Install Dependencies -- yum for CentOS
bluetack $ sudo apt install python3 python3-pip
[...]
bluetack $ sudo python3 -m pip install --upgrade pip
[...]

# Install taky
bluetack $ sudo python3 -m pip install taky
[...]

# Generate config + CA + Certs
bluetack $ sudo takyctl setup --host <hostname> --public-ip 123.45.67.89 --user bluetack
Installing site to system
 - Wrote /etc/taky/taky.conf
 - Generating certificate authority
 - Generating server certificate
 - Changing ownership to bluetack

# Install systemd Services
bluetack $ sudo takyctl systemd --user bluetack
 - Detected system-wide site install
 - Writing services to /etc/systemd/system
   - Writing taky-cot.service
   - Writing taky-dps.service
   - Writing taky.service
 - Reloading systemctl services
 - Enabling service
Created symlink /etc/systemd/system/multi-user.target.wants/taky.service → /etc/systemd/system/taky.service.
 - Starting service

# Make sure the services are running
bluetack $ ps aux | grep taky
bluetack  107862  5.5  0.4  57852 34292 ?        Ss   16:32   0:00 /usr/bin/python3 /usr/local/bin/taky -l info
bluetack  107863  7.4  0.5  69092 43384 ?        Ss   16:32   0:00 /usr/bin/python3 /usr/local/bin/taky_dps
[...]

# Build your first client certificate for ATAK/Wintak/TAKTracker
bluetack $ takyctl build_client JENNY
bluetack $ ls -l JENNY.zip
-rw-r--r-- 1 bluetack bluetack 7040 Apr  3 16:07 JENNY.zip

# Build your first client certificate for ITAK
bluetack $ takyctl build_client --is_itak JENNY-ITAK
bluetack $ ls -l JENNY-ITAK.zip
-rw-r--r-- 1 bluetack bluetack 7040 Apr  3 16:07 JENNY-ITAK.zip

# Transfer the .zip file to your device, and import it! If you want to serve it
# locally (ie: for Android clients), run this, and point the import manager to
# http://your.ip.address:8000/JENNY.zip

# Hit Ctrl+C when you're done!
$ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

## I want to delete everything and start over!

Pretty simple.

If you installed the systemd services:

```
root # systemctl stop taky
root # rm /etc/systemd/system/taky*.service
root # systemctl daemon-reload
```

Then, delete all the config and user data.

```
root # rm -rf /etc/taky /var/taky
```
