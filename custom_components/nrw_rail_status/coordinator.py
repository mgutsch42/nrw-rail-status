"""DataUpdateCoordinator for NRW Rail Status."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NRWHimApi, NRWMessage
from .const import (
    DOMAIN,
    DEFAULT_REFRESH_INTERVAL,
    CONF_REFRESH_INTERVAL,
    CONF_LINES,
    CONF_EXCLUDED_CATEGORIES,
)

_LOGGER = logging.getLogger(__name__)


class NRWRailStatusDataUpdateCoordinator(DataUpdateCoordinator[list[NRWMessage]]):
    """Holt die Meldungen von Zuginfo.nrw und haelt sie fuer die Sensoren bereit."""

    def __init__(
        self,
        hass: HomeAssistant,
        session,
        entry_data: dict,
        options: dict | None = None,
    ) -> None:
        """Coordinator anlegen.

        Die Linien und die ausgeschlossenen Kategorien kommen aus den Optionen
        (oder ersatzweise aus den Einstiegsdaten). Sie werden beim Aufbau des
        Clients ausgewertet, damit die Abfrage schon gefiltert stattfindet.
        """
        options = options or entry_data or {}

        refresh_interval = options.get(CONF_REFRESH_INTERVAL)
        if not isinstance(refresh_interval, (int, float)) or refresh_interval <= 0:
            refresh_interval = DEFAULT_REFRESH_INTERVAL

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=refresh_interval),
        )

        lines = options.get(CONF_LINES) or []
        excluded = options.get(CONF_EXCLUDED_CATEGORIES) or []

        self.entry_data = entry_data
        self.options = options
        self.lines = list(lines)
        self.excluded_categories = [str(x) for x in excluded]

        self.api = NRWHimApi(
            session,
            lines=self.lines,
            excluded_categories=self.excluded_categories,
        )

    async def _async_update_data(self) -> list[NRWMessage]:
        """Meldungen abrufen."""
        try:
            messages = await self.api.fetch_messages()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Fehler bei der Abfrage von Zuginfo.nrw: {err}") from err

        if not messages and self.api.last_error:
            # Kein harter Fehler: die Quelle kann schlicht leer sein.
            _LOGGER.warning(
                "Keine Meldungen erhalten (%s). Behalte den letzten Stand.",
                self.api.last_error,
            )

        _LOGGER.debug(
            "%s Meldungen geladen (Linien: %s, ausgeschlossen: %s)",
            len(messages),
            self.lines or "alle",
            self.excluded_categories or "keine",
        )
        return messages

    @property
    def diagnostics(self) -> dict:
        """Angaben aus dem letzten Abruf, fuer den Diagnose-Dienst."""
        return {
            "lines": self.lines,
            "excluded_categories": self.excluded_categories,
            "refresh_minutes": self.update_interval.total_seconds() / 60
            if self.update_interval
            else None,
            "api": dict(getattr(self.api, "diagnostics", {}) or {}),
            "last_error": getattr(self.api, "last_error", None),
            "count": len(self.data or []),
        }
