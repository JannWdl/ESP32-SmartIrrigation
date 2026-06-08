"""
hardware.py - Multi-Kanal Hardware.
Pumpe wird beim Initialisieren sofort AUS gesetzt.
"""
import time
from machine import Pin, ADC

class ChannelHardware:
    def __init__(self, ch_cfg):
        self.cfg = ch_cfg
        self.id = int(ch_cfg.get("id", 0))
        self.sensor_pin_no = int(ch_cfg.get("sensor_pin", 34))
        self.pump_pin_no = int(ch_cfg.get("pump_pin", 27))
        self.active_low = bool(ch_cfg.get("pump_active_low", False))
        self._pump_state = False

        self.sensor = ADC(Pin(self.sensor_pin_no))
        try:
            self.sensor.atten(ADC.ATTN_11DB)
        except Exception:
            pass
        try:
            self.sensor.width(ADC.WIDTH_12BIT)
        except Exception:
            pass

        self.pump = Pin(self.pump_pin_no, Pin.OUT)
        self.pump_off()

    def _level(self, state):
        if self.active_low:
            return 0 if state else 1
        return 1 if state else 0

    def set_pump(self, state):
        self._pump_state = bool(state)
        self.pump.value(self._level(self._pump_state))
        return self._pump_state

    def pump_on(self):
        return self.set_pump(True)

    def pump_off(self):
        return self.set_pump(False)

    def read_raw(self, samples=4):
        total = 0
        samples = max(1, int(samples))
        for _ in range(samples):
            total += self.sensor.read()
            time.sleep_ms(15)
        return int(total / samples)

    def moisture_percent(self, raw=None):
        if raw is None:
            raw = self.read_raw()
        dry = int(self.cfg.get("dry_adc", 3500))
        wet = int(self.cfg.get("wet_adc", 1500))
        if dry == wet:
            return 0
        pct = (dry - raw) * 100 / (dry - wet)
        if pct < 0:
            pct = 0
        if pct > 100:
            pct = 100
        return int(pct)

    def status(self):
        raw = self.read_raw()
        return {
            "id": self.id,
            "name": self.cfg.get("name", "Kanal"),
            "enabled": bool(self.cfg.get("enabled", True)),
            "sensor_pin": self.sensor_pin_no,
            "pump_pin": self.pump_pin_no,
            "pump_active_low": self.active_low,
            "raw_adc": raw,
            "moisture": self.moisture_percent(raw),
            "pump": self._pump_state
        }

class HardwareManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.channels = []
        pins_seen = set()
        for ch in cfg.get("channels", []):
            if not ch.get("enabled", True):
                continue
            pump_pin = int(ch.get("pump_pin", 27))
            sensor_pin = int(ch.get("sensor_pin", 34))
            key = (pump_pin, sensor_pin)
            if key in pins_seen:
                print("WARN: doppelte Pins bei Kanal", ch.get("id"))
            pins_seen.add(key)
            try:
                self.channels.append(ChannelHardware(ch))
            except Exception as exc:
                print("Hardware init Fehler Kanal", ch.get("id"), exc)
        self.all_pumps_off()

    def all_pumps_off(self):
        for c in self.channels:
            try:
                c.pump_off()
            except Exception:
                pass

    def get(self, channel_id=0):
        cid = int(channel_id)
        for c in self.channels:
            if c.id == cid:
                return c
        if self.channels:
            return self.channels[0]
        raise RuntimeError("Kein aktiver Kanal vorhanden")

    def status(self):
        return [c.status() for c in self.channels]
