"""Coordinator for IPP Printer Service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class IPPPrinterServiceData:
    """Data for IPP Printer Service."""

    printer: Any
    last_print_job: dict[str, Any] | None = None


class IPPPrinterServiceCoordinator(DataUpdateCoordinator[IPPPrinterServiceData]):
    """Class to manage fetching IPP data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
            config_entry=entry,
        )
        self.data = IPPPrinterServiceData(printer=None)

    async def _async_update_data(self) -> IPPPrinterServiceData:
        """Update data via library."""
        from homeassistant.const import (
            CONF_HOST,
            CONF_PASSWORD,
            CONF_PORT,
            CONF_SSL,
            CONF_USERNAME,
            CONF_VERIFY_SSL,
        )
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        from pyipp import IPP, IPPError

        from .const import CONF_BASE_PATH

        data = self.config_entry.data
        session = async_get_clientsession(self.hass)

        ipp = IPP(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            base_path=data[CONF_BASE_PATH],
            tls=data[CONF_SSL],
            verify_ssl=data[CONF_VERIFY_SSL],
            session=session,
            username=data.get(CONF_USERNAME),
            password=data.get(CONF_PASSWORD),
        )

        try:
            printer = await ipp.printer()
            # Preserve last print job if it exists
            last_job = self.data.last_print_job if self.data else None
            return IPPPrinterServiceData(printer=printer, last_print_job=last_job)
        except IPPError as error:
            raise UpdateFailed(error) from error

    @callback
    def async_set_last_job(self, job_details: dict[str, Any]) -> None:
        """Update the last print job details."""
        if self.data:
            self.data.last_print_job = job_details
            self.async_update_listeners()
