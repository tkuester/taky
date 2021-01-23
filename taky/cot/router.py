import queue
import threading
import enum
import logging
import traceback

from lxml import etree

from taky import cot

class Destination(enum.Enum):
    BROADCAST=1
    GROUP=2

class COTRouter(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.clients = set()

        self.event_q = queue.Queue()
        self.stopped = threading.Event()
        self.lgr = logging.getLogger()

    def client_connect(self, client):
        self.clients.add(client)

    def client_disconnect(self, client):
        self.clients.discard(client)

    def client_ident(self, client):
        self.lgr.debug("Sending active clients to %s", client)
        for _client in self.clients:
            if _client is client:
                continue

            xml = etree.tostring(_client.user.as_element)
            client.sock.sendall(xml)

    def push_event(self, src, event, dst=None):
        if not self.is_alive():
            raise RuntimeError("Router is not running")

        if not isinstance(event, (cot.Event, etree._Element)):
            raise ValueError("event must be cot.Event")

        if dst is None:
            dst = Destination.BROADCAST

        self.event_q.put((src, dst, event))

    def broadcast(self, src, msg):
        for client in self.clients:
            if client is src:
                continue

            # TODO: Timeouts? select() on writable sockets? Thread safety?
            client.sock.sendall(msg)

    def group_broadcast(self, src, msg):
        # TODO: Broadcast to group that isn't yours?
        for client in self.clients:
            if client is src:
                continue

            if client.group == src.group:
                client.sock.sendall(msg)

    def run(self):
        self.lgr.info("Starting COT Router")

        while not self.stopped.is_set():
            try:
                (src, dst, evt) = self.event_q.get(True, timeout=1)
                if src is self and evt == 'shutdown':
                    break

                if isinstance(evt, cot.Event):
                    xml = etree.tostring(evt.as_element)
                elif isinstance(evt, etree._Element):
                    xml = etree.tostring(evt)
                else:
                    continue

                if dst is Destination.BROADCAST:
                    self.broadcast(src, xml)
                elif isinstance(dst, cot.TAKClient):
                    dst.sock.sendall(xml)
            except queue.Empty:
                continue
            except Exception as e:
                self.lgr.error("Unhandled exception: %s", e)
                self.lgr.error(traceback.format_exc())

        self.lgr.info("Stopping COT Router")

    def stop(self):
        self.stopped.set()
        self.event_q.put((self, None, 'shutdown'))
