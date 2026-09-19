"""The IPP Printer Service integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import IPPPrinterServiceCoordinator
from .services import async_setup_services
from .views import IPPPrintUploadView

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IPP Printer Service from a config entry."""
    _LOGGER.info("Setting up IPP Printer Service entry")

    coordinator = IPPPrinterServiceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Register services (global)
    await async_setup_services(hass)

    # Register view (global)
    # Check if view is already registered to avoid duplicates on reload
    # Note: hass.http.register_view doesn't have a check method, but it's safe to call multiple times
    # if the view class handles it or if we just do it once.
    # Ideally, views are registered once per HA lifetime, but here we do it on entry setup.
    # A better place might be async_setup, but we want to ensure it's active when the integration is.
    hass.http.register_view(IPPPrintUploadView())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register frontend resources
    try:
        from homeassistant.components.http import StaticPathConfig

        # Register static path for frontend resources
        www_path = hass.config.path("custom_components/ipp_printer_service/www")
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/hacsfiles/ipp_printer_service", www_path, cache_headers=False
                )
            ]
        )

    except ImportError:
        # Fallback for older HA versions
        hass.http.register_static_path(
            "/hacsfiles/ipp_printer_service",
            hass.config.path("custom_components/ipp_printer_service/www"),
            cache_headers=False,
        )

    # Note: Lovelace resources must be manually added by users
    _LOGGER.info(
        "IPP Printer Service frontend resources are available at /hacsfiles/ipp_printer_service/. "
        "Please add the card manually to your Lovelace resources if needed."
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
