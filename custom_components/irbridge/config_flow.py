from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import CONF_INFRARED_ENTITY_ID, CONF_PROTOCOL, DOMAIN
from .errors import IRBridgeError
from .generators import available_protocols, get_generator
from .senders.infrared_entity import InfraredEntitySender

_LOGGER = logging.getLogger(__name__)

_PROTOCOL_OPTIONS = [
    {"value": p, "label": p.capitalize()} for p in available_protocols()
]

# What the test step sends. Cooling at 22 C is a state every supported
# protocol can express, and one whose effect is unmistakable on the unit:
# the display changes and the fan starts. Sending "off" instead would be
# ambiguous against an already-idle air conditioner.
TEST_HVAC_MODE = "cool"
TEST_TEMP = 22


def _infrared_platform_available(hass: HomeAssistant) -> bool:
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


def _setup_schema(defaults: dict | None = None) -> vol.Schema:
    """Protocol and emitter pickers, optionally pre-filled.

    Shared by the config flow and the options flow so the two can never
    drift apart.
    """
    defaults = defaults or {}

    def key(name: str) -> vol.Marker:
        if name in defaults:
            return vol.Required(name, default=defaults[name])
        return vol.Required(name)

    return vol.Schema({
        key(CONF_PROTOCOL): selector.SelectSelector(
            selector.SelectSelectorConfig(options=_PROTOCOL_OPTIONS)
        ),
        key(CONF_INFRARED_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="infrared")
        ),
    })


async def _async_send_test(hass: HomeAssistant, data: dict) -> None:
    """Transmit one command with the chosen protocol and emitter.

    Raises IRBridgeError when the emitter refuses it. A send that succeeds
    proves only that the blaster accepted the payload -- whether the air
    conditioner understood it is what the user is asked next.
    """
    generator = get_generator(data[CONF_PROTOCOL])
    sender = InfraredEntitySender(
        hass,
        data[CONF_INFRARED_ENTITY_ID],
        frequency=generator.capabilities.frequency,
    )
    caps = generator.capabilities
    raw = generator.generate(
        TEST_HVAC_MODE,
        TEST_TEMP,
        fan_mode=caps.fan_modes[0] if caps.fan_modes else "auto",
        swing_mode=caps.swing_modes[0] if caps.swing_modes else "off",
    )
    await sender.async_send_raw(raw)


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
            return await self.async_step_test()

        return self.async_show_form(
            step_id="user",
            data_schema=_setup_schema().extend({
                vol.Required("title"): str,
            }),
        )

    async def async_step_test(self, user_input=None):
        """Send a command, then ask whether the unit responded.

        This is the step that turns protocol choice from a guess into a
        check. Brand names are a poor guide -- the device this integration
        was built against is sold as Midea and speaks Gree -- so the only
        reliable answer comes from the air conditioner itself.
        """
        if user_input is not None:
            if user_input["worked"]:
                return self.async_create_entry(
                    title=self._data["title"], data=self._data
                )
            # Back to the picker, keeping what was typed so only the
            # protocol has to change.
            return self.async_show_form(
                step_id="user",
                data_schema=_setup_schema(self._data).extend({
                    vol.Required("title", default=self._data["title"]): str,
                }),
                errors={"base": "test_failed"},
            )

        try:
            await _async_send_test(self.hass, self._data)
        except IRBridgeError as err:
            _LOGGER.debug("IRBridge test send failed: %s", err)
            return self.async_show_form(
                step_id="user",
                data_schema=_setup_schema(self._data).extend({
                    vol.Required("title", default=self._data["title"]): str,
                }),
                errors={"base": "send_failed"},
                description_placeholders={"error": str(err)},
            )

        return self.async_show_form(
            step_id="test",
            data_schema=vol.Schema({
                vol.Required("worked", default=True): bool,
            }),
            description_placeholders={
                "protocol": self._data[CONF_PROTOCOL].capitalize(),
                "temp": str(TEST_TEMP),
            },
        )


class IRBridgeOptionsFlow(config_entries.OptionsFlow):
    """Allows reconfiguring protocol and emitter after setup."""

    def __init__(self, config_entry) -> None:
        self._entry = config_entry
        self._data: dict = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_test()

        return self.async_show_form(
            step_id="init", data_schema=_setup_schema(self._data)
        )

    async def async_step_test(self, user_input=None):
        """Same check as the config flow, before overwriting a working setup.

        Reconfiguring is where a wrong protocol does the most damage: the
        entry already works, and a bad guess would silently replace it.
        """
        if user_input is not None:
            if user_input["worked"]:
                self.hass.config_entries.async_update_entry(
                    self._entry, data=self._data
                )
                return self.async_create_entry(title="", data={})
            return self.async_show_form(
                step_id="init",
                data_schema=_setup_schema(self._data),
                errors={"base": "test_failed"},
            )

        try:
            await _async_send_test(self.hass, self._data)
        except IRBridgeError as err:
            _LOGGER.debug("IRBridge test send failed: %s", err)
            return self.async_show_form(
                step_id="init",
                data_schema=_setup_schema(self._data),
                errors={"base": "send_failed"},
                description_placeholders={"error": str(err)},
            )

        return self.async_show_form(
            step_id="test",
            data_schema=vol.Schema({
                vol.Required("worked", default=True): bool,
            }),
            description_placeholders={
                "protocol": self._data[CONF_PROTOCOL].capitalize(),
                "temp": str(TEST_TEMP),
            },
        )
