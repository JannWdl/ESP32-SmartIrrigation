import os
import json
import machine

class GitHubOTA:
    def __init__(self, cfg, hardware_manager=None):
        self.cfg = cfg
        self.hwman = hardware_manager

    def raw_url(self, path):
        o = self.cfg.get("ota", {})
        return "https://raw.githubusercontent.com/{}/{}/{}".format(
            o.get("github_repo", "JannWdl/ESP32-Bodenfeuchtigkeit-HA"),
            o.get("branch", "main"),
            path.lstrip("/")
        )

    def fetch_text(self, path):
        import urequests as requests
        r = requests.get(self.raw_url(path))
        text = r.text
        r.close()
        return text

    def check_version(self):
        remote = json.loads(self.fetch_text("ota/version.json"))
        return {"ok": True, "local": self.cfg.get("system", {}).get("version", "0.0.0"), "remote": remote.get("version"), "raw": remote}

    def update_from_github(self):
        if self.hwman:
            self.hwman.all_pumps_off()
        manifest = json.loads(self.fetch_text("ota/manifest.json"))
        files = manifest.get("files", [])
        base = self.cfg.get("ota", {}).get("base_path", "src").strip("/")
        updated = []
        for name in files:
            if name == "config.json":
                continue
            content = self.fetch_text(base + "/" + name)
            tmp = "/" + name + ".new"
            final = "/" + name
            with open(tmp, "w") as f:
                f.write(content)
            try:
                os.remove(final)
            except Exception:
                pass
            os.rename(tmp, final)
            updated.append(name)
        return {"ok": True, "updated": updated, "version": manifest.get("version")}

    def reboot(self):
        machine.reset()
