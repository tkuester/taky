#!/usr/bin/python3
from flask import Flask, request, send_from_directory
import sys
import os
import socket
import random

# Serves certificates from /tmp/taky_dp
# eg. http://192.168.1.107:1664/5036307/user_DP.zip

app = Flask(__name__, static_url_path='')
port = 1664

if len(sys.argv) < 2:
  print("Need a directory to serve up. eg. dpserver.py /tmp/somedir")
  quit()

webroot = os.path.join(os.getcwd(), sys.argv[1])

if not os.path.exists(webroot):
  print("Folder %s does not exist" % webroot)
  quit()


nonce = "takycerts" # str(random.randrange(1e6,10e6)) # Make URL harder to guess 

@app.route("/"+nonce+"/<path>")
def send_js(path):
    return send_from_directory(webroot, path)
  

if __name__ == "__main__":
    print("\nWARNING: Serving certificates insecurely from %s" % webroot)
    files = os.listdir(webroot)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 53)) # to resolve our external IP. Doesn't have to be reachable.
    ip = s.getsockname()[0]
    for f in files:
      print("http://%s:%d/%s/%s" % (ip,port,nonce,f))

    app.run(host="0.0.0.0",port=port)
