from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import CONF_INFRARED_ENTITY_ID
from ..generators.base import ClimateGenerator
from .base import IRSender
from .infrared_entity import InfraredEntitySender


def build_sender(
    hass: HomeAssistant,
    entry: ConfigEntry,
    generator: ClimateGenerator,
) -> IRSender:
    """Build the IRSender described by a config entry.

    The carrier comes from the generator, not the entry: it is a property of
    the protocol, so a user is never asked for it and cannot get it wrong.
    Shared by the climate and remote platforms so the two can never drift.
    """
    return InfraredEntitySender(
        hass,
        entry.data[CONF_INFRARED_ENTITY_ID],
        frequency=generator.capabilities.frequency,
    )
