"""Sensor platform for NRW Rail Status."""

from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the NRW Rail Status sensor from a config entry."""
    # Greife korrekt über die entry_id auf den Coordinator zu
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NRWRailStatusSensor(coordinator, entry)], True)


class NRWRailStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor that exposes the number of active disruptions."""

    _attr_name = "NRW Rail Status"
    _attr_icon = "mdi:train"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        # Dynamische Unique-ID basierend auf der ConfigEntry-ID verhindern Duplikate
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def native_value(self) -> int:
        """Return number of active disruptions."""
        data = self.coordinator.data

        if not data:
            _LOGGER.debug("Sensor state: no data available, returning 0")
            return 0

        # Zählt aktive Störungen
        active_count = sum(1 for m in data if getattr(m, "active", False))
        _LOGGER.debug("Sensor state: %s active disruptions", active_count)
        return active_count

    @property
    def extra_state_attributes(self) -> dict:
        """Return detailed attributes for the first disruption and full list."""
        data = self.coordinator.data

        if not data:
            _LOGGER.debug("Sensor attributes: no data available")
            return {"messages": []}

        # Falls Daten vorhanden sind, sichere Abfrage des ersten Eintrags
        first = data[0] if len(data) > 0 else None

        attributes = {
            "messages": [
                {
                    "id": getattr(m, "id", None),
                    "title": getattr(m, "title", ""),
                    "text": getattr(m, "text", ""),
                    "start": f"{getattr(m, 'start_date', '')} {getattr(m, 'start_time', '')}".strip(),
                    "end": f"{getattr(m, 'end_date', '')} {getattr(m, 'end_time', '')}".strip(),
                    "priority": getattr(m, "priority", None),
                    "comp": getattr(m, "comp", None),
                    "product": getattr(m, "product", None),
                    "active": getattr(m, "active", False),
                    "locations": getattr(m, "locations", []),
                    "products": getattr(m, "products", []),
                    "edges": getattr(m, "edges", []),
                    "events": getattr(m, "events", []),
                }
                for m in data
            ]
        }

        # Ergänze First-Meldungs-Attribute nur, wenn tatsächlich mindestens 1 Element existiert
        if first:
            attributes.update(
                {
                    "first_id": getattr(first, "id", None),
                    "first_title": getattr(first, "title", ""),
                    "first_text": getattr(first, "text", ""),
                    "first_start": f"{getattr(first, 'start_date', '')} {getattr(first, 'start_time', '')}".strip(),
                    "first_end": f"{getattr(first, 'end_date', '')} {getattr(first, 'end_time', '')}".strip(),
                    "first_priority": getattr(first, "priority", None),
                    "first_comp": getattr(first, "comp", None),
                    "first_product": getattr(first, "product", None),
                    "first_active": getattr(first, "first_active", getattr(first, "active", False)),
                    "first_locations": getattr(first, "locations", []),
                    "first_products": getattr(first, "products", []),
                    "first_edges": getattr(first, "edges", []),
                    "first_events": getattr(first, "events", []),
                }
            )

        return attributes
