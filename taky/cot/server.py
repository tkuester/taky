#!/usr/bin/python3
# pylint: disable=missing-module-docstring
import socket
import select
import ssl
import logging

from .router import COTRouter
from .client import SocketTAKClient, SSLState

class COTServer:
    '''
    COTServer is an object which hosts the server socket, handles client
    sockets, and routes packets between them.

    In the simplest usage, create the object, and call loop()
    '''

    def __init__(self, config):
        '''
        Construct the COTServer object, and build the server socket
        '''
        self.lgr = logging.getLogger(self.__class__.__name__)

        self.config = config
        self.clients = {}
        self.router = COTRouter()

        self.srv = None
        self._sock_setup()

    def _sock_setup(self):
        '''
        Build the server socket
        '''
        ip_addr = self.config.get('taky', 'bind_ip')
        port = self.config.getint('cot_server', 'port')

        if ip_addr is None:
            ip_addr = ''
            sock_fam = socket.AF_INET
            bind_args = ('', port)
        else:
            try:
                addr_info = socket.getaddrinfo(ip_addr, port, type=socket.SOCK_STREAM)
                if len(addr_info) > 1:
                    self.lgr.warning("Multiple address entities for %s:%s", ip_addr, port)
                (sock_fam, _, _, _, bind_args) = addr_info[0]
            except socket.gaierror as exc:
                raise ValueError(
                    f"Unable to determine address info for bind_ip: {ip_addr}"
                ) from exc

        self.ssl_ctx = self._ssl_setup()

        self.srv = socket.socket(sock_fam, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(bind_args)

        mode = 'ssl' if self.ssl_ctx else 'tcp'

        self.lgr.info("Listening for %s on %s:%s", mode, ip_addr, port)
        self.srv.listen()

    def _ssl_setup(self):
        '''
        Build the SSL context
        '''
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
        except (ssl.SSLError, OSError) as exc:
            self.lgr.error("Unable to load SSL certificate: %s", exc)
            raise exc

        return ssl_ctx

    def handle_accept(self):
        '''
        Accept a new client on the server socket
        '''
        try:
            (sock, addr) = self.srv.accept()
            if self.ssl_ctx:
                sock = self.ssl_ctx.wrap_socket(sock, server_side=True,
                                                do_handshake_on_connect=False)
                sock.setblocking(False)
        except (ssl.SSLError, socket.error, OSError) as exc:
            (ip_addr, port) = addr[0:2]
            self.lgr.info("Rejecting client %s:%s (%s)", ip_addr, port, exc)
            return

        (ip_addr, port) = addr[0:2]
        self.lgr.info("New client from %s:%s", ip_addr, port)
        self.clients[sock] = SocketTAKClient(
            self.router,
            cot_log_dir=self.config.get('cot_server', 'log_cot'),
            addr=addr[0:2]
        )
        if self.ssl_ctx:
            self.clients[sock].ssl_hs = SSLState.SSL_WAIT
        self.router.client_connect(self.clients[sock])

    def ssl_handshake(self, sock, client):
        ''' Preform the SSL handshake on the socket '''
        if not self.ssl_ctx or client.ssl_hs is SSLState.SSL_ESTAB:
            return

        try:
            sock.do_handshake()
            client.ssl_hs = SSLState.SSL_ESTAB
            sock.setblocking(True)
            # TODO: Check SSL certs here
        except ssl.SSLWantReadError:
            client.ssl_hs = SSLState.SSL_WAIT
        except ssl.SSLWantWriteError:
            client.ssl_hs = SSLState.SSL_WAIT_TX
        except (ssl.SSLError, OSError) as exc:
            self.client_disconnect(sock, str(exc))

    def client_rx(self, sock, client):
        '''
        Receive data from client socket, and feed to TAKClient
        '''
        try:
            data = sock.recv(4096)

            if len(data) == 0:
                self.client_disconnect(sock, "Disconnected")
                return

            client.feed(data)
        except (socket.error, IOError, OSError) as exc:
            self.client_disconnect(sock, str(exc))

    def client_tx(self, sock, client):
        '''
        Transmit data to client socket

        If the client is SSL enabled, and the handshake has not yet taken
        place, we fail silently.
        '''
        try:
            sent = sock.send(client.out_buff[0:4096])
            client.out_buff = client.out_buff[sent:]
        except (socket.error, IOError, OSError) as exc:
            self.client_disconnect(sock, str(exc))

    def client_disconnect(self, sock, reason=None):
        '''
        Disconnect a client from the server
        '''
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except: # pylint: disable=bare-except
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
        '''
        Main loop. Call outside this object in a "while True" block.
        '''
        rd_clients = list(self.clients)
        rd_clients.append(self.srv)
        wr_clients = list(filter(lambda x: self.clients[x].has_data, self.clients))

        (s_rd, s_wr, s_ex) = select.select(rd_clients, wr_clients, rd_clients, 10)

        # At each stage, we will need to re-check to make sure the previous
        # stage did not close our socket.

        # Process exception sockets
        for sock in s_ex:
            if sock is self.srv:
                raise RuntimeError("Server socket exceptional condition")

            self.client_disconnect(sock, "Exceptional condition")

        # Process sockets with incoming data
        for sock in s_rd:
            client = self.clients.get(sock)
            if sock.fileno() == -1:
                continue
            elif sock is self.srv:
                self.handle_accept()
            elif self.ssl_ctx and client.ssl_hs in [SSLState.SSL_WAIT, SSLState.SSL_WAIT_TX]:
                self.ssl_handshake(sock, client)
            else:
                self.client_rx(sock, client)

        # Process sockets with outgoing data
        for sock in filter(lambda x: x.fileno() != -1, s_wr):
            client = self.clients.get(sock)
            if sock.fileno() == -1:
                continue
            elif self.ssl_ctx and client.ssl_hs in [SSLState.SSL_WAIT, SSLState.SSL_WAIT_TX]:
                self.ssl_handshake(sock, client)
            else:
                self.client_tx(sock, client)

    def shutdown(self):
        '''
        Disconnect all clients, close server socket.
        '''
        self.lgr.info("Sending disconnect to clients")
        for sock in list(self.clients):
            self.client_disconnect(sock, 'Server shutting down')

        try:
            self.srv.shutdown(socket.SHUT_RDWR)
        except: # pylint: disable=bare-except
            pass

        self.srv.close()
        self.srv = None
        self.lgr.info("Stopped")
