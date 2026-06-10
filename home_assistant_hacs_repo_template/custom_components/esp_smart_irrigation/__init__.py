from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.components import mqtt

from .const import (
    CONF_BASE_TOPIC,
    DEFAULT_BASE_TOPIC,
    DOMAIN,
    SERVICE_AUTO_OFF,
    SERVICE_AUTO_ON,
    SERVICE_EMERGENCY_STOP,
    SERVICE_PUMP_OFF,
    SERVICE_PUMP_ON,
    SERVICE_PUMP_RUN,
    SERVICE_REDISCOVERY,
    SERVICE_SET_MQTT_INTERVAL,
)

PLATFORMS: list[str] = []

SERVICE_RUN_SCHEMA = vol.Schema({
    vol.Optional("seconds", default=10): vol.All(vol.Coerce(int), vol.Range(min=1, max=3600)),
    vol.Optional("channel", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=15)),
})

SERVICE_CHANNEL_SCHEMA = vol.Schema({
    vol.Optional("channel", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=15)),
})

SERVICE_INTERVAL_SCHEMA = vol.Schema({
    vol.Required("seconds"): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
})


def _get_base_topic(hass: HomeAssistant) -> str:
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return DEFAULT_BASE_TOPIC
    entry = entries[0]
    return entry.options.get(CONF_BASE_TOPIC, entry.data.get(CONF_BASE_TOPIC, DEFAULT_BASE_TOPIC)).strip().strip("/")


async def _publish(hass: HomeAssistant, topic: str, payload: str) -> None:
    # qos und retain bewusst explizit setzen, da None laut HA-Developer-Blog ab 2027.6 nicht mehr fallbacken soll.
    await mqtt.async_publish(hass, topic, payload, qos=0, retain=False)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data

    if not hass.services.has_service(DOMAIN, SERVICE_PUMP_ON):
        async def pump_on(call: ServiceCall) -> None:
            base = _get_base_topic(hass)
            channel = int(call.data.get("channel", 0))
            await _publish(hass, f"{base}/channel/{channel}/command/pump", "ON")

        async def pump_off(call: ServiceCall) -> None:
            base = _get_base_topic(hass)
            channel = int(call.data.get("channel", 0))
            await _publish(hass, f"{base}/channel/{channel}/command/pump", "OFF")

        async def pump_run(call: ServiceCall) -> None:
            seconds = int(call.data.get("seconds", 10))
            channel = int(call.data.get("channel", 0))
            base = _get_base_topic(hass)
            await _publish(hass, f"{base}/channel/{channel}/command/pump", f"RUN:{seconds}")

        async def auto_on(call: ServiceCall) -> None:
            base = _get_base_topic(hass)
            channel = int(call.data.get("channel", 0))
            await _publish(hass, f"{base}/channel/{channel}/command/auto", "ON")

        async def auto_off(call: ServiceCall) -> None:
            base = _get_base_topic(hass)
            channel = int(call.data.get("channel", 0))
            await _publish(hass, f"{base}/channel/{channel}/command/auto", "OFF")

        async def emergency_stop(call: ServiceCall) -> None:
            base = _get_base_topic(hass)
            await _publish(hass, f"{base}/system/command/stop", "STOP")

        async def rediscovery(call: ServiceCall) -> None:
            base = _get_base_topic(hass)
            await _publish(hass, f"{base}/system/command/discovery", "DISCOVERY")

        async def set_mqtt_interval(call: ServiceCall) -> None:
            base = _get_base_topic(hass)
            seconds = int(call.data.get("seconds"))
            await _publish(hass, f"{base}/system/command/mqtt_interval", str(seconds))

        hass.services.async_register(DOMAIN, SERVICE_PUMP_ON, pump_on, schema=SERVICE_CHANNEL_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_PUMP_OFF, pump_off, schema=SERVICE_CHANNEL_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_PUMP_RUN, pump_run, schema=SERVICE_RUN_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_AUTO_ON, auto_on, schema=SERVICE_CHANNEL_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_AUTO_OFF, auto_off, schema=SERVICE_CHANNEL_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_EMERGENCY_STOP, emergency_stop)
        hass.services.async_register(DOMAIN, SERVICE_REDISCOVERY, rediscovery)
        hass.services.async_register(DOMAIN, SERVICE_SET_MQTT_INTERVAL, set_mqtt_interval, schema=SERVICE_INTERVAL_SCHEMA)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
