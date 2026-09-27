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
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NRWRailStatusSensor(coordinator, entry)], True)


class NRWRailStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor that exposes the number of active disruptions."""

    _attr_name = "NRW Rail Status"
    _attr_icon = "mdi:train"
    _attr_state_class = SensorStateClass.MEASUREMENT

    # Beseitigt den Recorder-Fehler: Schließt das große "messages"-Attribut 
    # von der Datenbank-Speicherung aus, lässt es aber im RAM/Dashboard nutzbar.
    _unrecorded_attributes = frozenset({"messages"})

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def native_value(self) -> int:
        """Return number of active disruptions."""
        data = self.coordinator.data

        if not data:
            _LOGGER.debug("Sensor state: no data available, returning 0")
            return 0

        active_count = sum(1 for m in data if getattr(m, "active", False))
        _LOGGER.debug("Sensor state: %s active disruptions", active_count)
        return active_count

    @property
    def extra_state_attributes(self) -> dict:
        """Return detailed attributes for the disruptions list."""
        data = self.coordinator.data

        if not data:
            _LOGGER.debug("Sensor attributes: no data available")
            return {"messages": []}

        # Baut die Nachrichtenliste auf
        messages_list = [
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

        attributes = {"messages": messages_list}

        # Falls der erste Eintrag separat benötigt wird, greife auf die gefüllte Liste zurück,
        # statt die Objekte erneut mit getattr() abzufragen.
        if messages_list:
            first = messages_list[0]
            attributes.update(
                {
                    "first_id": first["id"],
                    "first_title": first["title"],
                    "first_text": first["text"],
                    "first_start": first["start"],
                    "first_end": first["end"],
                    "first_priority": first["priority"],
                    "first_comp": first["comp"],
                    "first_product": first["product"],
                    "first_active": first["active"],
                    "first_locations": first["locations"],
                    "first_products": first["products"],
                    "first_edges": first["edges"],
                    "first_events": first["events"],
                }
            )

        return attributes
