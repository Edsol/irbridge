from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .base import IRSender
from ..errors import SendError
from ..ir_command import DEFAULT_FREQUENCY, RawTimingsCommand

_LOGGER = logging.getLogger(__name__)


class InfraredEntitySender(IRSender):
    """Sends IR via HA's native ``infrared`` platform.

    Any emitter on that platform accepts the same object, so this one sender
    covers ESPHome, Tuya Local, Broadlink, SMLIGHT and ``mqtt.infrared`` --
    the last being how a Zigbee2MQTT UFO-R11/ZS05 appears, which is why
    IRBridge requires HA 2026.8 rather than the 2026.4 the platform landed in.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        *,
        frequency: int = DEFAULT_FREQUENCY,
    ) -> None:
        self._hass = hass
        self._entity_id = entity_id
        self._frequency = frequency

    async def async_send_raw(self, raw: list[int]) -> None:
        # Lazy import: the config flow already refuses a core without the
        # platform, so this guard only catches an install that bypassed it
        # (a manual copy onto an older core). Importing at module scope would
        # break the integration before it could explain why.
        try:
            from homeassistant.components.infrared import async_send_command
        except ImportError as err:
            raise SendError(
                "La piattaforma 'infrared' non e' disponibile: IRBridge "
                "richiede Home Assistant 2026.8 o successivo."
            ) from err

        state = self._hass.states.get(self._entity_id)
        if state is None:
            raise SendError(f"Emitter {self._entity_id} non trovato.")
        # "unknown" means merely NEVER USED -- an infrared emitter's state is
        # the timestamp of its last send, so a fresh blaster reads unknown and
        # must still be allowed to send its first command.
        if state.state == "unavailable":
            raise SendError(f"Emitter {self._entity_id} non disponibile.")

        command = RawTimingsCommand(raw, frequency=self._frequency)
        try:
            await async_send_command(self._hass, self._entity_id, command)
        except Exception as err:
            raise SendError(
                f"Invio IR fallito su {self._entity_id}: {err}"
            ) from err
