"""NRW Rail Status — Störungen und Bauarbeiten aus dem NRW-Regionalverkehr.

Die Integration holt die Meldungen der oeffentlichen Seite zuginfo.nrw und
stellt sie als Sensoren bereit: einen Sensor je ausgewaehlter Linie mit
Anzahl und Details der Meldungen.
"""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import async_run_diagnostics
from .const import DOMAIN
from .coordinator import NRWRailStatusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_DIAGNOSE = "diagnose"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration einrichten."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    options = dict(entry.options or entry.data or {})

    coordinator = NRWRailStatusDataUpdateCoordinator(
        hass, session, entry_data=dict(entry.data or {}), options=options
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Wird eine Option geaendert, den Coordinator neu aufbauen
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration entfernen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Optionen neu uebernehmen."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Dienst 'diagnose' bereitstellen.

    Er prueft beide Wege zu Zuginfo.nrw und gibt zurueck, was tatsaechlich
    gelesen wurde. Damit laesst sich nach dem Einspielen in einem Aufruf
    sehen, ob der Parser zur Seitenstruktur passt.
    """
    if hass.services.has_service(DOMAIN, SERVICE_DIAGNOSE):
        return

    async def _handle_diagnose(call: ServiceCall) -> dict:
        lines = call.data.get("lines") or []
        if not lines:
            # Ohne Angabe die konfigurierten Linien der ersten Instanz nutzen
            for coordinator in (hass.data.get(DOMAIN) or {}).values():
                if getattr(coordinator, "lines", None):
                    lines = coordinator.lines
                    break

        session = async_get_clientsession(hass)
        try:
            result = await async_run_diagnostics(session, lines=lines or None)
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Diagnose fehlgeschlagen")
            return {"ok": False, "error": str(err)}

        for coordinator in (hass.data.get(DOMAIN) or {}).values():
            result["coordinator"] = coordinator.diagnostics
            break

        return result

    hass.services.async_register(
        DOMAIN,
        SERVICE_DIAGNOSE,
        _handle_diagnose,
        supports_response=SupportsResponse.ONLY,
    )
