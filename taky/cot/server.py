#!/usr/bin/python3
import socket
import select
import ssl
import logging

from .router import COTRouter
from .client import TAKClient

class COTServer:
    def __init__(self, config):
        self.lgr = logging.getLogger(self.__class__.__name__)

        self.config = config
        self.clients = {}
        self.router = COTRouter()

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

        self.ssl_ctx = self.ssl_setup()

        self.srv = socket.socket(sock_fam, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(bind_args)

        mode = 'ssl' if self.ssl_ctx else 'tcp'

        self.lgr.info("Listening for %s on %s:%s", mode, ip, port)
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

    def handle_accept(self):
        try:
            (sock, addr) = self.srv.accept()
            if self.ssl_ctx:
                sock = self.ssl_ctx.wrap_socket(sock, server_side=True)
                # TODO: Check peer cert, get hostname, assign to TAKClient
        except ssl.SSLError as e:
            self.lgr.info("Rejecting client: %s", e)
            return
        except socket.error as e:
            self.lgr.info("Rejecting client: %s", e)
            return
        except OSError as e:
            # https://bugs.python.org/issue31122
            if e.errno != 0:
                self.lgr.warning("Unable to accept client: %s", e)
            return

        (ip, port) = addr[0:2]
        self.lgr.info("New client from %s:%s", ip, port)
        self.clients[sock] = TAKClient(
            ip,
            port,
            self.router,
            cot_log_dir=self.config.get('cot_server', 'log_cot')
        )
        self.router.client_connect(self.clients[sock])

    def client_rx(self, sock):
        client = self.clients[sock]
        try:
            data = sock.recv(4096)

            if len(data) == 0:
                self.client_disconnect(sock, "Disconnected")
                return

            client.feed(data)
        except (socket.error, IOError, OSError) as e:
            self.client_disconnect(sock, str(e))

    def client_tx(self, sock):
        try:
            client = self.clients[sock]
            sent = sock.send(client.out_buff[0:4096])
            client.out_buff = client.out_buff[sent:]
        except (socket.error, IOError, OSError) as e:
            self.client_disconnect(sock, str(e))

    def client_disconnect(self, sock, reason=None):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except:
            pass
        sock.close()

        client = self.clients.pop(sock)
        if reason:
            self.lgr.info('Client disconnect: %s (%s)', client, reason)
        else:
            self.lgr.info('Client disconnect: %s', client)
        self.router.client_disconnect(client)
        client.close()

    def loop(self):
        rd_clients = [self.srv]
        wr_clients = []
        for (sock, client) in self.clients.items():
            rd_clients.append(sock)
            if client.has_data:
                wr_clients.append(sock)

        (s_rd, s_wr, s_ex) = select.select(rd_clients, wr_clients, rd_clients, 10)

        for sock in s_ex:
            if sock is self.srv:
                raise RuntimeError("Server socket exceptional condition")

            self.client_disconnect(sock, "Exceptional condition")

        for sock in s_rd:
            if sock is self.srv:
                self.handle_accept()
            else:
                self.client_rx(sock)

        for sock in s_wr:
            self.client_tx(sock)

    def shutdown(self):
        self.lgr.info("Sending disconnect to clients")
        for (sock, client) in self.clients.items():
            self.lgr.debug("Closing %s", client)
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            sock.close()

        try:
            self.srv.shutdown(socket.SHUT_RDWR)
        except:
            pass

        self.srv.close()
        self.srv = None
        self.lgr.info("Stopped")
