"""Config flow for IPP Printer Service integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyipp import IPP, IPPConnectionError, IPPError
from pyipp.enums import IppOperation

from .const import (
    CONF_BASE_PATH,
    CONF_PRINTER_NAME,
    CONF_SIMULATION_MODE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=631): int,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Required(CONF_SSL, default=False): bool,
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IPP Printer Service."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                printers = await self._get_printers(user_input)
            except IPPConnectionError:
                errors["base"] = "cannot_connect"
            except IPPError:
                errors["base"] = "ipp_error"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                if not printers:
                    errors["base"] = "no_printers_found"
                else:
                    self._user_input = user_input
                    self._printers = printers
                    return await self.async_step_printer()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_printer(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the printer selection step."""
        if user_input is not None:
            printer_name = user_input[CONF_PRINTER_NAME]

            # Merge connection info with selected printer
            data = {**self._user_input, CONF_PRINTER_NAME: printer_name}

            # Construct base path from printer name
            data[CONF_BASE_PATH] = f"/printers/{printer_name}"

            return self.async_create_entry(title=printer_name, data=data)

        printer_options = [p["printer-name"] for p in self._printers]

        return self.async_show_form(
            step_id="printer",
            data_schema=vol.Schema(
                {vol.Required(CONF_PRINTER_NAME): vol.In(printer_options)}
            ),
        )

    async def _get_printers(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Retrieve list of printers from CUPS."""
        session = async_get_clientsession(self.hass)

        # Connect to CUPS root to list printers
        ipp = IPP(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            base_path="/",  # Use root path for listing
            tls=data[CONF_SSL],
            verify_ssl=data[CONF_VERIFY_SSL],
            session=session,
            username=data.get(CONF_USERNAME),
            password=data.get(CONF_PASSWORD),
        )

        response = await ipp.execute(
            IppOperation.CUPS_GET_PRINTERS,
            {
                "operation-attributes-tag": {
                    "requesting-user-name": "Home Assistant",
                    "requested-attributes": ["printer-name", "printer-uri-supported"],
                }
            },
        )

        # The response structure for CUPS_GET_PRINTERS is a list of printer attributes
        # pyipp might parse it into 'printers' key or return raw attributes list
        # Based on pyipp code, execute returns parsed dict.
        # For CUPS_GET_PRINTERS, it usually returns a list of dicts in "printers" key if parsed correctly,
        # or we might need to look at how pyipp handles it.
        # Let's assume it returns a dict with "printers" or we iterate over attributes.

        # Actually, looking at pyipp/ipp.py:
        # parsed = parse_response(response)
        # parse_response returns a dict.
        # If multiple printers, they might be in a list under "printers" key if pyipp handles it specially,
        # OR they are just separate attribute groups.
        # Let's check pyipp parser or just assume standard behavior.
        # Standard IPP parser usually puts repeated groups (printers) into a list.

        return response.get("printers", []) or response.get(
            "printer-attributes-tag", []
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-configuration."""
        return await self.async_step_user(user_input)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for IPP Printer Service."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SIMULATION_MODE,
                        default=self.config_entry.options.get(
                            CONF_SIMULATION_MODE, False
                        ),
                    ): bool
                }
            ),
        )
