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


def classify_message(title: str, text: str) -> str:
    """Classify HIM message based on title and content keywords."""
    combined = f"{title} {text}".lower()

    if any(k in combined for k in ["aufzug", "aufzüge", "fahrstuhl", "gleis 11/12 in hagen"]):
        return "elevator"

    if any(k in combined for k in ["ausfall", "teilausfall", "entfällt", "entfallen", "zugausfall"]):
        return "cancellation"

    if any(k in combined for k in ["bauarbeiten", "oberleitung", "gleis", "brücke", "weichen"]):
        return "construction"

    return "general"


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
        """Fetch data from the API with exact line filtering, category filtering, and deduplication."""

        _LOGGER.debug("Coordinator update triggered")

        try:
            messages = await self.api.fetch_messages()

            if not messages:
                _LOGGER.warning("API returned no messages (empty result)")
                raise UpdateFailed("API returned no messages (empty result).")

            _LOGGER.debug("Coordinator received %s raw HIM messages", len(messages))

            filtered_lines = self.entry.options.get("filtered_lines", [])
            excluded_categories = self.entry.options.get("excluded_categories", [])

            # 1. Linien- & Kategorie-Filterung
            candidate_messages = []

            for msg in messages:
                msg_title = getattr(msg, "title", "") or ""
                msg_text = getattr(msg, "text", "") or ""

                category = classify_message(msg_title, msg_text)

                # Kategorie-Ausschluss (z. B. Aufzüge herausfiltern)
                if category in excluded_categories:
                    continue

                raw_products = getattr(msg, "products", []) or []
                product_names = [
                    p.get("name", "") if isinstance(p, dict) else getattr(p, "name", str(p))
                    for p in raw_products
                ]

                match = False
                if not filtered_lines:
                    match = True
                else:
                    for line in filtered_lines:
                        if line in product_names:
                            match = True
                            break

                        pattern = r"\b" + re.escape(line).replace(r"\ ", r"\s*") + r"\b"
                        if re.search(pattern, msg_title, re.IGNORECASE) or re.search(pattern, msg_text, re.IGNORECASE):
                            match = True
                            break

                if match:
                    if isinstance(msg, dict):
                        msg["category"] = category
                    else:
                        setattr(msg, "category", category)

                    candidate_messages.append(msg)

            # 2. Deduplizierung: Identische Titel + Texte herausfiltern
            unique_messages = []
            seen_signatures = set()

            for msg in candidate_messages:
                title = (getattr(msg, "title", "") or "").strip()
                text = (getattr(msg, "text", "") or "").strip()

                signature = (title, text)

                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    unique_messages.append(msg)

            _LOGGER.debug(
                "Filtered %s raw messages down to %s unique messages",
                len(messages),
                len(unique_messages),
            )

            return unique_messages

        except UpdateFailed:
            raise

        except Exception as err:
            err_str = str(err)
            _LOGGER.error("Unexpected error in coordinator: %s", err_str)
            raise UpdateFailed(f"Unexpected error fetching NRW HIM data: {err_str}") from err
