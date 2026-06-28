from __future__ import annotations

from .base import ClimateCapabilities, ClimateGenerator
from . import electra


class ElectraClimateGenerator(ClimateGenerator):
    """IR climate generator for Electra/AUX/Beko protocol."""

    @property
    def capabilities(self) -> ClimateCapabilities:
        return ClimateCapabilities(
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
