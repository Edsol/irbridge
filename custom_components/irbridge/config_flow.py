from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import CONF_INFRARED_ENTITY_ID, CONF_PROTOCOL, DOMAIN
from .errors import IRBridgeError
from .generators import available_protocols, get_generator

_LOGGER = logging.getLogger(__name__)

# What the test step sends. Cooling at 22 C is a state every supported
# protocol can express, and one whose effect is unmistakable on the unit:
# the display changes and the fan starts. Sending "off" instead would be
# ambiguous against an already-idle air conditioner.
TEST_HVAC_MODE = "cool"
TEST_TEMP = 22

MODE_GUIDED = "guided"
MODE_EXPERT = "expert"


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


def protocol_label(protocol: str) -> str:
    """One line naming the protocol and the brands known to speak it.

    The picker is useless without this: "Gree" and "Electra" mean nothing to
    someone reading the badge on their own air conditioner.
    """
    caps = get_generator(protocol).capabilities
    if not caps.brands:
        return protocol.capitalize()
    return f"{protocol.capitalize()} — {', '.join(caps.brands)}"


def protocol_options() -> list[dict]:
    return [
        {"value": p, "label": protocol_label(p)} for p in available_protocols()
    ]


def _emitter_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="infrared")
    )


async def _async_send_test(hass: HomeAssistant, data: dict) -> None:
    """Transmit one command with the chosen protocol and emitter.

    Raises IRBridgeError when the emitter refuses it. A send that succeeds
    proves only that the blaster accepted the payload -- whether the air
    conditioner understood it is what the user is asked next.
    """
    # Imported here so the module loads on a core without the infrared
    # platform, which the guard above reports rather than crashing on.
    from .senders.infrared_entity import InfraredEntitySender

    generator = get_generator(data[CONF_PROTOCOL])
    caps = generator.capabilities
    sender = InfraredEntitySender(
        hass, data[CONF_INFRARED_ENTITY_ID], frequency=caps.frequency
    )
    raw = generator.generate(
        TEST_HVAC_MODE,
        TEST_TEMP,
        fan_mode=caps.fan_modes[0] if caps.fan_modes else "auto",
        swing_mode=caps.swing_modes[0] if caps.swing_modes else "off",
    )
    await sender.async_send_raw(raw)


class _TestMixin:
    """The try-it-and-see machinery, shared by both flows.

    Choosing a protocol from a list is a guess: brand names do not identify
    protocols, and the device this integration was built against is sold as
    Midea while speaking Gree. So every path here ends by transmitting a
    real command and asking the person watching the unit what happened.
    """

    _data: dict
    # Protocols already ruled out in guided mode, in order.
    _tried: list[str]

    def _placeholders(self) -> dict:
        protocol = self._data[CONF_PROTOCOL]
        caps = get_generator(protocol).capabilities
        return {
            "protocol": protocol.capitalize(),
            "brands": ", ".join(caps.brands) or protocol.capitalize(),
            "temp": str(TEST_TEMP),
            "tried": str(len(self._tried)),
            "total": str(len(available_protocols())),
        }

    def _remaining(self) -> list[str]:
        """Protocols guided mode has not offered yet, in registry order."""
        return [p for p in available_protocols() if p not in self._tried]

    async def _async_try(self, protocol: str):
        """Send with ``protocol`` and show the verdict form."""
        self._data[CONF_PROTOCOL] = protocol
        try:
            await _async_send_test(self.hass, self._data)
        except IRBridgeError as err:
            _LOGGER.debug("IRBridge test send failed: %s", err)
            return self._async_show_picker(
                errors={"base": "send_failed"},
                placeholders={"error": str(err)},
            )
        return self.async_show_form(
            step_id="test",
            data_schema=vol.Schema({
                vol.Required("worked", default=True): bool,
            }),
            description_placeholders=self._placeholders(),
        )


