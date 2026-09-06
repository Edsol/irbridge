"""Exercise the config flow's test-send logic with stubbed Home Assistant.

The flow itself needs a running core to drive, but the piece worth testing
is the one that decides what gets transmitted: a wrong protocol or a wrong
carrier here would send a payload no air conditioner answers, and the user
would blame their blaster.
"""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/irbridge'


def _stub_dependencies() -> None:
    """Minimal HA + voluptuous surface, so config_flow imports standalone.

    Both ship with Home Assistant rather than with this integration, so the
    unit tests stub what they touch instead of pulling in the whole core.
    """
    if 'homeassistant' in sys.modules:
        return

    def module(name: str, **attrs) -> types.ModuleType:
        mod = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(mod, key, value)
        sys.modules[name] = mod
        return mod

    class _Selector:
        def __init__(self, *args, **kwargs):
            pass

    class _ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            pass

    if 'voluptuous' not in sys.modules:
        class _Marker:
            def __init__(self, schema, default=None, **kwargs):
                self.schema = schema
                self.default = default

            def __hash__(self):
                return hash(self.schema)

        class _Schema:
            def __init__(self, schema=None, **kwargs):
                self.schema = schema or {}

            def extend(self, other):
                merged = dict(self.schema)
                merged.update(other)
                return _Schema(merged)

        module('voluptuous', Schema=_Schema, Required=_Marker,
               Optional=_Marker, Marker=_Marker)

    module('homeassistant')
    module('homeassistant.core', HomeAssistant=object)
    module('homeassistant.config_entries', ConfigFlow=_ConfigFlow,
           OptionsFlow=object, ConfigEntry=object)
    module('homeassistant.helpers')
    module('homeassistant.helpers.selector', EntitySelector=_Selector,
           EntitySelectorConfig=_Selector, SelectSelector=_Selector,
           SelectSelectorConfig=_Selector)
    module('homeassistant.helpers.entity_platform', AddEntitiesCallback=object)
    module('homeassistant.components')
    # No homeassistant.components.infrared: mirrors a core without the
    # platform, which is what _infrared_platform_available must detect.


def _load(name: str, path: Path, search: list[str] | None = None):
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=search)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_stub_dependencies()
_load('irbridge', COMPONENT / '__init__.py', [str(COMPONENT)])
config_flow = _load('irbridge.config_flow', COMPONENT / 'config_flow.py')


class SentPayload:
    """Records what a fake emitter was handed."""

    def __init__(self):
        self.raw = None
        self.frequency = None
        self.entity_id = None


class TestSendTests(unittest.TestCase):
    def _capture(self, protocol: str, entity_id='infrared.blaster') -> SentPayload:
        seen = SentPayload()

        class FakeSender:
            def __init__(self, hass, eid, frequency=38000):
                seen.entity_id = eid
                seen.frequency = frequency

            async def async_send_raw(self, raw):
                seen.raw = raw

        original = config_flow.InfraredEntitySender
        config_flow.InfraredEntitySender = FakeSender
        try:
            asyncio.run(config_flow._async_send_test(None, {
                'protocol': protocol,
                'infrared_entity_id': entity_id,
            }))
        finally:
            config_flow.InfraredEntitySender = original
        return seen

    def test_every_protocol_produces_a_payload(self):
        """A protocol the picker offers must survive the test step.

        The picker is built from the generator registry, so a generator
        that cannot express the test state would offer the user an option
        that always fails.
        """
        for protocol in config_flow.available_protocols():
            with self.subTest(protocol=protocol):
                seen = self._capture(protocol)
                self.assertTrue(seen.raw, f'{protocol} generated no timings')
                self.assertGreater(len(seen.raw), 10)

    def test_carrier_comes_from_the_generator(self):
        for protocol in config_flow.available_protocols():
            with self.subTest(protocol=protocol):
                expected = config_flow.get_generator(
                    protocol).capabilities.frequency
                self.assertEqual(self._capture(protocol).frequency, expected)

    def test_sends_to_the_chosen_emitter(self):
        seen = self._capture('gree', entity_id='infrared.living_room')
        self.assertEqual(seen.entity_id, 'infrared.living_room')

    def test_test_state_is_within_every_protocol_range(self):
        """The fixed test state must be legal for each protocol."""
        for protocol in config_flow.available_protocols():
            caps = config_flow.get_generator(protocol).capabilities
            with self.subTest(protocol=protocol):
                self.assertGreaterEqual(config_flow.TEST_TEMP, caps.temp_min)
                self.assertLessEqual(config_flow.TEST_TEMP, caps.temp_max)
                self.assertIn(config_flow.TEST_HVAC_MODE, caps.hvac_modes)


class PlatformGuardTests(unittest.TestCase):
    def test_missing_infrared_platform_is_detected(self):
        """Stubbed core has no infrared component, so the guard must say no."""
        self.assertFalse(config_flow._infrared_platform_available(None))


if __name__ == '__main__':
    unittest.main()
