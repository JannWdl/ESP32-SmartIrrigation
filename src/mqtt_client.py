import socket
import struct
import time

def enc_len(length):
    out = b""
    while True:
        digit = length % 128
        length //= 128
        if length:
            digit |= 128
        out += bytes([digit])
        if not length:
            return out

def mstr(s):
    if s is None:
        s = ""
    if not isinstance(s, bytes):
        s = str(s).encode()
    return struct.pack("!H", len(s)) + s

class MiniMQTT:
    def __init__(self, host, port=1883, client_id="esp32", username="", password=""):
        self.host = host
        self.port = int(port)
        self.client_id = client_id
        self.username = username
        self.password = password
        self.sock = None
        self.connected = False

    def connect(self):
        self.close()
        addr = socket.getaddrinfo(self.host, self.port)[0][-1]
        s = socket.socket()
        s.settimeout(5)
        s.connect(addr)
        flags = 2
        payload = mstr(self.client_id)
        if self.username:
            flags |= 0x80
            payload += mstr(self.username)
        if self.password:
            flags |= 0x40
            payload += mstr(self.password)
        var = mstr("MQTT") + bytes([4, flags]) + struct.pack("!H", 60)
        s.send(bytes([0x10]) + enc_len(len(var) + len(payload)) + var + payload)
        resp = s.recv(4)
        if len(resp) < 4 or resp[0] != 0x20 or resp[3] != 0:
            s.close()
            raise OSError("MQTT CONNACK: {}".format(resp))
        s.settimeout(2)
        self.sock = s
        self.connected = True

    def publish(self, topic, payload, retain=False):
        if not self.connected or self.sock is None:
            self.connect()
        if not isinstance(payload, bytes):
            payload = str(payload).encode()
        body = mstr(topic) + payload
        self.sock.send(bytes([0x30 | (1 if retain else 0)]) + enc_len(len(body)) + body)

    def close(self):
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.connected = False

