"""Sensor platform for IPP Printer Service."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PRINTER_NAME, DOMAIN
from .coordinator import IPPPrinterServiceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPP Printer Service sensor."""
    coordinator: IPPPrinterServiceCoordinator = entry.runtime_data
    async_add_entities(
        [
            IPPPrinterSensor(coordinator, entry),
            IPPLastJobSensor(coordinator, entry),
        ]
    )


class IPPPrinterSensor(CoordinatorEntity[IPPPrinterServiceCoordinator], SensorEntity):
    """Representation of an IPP Printer Sensor."""

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:printer"

    def __init__(
        self,
        coordinator: IPPPrinterServiceCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = entry.entry_id

        host = entry.data.get(CONF_HOST)
        port = entry.data.get(CONF_PORT)
        name = entry.data.get(CONF_PRINTER_NAME)

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "CUPS",
            "model": "IPP Printer",
            "configuration_url": f"http://{host}:{port}/printers/{name}"
            if host and port and name
            else None,
            "via_device": (DOMAIN, entry.entry_id),
        }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if self.coordinator.data and self.coordinator.data.printer:
            return self.coordinator.data.printer.state.printer_state
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if self.coordinator.data and self.coordinator.data.printer:
            return {
                "message": self.coordinator.data.printer.state.message,
                "reasons": self.coordinator.data.printer.state.reasons,
            }
        return {}


class IPPLastJobSensor(CoordinatorEntity[IPPPrinterServiceCoordinator], SensorEntity):
    """Representation of the Last Print Job Diagnostic Sensor."""

    _attr_has_entity_name = True
    _attr_name = "Last Print Job"
    _attr_icon = "mdi:file-document-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: IPPPrinterServiceCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_last_print_job"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if self.coordinator.data and self.coordinator.data.last_print_job:
            return self.coordinator.data.last_print_job.get("file_path")
        return "None"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if self.coordinator.data and self.coordinator.data.last_print_job:
            return self.coordinator.data.last_print_job
        return {}
