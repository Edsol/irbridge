from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_PROTOCOL,
    CONF_SENDER,
    CONF_TEXT_ENTITY_ID,
    CONF_INFRARED_ENTITY_ID,
    SENDER_MQTT_TUYA,
    SENDER_INFRARED_ENTITY,
    SENDERS,
)
from .generators import available_protocols

_PROTOCOL_OPTIONS = [{"value": p, "label": p.capitalize()} for p in available_protocols()]
_SENDER_OPTIONS = [
    {"value": SENDER_MQTT_TUYA, "label": "MQTT Tuya (Zigbee2MQTT)"},
    {"value": SENDER_INFRARED_ENTITY, "label": "Infrared Entity (ESPHome)"},
]


class IRBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}

    @staticmethod
    def async_get_options_flow(config_entry):
        return IRBridgeOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            if user_input[CONF_SENDER] == SENDER_MQTT_TUYA:
                return await self.async_step_mqtt()
            return await self.async_step_infrared()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("title"): str,
                vol.Required(CONF_PROTOCOL): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=_PROTOCOL_OPTIONS)
                ),
                vol.Required(CONF_SENDER): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=_SENDER_OPTIONS)
                ),
            }),
        )

    async def async_step_mqtt(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=self._data["title"], data=self._data)

        return self.async_show_form(
            step_id="mqtt",
            data_schema=vol.Schema({
                vol.Required(CONF_TEXT_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="text")
                ),
            }),
        )

    async def async_step_infrared(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title=self._data["title"], data=self._data)

        return self.async_show_form(
            step_id="infrared",
            data_schema=vol.Schema({
                vol.Required(CONF_INFRARED_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="infrared")
                ),
            }),
        )


class IRBridgeOptionsFlow(config_entries.OptionsFlow):
    """Allows reconfiguring protocol, sender and blaster after setup."""

    def __init__(self, config_entry) -> None:
        self._entry = config_entry
        self._data: dict = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            if user_input[CONF_SENDER] == SENDER_MQTT_TUYA:
                return await self.async_step_mqtt()
            return await self.async_step_infrared()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_PROTOCOL, default=self._data.get(CONF_PROTOCOL)): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=_PROTOCOL_OPTIONS)
                ),
                vol.Required(CONF_SENDER, default=self._data.get(CONF_SENDER)): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=_SENDER_OPTIONS)
                ),
            }),
        )

    async def async_step_mqtt(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            self.hass.config_entries.async_update_entry(self._entry, data=self._data)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="mqtt",
            data_schema=vol.Schema({
                vol.Required(CONF_TEXT_ENTITY_ID, default=self._data.get(CONF_TEXT_ENTITY_ID)): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="text")
                ),
            }),
        )

    async def async_step_infrared(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            self.hass.config_entries.async_update_entry(self._entry, data=self._data)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="infrared",
            data_schema=vol.Schema({
                vol.Required(CONF_INFRARED_ENTITY_ID, default=self._data.get(CONF_INFRARED_ENTITY_ID)): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="infrared")
                ),
            }),
        )
