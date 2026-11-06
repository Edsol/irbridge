# IRBridge - generate IR codes on-the-fly for climate devices in Home Assistant
# Copyright (C) 2026 Edoardo Soloperto
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoredExtraData, RestoreEntity
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import CONF_PROTOCOL
from .generators import get_generator
from .generators.base import ClimateGenerator
from .senders import build_sender

# Home Assistant 2026.11 renamed the climate temperature members to native_*.
# The old names log a warning there and stop working in 2027.11, while the
# new ones do not exist before 2026.11 -- and hacs.json still admits 2026.7.
# The entity therefore declares whichever pair the running core knows.
_NATIVE_TEMPERATURES = hasattr(ClimateEntity, "native_target_temperature")

DEFAULT_TEMP = 22
ATTR_LAST_ACTIVE_MODE = "last_active_mode"

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
    generator = get_generator(entry.data[CONF_PROTOCOL])
    sender = build_sender(hass, entry, generator)

    async_add_entities([IRBridgeClimate(entry, generator, sender)])


class IRBridgeClimate(ClimateEntity, RestoreEntity):
    """An air conditioner driven blind, through generated IR frames.

    IR is one-way, so the unit can never be asked what it is doing: the
    entity's state is only what it last told the unit. That state is restored
    across restarts without transmitting -- the unit already holds it, and a
    restart that re-sent it would beep every AC in the house, or switch on
    one somebody had turned off with the original remote in the meantime.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_target_temperature_step = 1
    if _NATIVE_TEMPERATURES:
        _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    else:
        _attr_temperature_unit = UnitOfTemperature.CELSIUS

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
        self._target_temp = DEFAULT_TEMP
        self._attr_fan_mode = caps.fan_modes[0] if caps.fan_modes else None
        self._attr_swing_mode = caps.swing_modes[0] if caps.swing_modes else None
        self._last_active_mode = HVACMode.COOL

    # The target temperature lives in _target_temp and is exposed through
    # whichever property the running core reads (see _NATIVE_TEMPERATURES).
    if _NATIVE_TEMPERATURES:
        @property
        def native_target_temperature(self) -> float | None:
            return self._target_temp
    else:
        @property
        def target_temperature(self) -> float | None:
            return self._target_temp

    @property
    def extra_restore_state_data(self) -> RestoredExtraData:
        # The last active mode is not part of the visible state while the
        # unit is off, yet turn_on needs it: without it, the first turn_on
        # after a restart would switch a heating unit to cooling.
        return RestoredExtraData(
            {ATTR_LAST_ACTIVE_MODE: self._last_active_mode.value})

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            extra = await self.async_get_last_extra_data()
            self._restore(
                last_state.state,
                last_state.attributes,
                extra.as_dict() if extra is not None else {},
                self.hass.config.units.temperature_unit,
            )

    def _restore(
        self,
        state: str,
        attributes: Mapping[str, Any],
        extra: Mapping[str, Any],
        system_unit: str,
    ) -> None:
        """Adopt a previously saved state, without transmitting anything.

        Each value is taken only if this protocol can still express it --
        the entry may have been switched to a protocol with other modes or
        another temperature range -- and is otherwise left at its default.
        """
        modes = {mode.value: mode for mode in self._attr_hvac_modes}
        if (mode := modes.get(state)) is not None:
            self._attr_hvac_mode = mode
        if (active := modes.get(extra.get(ATTR_LAST_ACTIVE_MODE))) is not None:
            if active != HVACMode.OFF:
                self._last_active_mode = active
        elif mode is not None and mode != HVACMode.OFF:
            self._last_active_mode = mode

        if (temp := self._restored_temperature(
                attributes.get(ATTR_TEMPERATURE), system_unit)) is not None:
            self._target_temp = temp
        if self._attr_fan_modes and attributes.get("fan_mode") in self._attr_fan_modes:
            self._attr_fan_mode = attributes["fan_mode"]
        if (self._attr_swing_modes
                and attributes.get("swing_mode") in self._attr_swing_modes):
            self._attr_swing_mode = attributes["swing_mode"]

    def _restored_temperature(self, value: Any, system_unit: str) -> int | None:
        """The saved target in °C, or None if it is unusable here.

        State attributes are written in the system unit, so a Fahrenheit
        install stored 72 for 22 °C.
        """
        try:
            celsius = TemperatureConverter.convert(
                float(value), system_unit, UnitOfTemperature.CELSIUS)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(celsius):
            return None
        temp = round(celsius)
        if not self._attr_min_temp <= temp <= self._attr_max_temp:
            return None
        return temp

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
            self._target_temp = int(temp)
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
            temp=self._target_temp or DEFAULT_TEMP,
            fan_mode=self._attr_fan_mode or "auto",
            swing_mode=self._attr_swing_mode or "off",
        )
        await self._sender.async_send_raw(raw)
