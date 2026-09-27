"""DataUpdateCoordinator for NRW Rail Status."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NRWHimApi, NRWMessage
from .const import DOMAIN, DEFAULT_REFRESH_INTERVAL, CONF_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)


class NRWRailStatusDataUpdateCoordinator(DataUpdateCoordinator[list[NRWMessage]]):
    """Class to manage fetching NRW Rail Status data from the API."""

    def __init__(self, hass: HomeAssistant, api: NRWHimApi, entry_data: dict) -> None:
        """Initialize coordinator."""
        refresh_interval = entry_data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=refresh_interval),
        )
        self.api = api
        self.entry_data = entry_data

    async def _async_update_data(self) -> list[NRWMessage]:
        """Fetch data from API endpoint."""
        try:
            messages = await self.api.fetch_messages()
            _LOGGER.debug("Coordinator fetched %s messages from API", len(messages))
            return messages
        except Exception as err:
            _LOGGER.error("Error fetching data from NRW Rail Status API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
