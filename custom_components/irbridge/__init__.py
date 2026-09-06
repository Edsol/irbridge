from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PROTOCOL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "remote"]

# Entries created before the Gree identification carry protocol "midea".
# That name never described the Midea protocol: it was the first, partly
# wrong reading of a Gree-compatible unit, and the device it was built
# against is sold as Midea while speaking Gree. Gree is what those entries
# meant all along, so the migration renames rather than drops them.
_RENAMED_PROTOCOLS = {"midea": "gree"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Bring an older entry up to the current schema.

    Version 1 entries may name a protocol that no longer exists in the
    registry; left alone they would raise KeyError at setup and take the
    integration down, so they are rewritten before anything reads them.
    """
    if entry.version > 2:
        # Downgrade: this build cannot know what a newer version stored.
        return False

    if entry.version == 1:
        data = dict(entry.data)
        old = data.get(CONF_PROTOCOL)
        new = _RENAMED_PROTOCOLS.get(old)
        if new is not None:
            data[CONF_PROTOCOL] = new
            _LOGGER.info(
                "IRBridge: migrating %s from protocol '%s' to '%s'",
                entry.title, old, new,
            )
        hass.config_entries.async_update_entry(entry, data=data, version=2)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change so new capabilities take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
