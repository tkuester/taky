import logging
import time
import json

from .client import SocketClient, TAKClient


class MgmtClient(SocketClient):
    """
    MgmtClient implements a socket client that handles connections to taky's
    management socket. This socket communicates with null terminated JSON,
    in the style of {"cmd": "..."}\\0
    """

    def __init__(self, server, **kwargs):
        self.lgr = logging.getLogger(self.__class__.__name__)
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
            elif msg.get("cmd") == "ping":
                ret = {"pong": "taky"}
            elif msg.get("cmd") == "kickban":
                ret = self.kickban(msg.get("user"))
            else:
                ret = {"error": f"Invalid cmd: {msg.get('cmd')}"}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            ret = {"error": str(exc)}

        ret = json.dumps(ret)
        self.out_buff += ret.encode() + b"\0"

    def kickban(self, user):
        cdb = self.server.cert_db
        revoked_sns = []

        for cert in cdb.get_certificates_by_name(user):
            if cert["status"] == "R":
                continue

            cdb.revoke_certificate(cert["serial_num"])
            revoked_sns.append(cert["serial_num"])
            self.lgr.info(
                f"Revoked certificate for {user} (SN: {cert['serial_num']:040x})"
            )

            for client in list(self.server.clients.values()):
                if not client.peer_cert:
                    continue

                if int(client.peer_cert.get("serialNumber"), 16) == cert["serial_num"]:
                    self.lgr.info(f"Kicking user {user} from server")
                    self.server.client_disconnect(client, "Banned")

        return {"revoked_sns": revoked_sns}

    def status(self):
        ret = {
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
            if client.user:
                if isinstance(client, SocketClient):
                    cli_meta["ip"] = client.addr[0]
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
