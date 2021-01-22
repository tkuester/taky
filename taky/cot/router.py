import queue
import threading
import logging
import traceback

from lxml import etree

class COTRouter(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)

        self.server = server
        self.by_uid = {}
        self.by_group = {}

        self.event_q = queue.Queue()
        self.stopped = threading.Event()
        self.lgr = logging.getLogger()

    def run(self):
        self.lgr.info("Starting COT Router")

        while not self.stopped.is_set():
            try:
                (source, event) = self.event_q.get(True, timeout=1)
                if source is None and event is None:
                    break

                msg = etree.tostring(event)
                for client in self.server.clients.values():
                    if client is source:
                        continue

                    client.sock.sendall(msg)
            except queue.Empty:
                continue
            except Exception as e:
                self.lgr.error("Unhandled exception: %s", e)
                self.lgr.error(traceback.format_exc())

        self.lgr.info("Stopping COT Router")

    def stop(self):
        self.stopped.set()
        self.event_q.put((None, None))