class IRBridgeConfigFlow(_TestMixin, config_entries.ConfigFlow, domain=DOMAIN):
    # 2: entries no longer carry the retired "midea" protocol name.
    VERSION = 2

    def __init__(self) -> None:
        self._data: dict = {}
        self._tried: list[str] = []
        self._mode: str = MODE_GUIDED

    @staticmethod
    def async_get_options_flow(config_entry):
        return IRBridgeOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Explain what is about to happen, and how much to be asked.

        Someone installing this for the first time does not know what an IR
        protocol is, or that the setup will transmit to their air
        conditioner. Saying so once, here, is cheaper than a support issue.
        """
        if not _infrared_platform_available(self.hass):
            return self.async_abort(reason="infrared_unavailable")

        if user_input is not None:
            self._data["title"] = user_input["title"]
            self._data[CONF_INFRARED_ENTITY_ID] = (
                user_input[CONF_INFRARED_ENTITY_ID]
            )
            self._mode = user_input["mode"]
            if self._mode == MODE_EXPERT:
                return await self.async_step_protocol()
            return await self.async_step_guided()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("title"): str,
                vol.Required(CONF_INFRARED_ENTITY_ID): _emitter_selector(),
                vol.Required("mode", default=MODE_GUIDED):
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": MODE_GUIDED, "label": "Guided — try protocols for me"},
                                {"value": MODE_EXPERT, "label": "Expert — I will pick the protocol"},
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
            }),
            description_placeholders={
                "total": str(len(available_protocols())),
            },
        )

    # -- expert path -------------------------------------------------------

    def _async_show_picker(self, errors=None, placeholders=None):
        """The protocol list, with whatever went wrong last time."""
        return self.async_show_form(
            step_id="protocol",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_PROTOCOL,
                    default=self._data.get(CONF_PROTOCOL,
                                           available_protocols()[0]),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=protocol_options(),
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            errors=errors,
            description_placeholders=placeholders or {},
        )

    async def async_step_protocol(self, user_input=None):
        if user_input is not None:
            return await self._async_try(user_input[CONF_PROTOCOL])
        return self._async_show_picker()

    # -- guided path -------------------------------------------------------

    async def async_step_guided(self, user_input=None):
        """Work through the protocols one at a time.

        Nothing is asked about protocols at all: each round transmits and
        asks whether the unit reacted. Falls back to the picker when the
        list runs out, so a user is never left without a way forward.
        """
        remaining = self._remaining()
        if not remaining:
            return self._async_show_picker(errors={"base": "none_worked"})
        return await self._async_try(remaining[0])

    # -- verdict -----------------------------------------------------------

    async def async_step_test(self, user_input=None):
        if user_input is None:
            # Re-entered without an answer; ask again rather than assume.
            return await self._async_try(self._data[CONF_PROTOCOL])

        if user_input["worked"]:
            return self.async_create_entry(
                title=self._data["title"], data=self._data
            )

        self._tried.append(self._data[CONF_PROTOCOL])
        if self._mode == MODE_GUIDED:
            return await self.async_step_guided()
        return self._async_show_picker(errors={"base": "test_failed"})


class IRBridgeOptionsFlow(_TestMixin, config_entries.OptionsFlow):
    """Change the protocol or emitter of a device that already exists."""

    def __init__(self, config_entry) -> None:
        self._entry = config_entry
        self._data: dict = dict(config_entry.data)
        self._tried: list[str] = []

    def _async_show_picker(self, errors=None, placeholders=None):
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_PROTOCOL, default=self._data.get(CONF_PROTOCOL)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=protocol_options(),
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_INFRARED_ENTITY_ID,
                    default=self._data.get(CONF_INFRARED_ENTITY_ID),
                ): _emitter_selector(),
            }),
            errors=errors,
            description_placeholders=placeholders or {},
        )

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return await self._async_try(user_input[CONF_PROTOCOL])
        return self._async_show_picker()

    async def async_step_test(self, user_input=None):
        """Confirm before overwriting a setup that already works.

        This is where a wrong protocol costs the most: the entry works
        today, so nothing is written until the unit has answered.
        """
        if user_input is None:
            return await self._async_try(self._data[CONF_PROTOCOL])

        if user_input["worked"]:
            self.hass.config_entries.async_update_entry(
                self._entry, data=self._data
            )
            return self.async_create_entry(title="", data={})

        return self._async_show_picker(errors={"base": "test_failed"})
