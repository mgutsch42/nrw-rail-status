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
    """Set up NRW Rail Status sensors based on config entry."""
    coordinator: NRWRailStatusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    selected_lines = entry.options.get(CONF_LINES) or entry.data.get(CONF_LINES) or []

    entities = []
    if selected_lines:
        for line in selected_lines:
            entities.append(NRWRailStatusLineSensor(coordinator, line, entry))
    else:
        entities.append(NRWRailStatusOverviewSensor(coordinator, entry))

    async_add_entities(entities)


class NRWRailStatusOverviewSensor(
    CoordinatorEntity[NRWRailStatusDataUpdateCoordinator], SensorEntity
):
    """Sensor showing overall messages count."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:train"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: NRWRailStatusDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_overview"
        self._attr_name = "NRW Rail Status Gesamt"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {"messages": []}

        return {
            "messages": [
                {
                    "id": m.id,
                    "title": m.title,
                    "text": m.text,
                    "products": [p.get("name") for p in m.products if p.get("name")],
                }
                for m in self.coordinator.data
            ]
        }


class NRWRailStatusLineSensor(
    CoordinatorEntity[NRWRailStatusDataUpdateCoordinator], SensorEntity
):
    """Sensor for a specific train/bus line."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:train"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: NRWRailStatusDataUpdateCoordinator,
        line: str,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.line = line
        self._attr_unique_id = f"{entry.entry_id}_line_{line.lower()}"
        self._attr_name = f"NRW Rail Status {line}"

    @property
    def native_value(self) -> int:
        return len(self._get_line_messages())

    def _get_line_messages(self) -> list:
        if not self.coordinator.data:
            return []

        line_msgs = []
        for msg in self.coordinator.data:
            for prod in msg.products:
                prod_name = (prod.get("name") or "").upper().replace(" ", "")
                line_name = self.line.upper().replace(" ", "")
                if line_name in prod_name or prod_name in line_name:
                    line_msgs.append(msg)
                    break
        return line_msgs

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        msgs = self._get_line_messages()
        return {
            "disruption_count": len(msgs),
            "messages": [{"id": m.id, "title": m.title, "text": m.text} for m in msgs],
        }