class MQTTService:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = None
        self.last_error = ""
        self.last_publish = 0
        self.last_publish_count = 0
        self.last_test = 0
        self.last_test_ok = False
        self.discovery_done = False
        self.connected_once = False
        self.last_topic = ""
        self.last_payload = ""

    def enabled(self):
        m = self.cfg.get("mqtt", {})
        return bool(m.get("enabled") and m.get("host"))

    def base(self):
        return self.cfg.get("mqtt", {}).get("base_topic", "smart_irrigation").rstrip("/")

    def discovery_prefix(self):
        return self.cfg.get("mqtt", {}).get("discovery_prefix", "homeassistant").rstrip("/")

    def is_connected(self):
        return bool(self.client and self.client.connected)

    def _client(self):
        if not self.enabled():
            raise RuntimeError("MQTT nicht aktiviert oder Host fehlt")
        m = self.cfg["mqtt"]
        if self.client is None:
            self.client = MiniMQTT(
                m.get("host"),
                m.get("port", 1883),
                m.get("client_id", "smart-irrigation-esp32"),
                m.get("username", ""),
                m.get("password", "")
            )
        if not self.client.connected:
            self.client.connect()
            self.connected_once = True
        return self.client

    def publish(self, suffix, payload, retain=False):
        topic = self.base() + "/" + suffix.lstrip("/")
        try:
            c = self._client()
            c.publish(topic, payload, retain=retain)
            self.last_error = ""
            self.last_topic = topic
            self.last_payload = str(payload)[:50]
            return True
        except Exception as exc:
            self.last_error = str(exc)
            try:
                if self.client:
                    self.client.close()
            except Exception:
                pass
            self.client = None
            print("MQTT Fehler:", exc)
            return False

    def publish_abs(self, topic, payload, retain=False):
        try:
            c = self._client()
            c.publish(topic, payload, retain=retain)
            self.last_error = ""
            self.last_topic = topic
            self.last_payload = str(payload)[:50]
            return True
        except Exception as exc:
            self.last_error = str(exc)
            try:
                if self.client:
                    self.client.close()
            except Exception:
                pass
            self.client = None
            print("MQTT Fehler:", exc)
            return False

    def discovery(self, channels):
        if not self.enabled() or not self.cfg.get("mqtt", {}).get("homeassistant_discovery", True):
            return False
        base = self.base()
        pref = self.discovery_prefix()
        ok = True
        for ch in channels:
            cid = ch.get("id", 0)
            name = ch.get("name", "Kanal {}".format(cid + 1))
            dev = '"device":{"identifiers":["smart_irrigation_esp32"],"name":"Smart Irrigation","manufacturer":"JannWdl","model":"ESP32"}'
            topic_base = base + "/channel/" + str(cid)
            cfgs = [
                ("sensor", "moisture", "Feuchtigkeit", "%", "humidity", topic_base + "/moisture"),
                ("sensor", "raw_adc", "ADC", "", "", topic_base + "/raw_adc"),
                ("binary_sensor", "pump", "Pumpe", "", "running", topic_base + "/pump/state"),
                ("binary_sensor", "auto", "Automatik", "", "", topic_base + "/auto/state"),
                ("sensor", "cooldown", "Cooldown", "s", "", topic_base + "/cooldown_remaining"),
            ]
            for typ, key, label, unit, devclass, state_topic in cfgs:
                unique = "smart_irrigation_{}_{}".format(cid, key)
                cfg_topic = "{}/{}/smart_irrigation/{}/config".format(pref, typ, unique)
                payload = '{"name":"%s %s","unique_id":"%s","state_topic":"%s","availability_topic":"%s/status","payload_available":"online","payload_not_available":"offline",%s' % (name, label, unique, state_topic, base, dev)
                if unit:
                    payload += ',"unit_of_measurement":"{}"'.format(unit)
                if devclass:
                    payload += ',"device_class":"{}"'.format(devclass)
                if typ == "binary_sensor":
                    payload += ',"payload_on":"ON","payload_off":"OFF"'
                payload += "}"
                ok = self.publish_abs(cfg_topic, payload, retain=True) and ok
        self.discovery_done = ok
        return ok

    def publish_status(self, channels, irrigation_status=None, force=False):
        if not self.enabled():
            return False
        now = time.time()
        interval = int(self.cfg.get("mqtt", {}).get("publish_interval_seconds", 60))
        if not force and now - self.last_publish < interval:
            return False

        if not self.discovery_done:
            self.discovery(channels)

        ok = True
        count = 0
        ok = self.publish("status", "online", retain=True) and ok
        count += 1

        status_by_id = {}
        if irrigation_status:
            for s in irrigation_status:
                status_by_id[int(s.get("id", 0))] = s

        for ch in channels:
            cid = int(ch.get("id", 0))
            prefix = "channel/{}/".format(cid)
            ist = status_by_id.get(cid, {})
            auto_state = "ON" if ist.get("auto_reason") not in ("auto_off", "disabled", None) else "OFF"

            ok = self.publish(prefix + "moisture", ch.get("moisture"), retain=True) and ok; count += 1
            ok = self.publish(prefix + "raw_adc", ch.get("raw_adc"), retain=True) and ok; count += 1
            ok = self.publish(prefix + "pump/state", "ON" if ch.get("pump") else "OFF", retain=True) and ok; count += 1
            ok = self.publish(prefix + "auto/state", auto_state, retain=True) and ok; count += 1
            ok = self.publish(prefix + "cooldown_remaining", ist.get("cooldown_remaining", 0), retain=True) and ok; count += 1

        if ok:
            self.last_publish = now
            self.last_publish_count = count
        return ok

    def test(self):
        if not self.enabled():
            self.last_test_ok = False
            self.last_error = "MQTT nicht aktiviert oder Host fehlt"
            return {"ok": False, "error": self.last_error}
        ok = self.publish("test", "Smart Irrigation MQTT-Test erfolgreich", retain=False)
        self.last_test = time.time()
        self.last_test_ok = bool(ok)
        return {
            "ok": ok,
            "error": self.last_error,
            "connected": self.is_connected(),
            "topic": self.base() + "/test"
        }

    def status(self):
        m = self.cfg.get("mqtt", {})
        return {
            "enabled": self.enabled(),
            "host": m.get("host", ""),
            "port": m.get("port", 1883),
            "base_topic": self.base(),
            "connected": self.is_connected(),
            "connected_once": self.connected_once,
            "last_error": self.last_error,
            "last_publish": self.last_publish,
            "last_publish_count": self.last_publish_count,
            "last_test": self.last_test,
            "last_test_ok": self.last_test_ok,
            "discovery_done": self.discovery_done,
            "homeassistant_discovery": bool(m.get("homeassistant_discovery", True)),
            "last_topic": self.last_topic,
            "last_payload": self.last_payload
        }
