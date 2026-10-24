"""
hardware.py - Multi-Kanal Hardware.
Pumpe wird beim Initialisieren sofort AUS gesetzt.
"""
import time
from machine import Pin, ADC

try:
    from machine import time_pulse_us
except Exception:
    time_pulse_us = None

try:
    import dht
except Exception:
    dht = None

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
        self.environment = EnvironmentSensor(cfg.get("environment", {}))
        self.water_level = WaterLevelSensor(cfg.get("water_level", {}))
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

    def environment_status(self):
        return self.environment.status()

    def water_level_status(self):
        return self.water_level.status()

class EnvironmentSensor:
    def __init__(self, cfg):
        self.cfg = cfg
        self.enabled = bool(cfg.get("enabled", False))
        self.sensor_type = str(cfg.get("type", "DHT11")).upper()
        self.pin_no = int(cfg.get("pin", 33))
        self.interval = max(2, int(cfg.get("read_interval_seconds", 20)))
        self.sensor = None
        self.last_read = 0
        self.temperature = None
        self.humidity = None
        self.error = ""
        if self.enabled and dht:
            try:
                cls = dht.DHT22 if self.sensor_type == "DHT22" else dht.DHT11
                self.sensor = cls(Pin(self.pin_no))
            except Exception as exc:
                self.error = str(exc)

    def read(self, force=False):
        if not self.enabled:
            return False
        if not dht:
            self.error = "dht Modul fehlt"
            return False
        now = time.time()
        if not force and self.last_read and now - self.last_read < self.interval:
            return True
        try:
            if self.sensor is None:
                cls = dht.DHT22 if self.sensor_type == "DHT22" else dht.DHT11
                self.sensor = cls(Pin(self.pin_no))
            self.sensor.measure()
            self.temperature = self.sensor.temperature()
            self.humidity = self.sensor.humidity()
            self.last_read = now
            self.error = ""
            return True
        except Exception as exc:
            self.error = str(exc)
            self.last_read = now
            return False

    def status(self):
        self.read()
        return {
            "enabled": self.enabled,
            "type": self.sensor_type,
            "pin": self.pin_no,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "last_read": self.last_read,
            "error": self.error
        }

class WaterLevelSensor:
    def __init__(self, cfg):
        self.cfg = cfg
        self.enabled = bool(cfg.get("enabled", False))
        self.sensor_type = str(cfg.get("type", "HC-SR04"))
        self.trigger_pin_no = int(cfg.get("trigger_pin", 25))
        self.echo_pin_no = int(cfg.get("echo_pin", 26))
        self.empty_distance_cm = float(cfg.get("empty_distance_cm", 30))
        self.full_distance_cm = float(cfg.get("full_distance_cm", 5))
        self.interval = max(2, int(cfg.get("read_interval_seconds", 10)))
        self.trigger = None
        self.echo = None
        self.last_read = 0
        self.distance_cm = None
        self.level_percent = None
        self.error = ""
        if self.enabled:
            try:
                self.trigger = Pin(self.trigger_pin_no, Pin.OUT)
                self.echo = Pin(self.echo_pin_no, Pin.IN)
                self.trigger.value(0)
            except Exception as exc:
                self.error = str(exc)

    def _percent(self, distance):
        empty = self.empty_distance_cm
        full = self.full_distance_cm
        if empty == full:
            return None
        pct = (empty - distance) * 100 / (empty - full)
        if pct < 0:
            pct = 0
        if pct > 100:
            pct = 100
        return int(pct)

    def read(self, force=False):
        if not self.enabled:
            return False
        if time_pulse_us is None:
            self.error = "time_pulse_us fehlt"
            return False
        now = time.time()
        if not force and self.last_read and now - self.last_read < self.interval:
            return True
        try:
            if self.trigger is None or self.echo is None:
                self.trigger = Pin(self.trigger_pin_no, Pin.OUT)
                self.echo = Pin(self.echo_pin_no, Pin.IN)
            self.trigger.value(0)
            time.sleep_us(2)
            self.trigger.value(1)
            time.sleep_us(10)
            self.trigger.value(0)
            pulse = time_pulse_us(self.echo, 1, 30000)
            if pulse < 0:
                raise RuntimeError("Echo Timeout")
            distance = (pulse / 2) / 29.1
            self.distance_cm = round(distance, 1)
            self.level_percent = self._percent(distance)
            self.last_read = now
            self.error = ""
            return True
        except Exception as exc:
            self.error = str(exc)
            self.last_read = now
            return False

    def status(self):
        self.read()
        return {
            "enabled": self.enabled,
            "type": self.sensor_type,
            "trigger_pin": self.trigger_pin_no,
            "echo_pin": self.echo_pin_no,
            "distance_cm": self.distance_cm,
            "level_percent": self.level_percent,
            "empty_distance_cm": self.empty_distance_cm,
            "full_distance_cm": self.full_distance_cm,
            "last_read": self.last_read,
            "error": self.error
        }
