from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import CONF_INFRARED_ENTITY_ID, CONF_PROTOCOL, DOMAIN
from .generators import available_protocols

_PROTOCOL_OPTIONS = [
    {"value": p, "label": p.capitalize()} for p in available_protocols()
]


def _infrared_platform_available(hass) -> bool:
    """True when this core ships the ``infrared`` platform.

    Checked before showing the emitter picker: on an older core the domain
    holds no entities and the selector would come up empty with nothing to
    explain why.
    """
    try:
        import homeassistant.components.infrared  # noqa: F401
    except ImportError:
        return False
    return True


def _emitter_schema(default: str | None = None) -> vol.Schema:
    """Schema for the emitter picker, optionally pre-filled."""
    key = (
        vol.Required(CONF_INFRARED_ENTITY_ID, default=default)
        if default
        else vol.Required(CONF_INFRARED_ENTITY_ID)
    )
    return vol.Schema({
        key: selector.EntitySelector(
            selector.EntitySelectorConfig(domain="infrared")
        ),
    })


class IRBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict = {}

    @staticmethod
    def async_get_options_flow(config_entry):
        return IRBridgeOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        if not _infrared_platform_available(self.hass):
            return self.async_abort(reason="infrared_unavailable")

        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title=self._data["title"], data=self._data
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("title"): str,
                vol.Required(CONF_PROTOCOL): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=_PROTOCOL_OPTIONS)
                ),
                vol.Required(CONF_INFRARED_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="infrared")
                ),
            }),
        )


class IRBridgeOptionsFlow(config_entries.OptionsFlow):
    """Allows reconfiguring protocol and emitter after setup."""

    def __init__(self, config_entry) -> None:
        self._entry = config_entry
        self._data: dict = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            self.hass.config_entries.async_update_entry(
                self._entry, data=self._data
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_PROTOCOL, default=self._data.get(CONF_PROTOCOL)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=_PROTOCOL_OPTIONS)
                ),
                vol.Required(
                    CONF_INFRARED_ENTITY_ID,
                    default=self._data.get(CONF_INFRARED_ENTITY_ID),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="infrared")
                ),
            }),
        )
