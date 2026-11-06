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

"""Restoring the climate state after a restart, with stubbed Home Assistant.

An IR unit cannot be asked what it is doing, so after a restart the entity
only knows what it saved. Getting this wrong is not cosmetic: a restart that
transmitted would beep every AC in the house (or switch one back on), and a
lost last-active mode makes the next turn_on cool a room that was heating.
"""
import asyncio
from enum import IntFlag, StrEnum
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/irbridge'
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Reuses the HA stubs and the loaded irbridge package of the config flow
# tests, so the two files can run in either order.
import test_config_flow  # noqa: E402,F401


def _module(name: str, **attrs) -> types.ModuleType:
    mod = sys.modules.get(name) or types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


class HVACMode(StrEnum):
    OFF = 'off'
    HEAT = 'heat'
    COOL = 'cool'
    HEAT_COOL = 'heat_cool'
    AUTO = 'auto'
    DRY = 'dry'
    FAN_ONLY = 'fan_only'


class ClimateEntityFeature(IntFlag):
    TARGET_TEMPERATURE = 1
    FAN_MODE = 8
    SWING_MODE = 32
    TURN_OFF = 128
    TURN_ON = 256


class ClimateEntity:
    """The 2026.11 shape: the native_* members exist."""

    native_target_temperature = None

    def async_write_ha_state(self):
        pass


class RestoreEntity:
    async def async_added_to_hass(self):
        pass


class RestoredExtraData:
    def __init__(self, data):
        self._data = data

    def as_dict(self):
        return dict(self._data)


class TemperatureConverter:
    @staticmethod
    def convert(value, from_unit, to_unit):
        if from_unit == to_unit:
            return value
        if (from_unit, to_unit) == ('°F', '°C'):
            return (value - 32) * 5 / 9
        raise ValueError(f'{from_unit} -> {to_unit}')


class UnitOfTemperature(StrEnum):
    CELSIUS = '°C'
    FAHRENHEIT = '°F'


_module('homeassistant.components.climate', ClimateEntity=ClimateEntity,
        ClimateEntityFeature=ClimateEntityFeature, HVACMode=HVACMode)
_module('homeassistant.const', ATTR_TEMPERATURE='temperature',
        UnitOfTemperature=UnitOfTemperature)
_module('homeassistant.helpers.restore_state',
        RestoredExtraData=RestoredExtraData, RestoreEntity=RestoreEntity)
_module('homeassistant.util')
_module('homeassistant.util.unit_conversion',
        TemperatureConverter=TemperatureConverter)

spec = importlib.util.spec_from_file_location(
    'irbridge.climate', COMPONENT / 'climate.py')
climate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = climate
spec.loader.exec_module(climate)


class FakeSender:
    def __init__(self):
        self.sent = []

    async def async_send_raw(self, raw):
        self.sent.append(raw)


class FakeState:
    def __init__(self, state, attributes):
        self.state = state
        self.attributes = attributes


def _entity(protocol='gree'):
    entry = types.SimpleNamespace(entry_id='abc', title='Camera')
    sender = FakeSender()
    entity = climate.IRBridgeClimate(
        entry, climate.get_generator(protocol), sender)
    return entity, sender


def _added(entity, state, attributes=None, extra=None, unit='°C'):
    """Run async_added_to_hass against a saved state."""
    last = None if state is None else FakeState(state, attributes or {})

    async def last_state():
        return last

    async def last_extra():
        return None if extra is None else RestoredExtraData(extra)

    entity.async_get_last_state = last_state
    entity.async_get_last_extra_data = last_extra
    entity.hass = types.SimpleNamespace(config=types.SimpleNamespace(
        units=types.SimpleNamespace(temperature_unit=unit)))
    asyncio.run(entity.async_added_to_hass())


