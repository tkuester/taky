#!/bin/sh
# 
# Builds a secure taky server now, not next week.

NIC=`route -n | grep '0.0.0.0' | head -1 |  awk '{print $8}'`
IP=`ifconfig $NIC | grep 'inet ' | awk '{print $2}'`
#IP=90.216.1.129
TAKY_SERVER="/tmp/takyserver"

takyctl setup --public-ip $IP --host $IP $TAKY_SERVER
takyctl -c $TAKY_SERVER/taky.conf build_client --dump_pem user
mkdir $TAKY_SERVER/taky_dp
cp user.zip $TAKY_SERVER/taky_dp
cp user.* $TAKY_SERVER/ssl

# Comment this line to NOT serve your certificates insecurely via HTTP :1664
# It will serve the certs for 15 minutes only. After that you need to sideload the .zip
timeout 15m python3 dpserver.py $TAKY_SERVER/taky_dp &
taky -c $TAKY_SERVER/taky.conf

