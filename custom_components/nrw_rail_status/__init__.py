"""The NRW Rail Status integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import NRWRailStatusCoordinator

_LOGGER = logging.getLogger(__name__)

# Plattformen, die geladen werden sollen (sensor.py)
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NRW Rail Status from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Instanziierung des Coordinators mit hass und entry
    coordinator = NRWRailStatusCoordinator(hass, entry)

    # Ersten Datenabruf ausführen
    await coordinator.async_config_entry_first_refresh()

    # Coordinator im hass.data Speicher ablegen
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward der Setup-Anfrage an die Plattformen (Sensor)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listener für Änderungen im Options-Menü registrieren
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
