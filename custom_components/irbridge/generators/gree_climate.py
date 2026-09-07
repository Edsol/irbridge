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

from . import gree
from .base import ClimateCapabilities, ClimateGenerator


class GreeClimateGenerator(ClimateGenerator):
    """Gree profile verified on the device formerly labelled midea_camera."""

    @property
    def capabilities(self) -> ClimateCapabilities:
        return ClimateCapabilities(
            brands=["Gree", "Sinclair", "Rotenso", "Tosot", "Cooper&Hunter"],
            temp_min=16,
            temp_max=30,
            fan_modes=["auto", "low", "mid", "high"],
            swing_modes=["off", "vertical"],
            hvac_modes=["off", "cool", "heat", "dry", "fan_only", "auto"],
        )

    def generate(
        self, hvac_mode: str, temp: int, fan_mode: str = "auto", swing_mode: str = "off",
    ) -> list[int]:
        if swing_mode not in ("off", "vertical"):
            raise ValueError(f"Unsupported Gree swing mode: {swing_mode!r}")
        return gree.generate_raw(
            "cool" if hvac_mode == "off" else hvac_mode,
            temp, fan_mode, power=hvac_mode != "off", swing_v=swing_mode == "vertical",
        )
