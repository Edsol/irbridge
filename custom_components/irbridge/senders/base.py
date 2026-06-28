from __future__ import annotations

from abc import ABC, abstractmethod


class IRSender(ABC):
    """Abstract base class for IR transmission backends."""

    @abstractmethod
    async def async_send_raw(self, raw: list[int]) -> None:
        """Send raw IR timings (microseconds, alternating mark/space)."""
