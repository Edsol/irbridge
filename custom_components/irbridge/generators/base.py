from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ClimateCapabilities:
    """Describes what a protocol supports."""
    temp_min: int = 16
    temp_max: int = 30
    fan_modes: list[str] = field(default_factory=lambda: ["auto"])
    swing_modes: list[str] = field(default_factory=list)  # empty = no swing
    hvac_modes: list[str] = field(default_factory=lambda: ["off", "cool", "heat", "dry", "fan_only", "auto"])


class ClimateGenerator(ABC):
    """Base class for all IR climate protocol generators.

    Implement this to add a new protocol to IRBridge.
    """

    @property
    @abstractmethod
    def capabilities(self) -> ClimateCapabilities:
        """Return what this protocol supports."""

    @abstractmethod
    def generate(
        self,
        hvac_mode: str,
        temp: int,
        fan_mode: str = "auto",
        swing_mode: str = "off",
    ) -> list[int]:
        """Generate raw IR timings for the given state.

        Args:
            hvac_mode: "off" | "cool" | "heat" | "dry" | "fan_only" | "auto"
            temp:      target temperature in °C
            fan_mode:  fan speed — must be one of capabilities.fan_modes
            swing_mode: swing state — must be one of capabilities.swing_modes

        Returns:
            Raw IR timings in microseconds (alternating mark/space).
        """
