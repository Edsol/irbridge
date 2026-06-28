from __future__ import annotations

import json

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, device_registry as dr

from .base import IRSender
from ..tuya_codec import encode_tuya_ir


class MqttTuyaSender(IRSender):
    """Sends IR commands via MQTT in Tuya base64 format.

    The user picks a text entity (e.g. text.ir_blaster_battery_ir_code_to_send).
    We derive the Zigbee2MQTT topic from the entity's device friendly name.
    """

    def __init__(self, hass: HomeAssistant, text_entity_id: str) -> None:
        self._hass = hass
        self._entity_id = text_entity_id
        self._topic: str | None = None

    def _resolve_topic(self) -> str:
        if self._topic:
            return self._topic

        ent_reg = er.async_get(self._hass)
        dev_reg = dr.async_get(self._hass)

        entry = ent_reg.async_get(self._entity_id)
        if entry and entry.device_id:
            device = dev_reg.async_get(entry.device_id)
            if device and device.name_by_user:
                friendly = device.name_by_user
            elif device and device.name:
                friendly = device.name
            else:
                friendly = None
            if friendly:
                self._topic = f"zigbee2mqtt/{friendly}/set"
                return self._topic

        # Fallback: derive from entity_id slug
        # text.ir_blaster_battery_ir_code_to_send -> ir_blaster_battery
        slug = self._entity_id.removeprefix("text.").removesuffix("_ir_code_to_send")
        self._topic = f"zigbee2mqtt/{slug}/set"
        return self._topic

    async def async_send_raw(self, raw: list[int]) -> None:
        code = encode_tuya_ir(raw)
        topic = self._resolve_topic()
        await self._hass.services.async_call(
            "mqtt",
            "publish",
            {"topic": topic, "payload": json.dumps({"ir_code_to_send": code})},
        )
