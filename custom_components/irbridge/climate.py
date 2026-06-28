from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
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

_HA_TO_INTERNAL = {
    HVACMode.OFF:      "off",
    HVACMode.COOL:     "cool",
    HVACMode.HEAT:     "heat",
    HVACMode.DRY:      "dry",
    HVACMode.FAN_ONLY: "fan_only",
    HVACMode.AUTO:     "auto",
}

_INTERNAL_TO_HA = {v: k for k, v in _HA_TO_INTERNAL.items()}


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

    async_add_entities([IRBridgeClimate(entry, generator, sender)])


class IRBridgeClimate(ClimateEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1

    def __init__(self, entry: ConfigEntry, generator: ClimateGenerator, sender) -> None:
        self._entry = entry
        self._generator = generator
        self._sender = sender
        caps = generator.capabilities

        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.title
        self._attr_min_temp = caps.temp_min
        self._attr_max_temp = caps.temp_max
        self._attr_hvac_modes = [_INTERNAL_TO_HA[m] for m in caps.hvac_modes]
        self._attr_fan_modes = caps.fan_modes if caps.fan_modes else None
        self._attr_swing_modes = caps.swing_modes if caps.swing_modes else None

        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        if caps.fan_modes:
            features |= ClimateEntityFeature.FAN_MODE
        if caps.swing_modes:
            features |= ClimateEntityFeature.SWING_MODE
        self._attr_supported_features = features

        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 22
        self._attr_fan_mode = caps.fan_modes[0] if caps.fan_modes else None
        self._attr_swing_mode = caps.swing_modes[0] if caps.swing_modes else None
        self._last_active_mode = HVACMode.COOL

    @property
    def device_info(self):
        return {
            "identifiers": {("irbridge", self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "IRBridge",
            "model": type(self._generator).__name__.replace("ClimateGenerator", ""),
        }

    async def async_turn_on(self) -> None:
        self._attr_hvac_mode = self._last_active_mode
        await self._send_current_state()
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        self._attr_hvac_mode = HVACMode.OFF
        await self._send_current_state()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode != HVACMode.OFF:
            self._last_active_mode = hvac_mode
        self._attr_hvac_mode = hvac_mode
        await self._send_current_state()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._attr_target_temperature = int(temp)
        await self._send_current_state()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        self._attr_fan_mode = fan_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_current_state()
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        self._attr_swing_mode = swing_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._send_current_state()
        self.async_write_ha_state()

    async def _send_current_state(self) -> None:
        raw = self._generator.generate(
            hvac_mode=_HA_TO_INTERNAL[self._attr_hvac_mode],
            temp=self._attr_target_temperature or 22,
            fan_mode=self._attr_fan_mode or "auto",
            swing_mode=self._attr_swing_mode or "off",
        )
        await self._sender.async_send_raw(raw)
