"""Binary sensor platform for IPP Printer Service."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SIMULATION_MODE, DOMAIN
from .coordinator import IPPPrinterServiceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IPP Printer Service binary sensor."""
    coordinator: IPPPrinterServiceCoordinator = entry.runtime_data
    async_add_entities([IPPSimulationModeSensor(coordinator, entry)])


class IPPSimulationModeSensor(
    CoordinatorEntity[IPPPrinterServiceCoordinator], BinarySensorEntity
):
    """Representation of an IPP Simulation Mode Binary Sensor."""

    _attr_has_entity_name = True
    _attr_name = "Simulation Mode"
    _attr_icon = "mdi:test-tube"

    def __init__(
        self,
        coordinator: IPPPrinterServiceCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_simulation_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "CUPS",
            "model": "IPP Printer",
        }

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._entry.options.get(CONF_SIMULATION_MODE, False)
