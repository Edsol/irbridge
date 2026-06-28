from __future__ import annotations

from .base import ClimateCapabilities, ClimateGenerator
from . import midea


class MideaClimateGenerator(ClimateGenerator):
    """IR climate generator for Midea/Ferroli protocol."""

    @property
    def capabilities(self) -> ClimateCapabilities:
        return ClimateCapabilities(
            temp_min=16,
            temp_max=30,
            fan_modes=["auto"],
            swing_modes=[],
            hvac_modes=["off", "cool", "heat", "dry", "fan_only", "auto"],
        )

    def generate(self, hvac_mode: str, temp: int, fan_mode: str = "auto", swing_mode: str = "off") -> list[int]:
        if hvac_mode == "off":
            return midea.generate_power_off()
        ha_to_midea = {
            "cool": "cool",
            "heat": "heat",
            "dry": "dry",
            "auto": "auto",
            "fan_only": "fan",
        }
        return midea.generate_raw(ha_to_midea[hvac_mode], temp)
