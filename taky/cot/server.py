#!/usr/bin/python3
from datetime import datetime, timedelta
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
        addr = self.clients[sock]['addr']
        parser = self.clients[sock]['parser']
        try:
            data = sock.recv(4096)
            self.lgr.log(logging.DEBUG - 1, "%s: %s", addr, data)

            if len(data) == 0:
                self.lgr.info('Client disconnect: %s', addr)
                sock.close()
                self.clients.pop(sock)
                return

            for ch in data:
                try:
                    parser.feed(chr(ch))
                except etree.XMLSyntaxError as e:
                    continue

            for (etype, elm) in parser.read_events():
                self.lgr.debug('UID: %s', elm.get('uid'))
                if elm.get('uid').endswith('-ping'):
                    now = datetime.now()
                    pong = cot.Event(
                        uid='takPong',
                        etype='t-x-c-t-r',
                        how='h-g-i-g-o',
                        time=now,
                        start=now,
                        stale=now + timedelta(seconds=20)
                    )
                    sock.sendall(pong.as_xml)
                elm.clear(keep_tail=True)
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
                        self.clients[sock] = {'addr': addr,
                                              'parser': etree.XMLPullParser(tag="event")}
                    else:
                        self.handle_client(sock)
        except Exception as e:
            self.lgr.crit("Unhandled exception: %s", e)
            self.lgr.crit(traceback.format_exc())
        finally:
            for (sock, addr) in self.clients.items():
                self.lgr.debug("Closing %s", addr['addr'])
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()

            self.srv.close()

    def stop(self):
        self.stopped.set()
