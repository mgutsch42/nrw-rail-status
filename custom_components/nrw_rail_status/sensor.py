"""Sensor platform for NRW Rail Status."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import NRWRailStatusDataUpdateCoordinator
from .const import DOMAIN, CONF_LINES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensoren anlegen."""
    coordinator: NRWRailStatusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    selected_lines = entry.options.get(CONF_LINES) or entry.data.get(CONF_LINES) or []

    entities: list[SensorEntity] = []
    if selected_lines:
        for line in selected_lines:
            entities.append(NRWRailStatusLineSensor(coordinator, line, entry))
    else:
        entities.append(NRWRailStatusOverviewSensor(coordinator, entry))

    async_add_entities(entities)


def _message_to_attributes(msg) -> dict[str, Any]:
    """Eine Meldung als Attribut-Datensatz.

    Enthaelt bewusst Zeitraum und Kategorie mit: gerade fuer anstehende
    Bauarbeiten sind das die entscheidenden Angaben.
    """
    return {
        "id": msg.id,
        "title": msg.title,
        "text": msg.text,
        "category": msg.category,
        "lines": msg.line_names,
        "published": msg.published_at,
        "period": msg.period,
        "period_start": msg.period_start,
        "period_end": msg.period_end,
        "url": msg.url,
    }


class NRWRailStatusOverviewSensor(
    CoordinatorEntity[NRWRailStatusDataUpdateCoordinator], SensorEntity
):
    """Sensor mit der Gesamtzahl aller Meldungen."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:train"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: NRWRailStatusDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Sensor anlegen."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_overview"
        self._attr_name = "NRW Rail Status Gesamt"

    @property
    def native_value(self) -> int:
        """Anzahl der Meldungen."""
        return len(self.coordinator.data) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Alle Meldungen als Liste."""
        data = self.coordinator.data or []
        return {
            "count": len(data),
            "messages": [_message_to_attributes(m) for m in data],
            # Kurzform fuer Markdown-Karten auf dem Dashboard
            "titles": [m.title for m in data],
        }


class NRWRailStatusLineSensor(
    CoordinatorEntity[NRWRailStatusDataUpdateCoordinator], SensorEntity
):
    """Sensor fuer eine bestimmte Linie."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:train"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: NRWRailStatusDataUpdateCoordinator,
        line: str,
        entry: ConfigEntry,
    ) -> None:
        """Sensor anlegen."""
        super().__init__(coordinator)
        self.line = line
        # Eindeutige ID ohne Sonderzeichen
        slug = line.lower().replace(" ", "_").replace("(", "").replace(")", "")
        self._attr_unique_id = f"{entry.entry_id}_line_{slug}"
        self._attr_name = f"NRW Rail Status {line}"

    def _get_line_messages(self) -> list:
        """Alle Meldungen, die diese Linie betreffen."""
        if not self.coordinator.data:
            return []
        return [m for m in self.coordinator.data if m.matches_line(self.line)]

    @property
    def native_value(self) -> int:
        """Anzahl der Meldungen zu dieser Linie."""
        return len(self._get_line_messages())

    @property
    def icon(self) -> str:
        """Zug-Symbol, bei Stoerungen ein Warndreieck."""
        return "mdi:alert" if self._get_line_messages() else "mdi:train"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Meldungen und Kurzangaben zu dieser Linie."""
        msgs = self._get_line_messages()
        bauarbeiten = [m for m in msgs if (m.category or "").lower() == "bauarbeiten"]

        return {
            "line": self.line,
            "disruption_count": len(msgs),
            "construction_count": len(bauarbeiten),
            # Erste Meldung einzeln, damit Karten sie direkt anzeigen koennen
            "first_title": msgs[0].title if msgs else None,
            "first_period": msgs[0].period if msgs else None,
            "first_url": msgs[0].url if msgs else None,
            "messages": [_message_to_attributes(m) for m in msgs],
            "titles": [m.title for m in msgs],
        }
