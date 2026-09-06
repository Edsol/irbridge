"""Exercise the actual generator registry without importing Home Assistant."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'custom_components/irbridge/generators'
spec = importlib.util.spec_from_file_location(
    'irbridge_test_generators', PACKAGE / '__init__.py',
    submodule_search_locations=[str(PACKAGE)],
)
generators = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = generators
spec.loader.exec_module(generators)


class GreeTests(unittest.TestCase):
    def test_verified_wire_messages(self):
        probes = json.loads((ROOT / 'tests/fixtures/gree_verified.json').read_text())
        generator = generators.get_generator('gree')
        for probe in probes:
            with self.subTest(state=probe['expected']):
                expected = probe['expected']
                raw = generator.generate(
                    'cool', 24, expected['fan'],
                    'vertical' if expected['swing'] == 'vertical_auto' else 'off',
                )
                self.assertEqual(raw, probe['raw'])

    def test_capabilities(self):
        caps = generators.get_generator('gree').capabilities
        self.assertEqual(caps.fan_modes, ['auto', 'low', 'mid', 'high'])
        self.assertEqual(caps.swing_modes, ['off', 'vertical'])
        self.assertEqual(caps.frequency, 38000)

    def test_midea_is_retired(self):
        """The name never described a protocol, so it must not come back.

        'midea' was the first, partly wrong reading of a Gree-compatible
        unit. Entries that still carry it are renamed by async_migrate_entry;
        offering it again in the picker would recreate the confusion.
        """
        self.assertNotIn('midea', generators.available_protocols())
        with self.assertRaises(KeyError):
            generators.get_generator('midea')

    def test_off_and_invalid_swing(self):
        generator = generators.get_generator('gree')
        self.assertEqual(generator.generate('off', 24),
                         generators.gree.generate_raw('cool', 24, power=False))
        with self.assertRaises(ValueError):
            generator.generate('cool', 24, swing_mode='horizontal')


if __name__ == '__main__':
    unittest.main()