class RestoreTests(unittest.TestCase):
    def test_restores_without_transmitting(self):
        entity, sender = _entity()
        _added(entity, 'heat', {'temperature': 19, 'fan_mode': 'low',
                                'swing_mode': 'vertical'})
        self.assertEqual(entity._attr_hvac_mode, HVACMode.HEAT)
        self.assertEqual(entity.native_target_temperature, 19)
        self.assertEqual(entity._attr_fan_mode, 'low')
        self.assertEqual(entity._attr_swing_mode, 'vertical')
        self.assertEqual(sender.sent, [])

    def test_first_start_keeps_defaults(self):
        entity, sender = _entity()
        _added(entity, None)
        self.assertEqual(entity._attr_hvac_mode, HVACMode.OFF)
        self.assertEqual(entity.native_target_temperature, climate.DEFAULT_TEMP)
        self.assertEqual(sender.sent, [])

    def test_turn_on_after_restart_resumes_the_last_active_mode(self):
        """Off at restart, heating before it: turn_on must heat, not cool."""
        entity, sender = _entity()
        _added(entity, 'off', {'temperature': 16},
               extra={climate.ATTR_LAST_ACTIVE_MODE: 'heat'})
        self.assertEqual(entity._attr_hvac_mode, HVACMode.OFF)
        asyncio.run(entity.async_turn_on())
        self.assertEqual(entity._attr_hvac_mode, HVACMode.HEAT)
        self.assertEqual(len(sender.sent), 1)

    def test_active_state_counts_as_last_active_without_extra_data(self):
        """States saved before this version carry no extra data."""
        entity, _ = _entity()
        _added(entity, 'heat', {'temperature': 20})
        self.assertEqual(entity._last_active_mode, HVACMode.HEAT)

    def test_saves_the_last_active_mode(self):
        entity, _ = _entity()
        asyncio.run(entity.async_set_hvac_mode(HVACMode.HEAT))
        asyncio.run(entity.async_turn_off())
        self.assertEqual(entity.extra_restore_state_data.as_dict(),
                         {climate.ATTR_LAST_ACTIVE_MODE: 'heat'})

    def test_ignores_values_the_protocol_cannot_express(self):
        entity, _ = _entity()
        caps = climate.get_generator('gree').capabilities
        _added(entity, 'unavailable', {'temperature': caps.temp_max + 5,
                                       'fan_mode': 'turbo',
                                       'swing_mode': 'horizontal'})
        self.assertEqual(entity._attr_hvac_mode, HVACMode.OFF)
        self.assertEqual(entity.native_target_temperature, climate.DEFAULT_TEMP)
        self.assertEqual(entity._attr_fan_mode, caps.fan_modes[0])
        self.assertEqual(entity._attr_swing_mode, caps.swing_modes[0])

    def test_unusable_temperature_is_ignored(self):
        for value in (None, 'unknown', float('nan')):
            with self.subTest(value=value):
                entity, _ = _entity()
                _added(entity, 'cool', {'temperature': value})
                self.assertEqual(entity.native_target_temperature,
                                 climate.DEFAULT_TEMP)

    def test_fahrenheit_install(self):
        entity, _ = _entity()
        _added(entity, 'cool', {'temperature': 72}, unit='°F')
        self.assertEqual(entity.native_target_temperature, 22)

    def test_sends_the_restored_state_on_the_next_command(self):
        """A fan change after a restart must not reset the temperature."""
        entity, sender = _entity()
        _added(entity, 'heat', {'temperature': 19})
        sent = []
        original = entity._generator.generate
        entity._generator.generate = lambda **kw: sent.append(kw) or original(**kw)
        asyncio.run(entity.async_set_fan_mode('high'))
        self.assertEqual(sent[0]['temp'], 19)
        self.assertEqual(sent[0]['hvac_mode'], 'heat')
        self.assertEqual(len(sender.sent), 1)


class UnitDeclarationTests(unittest.TestCase):
    def test_declares_the_native_unit_on_new_cores(self):
        self.assertTrue(climate._NATIVE_TEMPERATURES)
        self.assertEqual(climate.IRBridgeClimate._attr_native_temperature_unit,
                         UnitOfTemperature.CELSIUS)
        self.assertNotIn('_attr_temperature_unit',
                         vars(climate.IRBridgeClimate))
        self.assertNotIn('target_temperature', vars(climate.IRBridgeClimate))


if __name__ == '__main__':
    unittest.main()
