"""Data coordinator for the NRW Rail Status integration."""

from __future__ import annotations

import logging
import re
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
        """Fetch data from the API with exact line filtering and deduplication."""

        _LOGGER.debug("Coordinator update triggered")

        try:
            messages = await self.api.fetch_messages()

            if not messages:
                _LOGGER.warning("API returned no messages (empty result)")
                raise UpdateFailed("API returned no messages (empty result).")

            _LOGGER.debug("Coordinator received %s raw HIM messages", len(messages))

            filtered_lines = self.entry.options.get("filtered_lines", [])

            # -------------------------------------------------------------
            # 1. Exakte Linien-Filterung anwenden
            # -------------------------------------------------------------
            candidate_messages = []
            if not filtered_lines:
                candidate_messages = messages
            else:
                for msg in messages:
                    # Extrahiere alle Produktnamen (z. B. "RE 4", "S 8")
                    raw_products = getattr(msg, "products", []) or []
                    product_names = [
                        p.get("name", "") if isinstance(p, dict) else getattr(p, "name", str(p))
                        for p in raw_products
                    ]

                    msg_title = getattr(msg, "title", "") or ""
                    msg_text = getattr(msg, "text", "") or ""

                    match = False
                    for line in filtered_lines:
                        # Exakter Abgleich im Produkte-Array
                        if line in product_names:
                            match = True
                            break

                        # Wortgrenzen-Regex für Titel & Text (verhindert z.B. "RE 4" Matching bei "RE 44")
                        pattern = r"\b" + re.escape(line).replace(r"\ ", r"\s*") + r"\b"
                        if re.search(pattern, msg_title, re.IGNORECASE) or re.search(pattern, msg_text, re.IGNORECASE):
                            match = True
                            break

                    if match:
                        candidate_messages.append(msg)

            # -------------------------------------------------------------
            # 2. Deduplizierung: Identische Titel + Texte herausfiltern
            # -------------------------------------------------------------
            unique_messages = []
            seen_signatures = set()

            for msg in candidate_messages:
                title = (getattr(msg, "title", "") or "").strip()
                text = (getattr(msg, "text", "") or "").strip()

                # Kombination aus Titel und Text als eindeutiger Schlüssel
                signature = (title, text)

                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    unique_messages.append(msg)

            _LOGGER.debug(
                "Filtered %s raw messages down to %s unique messages for selected lines: %s",
                len(messages),
                len(unique_messages),
                filtered_lines,
            )

            return unique_messages

        except UpdateFailed:
            raise

        except Exception as err:
            err_str = str(err)
            _LOGGER.error("Unexpected error in coordinator: %s", err_str)

            if "hammError" in err_str:
                raise UpdateFailed("HAFAS returned hammError (invalid session or payload).")

            if "svcResL" in err_str and "[]" in err_str:
                raise UpdateFailed("HAFAS returned empty svcResL (invalid request).")

            if "HCI" in err_str:
                raise UpdateFailed(f"HAFAS internal error: {err_str}")

            raise UpdateFailed(f"Unexpected error fetching NRW HIM data: {err_str}") from err
