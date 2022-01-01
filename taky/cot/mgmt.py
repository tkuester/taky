import time
import json

from taky import __version__
from .client import SocketClient, TAKClient


class MgmtClient(SocketClient):
    """
    MgmtClient implements a socket client that handles connections to taky's
    management socket. This socket communicates with null terminated JSON,
    in the style of {"cmd": "..."}\\0
    """

    def __init__(self, server, **kwargs):
        self.server = server
        self.buff = b""
        super().__init__(**kwargs)

    @property
    def has_data(self):
        self.handle_rx()
        return super().has_data

    def feed(self, data):
        self.buff += data
        self.handle_rx()

    def handle_rx(self):
        try:
            idx = self.buff.index(b"\0")
        except ValueError:
            return

        msg = self.buff[0:idx]
        self.buff = self.buff[idx + 1 :]

        try:
            msg = msg.decode()
            msg = json.loads(msg)

            if msg.get("cmd") == "status":
                ret = self.status()
            elif msg.get("cmd") == "purge_persist":
                ret = self.purge_persist()
            elif msg.get("cmd") == "ping":
                ret = {"pong": "taky"}
            else:
                ret = {"error": f"Invalid cmd: {msg.get('cmd')}"}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            ret = {"error": str(exc)}

        ret = json.dumps(ret)
        self.out_buff += ret.encode() + b"\0"

    def purge_persist(self):
        return {"purged": self.server.router.persist.purge()}

    def status(self):
        ret = {
            "version": __version__,
            "uptime": time.time() - self.server.started,
            "num_clients": 0,
            "clients": [],
        }
        for client in self.server.clients.values():
            if not isinstance(client, TAKClient):
                continue

            ret["num_clients"] += 1
            cli_meta = {
                "last_rx": client.last_rx,
                "num_rx": client.num_rx,
                "connected": client.connected,
            }

            if isinstance(client, SocketClient):
                cli_meta["ip"] = client.addr[0]

            if client.user:
                cli_meta["uid"] = client.user.uid
                cli_meta["callsign"] = client.user.callsign
                cli_meta["group"] = str(client.user.group)
                cli_meta["battery"] = client.user.battery
                cli_meta["device"] = client.user.device.device
                cli_meta["os"] = client.user.device.os
                cli_meta["version"] = client.user.device.version
                cli_meta["platform"] = client.user.device.platform
            else:
                cli_meta["anonymous"] = True

            ret["clients"].append(cli_meta)

        return ret
