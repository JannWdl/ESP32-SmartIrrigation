import socket
import struct
import time

try:
    import uasyncio as asyncio
except ImportError:
    asyncio = None


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
        self.packet_id = 1

    def _next_pid(self):
        self.packet_id += 1
        if self.packet_id > 65535:
            self.packet_id = 1
        return self.packet_id

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
        s.settimeout(0)
        self.sock = s
        self.connected = True

    def close(self):
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.connected = False

    def publish(self, topic, payload, retain=False):
        if not self.connected or self.sock is None:
            self.connect()
        if not isinstance(payload, bytes):
            payload = str(payload).encode()
        pkt = mstr(topic) + payload
        header = 0x30 | (1 if retain else 0)
        self.sock.send(bytes([header]) + enc_len(len(pkt)) + pkt)

    def subscribe(self, topic):
        if not self.connected or self.sock is None:
            self.connect()
        pid = self._next_pid()
        payload = mstr(topic) + b"\x00"  # QoS 0
        var = struct.pack("!H", pid)
        self.sock.send(b"\x82" + enc_len(len(var) + len(payload)) + var + payload)
        return pid

    def _recv_exact(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise OSError("MQTT Verbindung geschlossen")
            data += chunk
        return data

    def check_msg(self):
        if not self.connected or self.sock is None:
            return None
        try:
            b1 = self.sock.recv(1)
            if not b1:
                return None
            try:
                self.sock.settimeout(0.2)
            except Exception:
                pass
            packet_type = b1[0] & 0xF0
            multiplier = 1
            remaining = 0
            while True:
                d = self._recv_exact(1)[0]
                remaining += (d & 127) * multiplier
                if not (d & 128):
                    break
                multiplier *= 128
            data = self._recv_exact(remaining) if remaining else b""
            if packet_type == 0x30:  # PUBLISH QoS 0
                if len(data) < 2:
                    return None
                tlen = (data[0] << 8) | data[1]
                topic = data[2:2+tlen].decode()
                payload = data[2+tlen:].decode()
                return topic, payload
            return None
        except OSError:
            return None
        except Exception:
            self.close()
            raise
        finally:
            try:
                if self.sock:
                    self.sock.settimeout(0)
            except Exception:
                pass


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
        self.subscriptions_done = False
        self.last_command_poll = 0
        self.last_command_topic = ""
        self.last_command_payload = ""
        self.last_command_result = ""

    def enabled(self):
        m = self.cfg.get("mqtt", {})
        return bool(m.get("enabled") and m.get("host"))

    def commands_enabled(self):
        return self.enabled() and bool(self.cfg.get("mqtt", {}).get("commands_enabled", True))

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
            self.subscriptions_done = False
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
            self.subscriptions_done = False
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
            self.subscriptions_done = False
            print("MQTT Fehler:", exc)
            return False

    def command_topics(self):
        b = self.base()
        return [
            b + "/system/command/stop",
            b + "/system/command/discovery",
            b + "/system/command/mqtt_interval",
            b + "/channel/0/command/pump",
            b + "/channel/0/command/run",
            b + "/channel/0/command/auto",
        ]

    def ensure_subscriptions(self):
        if not self.commands_enabled() or self.subscriptions_done:
            return False
        c = self._client()
        for topic in self.command_topics():
            c.subscribe(topic)
        self.subscriptions_done = True
        return True

    def discovery(self, channels):
        if not self.enabled() or not self.cfg.get("mqtt", {}).get("homeassistant_discovery", True):
            return False
        base = self.base()
        pref = self.discovery_prefix()
        ok = True
        dev = '"device":{"identifiers":["smart_irrigation_esp32"],"name":"Smart Irrigation","manufacturer":"JannWdl","model":"ESP32"}'
        interval_unique = "smart_irrigation_mqtt_update_interval"
        interval_cfg_topic = "{}/number/smart_irrigation/{}/config".format(pref, interval_unique)
        interval_payload = '{"name":"MQTT Updateintervall","unique_id":"%s","state_topic":"%s/system/mqtt_interval","command_topic":"%s/system/command/mqtt_interval","min":5,"max":3600,"step":1,"mode":"box","unit_of_measurement":"s",%s}' % (interval_unique, base, base, dev)
        ok = self.publish_abs(interval_cfg_topic, interval_payload, retain=True) and ok
        stop_unique = "smart_irrigation_emergency_stop"
        stop_cfg_topic = "{}/button/smart_irrigation/{}/config".format(pref, stop_unique)
        stop_payload = '{"name":"Not-Aus","unique_id":"%s","command_topic":"%s/system/command/stop","payload_press":"STOP",%s}' % (stop_unique, base, dev)
        ok = self.publish_abs(stop_cfg_topic, stop_payload, retain=True) and ok
        rediscovery_unique = "smart_irrigation_rediscovery"
        rediscovery_cfg_topic = "{}/button/smart_irrigation/{}/config".format(pref, rediscovery_unique)
        rediscovery_payload = '{"name":"HA Discovery neu senden","unique_id":"%s","command_topic":"%s/system/command/discovery","payload_press":"DISCOVERY",%s}' % (rediscovery_unique, base, dev)
        ok = self.publish_abs(rediscovery_cfg_topic, rediscovery_payload, retain=True) and ok

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

            # Einfache HA-Schalter/Buttons für MQTT-Kommandos.
            command_cfgs = [
                ("switch", "auto_cmd", "Auto Steuerung", topic_base + "/command/auto", topic_base + "/auto/state", "ON", "OFF"),
                ("switch", "pump_cmd", "Pumpe manuell", topic_base + "/command/pump", topic_base + "/pump/state", "ON", "OFF"),
                ("button", "run5", "Pumpe 5s", topic_base + "/command/pump", "RUN:5", ""),
                ("button", "run10", "Pumpe 10s", topic_base + "/command/pump", "RUN:10", ""),
            ]
            for item in command_cfgs:
                typ = item[0]
                key = item[1]
                label = item[2]
                unique = "smart_irrigation_{}_{}".format(cid, key)
                cfg_topic = "{}/{}/smart_irrigation/{}/config".format(pref, typ, unique)
                if typ == "switch":
                    _, _, _, cmd_topic, state_topic, payload_on, payload_off = item
                    payload = '{"name":"%s %s","unique_id":"%s","command_topic":"%s","state_topic":"%s","payload_on":"%s","payload_off":"%s",%s}' % (name, label, unique, cmd_topic, state_topic, payload_on, payload_off, dev)
                else:
                    _, _, _, cmd_topic, payload_press, _ = item
                    payload = '{"name":"%s %s","unique_id":"%s","command_topic":"%s","payload_press":"%s",%s}' % (name, label, unique, cmd_topic, payload_press, dev)
                ok = self.publish_abs(cfg_topic, payload, retain=True) and ok
        self.discovery_done = ok
        return ok

    def publish_status(self, channels, irrigation_status=None, force=False):
        if not self.enabled():
            return False
        now = time.time()
        try:
            interval = max(5, int(self.cfg.get("mqtt", {}).get("publish_interval_seconds", 60)))
        except Exception:
            interval = 60
        if not force and now - self.last_publish < interval:
            return False

        if not self.discovery_done:
            self.discovery(channels)
        if self.commands_enabled():
            try:
                self.ensure_subscriptions()
            except Exception as exc:
                self.last_error = str(exc)

        ok = True
        count = 0
        ok = self.publish("status", "online", retain=True) and ok
        count += 1
        ok = self.publish("system/mqtt_interval", interval, retain=True) and ok
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
        if ok and self.commands_enabled():
            try:
                self.ensure_subscriptions()
            except Exception as exc:
                self.last_error = str(exc)
        return {
            "ok": ok,
            "error": self.last_error,
            "connected": self.is_connected(),
            "topic": self.base() + "/test"
        }

    def _set_auto(self, cfg, channel_id, enabled):
        for ch in cfg.get("channels", []):
            if int(ch.get("id", 0)) == int(channel_id):
                ch["auto_mode"] = bool(enabled)
                return True
        return False

    def _handle_command(self, topic, payload, irrigation, hardware_manager):
        base = self.base()
        p = str(payload or "").strip().upper()
        self.last_command_topic = topic
        self.last_command_payload = p

        if topic == base + "/system/command/stop" and p in ("STOP", "ON", "1", "TRUE"):
            irrigation.request_stop()
            self.publish("system/command/result", "STOPPED", retain=False)
            self.last_command_result = "Alle Pumpen gestoppt"
            return True

        if topic == base + "/system/command/discovery" and p in ("DISCOVERY", "ON", "1", "TRUE"):
            self.discovery(hardware_manager.status())
            self.last_command_result = "Discovery gesendet"
            return True

        if topic == base + "/system/command/mqtt_interval":
            try:
                seconds = max(5, min(3600, int(p)))
            except Exception:
                self.last_command_result = "Ungültiges MQTT-Intervall"
                return False
            self.cfg.setdefault("mqtt", {})["publish_interval_seconds"] = seconds
            try:
                from config import save_config
                save_config(self.cfg)
            except Exception:
                pass
            self.publish("system/mqtt_interval", seconds, retain=True)
            self.last_command_result = "MQTT Updateintervall {}s".format(seconds)
            return True

        marker = base + "/channel/"
        if not topic.startswith(marker):
            return False
        rest = topic[len(marker):].split("/")
        if len(rest) < 3 or rest[1] != "command":
            return False
        cid = int(rest[0])
        cmd = rest[2]

        if cmd == "auto":
            if p in ("ON", "1", "TRUE", "AUTO"):
                self._set_auto(self.cfg, cid, True)
                self.publish("channel/{}/auto/state".format(cid), "ON", retain=True)
                self.last_command_result = "Auto Kanal {} EIN".format(cid)
            elif p in ("OFF", "0", "FALSE"):
                self._set_auto(self.cfg, cid, False)
                self.publish("channel/{}/auto/state".format(cid), "OFF", retain=True)
                self.last_command_result = "Auto Kanal {} AUS".format(cid)
            else:
                return False
            try:
                from config import save_config
                save_config(self.cfg)
            except Exception:
                pass
            return True

        if cmd == "pump":
            if p == "ON":
                seconds = int(self.cfg.get("channels", [{}])[cid].get("duration", 5))
                if asyncio:
                    asyncio.create_task(irrigation.run_pump_for(cid, seconds, "mqtt"))
                self.last_command_result = "Pumpe Kanal {} {}s".format(cid, seconds)
                return True
            if p == "OFF":
                irrigation.request_stop(cid)
                self.last_command_result = "Pumpe Kanal {} AUS".format(cid)
                return True
            if p.startswith("RUN:"):
                seconds = int(p.split(":", 1)[1])
                if asyncio:
                    asyncio.create_task(irrigation.run_pump_for(cid, seconds, "mqtt"))
                self.last_command_result = "Pumpe Kanal {} RUN:{}".format(cid, seconds)
                return True

        if cmd == "run":
            seconds = int(p)
            if asyncio:
                asyncio.create_task(irrigation.run_pump_for(cid, seconds, "mqtt"))
            self.last_command_result = "Pumpe Kanal {} RUN:{}".format(cid, seconds)
            return True
        return False

    def poll_commands(self, irrigation, hardware_manager):
        if not self.commands_enabled():
            return False
        now_ms = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
        try:
            interval = max(250, int(self.cfg.get("mqtt", {}).get("command_poll_interval_ms", 500)))
        except Exception:
            interval = 500
        try:
            diff = time.ticks_diff(now_ms, self.last_command_poll) if hasattr(time, "ticks_diff") else now_ms - self.last_command_poll
            if diff < interval:
                return False
            self.last_command_poll = now_ms
            self.ensure_subscriptions()
            msg = self.client.check_msg() if self.client else None
            if not msg:
                return False
            topic, payload = msg
            return self._handle_command(topic, payload, irrigation, hardware_manager)
        except Exception as exc:
            self.last_error = str(exc)
            try:
                if self.client:
                    self.client.close()
            except Exception:
                pass
            self.client = None
            self.subscriptions_done = False
            print("MQTT Command Fehler:", exc)
            return False

    def status(self):
        m = self.cfg.get("mqtt", {})
        return {
            "enabled": self.enabled(),
            "host": m.get("host", ""),
            "port": m.get("port", 1883),
            "base_topic": self.base(),
            "publish_interval_seconds": int(m.get("publish_interval_seconds", 60)),
            "commands_enabled": bool(m.get("commands_enabled", True)),
            "command_poll_interval_ms": int(m.get("command_poll_interval_ms", 500)),
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
            "last_payload": self.last_payload,
            "subscriptions_done": self.subscriptions_done,
            "last_command_topic": self.last_command_topic,
            "last_command_payload": self.last_command_payload,
            "last_command_result": self.last_command_result,
            "telegram_mode": "Home Assistant MQTT Proxy"
        }
