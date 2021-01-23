#!/usr/bin/python3
import socket
import select
import ssl
import threading
import traceback
import logging
from ipaddress import ip_address, IPv4Address, IPv6Address

from taky import cot

class COTServer(threading.Thread):
    def __init__(self, ip=None, port=8087,
                 ca_cert=None, ssl_cert=None, ssl_key=None, verify_client=False):
        threading.Thread.__init__(self)

        if ip is None:
            ip = ip_address('::')

        self.address = (ip, port)
        self.srv = None

        self.ssl_ctx = None
        self.verify_client = verify_client

        self.clients = {}
        self.router = cot.COTRouter(self)

        self.lgr = logging.getLogger(COTServer.__name__)
        self.stopped = threading.Event()
        
        if ssl_cert and ssl_key:
            self.ssl_setup(ssl_cert, ssl_key, ca_cert, verify_client)

    def handle_client(self, sock):
        client = self.clients[sock]
        try:
            data = sock.recv(4096)
            #self.lgr.log(logging.DEBUG - 1, "%s: %s", addr, data)

            if len(data) == 0:
                self.lgr.info('Client disconnect: %s', client)
                sock.close()
                self.clients.pop(sock)
                self.router.client_disconnect(client)
                return

            self.router.event_q.put((self, client, data))
        except (socket.error, IOError, OSError) as e:
            self.lgr.info('%s closed on error: %s', addr, e)
            sock.close()
            self.clients.pop(sock)

    def ssl_setup(self, ssl_cert, ssl_key, ca_cert=None, verify_client=False):
        self.ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        # Load up CA certificates
        if ca_cert:
            self.lgr.info("Loading CA certificate from %s", ca_cert)
            try:
                self.ssl_ctx.load_verify_locations(ca_cert)
            except (ssl.SSLError, FileNotFoundError) as e:
                self.lgr.error("Unable to load CA certificates: %s", e)
                raise e
        else:
            self.lgr.info("Using default CA certificates")
            self.ssl_ctx.load_default_certs()

        if self.verify_client:
            self.ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        else:
            self.lgr.info("Clients will not need to present a certificate")
            self.ssl_ctx.verify_mode = ssl.CERT_OPTIONAL

        try:
            self.ssl_ctx.load_cert_chain(ssl_cert, ssl_key)
        except (ssl.SSLError, FileNotFoundError) as e:
            self.lgr.error("Unable to load SSL certificate / key: %s", e)
            raise e

        return True

    def run(self):
        if isinstance(self.address[0], IPv4Address):
            self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        elif isinstance(self.address[0], IPv6Address):
            self.srv = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind((str(self.address[0]), self.address[1]))
        self.srv.listen()


        if self.ssl_ctx:
            self.srv = self.ssl_ctx.wrap_socket(self.srv, server_side=True)
            self.lgr.info("Listening for SSL on %s:%s", self.address[0], self.address[1])
        else:
            self.lgr.info("Listening on %s:%s", self.address[0], self.address[1])

        self.router.start()

        try:
            while not self.stopped.is_set():
                sox = [self.srv]
                sox.extend(self.clients.keys())

                (rd, _, ex) = select.select(sox, [], sox, 1)

                if len(rd) == 0:
                    continue

                for sock in rd:
                    if sock is self.srv:
                        try:
                            (sock, addr) = self.srv.accept()
                        except ssl.SSLError as e:
                            self.lgr.info("Rejecting client: %s", e)
                            continue
                        except OSError as e:
                            self.lgr.info("Server socket closed")
                            self.stop()
                            break

                        self.lgr.info("New client from %s:%s", addr[0], addr[1])
                        self.clients[sock] = cot.TAKClient(sock, self.router)
                        self.router.client_connect(self.clients[sock])
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

        self.router.stop()
        self.router.join()

    def stop(self):
        self.router.stop()
        self.stopped.set()
        try:
            self.srv.shutdown(socket.SHUT_RDWR)
        except:
            pass
