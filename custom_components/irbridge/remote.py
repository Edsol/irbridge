from __future__ import annotations

from collections.abc import Iterable

from homeassistant.components.remote import RemoteEntity, RemoteEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_PROTOCOL,
    CONF_SENDER,
    CONF_TEXT_ENTITY_ID,
    CONF_INFRARED_ENTITY_ID,
    SENDER_MQTT_TUYA,
)
from .generators import get_generator
from .generators.base import ClimateGenerator
from .senders.mqtt_tuya import MqttTuyaSender
from .senders.infrared_entity import InfraredEntitySender


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    protocol = entry.data[CONF_PROTOCOL]
    sender_type = entry.data[CONF_SENDER]

    generator = get_generator(protocol)

    if sender_type == SENDER_MQTT_TUYA:
        sender = MqttTuyaSender(hass, entry.data[CONF_TEXT_ENTITY_ID])
    else:
        sender = InfraredEntitySender(hass, entry.data[CONF_INFRARED_ENTITY_ID])

    async_add_entities([IRBridgeRemote(entry, generator, sender)])


class IRBridgeRemote(RemoteEntity):
    """Remote entity for IRBridge — accepts command strings and generates IR on-the-fly.

    Command format:
        "<mode>"            — e.g. "off", "cool", "heat", "dry", "fan_only", "auto"
        "<mode>_<temp>"     — e.g. "cool_22", "heat_20"
        "<mode>_<temp>_<fan>" — e.g. "cool_22_high", "heat_20_low"
        "swing_on" / "swing_off"
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_supported_features = RemoteEntityFeature(0)

    def __init__(self, entry: ConfigEntry, generator: ClimateGenerator, sender) -> None:
        self._entry = entry
        self._generator = generator
        self._sender = sender
        self._attr_unique_id = f"{entry.entry_id}_remote"
        self._attr_name = f"{entry.title} Remote"
        self._attr_is_on = False

        caps = generator.capabilities
        self._default_fan = caps.fan_modes[0] if caps.fan_modes else "auto"
        self._default_swing = caps.swing_modes[0] if caps.swing_modes else "off"
        self._current_swing = self._default_swing
        self._current_temp = 22

    @property
    def device_info(self):
        return {
            "identifiers": {("irbridge", self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "IRBridge",
            "model": type(self._generator).__name__.replace("ClimateGenerator", ""),
        }

    @property
    def extra_state_attributes(self):
        caps = self._generator.capabilities
        return {
            "supported_commands": self._build_command_list(caps),
        }

    def _build_command_list(self, caps) -> list[str]:
        commands = ["off"]
        for mode in caps.hvac_modes:
            if mode == "off":
                continue
            if mode == "fan_only":
                commands.append("fan_only")
                continue
            for temp in range(caps.temp_min, caps.temp_max + 1):
                commands.append(f"{mode}_{temp}")
        if caps.swing_modes:
            commands += ["swing_on", "swing_off"]
        return commands

    async def async_turn_on(self, **kwargs) -> None:
        raw = self._generator.generate("cool", self._current_temp, swing_mode=self._current_swing)
        await self._sender.async_send_raw(raw)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        raw = self._generator.generate("off", self._current_temp)
        await self._sender.async_send_raw(raw)
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_send_command(self, command: Iterable[str], **kwargs) -> None:
        for cmd in command:
            raw = self._parse_and_generate(cmd)
            if raw:
                await self._sender.async_send_raw(raw)
        self.async_write_ha_state()

    def _parse_and_generate(self, cmd: str) -> list[int] | None:
        parts = cmd.lower().split("_")

        if cmd == "off":
            self._attr_is_on = False
            return self._generator.generate("off", self._current_temp)

        if cmd in ("swing_on", "swing_vertical"):
            self._current_swing = "vertical"
            return None  # swing applied on next mode command

        if cmd in ("swing_off",):
            self._current_swing = "off"
            return None

        # <mode> or <mode>_<temp> or <mode>_<temp>_<fan>
        valid_modes = {"cool", "heat", "dry", "auto", "fan", "fanonly", "fan_only"}

        mode = parts[0]
        if mode == "fan" and len(parts) > 1 and parts[1] == "only":
            mode = "fan_only"
            parts = ["fan_only"] + parts[2:]

        if mode not in valid_modes:
            return None

        # normalize fan_only
        if mode in ("fan", "fanonly"):
            mode = "fan_only"

        temp = self._current_temp
        fan = self._default_fan

        if len(parts) >= 2:
            try:
                temp = int(parts[1])
                self._current_temp = temp
            except ValueError:
                fan = parts[1]

        if len(parts) >= 3:
            fan = parts[2]

        self._attr_is_on = True
        caps = self._generator.capabilities
        fan = fan if fan in caps.fan_modes else self._default_fan

        return self._generator.generate(mode, temp, fan_mode=fan, swing_mode=self._current_swing)
