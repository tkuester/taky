#!/usr/bin/python3
import socket
import select
import ssl
import threading
import traceback
import logging

from .router import COTRouter
from .client import TAKClient

class COTServer(threading.Thread):
    def __init__(self, config):
        threading.Thread.__init__(self)
        self.lgr = logging.getLogger(self.__class__.__name__)
        self.stopped = threading.Event()

        self.config = config
        self.clients = {}
        self.router = COTRouter(self)

        self.srv = None

        self.sock_setup()

    def sock_setup(self):
        ip = self.config.get('taky', 'bind_ip')
        port = self.config.getint('cot_server', 'port')

        if ip is None:
            ip = ''
            sock_fam = socket.AF_INET
            bind_args = ('', port)
        else:
            try:
                ai = socket.getaddrinfo(ip, port, type=socket.SOCK_STREAM)
                if len(ai) > 1:
                    self.lgr.warning("Multiple address entities for %s:%s", ip, port)
                (sock_fam, _, _, _, bind_args) = ai[0]
            except socket.gaierror as e:
                raise ValueError(f"Unable to determine address info for bind_ip: {ip}") from e

        ssl_ctx = self.ssl_setup()

        self.srv = socket.socket(sock_fam, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(bind_args)

        if ssl_ctx:
            self.srv = ssl_ctx.wrap_socket(self.srv, server_side=True)

        self.lgr.info("Listening on %s:%s", ip, port)
        self.srv.listen()

    def ssl_setup(self):
        if not self.config.getboolean('ssl', 'enabled'):
            return None

        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        if self.config.getboolean('ssl', 'client_cert_required'):
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        else:
            self.lgr.info("Clients will not need to present a certificate")
            ssl_ctx.verify_mode = ssl.CERT_OPTIONAL

        # Load up CA certificates
        try:
            ca_cert = self.config.get('ssl', 'ca')
            if ca_cert:
                self.lgr.info("Loading CA certificate from %s", ca_cert)
                ssl_ctx.load_verify_locations(ca_cert)
            else:
                self.lgr.info("Using default CA certificates")
                ssl_ctx.load_default_certs()

            ssl_ctx.load_cert_chain(certfile=self.config.get('ssl', 'cert'),
                                    keyfile=self.config.get('ssl', 'key'),
                                    password=self.config.get('ssl', 'key_pw'))
        except (ssl.SSLError, OSError) as e:
            self.lgr.error("Unable to load SSL certificate: %s", e)
            raise e

        return ssl_ctx

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
            self.lgr.info('%s closed on error: %s', client, e)
            sock.close()
            self.clients.pop(sock)

    def run(self):
        self.router.start()

        while not self.stopped.is_set():
            try:
                sox = [self.srv]
                sox.extend(self.clients.keys())

                (rd, _, _) = select.select(sox, [], [], 10)

                if len(rd) == 0:
                    continue
                elif self.stopped.is_set():
                    break

                for sock in rd:
                    if sock is self.srv:
                        (sock, addr) = self.srv.accept()

                        self.lgr.info("New client from %s:%s", addr[0], addr[1])
                        self.clients[sock] = TAKClient(
                            sock,
                            self.router,
                            cot_log_dir=self.config.get('cot_server', 'log_cot')
                        )
                        self.router.client_connect(self.clients[sock])
                    else:
                        self.handle_client(sock)
            except ssl.SSLError as e:
                self.lgr.info("Rejecting client: %s", e)
            except Exception as e:
                self.lgr.critical("Unhandled exception: %s", e)
                self.lgr.critical(traceback.format_exc())
                break

        for (sock, client) in self.clients.items():
            self.lgr.debug("Closing %s", client)
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
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
