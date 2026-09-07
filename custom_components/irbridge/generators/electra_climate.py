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

from .base import ClimateCapabilities, ClimateGenerator
from . import electra


class ElectraClimateGenerator(ClimateGenerator):
    """IR climate generator for Electra/AUX/Beko protocol."""

    @property
    def capabilities(self) -> ClimateCapabilities:
        return ClimateCapabilities(
            brands=["Beko", "AUX", "Electrolux", "Frigidaire", "Electra"],
            temp_min=16,
            temp_max=32,
            fan_modes=["auto", "high", "mid", "low"],
            swing_modes=["off", "vertical"],
            hvac_modes=["off", "cool", "heat", "dry", "fan_only", "auto"],
        )

    def generate(self, hvac_mode: str, temp: int, fan_mode: str = "auto", swing_mode: str = "off") -> list[int]:
        ha_to_electra = {
            "cool": "cool",
            "heat": "heat",
            "dry": "dry",
            "auto": "auto",
            "fan_only": "fan",
        }
        power = hvac_mode != "off"
        electra_mode = ha_to_electra.get(hvac_mode, "cool")
        swing_v = swing_mode == "vertical"
        return electra.generate_raw(electra_mode, temp, fan=fan_mode, power=power, swing_v=swing_v)
