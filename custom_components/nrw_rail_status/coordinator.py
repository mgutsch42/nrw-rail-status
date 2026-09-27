"""Data coordinator for the NRW Rail Status integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import NRWHimApi
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class NRWRailStatusCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch HIM messages from Zuginfo.nrw."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

        self.entry = entry
        session = aiohttp_client.async_get_clientsession(hass)
        self.api = NRWHimApi(session)

    async def _async_update_data(self):
        """Fetch data from the API with retry, error handling, and line filtering."""

        _LOGGER.debug("Coordinator update triggered")

        try:
            messages = await self.api.fetch_messages()

            if not messages:
                _LOGGER.warning("API returned no messages (empty result)")
                raise UpdateFailed("API returned no messages (empty result).")

            _LOGGER.debug("Coordinator received %s raw HIM messages", len(messages))

            # -------------------------------------------------------------
            # Linien-Filter anwenden
            # -------------------------------------------------------------
            filtered_lines = self.entry.options.get("filtered_lines", [])

            # Wenn keine Filter gesetzt sind -> alle Meldungen behalten
            if not filtered_lines:
                return messages

            filtered_messages = []
            for msg in messages:
                # Produkte/Linien-Liste aus der Meldung abrufen
                msg_products = getattr(msg, "products", [])
                msg_title = getattr(msg, "title", "")
                msg_text = getattr(msg, "text", "")

                # Prüfen, ob eine der ausgewählten Linien passt
                match = False
                for line in filtered_lines:
                    # Direkter Treffer in Produkten oder Erwähnung im Titel/Text
                    if (
                        line in msg_products
                        or line in msg_title
                        or line in msg_text
                    ):
                        match = True
                        break

                if match:
                    filtered_messages.append(msg)

            _LOGGER.debug(
                "Filtered %s messages down to %s for selected lines: %s",
                len(messages),
                len(filtered_messages),
                filtered_lines,
            )

            return filtered_messages

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
