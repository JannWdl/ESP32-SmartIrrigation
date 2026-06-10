import gc
import machine
import uasyncio as asyncio
try:
    import ujson as json
except ImportError:
    import json

import config
import history
import ota
import serial_log

MIME = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
}


class WebApp:
    def __init__(self, cfg, channels, pump_manager):
        self.cfg = cfg
        self.channels = channels
        self.pm = pump_manager

    async def start(self, port=80):
        return await asyncio.start_server(self.handle, "0.0.0.0", port)

    async def handle(self, r, w):
        try:
            line = await r.readline()
            if not line:
                await w.aclose()
                return
            parts = line.decode().split()
            method, path = parts[0], parts[1]
            serial_log.log("HTTP %s %s" % (method, path))
            headers = {}
            while True:
                h = await r.readline()
                if h == b"\r\n" or not h:
                    break
                k, v = h.decode().split(":", 1)
                headers[k.lower()] = v.strip()
            if path == "/" or path.startswith("/index.html"):
                await self.file(w, "index.html")
            elif path == "/api/status":
                await self.json(w, self.status())
            elif path == "/api/config":
                if method == "GET":
                    await self.json(w, config.public(self.cfg))
                else:
                    await self.update_config(r, w, headers)
            elif path == "/api/water":
                await self.water(r, w, headers)
            elif path == "/api/stop":
                self.pm.stop_all()
                await self.json(w, {"ok": True})
            elif path == "/api/logs":
                await self.json(w, {"items": history.recent()})
            elif path == "/api/ota":
                await self.upload(r, w, headers)
            elif path == "/api/github":
                await self.github(w)
            elif path == "/api/revert":
                await self.revert(r, w, headers)
            elif path == "/api/reboot":
                await self.json(w, {"ok": True})
                machine.reset()
            else:
                await self.not_found(w)
        except Exception as e:
            try:
                await self.json(w, {"ok": False, "error": str(e)}, 500)
            except Exception:
                pass
        gc.collect()

    def status(self):
        return {
            "running": self.pm.current,
            "queue": len(self.pm.queue),
            "channels": [c.status() for c in self.channels],
        }

    async def json(self, w, obj, code=200):
        data = json.dumps(obj)
        await w.awrite("HTTP/1.0 %d OK\r\nContent-Type: application/json\r\nCache-Control: no-store\r\n\r\n" % code)
        await w.awrite(data)
        await w.aclose()

    async def file(self, w, path):
        await w.awrite("HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
        with open(path, "rb") as f:
            while True:
                b = f.read(512)
                if not b:
                    break
                await w.awrite(b)
                await asyncio.sleep_ms(0)
        await w.aclose()

    async def not_found(self, w):
        await w.awrite("HTTP/1.0 404 Not Found\r\n\r\nnot found")
        await w.aclose()

    async def _body(self, r, headers, max_len=4096):
        ln = int(headers.get("content-length", "0"))
        if ln > max_len:
            raise ValueError("body zu gross")
        return await r.read(ln)

    async def update_config(self, r, w, headers):
        data = json.loads((await self._body(r, headers)).decode())
        serial_log.log("Konfiguration speichern")
        for k in ("wifi", "telegram", "mqtt", "github", "ap"):
            if k in data:
                self.cfg[k].update(data[k])
        if "channels" in data:
            self.cfg["channels"] = data["channels"][:config.MAX_CHANNELS]
            for i, ch in enumerate(self.channels):
                ch.cfg.update(self.cfg["channels"][i])
        config.save(self.cfg)
        serial_log.log("Konfiguration gespeichert")
        await self.json(w, {"ok": True})

    async def water(self, r, w, headers):
        data = json.loads((await self._body(r, headers)).decode() or "{}")
        ok = self.pm.request(int(data.get("channel", 0)), data.get("seconds"))
        await self.json(w, {"ok": ok})

    async def upload(self, r, w, headers):
        path = headers.get("x-filename", "main.py").replace("/", "")
        length = int(headers.get("content-length", "0"))

        async def rd(n):
            return await r.read(n)

        tmp = path + ".new"
        done = 0
        with open(tmp, "wb") as f:
            while done < length:
                b = await rd(min(512, length - done))
                if not b:
                    break
                f.write(b)
                done += len(b)
                await asyncio.sleep_ms(0)
        ota._backup(path)
        import os
        os.rename(tmp, path)
        serial_log.log("OTA Upload %s %d Bytes" % (path, done))
        await self.json(w, {"ok": True, "bytes": done, "file": path})

    async def github(self, w):
        url = self.cfg.get("github", {}).get("raw_url", "")
        try:
            n = ota.github_download(url, "main.py")
            await self.json(w, {"ok": True, "bytes": n})
        except Exception as e:
            await self.json(w, {"ok": False, "error": str(e)}, 500)

    async def revert(self, r, w, headers):
        data = json.loads((await self._body(r, headers)).decode() or "{}")
        path = data.get("file", "main.py").replace("/", "")
        try:
            ota.revert(path)
            await self.json(w, {"ok": True, "file": path})
        except Exception as e:
            await self.json(w, {"ok": False, "error": str(e)}, 500)
