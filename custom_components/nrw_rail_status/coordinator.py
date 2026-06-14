"""Data coordinator for the NRW Rail Status integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL
from .api import NRWHimApi

_LOGGER = logging.getLogger(__name__)


class NRWRailStatusCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch HIM messages from Zuginfo.nrw."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

        session = aiohttp_client.async_get_clientsession(hass)
        self.api = NRWHimApi(session)

    async def _async_update_data(self):
        """Fetch data from the API with retry and error handling."""

        _LOGGER.debug("Coordinator update triggered")

        try:
            messages = await self.api.fetch_messages()

            if not messages:
                _LOGGER.warning("API returned no messages (empty result)")
                raise UpdateFailed("API returned no messages (empty result).")

            _LOGGER.debug("Coordinator received %s HIM messages", len(messages))
            return messages

        except UpdateFailed:
            # Bereits klassifizierter Fehler → direkt weiterreichen
            raise

        except Exception as err:
            err_str = str(err)
            _LOGGER.error("Unexpected error in coordinator: %s", err_str)

            # HAFAS-spezifische Fehler erkennen
            if "hammError" in err_str:
                raise UpdateFailed("HAFAS returned hammError (invalid session or payload).")

            if "svcResL" in err_str and "[]" in err_str:
                raise UpdateFailed("HAFAS returned empty svcResL (invalid request).")

            if "HCI" in err_str:
                raise UpdateFailed(f"HAFAS internal error: {err_str}")

            # Generischer Fehler
            raise UpdateFailed(f"Unexpected error fetching NRW HIM data: {err_str}") from err

