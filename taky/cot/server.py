import os
import time
import socket
import select
import ssl
import logging

from taky.config import app_config as config
from .router import COTRouter
from .client import TAKClient, SocketTAKClient
from .mgmt import MgmtClient


def build_srv(ip_addr, port):
    if ip_addr is None:
        ip_addr = ""
        sock_fam = socket.AF_INET
        bind_args = ("", port)
    else:
        try:
            addr_info = socket.getaddrinfo(ip_addr, port, type=socket.SOCK_STREAM)
            if len(addr_info) > 1:
                logging.warning("Multiple address entities for %s:%s", ip_addr, port)
            (sock_fam, _, _, _, bind_args) = addr_info[0]
        except socket.gaierror as exc:
            raise ValueError(
                f"Unable to determine address info for bind_ip: {ip_addr}"
            ) from exc

    sock = socket.socket(sock_fam, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(bind_args)
    sock.listen()

    return sock


def check_socket(mgmt_sock_path):
    """Checks if the management socket is available for binding"""
    if not os.path.exists(mgmt_sock_path):
        return True

    if not ping_socket(mgmt_sock_path):
        os.remove(mgmt_sock_path)
        return True

    return False


def ping_socket(mgmt_sock_path):
    """Attemps to send a ping to the management socket to check for a running server"""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(mgmt_sock_path)
        client.sendall(b'{"cmd": "ping"}\0')
        client.settimeout(1)
        recv = client.recv(4096)
        if len(recv.decode()) > 0:
            return True
    except socket.error:
        return False
    finally:
        client.close()
    return False


class COTServer:
    """
    COTServer is an object which hosts the server socket, handles client
    sockets, and routes packets between them.

    In the simplest usage, create the object, and call loop()
    """

    def __init__(self):
        """
        Construct the COTServer object, and build the server socket
        """
        self.lgr = logging.getLogger(self.__class__.__name__)

        self.clients = {}
        self.router = COTRouter()

        self.mgmt = None
        self.mon = None
        self.srv = None
        self.ssl_ctx = None

        self.started = -1

    def sock_setup(self):
        """
        Build the server socket
        """
        self.started = time.time()

        # Setup the Management Socket
        mgmt_sock_path = os.path.join(config.get("taky", "root_dir"), "taky-mgmt.sock")
        if check_socket(mgmt_sock_path):
            self.mgmt = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.mgmt.bind(mgmt_sock_path)
            self.mgmt.listen()
        else:
            raise RuntimeError(
                f"Taky already appears to be running via {mgmt_sock_path}"
            )

        # Build the SSL Context
        self.ssl_ctx = self._ssl_setup()

        # Setup the Server Socket
        ip_addr = config.get("taky", "bind_ip")
        port = config.getint("cot_server", "port")

        mode = "ssl" if self.ssl_ctx else "tcp"
        self.lgr.info("Listening for %s on %s:%s", mode, ip_addr, port)
        self.srv = build_srv(ip_addr, port)

        # Setup the Monitor Socket
        if mode == "tcp":
            return

        ip_addr = config.get("cot_server", "mon_ip")
        port = config.getint("cot_server", "mon_port")

        if ip_addr is None:
            return

        self.lgr.info("Monitor listening for tcp on %s:%s", ip_addr, port)
        self.mon = build_srv(ip_addr, port)

    def _ssl_setup(self):
        """
        Build the SSL context
        """
        if not config.getboolean("ssl", "enabled"):
            return None

        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        if config.getboolean("ssl", "client_cert_required"):
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        else:
            self.lgr.info("Clients will not need to present a certificate")
            ssl_ctx.verify_mode = ssl.CERT_OPTIONAL

        # Load up CA certificates
        try:
            ca_cert = config.get("ssl", "ca")
            if ca_cert:
                self.lgr.info("Loading CA certificate from %s", ca_cert)
                ssl_ctx.load_verify_locations(ca_cert)
            else:
                self.lgr.info("Using default CA certificates")
                ssl_ctx.load_default_certs()

            ssl_ctx.load_cert_chain(
                certfile=config.get("ssl", "cert"),
                keyfile=config.get("ssl", "key"),
                password=config.get("ssl", "key_pw"),
            )
        except (ssl.SSLError, OSError) as exc:
            self.lgr.error("Unable to load SSL certificate: %s", exc)
            raise exc

        return ssl_ctx

    def mgmt_accept(self):
        """
        Accept a new client on the management socket
        """
        try:
            (sock, _) = self.mgmt.accept()
        except (socket.error, OSError) as exc:
            self.lgr.info("Dropping management client: %s", exc)
            return

        self.lgr.info("New management client")
        self.clients[sock] = MgmtClient(sock=sock, use_ssl=False, server=self)

    def srv_accept(self, srv_sock, force_tcp=False):
        """
        Accept a new client from a server socket
        """
        ip_addr = None
        port = None
        use_ssl = self.ssl_ctx and not force_tcp

        try:
            (sock, addr) = srv_sock.accept()
            (ip_addr, port) = addr[0:2]

            if use_ssl:
                sock = self.ssl_ctx.wrap_socket(
                    sock, server_side=True, do_handshake_on_connect=False
                )
                sock.setblocking(False)
        except ssl.SSLError as exc:
            self.lgr.info("Rejecting client %s:%s (%s)", ip_addr, port, exc)
            return
        except (socket.error, OSError) as exc:
            self.lgr.info("Client connect failed %s:%s (%s)", ip_addr, port, exc)
            return

        stype = "ssl" if use_ssl else "tcp"
        self.lgr.info("New %s client from %s:%s", stype, ip_addr, port)
        self.clients[sock] = SocketTAKClient(
            sock=sock,
            use_ssl=use_ssl,
            router=self.router,
            log_cot_dir=config.get("cot_server", "log_cot"),
            connect_cb=self.client_connect,
        )

    def client_connect(self, client):
        self.router.client_connect(client)

    def client_disconnect(self, client, reason=None):
        """
        Disconnect a client from the server
        """
        client.disconnect(reason)
        if client.sock in self.clients:
            client = self.clients.pop(client.sock)

        if isinstance(client, TAKClient):
            self.router.client_disconnect(client)

    def loop(self):
        """
        Main loop. Call outside this object in a "while True" block.
        """
        rd_clients = list(self.clients)
        rd_clients.append(self.srv)
        if self.mon:
            rd_clients.append(self.mon)
        rd_clients.append(self.mgmt)
        wr_clients = list(filter(lambda x: self.clients[x].has_data, self.clients))

        (s_rd, s_wr, s_ex) = select.select(rd_clients, wr_clients, rd_clients, 1)

        # At each stage, we will need to re-check to make sure the previous
        # stage did not close our socket.

        # Process exception sockets
        for sock in s_ex:
            if sock in [self.srv, self.mgmt]:
                raise RuntimeError("Server socket exceptional condition")

            client = self.clients.get(sock)
            self.client_disconnect(client, "Exceptional condition")

        # Process sockets with incoming data
        for sock in s_rd:
            if sock is self.srv:
                self.srv_accept(sock)
            elif sock is self.mon:
                self.srv_accept(sock, force_tcp=True)
            elif sock is self.mgmt:
                self.mgmt_accept()
            else:
                client = self.clients.get(sock)
                if not client.is_closed:
                    client.socket_rx()

        # Process sockets with outgoing data
        for sock in s_wr:
            client = self.clients.get(sock)
            if not client.is_closed:
                client.socket_tx()

        # Prune the persistence database
        self.router.prune()

        # Prune sockets
        now = time.time()
        prune_sox = list(self.clients.items())
        for (sock, client) in prune_sox:
            if client.is_closed:
                self.client_disconnect(client, "Is closed")
                continue

            if not client.ready and (now - client.connected) > 10:
                self.client_disconnect(client, "SSL Handshake timeout")

    def shutdown(self):
        """
        Disconnect all clients, close server socket.
        """
        self.lgr.info("Sending disconnect to clients")
        for client in list(self.clients.values()):
            self.client_disconnect(client, "Server shutting down")

        if self.srv:
            try:
                self.srv.shutdown(socket.SHUT_RDWR)
            except:  # pylint: disable=bare-except
                pass
            finally:
                self.srv.close()
            self.srv = None

        if self.mon:
            try:
                self.mon.shutdown(socket.SHUT_RDWR)
            except:  # pylint: disable=bare-except
                pass
            finally:
                self.mon.close()

            self.mon = None

        if self.mgmt:
            mgmt_sock_path = os.path.join(
                config.get("taky", "root_dir"), "taky-mgmt.sock"
            )
            try:
                self.mgmt.shutdown(socket.SHUT_RDWR)
            except:  # pylint: disable=bare-except
                pass
            finally:
                self.mgmt.close()

            try:
                os.remove(mgmt_sock_path)
            except FileNotFoundError:
                pass

            self.mgmt = None

        self.lgr.info("Stopped")
