"""The NRW Rail Status integration."""

from __future__ import annotations

import logging
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import NRWRailStatusCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NRW Rail Status from a config entry."""

    # Web-Pfad für die custom Lovelace Card (www/nrw-rail-card.js) registrieren
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            url_path="/nrw_rail_status",
            path=str(hass.config.path("custom_components/nrw_rail_status/www")),
            cache_headers=False,
        )
    ])

    coordinator = NRWRailStatusCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listener für Änderungen im Optionen-Dialog (Options Flow)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
