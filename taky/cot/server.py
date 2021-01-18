#!/usr/bin/python3
import socket
import select
import threading
import traceback
import logging
from ipaddress import ip_address, IPv4Address, IPv6Address

from lxml import etree

from taky import cot

class COTServer(threading.Thread):
    def __init__(self, ip=None, port=8087):
        threading.Thread.__init__(self)

        if ip is None:
            ip = ip_address('::')

        self.address = (ip, port)
        self.srv = None
        self.clients = {}

        self.lgr = logging.getLogger()
        self.stopped = threading.Event()

    def handle_client(self, sock):
        client = self.clients[sock]
        try:
            data = sock.recv(4096)
            #self.lgr.log(logging.DEBUG - 1, "%s: %s", addr, data)

            if len(data) == 0:
                self.lgr.debug('Client disconnect: %s', client)
                sock.close()
                self.clients.pop(sock)
                return

            client.feed(data)
        except (socket.error, IOError, OSError) as e:
            self.lgr.info('%s closed on error: %s', addr, e)
            sock.close()
            self.clients.pop(sock)

    def run(self):
        if isinstance(self.address[0], IPv4Address):
            self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        elif isinstance(self.address[0], IPv6Address):
            self.srv = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind((str(self.address[0]), self.address[1]))
        self.srv.listen()
        self.lgr.info("Listening on %s:%s", self.address[0], self.address[1])

        try:
            while not self.stopped.is_set():
                sox = [self.srv]
                sox.extend(self.clients.keys())

                (rd, _, ex) = select.select(sox, [], sox, 1)

                if len(rd) == 0:
                    continue

                for sock in rd:
                    if sock is self.srv:
                        (sock, addr) = sock.accept()
                        self.lgr.debug("New client: %s", addr)
                        self.clients[sock] = cot.TAKClient(sock)
                    else:
                        self.handle_client(sock)
        except Exception as e:
            self.lgr.critical("Unhandled exception: %s", e)
            self.lgr.critical(traceback.format_exc())
        finally:
            for (sock, client) in self.clients.items():
                self.lgr.debug("Closing %s", client)
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()

            self.srv.close()

    def stop(self):
        self.stopped.set()
