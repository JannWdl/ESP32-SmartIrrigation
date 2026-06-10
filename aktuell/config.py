"""
config.py - zentrale Config.
v2.6: Multi-Kanal mit max_pump_seconds, cooldown_minutes, Auto pro Kanal,
Telegram Commands und MQTT Home Assistant Discovery.
"""
from storage import read_json, write_json, deep_merge, CONFIG_PATH

DEFAULT_CONFIG = {
    "system": {
        "name": "Smart Irrigation",
        "version": "3.8.0",
        "setup_done": False,
        "ui_theme": "dark"
    },
    "wifi": {"ssid": "", "password": "", "hostname": "smart-irrigation", "fallback_ap_on_fail": True, "connect_attempts": 3, "connect_timeout_seconds": 20, "setup_ap_ssid": "Irrigation-Setup", "setup_ap_password": "", "setup_ap_open": True, "setup_ap_channel": 1},
    "channels": [
        {
            "id": 0,
            "name": "Kanal 1",
            "enabled": True,
            "manual_allowed": True,
            "sensor_pin": 34,
            "pump_pin": 27,
            "pump_active_low": False,
            "dry_adc": 3500,
            "wet_adc": 1500,
            "threshold": 40,
            "duration": 5,
            "max_pump_seconds": 30,
            "cooldown_minutes": 60,
            "auto_mode": False,
            "min_interval_minutes": 60,
            "last_watered": 0,
            "total_waterings": 0
        }
    ],
    "mqtt": {
        "enabled": False,
        "host": "",
        "port": 1883,
        "username": "",
        "password": "",
        "client_id": "smart-irrigation-esp32",
        "base_topic": "smart_irrigation",
        "publish_interval_seconds": 60,
        "commands_enabled": True,
        "command_poll_interval_ms": 500,
        "homeassistant_discovery": True,
        "discovery_prefix": "homeassistant"
    },
    "ota": {
        "enabled": True,
        "github_repo": "JannWdl/ESP32-Bodenfeuchtigkeit-HA",
        "branch": "main",
        "base_path": "src"
    },
    "safety": {
        "notify_on_manual_pump": False,
        "notify_on_auto_pump": True,
        "mqtt_publish_while_pump_running": False,
        "pump_start_delay_ms": 150,
        "pump_max_manual_seconds": 30
    }
}

_cache = None

def _migrate(cfg):
    if isinstance(cfg, dict) and "channel" in cfg and "channels" not in cfg:
        ch = cfg.get("channel", {})
        ch["id"] = 0
        ch.setdefault("enabled", True)
        cfg["channels"] = [ch]
    if isinstance(cfg, dict):
        cfg.pop("channel", None)
    if not cfg.get("channels"):
        cfg["channels"] = DEFAULT_CONFIG["channels"]

    for i, ch in enumerate(cfg["channels"]):
        ch.setdefault("id", i)
        ch.setdefault("name", "Kanal {}".format(i + 1))
        ch.setdefault("enabled", True)
        ch.setdefault("manual_allowed", True)
        ch.setdefault("sensor_pin", 34)
        ch.setdefault("pump_pin", 27)
        ch.setdefault("pump_active_low", False)
        ch.setdefault("dry_adc", 3500)
        ch.setdefault("wet_adc", 1500)
        ch.setdefault("threshold", 40)
        ch.setdefault("duration", 5)
        ch.setdefault("max_pump_seconds", 30)
        ch.setdefault("cooldown_minutes", ch.get("min_interval_minutes", 60))
        ch.setdefault("min_interval_minutes", ch.get("cooldown_minutes", 60))
        ch.setdefault("auto_mode", False)
        ch.setdefault("last_watered", 0)
        ch.setdefault("total_waterings", 0)

    cfg.setdefault("mqtt", {})
    cfg["mqtt"].setdefault("homeassistant_discovery", True)
    cfg["mqtt"].setdefault("discovery_prefix", "homeassistant")
    cfg["mqtt"].setdefault("publish_interval_seconds", 60)
    cfg["mqtt"].setdefault("commands_enabled", True)
    cfg["mqtt"].setdefault("command_poll_interval_ms", 500)
    try:
        cfg["mqtt"]["publish_interval_seconds"] = max(5, int(cfg["mqtt"].get("publish_interval_seconds", 60)))
    except Exception:
        cfg["mqtt"]["publish_interval_seconds"] = 60
    try:
        cfg["mqtt"]["command_poll_interval_ms"] = max(250, int(cfg["mqtt"].get("command_poll_interval_ms", 500)))
    except Exception:
        cfg["mqtt"]["command_poll_interval_ms"] = 500

    # Telegram Direct läuft absichtlich nicht mehr auf dem ESP32.
    # Steuerung/Benachrichtigung soll über Home Assistant + MQTT erfolgen.
    cfg.setdefault("telegram", {})
    cfg["telegram"] = {
        "mode": "home_assistant_mqtt_proxy",
        "direct_on_esp32": False,
        "enabled_on_esp32": False
    }
    cfg.setdefault("safety", DEFAULT_CONFIG["safety"])
    return cfg

def get_config(reload=False):
    global _cache
    if _cache is None or reload:
        loaded = read_json(CONFIG_PATH, {})
        if loaded is None:
            loaded = {}
        loaded = _migrate(loaded)
        _cache = deep_merge(DEFAULT_CONFIG, loaded)
        _cache["system"]["version"] = DEFAULT_CONFIG["system"]["version"]
        save_config(_cache)
    return _cache

def save_config(cfg=None):
    global _cache
    if cfg is None:
        cfg = _cache or DEFAULT_CONFIG
    cfg = _migrate(cfg)
    _cache = deep_merge(DEFAULT_CONFIG, cfg)
    return write_json(CONFIG_PATH, _cache)

def get_channel(cfg, channel_id=0):
    for ch in cfg.get("channels", []):
        if int(ch.get("id", 0)) == int(channel_id):
            return ch
    return cfg["channels"][0]
