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
