from __future__ import annotations

from homeassistant.core import HomeAssistant

from .base import IRSender


class InfraredEntitySender(IRSender):
    """Sends IR commands via a HA InfraredEmitterEntity (new infrared platform)."""

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self._hass = hass
        self._entity_id = entity_id

    async def async_send_raw(self, raw: list[int]) -> None:
        await self._hass.services.async_call(
            "infrared",
            "send_command",
            {"entity_id": self._entity_id, "raw": raw},
        )
