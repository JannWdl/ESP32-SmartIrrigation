from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_BASE_TOPIC, DEFAULT_BASE_TOPIC, DEFAULT_NAME, DOMAIN


class EspSmartIrrigationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            base_topic = user_input[CONF_BASE_TOPIC].strip().strip("/")
            if not base_topic:
                errors[CONF_BASE_TOPIC] = "base_topic_required"
            else:
                await self.async_set_unique_id(base_topic)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data={CONF_BASE_TOPIC: base_topic},
                )

        schema = vol.Schema({
            vol.Required(CONF_BASE_TOPIC, default=DEFAULT_BASE_TOPIC): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EspSmartIrrigationOptionsFlow(config_entry)


class EspSmartIrrigationOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data={
                CONF_BASE_TOPIC: user_input[CONF_BASE_TOPIC].strip().strip("/"),
            })

        current = self.config_entry.options.get(
            CONF_BASE_TOPIC,
            self.config_entry.data.get(CONF_BASE_TOPIC, DEFAULT_BASE_TOPIC),
        )
        schema = vol.Schema({
            vol.Required(CONF_BASE_TOPIC, default=current): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
