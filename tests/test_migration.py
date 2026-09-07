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

"""Cover the config entry migration with a stubbed Home Assistant.

The migration runs once, unattended, against a user's stored configuration.
A mistake here does not fail loudly in testing -- it silently rewrites or
drops someone's working setup on upgrade, so the paths are pinned down.
"""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/irbridge'


def _stub_homeassistant() -> None:
    if 'homeassistant' in sys.modules:
        return

    def module(name: str, **attrs) -> types.ModuleType:
        mod = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(mod, key, value)
        sys.modules[name] = mod
        return mod

    module('homeassistant')
    module('homeassistant.core', HomeAssistant=object)
    module('homeassistant.config_entries', ConfigEntry=object,
           ConfigFlow=object, OptionsFlow=object)


_stub_homeassistant()

_spec = importlib.util.spec_from_file_location(
    'irbridge_pkg', COMPONENT / '__init__.py',
    submodule_search_locations=[str(COMPONENT)])
irbridge = importlib.util.module_from_spec(_spec)
sys.modules['irbridge_pkg'] = irbridge
_spec.loader.exec_module(irbridge)


class FakeEntry:
    def __init__(self, data: dict, version: int = 1, title: str = 'AC'):
        self.data = dict(data)
        self.version = version
        self.title = title


class FakeConfigEntries:
    """Records the update the migration asks for, as HA would apply it."""

    def __init__(self):
        self.calls = 0

    def async_update_entry(self, entry, *, data=None, version=None):
        self.calls += 1
        if data is not None:
            entry.data = data
        if version is not None:
            entry.version = version


class FakeHass:
    def __init__(self):
        self.config_entries = FakeConfigEntries()


def migrate(entry: FakeEntry) -> tuple[bool, FakeHass]:
    hass = FakeHass()
    ok = asyncio.run(irbridge.async_migrate_entry(hass, entry))
    return ok, hass


class MigrationTests(unittest.TestCase):
    def test_midea_becomes_gree(self):
        entry = FakeEntry({'protocol': 'midea',
                           'infrared_entity_id': 'infrared.blaster'})
        ok, _ = migrate(entry)
        self.assertTrue(ok)
        self.assertEqual(entry.data['protocol'], 'gree')
        self.assertEqual(entry.version, 2)

    def test_migrated_protocol_is_actually_registered(self):
        """A rename that points at a missing generator would still break setup."""
        sys.path.insert(0, str(COMPONENT.parent))
        spec = importlib.util.spec_from_file_location(
            'gens', COMPONENT / 'generators/__init__.py',
            submodule_search_locations=[str(COMPONENT / 'generators')])
        gens = importlib.util.module_from_spec(spec)
        sys.modules['gens'] = gens
        spec.loader.exec_module(gens)
        for target in irbridge._RENAMED_PROTOCOLS.values():
            with self.subTest(target=target):
                self.assertIn(target, gens.available_protocols())

    def test_other_settings_survive(self):
        entry = FakeEntry({'protocol': 'midea',
                           'infrared_entity_id': 'infrared.living_room'})
        migrate(entry)
        self.assertEqual(entry.data['infrared_entity_id'],
                         'infrared.living_room')

    def test_untouched_protocol_keeps_its_name(self):
        entry = FakeEntry({'protocol': 'electra',
                           'infrared_entity_id': 'infrared.blaster'})
        ok, _ = migrate(entry)
        self.assertTrue(ok)
        self.assertEqual(entry.data['protocol'], 'electra')
        self.assertEqual(entry.version, 2)

    def test_current_version_is_left_alone(self):
        entry = FakeEntry({'protocol': 'gree'}, version=2)
        ok, hass = migrate(entry)
        self.assertTrue(ok)
        self.assertEqual(hass.config_entries.calls, 0)

    def test_future_version_is_refused(self):
        """A downgrade must fail loudly rather than reinterpret newer data."""
        entry = FakeEntry({'protocol': 'gree'}, version=3)
        ok, hass = migrate(entry)
        self.assertFalse(ok)
        self.assertEqual(hass.config_entries.calls, 0)

    def test_missing_protocol_does_not_crash(self):
        """A corrupt entry should still reach version 2, not raise."""
        entry = FakeEntry({'infrared_entity_id': 'infrared.blaster'})
        ok, _ = migrate(entry)
        self.assertTrue(ok)
        self.assertEqual(entry.version, 2)


if __name__ == '__main__':
    unittest.main()
