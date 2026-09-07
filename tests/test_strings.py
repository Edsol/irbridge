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

"""Check that every flow step has the text Home Assistant will look for.

Home Assistant resolves flow labels from strings.json, falling back to
translations/<lang>.json for translated locales. A step missing from those
files does not fail: it renders its raw keys, so the user sees "worked"
where a question should be. That is invisible to every other test here,
which is why it gets its own.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/irbridge'
STRINGS = COMPONENT / 'strings.json'
TRANSLATIONS = COMPONENT / 'translations'
CONFIG_FLOW = (COMPONENT / 'config_flow.py').read_text()


def _steps_in_source(cls_marker: str) -> set[str]:
    """Step ids the flow actually shows, read from async_show_form calls.

    Bounded at the next top-level class, or the two flows would read each
    other's steps and the check would pass on a file that is missing one.
    """
    body = CONFIG_FLOW.split(cls_marker, 1)[1]
    body = re.split(r'\nclass ', body)[0]
    return set(re.findall(r'step_id="(\w+)"', body))


class StringsTests(unittest.TestCase):
    def setUp(self):
        self.strings = json.loads(STRINGS.read_text())

    def test_strings_file_exists(self):
        """Without it HA has nothing to resolve, whatever translations hold."""
        self.assertTrue(STRINGS.is_file())

    def test_every_config_step_has_text(self):
        shown = _steps_in_source('class IRBridgeConfigFlow')
        described = set(self.strings['config']['step'])
        self.assertTrue(shown)
        self.assertEqual(shown - described, set(),
                         'config steps shown but not described')

    def test_every_options_step_has_text(self):
        shown = _steps_in_source('class IRBridgeOptionsFlow')
        described = set(self.strings['options']['step'])
        self.assertTrue(shown)
        self.assertEqual(shown - described, set(),
                         'options steps shown but not described')

    def test_steps_carry_a_title(self):
        for section in ('config', 'options'):
            for name, step in self.strings[section]['step'].items():
                with self.subTest(step=f'{section}.{name}'):
                    self.assertIn('title', step)

    def test_every_field_is_labelled(self):
        """A field with no label renders its raw key, as 'worked' did."""
        for section in ('config', 'options'):
            for name, step in self.strings[section]['step'].items():
                for field in step.get('data', {}):
                    with self.subTest(field=f'{section}.{name}.{field}'):
                        self.assertTrue(step['data'][field].strip())

    def test_placeholders_are_supplied_by_the_flow(self):
        """Every {name} in a description must be passed as a placeholder."""
        # Placeholders are written either inline in a description_placeholders
        # literal or in the shared _placeholders() helper; both are dict keys.
        supplied = set(re.findall(r'"(\w+)":\s*\S', CONFIG_FLOW))
        for section in ('config', 'options'):
            for name, step in self.strings[section]['step'].items():
                for ph in re.findall(r'\{(\w+)\}',
                                     step.get('description', '')):
                    with self.subTest(step=f'{section}.{name}', ph=ph):
                        self.assertIn(ph, supplied)

    def test_errors_referenced_by_the_flow_are_defined(self):
        for key in set(re.findall(r'"base": "(\w+)"', CONFIG_FLOW)):
            with self.subTest(error=key):
                self.assertTrue(
                    key in self.strings['config'].get('error', {})
                    or key in self.strings['options'].get('error', {}),
                    f'error {key!r} shown by the flow but not defined')

    def test_aborts_referenced_by_the_flow_are_defined(self):
        for key in set(re.findall(r'async_abort\(reason="(\w+)"', CONFIG_FLOW)):
            with self.subTest(abort=key):
                self.assertIn(key, self.strings['config'].get('abort', {}))

    def test_translations_match_strings(self):
        """en.json is the English copy of strings.json; drift confuses both."""
        english = TRANSLATIONS / 'en.json'
        self.assertTrue(english.is_file())
        self.assertEqual(json.loads(english.read_text()), self.strings,
                         'translations/en.json has drifted from strings.json')


if __name__ == '__main__':
    unittest.main()
