import time
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

class IrrigationController:
    def __init__(self, cfg, hardware_manager, telegram=None, mqtt=None):
        self.cfg = cfg
        self.hwman = hardware_manager
        self.telegram = None  # Telegram entfernt in v3.4
        self.mqtt = mqtt
        self.running = {}
        self.stop_requested = {}
        self.last_pump_activity = 0

    def any_running(self):
        for v in self.running.values():
            if v:
                return True
        return False

    def request_stop(self, channel_id=None):
        if channel_id is None:
            for ch in self.hwman.channels:
                self.stop_requested[ch.id] = True
            self.hwman.all_pumps_off()
        else:
            self.stop_requested[int(channel_id)] = True
            self.hwman.get(channel_id).pump_off()

    def cooldown_remaining(self, hw):
        ch = hw.cfg
        cooldown = int(ch.get("cooldown_minutes", ch.get("min_interval_minutes", 60))) * 60
        last = int(ch.get("last_watered", 0) or 0)
        if not last:
            return 0
        remain = cooldown - int(time.time() - last)
        return remain if remain > 0 else 0

    async def notify(self, text, kind="info"):
        # Telegram entfernt: nur seriell loggen.
        if kind in ("error", "auto"):
            print("EVENT:", kind, text)

    async def run_pump_for(self, channel_id=0, seconds=5, reason="manual", ignore_cooldown=False):
        cid = int(channel_id)
        hw = self.hwman.get(cid)
        ch = hw.cfg

        if not ch.get("enabled", True):
            return {"ok": False, "error": "Kanal deaktiviert"}
        if reason in ("web", "manual", "telegram") and not ch.get("manual_allowed", True):
            return {"ok": False, "error": "Manuelle Steuerung deaktiviert"}

        max_seconds = int(ch.get("max_pump_seconds", self.cfg.get("safety", {}).get("pump_max_manual_seconds", 30)))
        seconds = max(1, min(int(seconds), max_seconds))

        remain = self.cooldown_remaining(hw)
        if remain and not ignore_cooldown and reason in ("auto",):
            await self.notify("Cooldown aktiv für {}: {}s".format(ch.get("name", "Kanal"), remain), kind="cooldown")
            return {"ok": False, "error": "cooldown", "remaining": remain}

        self.stop_requested[cid] = False
        self.running[cid] = True
        notify_kind = "auto" if reason == "auto" else "manual"

        try:
            await asyncio.sleep_ms(int(self.cfg.get("safety", {}).get("pump_start_delay_ms", 150)))
            self.last_pump_activity = time.time()
            print("PUMP_START channel={} seconds={} reason={}".format(cid, seconds, reason))
            hw.pump_on()
            await self.notify("💧 {} gestartet: {}s ({})".format(ch.get("name", "Kanal"), seconds, reason), kind=notify_kind)

            start = time.time()
            while time.time() - start < seconds:
                if self.stop_requested.get(cid):
                    print("PUMP_STOP_REQUEST channel={}".format(cid))
                    break
                await asyncio.sleep(0.2)

            return {"ok": True, "id": cid, "seconds": seconds}

        except Exception as exc:
            print("PUMP_ERROR channel={} {}".format(cid, exc))
            await self.notify("⚠ Pumpenfehler {}: {}".format(ch.get("name", "Kanal"), exc), kind="error")
            return {"ok": False, "error": str(exc)}
        finally:
            try:
                hw.pump_off()
            except Exception:
                pass
            self.running[cid] = False
            ch["last_watered"] = time.time()
            ch["total_waterings"] = int(ch.get("total_waterings", 0)) + 1
            self.last_pump_activity = time.time()
            print("PUMP_END channel={}".format(cid))

    async def pin_test(self, channel_id=0, ms=300):
        cid = int(channel_id)
        hw = self.hwman.get(cid)
        ms = max(50, min(int(ms), 2000))
        print("PIN_TEST_START channel={} ms={}".format(cid, ms))
        try:
            hw.pump_on()
            await asyncio.sleep_ms(ms)
        finally:
            hw.pump_off()
            print("PIN_TEST_END channel={}".format(cid))
        return {"ok": True, "id": cid, "ms": ms}

    def should_water(self, hw):
        ch = hw.cfg
        if not ch.get("enabled", True):
            return False, "disabled"
        if not ch.get("auto_mode", False):
            return False, "auto_off"
        raw = hw.read_raw()
        moisture = hw.moisture_percent(raw)
        if moisture >= int(ch.get("threshold", 40)):
            return False, "moist_enough"
        remain = self.cooldown_remaining(hw)
        if remain:
            return False, "cooldown"
        return True, "dry"

    async def auto_loop(self):
        while True:
            try:
                for hw in self.hwman.channels:
                    should, reason = self.should_water(hw)
                    if should and not self.running.get(hw.id, False):
                        duration = int(hw.cfg.get("duration", 5))
                        await self.run_pump_for(hw.id, duration, reason="auto")
            except Exception as exc:
                print("Auto-Loop Fehler:", exc)
                self.hwman.all_pumps_off()
                await self.notify("⚠ Auto-Loop Fehler: {}".format(exc), kind="error")
            await asyncio.sleep(10)

    def network_pause_active(self):
        pause = int(self.cfg.get("safety", {}).get("network_pause_after_pump_seconds", 6))
        if not self.last_pump_activity:
            return False
        return time.time() - self.last_pump_activity < pause

    def status(self):
        out = []
        for hw in self.hwman.channels:
            should, reason = self.should_water(hw)
            out.append({
                "id": hw.id,
                "running": bool(self.running.get(hw.id, False)),
                "auto_should_water": should,
                "auto_reason": reason,
                "cooldown_remaining": self.cooldown_remaining(hw)
            })
        return out
