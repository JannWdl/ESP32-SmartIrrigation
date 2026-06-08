import json
import gc
import socket
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

from config import save_config

INDEX_PATH = "/index.html"
CHUNK = 512

class WebServer:
    def __init__(self, cfg, hwman, irrigation, telegram=None, mqtt=None, ota=None, ip=""):
        self.cfg = cfg
        self.hwman = hwman
        self.irrigation = irrigation
        self.mqtt = mqtt
        self.ota = ota
        self.ip = ip
        self.sock = None

    def start(self, port=80):
        self.close()
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        s.listen(2)
        s.settimeout(0.05)
        self.sock = s
        print("Webserver läuft auf Port", port)

    def close(self):
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None

    async def poll(self):
        if not self.sock:
            return
        try:
            conn, addr = self.sock.accept()
        except OSError:
            return
        except Exception as exc:
            print("WEB_ACCEPT_ERROR:", exc)
            await asyncio.sleep_ms(100)
            return

        try:
            self.handle_conn(conn)
        except Exception as exc:
            if "ETIMEDOUT" in str(exc) or "[Errno 116]" in str(exc):
                print("WEB_TIMEOUT_IGNORED")
            else:
                print("WEB_HANDLE_ERROR:", exc)
        finally:
            try:
                conn.close()
            except Exception:
                pass
            gc.collect()

    def recv_request(self, conn):
        conn.settimeout(2)
        data = b""
        while b"\r\n\r\n" not in data and len(data) < 3072:
            chunk = conn.recv(384)
            if not chunk:
                break
            data += chunk
        if not data:
            return None, {}, b""
        if b"\r\n\r\n" in data:
            header, body = data.split(b"\r\n\r\n", 1)
        else:
            header, body = data, b""
        txt = header.decode("utf-8", "ignore")
        first = txt.split("\r\n", 1)[0]
        headers = {}
        for line in txt.split("\r\n")[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.lower()] = v.strip()
        length = int(headers.get("content-length", "0") or "0")
        while len(body) < length:
            try:
                chunk = conn.recv(min(384, length - len(body)))
                if not chunk:
                    break
                body += chunk
            except OSError as exc:
                print("WEB_RECV_TIMEOUT_OR_ERROR:", exc)
                break
        return first, headers, body

    def send(self, conn, body, ctype="application/json", status="200 OK"):
        if not isinstance(body, bytes):
            body = body.encode("utf-8")
        hdr = "HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n".format(status, ctype, len(body))
        conn.sendall(hdr.encode("utf-8"))
        conn.sendall(body)

    def send_file(self, conn, path, ctype="text/html; charset=utf-8"):
        try:
            try:
                import os
                size = os.stat(path)[6]
            except Exception:
                size = 0
            if size:
                hdr = "HTTP/1.1 200 OK\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n".format(ctype, size)
            else:
                hdr = "HTTP/1.1 200 OK\r\nContent-Type: {}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n".format(ctype)
            conn.sendall(hdr.encode("utf-8"))
            with open(path, "rb") as f:
                while True:
                    b = f.read(CHUNK)
                    if not b:
                        break
                    conn.sendall(b)
            gc.collect()
        except Exception as exc:
            self.send(conn, "index.html fehlt: {}".format(exc), "text/plain", "500 Internal Server Error")

    def body_json(self, body):
        try:
            return json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            return {}

    def heap(self):
        gc.collect()
        try:
            return gc.mem_free()
        except Exception:
            return -1

    def status(self):
        return {
            "ok": True,
            "ip": self.ip,
            "version": self.cfg.get("system", {}).get("version", ""),
            "heap": self.heap(),
            "hardware": self.hwman.status(),
            "irrigation": self.irrigation.status(),
            "mqtt": self.mqtt.status() if self.mqtt else {"enabled": False},
            "network_pause": self.irrigation.network_pause_active() if hasattr(self.irrigation, "network_pause_active") else False
        }

    def handle_conn(self, conn):
        first, headers, body = self.recv_request(conn)
        if not first:
            return
        parts = first.split()
        if len(parts) < 2:
            self.send(conn, '{"ok":false,"error":"bad request"}', status="400 Bad Request")
            return

        method = parts[0]
        path = parts[1].split("?", 1)[0]
        data = self.body_json(body)

        if method == "GET" and path == "/":
            self.send_file(conn, INDEX_PATH)
        elif method == "GET" and path == "/api/status":
            self.send(conn, json.dumps(self.status()))
        elif method == "GET" and path == "/api/heap":
            self.send(conn, json.dumps({"heap": self.heap()}))
        elif method == "GET" and path == "/api/config-full":
            self.send(conn, json.dumps(self.cfg))
        elif method == "POST" and path == "/api/setup/finish":
            if "channels" in data:
                self.cfg["channels"] = data["channels"]
            if "mqtt" in data:
                self.cfg["mqtt"].update(data["mqtt"])
            self.cfg["system"]["setup_done"] = True
            save_config(self.cfg)
            self.send(conn, '{"ok":true,"message":"Setup gespeichert"}')
        elif method == "POST" and path == "/api/config":
            for key in ("wifi", "mqtt", "ota", "system", "safety"):
                if key in data:
                    self.cfg[key].update(data[key])
            if "channels" in data:
                self.cfg["channels"] = data["channels"]
            save_config(self.cfg)
            gc.collect()
            self.send(conn, json.dumps({"ok": True, "message": "Config gespeichert", "heap": self.heap()}))
        elif method == "POST" and path == "/api/pump/run":
            cid = int(data.get("id", 0))
            seconds = int(data.get("seconds", 5))
            asyncio.create_task(self.irrigation.run_pump_for(cid, seconds, "web"))
            self.send(conn, json.dumps({"ok": True, "running": cid, "seconds": seconds}))
        elif method == "POST" and path == "/api/pump/pin-test":
            cid = int(data.get("id", 0))
            ms = int(data.get("ms", 300))
            asyncio.create_task(self.irrigation.pin_test(cid, ms))
            self.send(conn, json.dumps({"ok": True, "pin_test": cid, "ms": ms}))
        elif method == "POST" and path == "/api/pump/off":
            self.irrigation.request_stop(data.get("id", None))
            self.send(conn, '{"ok":true,"stopped":true}')
        elif method == "POST" and path == "/api/stop":
            self.irrigation.request_stop()
            self.send(conn, '{"ok":true,"stopped_all":true}')
        elif method == "POST" and path == "/api/calibrate/dry":
            cid = int(data.get("id", 0))
            hw = self.hwman.get(cid)
            raw = hw.read_raw()
            hw.cfg["dry_adc"] = raw
            save_config(self.cfg)
            self.send(conn, json.dumps({"ok": True, "id": cid, "dry_adc": raw}))
        elif method == "POST" and path == "/api/calibrate/wet":
            cid = int(data.get("id", 0))
            hw = self.hwman.get(cid)
            raw = hw.read_raw()
            hw.cfg["wet_adc"] = raw
            save_config(self.cfg)
            self.send(conn, json.dumps({"ok": True, "id": cid, "wet_adc": raw}))
        elif method == "POST" and path == "/api/mqtt/test":
            res = self.mqtt.test() if self.mqtt else {"ok": False, "error": "MQTT fehlt"}
            self.send(conn, json.dumps(res))
        elif method == "POST" and path == "/api/mqtt/discovery":
            res = self.mqtt.discovery(self.hwman.status()) if self.mqtt else False
            err = getattr(self.mqtt, "last_error", "") if self.mqtt else "MQTT fehlt"
            self.send(conn, json.dumps({"ok": bool(res), "error": err, "mqtt": self.mqtt.status() if self.mqtt else {}}))
        elif method == "POST" and path == "/api/mqtt/publish-now":
            res = self.mqtt.publish_status(self.hwman.status(), self.irrigation.status(), force=True) if self.mqtt else False
            err = getattr(self.mqtt, "last_error", "") if self.mqtt else "MQTT fehlt"
            self.send(conn, json.dumps({"ok": bool(res), "error": err, "mqtt": self.mqtt.status() if self.mqtt else {}}))
        elif method == "POST" and path == "/api/ota/check":
            res = self.ota.check_version() if self.ota else {"ok": False, "error": "OTA fehlt"}
            self.send(conn, json.dumps(res))
        else:
            self.send(conn, '{"ok":false,"error":"not found"}', status="404 Not Found")
