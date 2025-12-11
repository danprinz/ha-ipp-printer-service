import logging
import tempfile
from datetime import datetime
from pathlib import Path

import aiofiles
from aiohttp import ClientError
from pyipp import IPP
from pyipp.enums import IppOperation
from pyipp.exceptions import IPPError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SIMULATION_MODE

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant):
    """Set up the IPP Printer Service services."""

    async def async_print_pdf(call: ServiceCall):
        """Handle the print_pdf service call."""
        entity_id = call.data.get("entity_id")
        file_path_template = call.data.get("file_path")
        is_local_path = call.data.get("is_local_path", False)
        copies = call.data.get("copies", 1)

        if not isinstance(file_path_template, str):
            raise HomeAssistantError("File path must be a string template")

        from homeassistant.helpers import template
        from homeassistant.helpers.network import get_url

        tpl = template.Template(file_path_template, hass)
        file_path = tpl.async_render(parse_result=False)

        if not entity_id:
            raise HomeAssistantError("Entity ID is required")
        if not file_path:
            raise HomeAssistantError("File path is required")

        if is_local_path:
            # Make sure it starts with / if not already
            if not file_path.startswith("/"):
                file_path = f"/{file_path}"

            # Use local loopback for safety and speed
            # We assume standard port 8123 or try to fetch it
            try:
                base_url = get_url(
                    hass, allow_external=False, allow_ip=True, allow_cloud=False
                )
            except Exception:
                # Fallback if get_url can't determine it easily (e.g. strict setup)
                # But usually 127.0.0.1:8123 is a safe bet for internal calls if not behind weird proxy
                base_url = "http://127.0.0.1:8123"

            file_path = f"{base_url}{file_path}"
            _LOGGER.debug("Converted local path to URL: %s", file_path)

        # Handle URL download
        is_url = file_path.startswith(("http://", "https://"))
        msg_file_path = file_path  # For logging purposes

        if is_url:
            session = async_get_clientsession(hass)
            try:
                async with session.get(file_path) as response:
                    response.raise_for_status()
                    content = await response.read()

                    # Create a temporary file
                    # We use delete=False because we need to close it before
                    # passing to the rest of the logic which opens it again
                    # and eventually deletes it
                    with tempfile.NamedTemporaryFile(
                        suffix=".pdf", delete=False
                    ) as tmp:
                        tmp.write(content)
                        file_path = tmp.name

                    _LOGGER.info(
                        "Downloaded %s to temporary file %s", msg_file_path, file_path
                    )

            except (ClientError, OSError) as err:
                raise HomeAssistantError(
                    f"Failed to download file from {msg_file_path}: {err}"
                ) from err
        elif not Path(file_path).exists():
            raise HomeAssistantError(f"File not found: {file_path}")

        registry = er.async_get(hass)
        entry = registry.async_get(entity_id)

        # Helper to clean up temp file if something goes wrong
        def cleanup_temp_file():
            if is_url:
                try:
                    path_obj = Path(file_path)
                    if path_obj.exists():
                        path_obj.unlink()
                except OSError as cleanup_err:
                    _LOGGER.warning(
                        "Failed to remove temporary file %s: %s", file_path, cleanup_err
                    )

        if not entry:
            cleanup_temp_file()
            raise HomeAssistantError(f"Entity not found: {entity_id}")

        if not entry.config_entry_id:
            cleanup_temp_file()
            raise HomeAssistantError(
                f"Entity {entity_id} is not linked to a config entry"
            )

        config_entry = hass.config_entries.async_get_entry(entry.config_entry_id)

        if not config_entry:
            cleanup_temp_file()
            raise HomeAssistantError(f"Config entry not found for {entity_id}")

        if config_entry.domain != "ipp_printer_service":
            cleanup_temp_file()
            raise HomeAssistantError(
                f"Entity {entity_id} is not an IPP Printer Service entity"
            )

        # Check for simulation mode
        if config_entry.options.get(CONF_SIMULATION_MODE, False):
            _LOGGER.info(
                "Simulation mode active. Printing %d copies of %s simulated.",
                copies,
                msg_file_path,
            )
            coordinator = config_entry.runtime_data
            coordinator.async_set_last_job(
                {
                    "entity_id": entity_id,
                    "file_path": msg_file_path,  # Log the original path/URL
                    "copies": copies,
                    "timestamp": str(datetime.now()),
                    "status": "simulated",
                }
            )
            # Cleanup
            try:
                path_obj = Path(file_path)
                if path_obj.exists():
                    path_obj.unlink()
            except Exception as e:
                _LOGGER.warning("Failed to remove temporary file %s: %s", file_path, e)
            return

        # Create a fresh IPP client using config entry data
        host = config_entry.data.get(CONF_HOST)
        port = config_entry.data.get(CONF_PORT)
        base_path = config_entry.data.get("base_path")
        ssl = config_entry.data.get(CONF_SSL, False)
        verify_ssl = config_entry.data.get(CONF_VERIFY_SSL, True)
        username = config_entry.data.get("username")
        password = config_entry.data.get("password")

        session = async_get_clientsession(hass)

        ipp = IPP(
            host=host,
            port=port,
            base_path=base_path,
            tls=ssl,
            verify_ssl=verify_ssl,
            session=session,
            username=username,
            password=password,
        )

        try:
            async with aiofiles.open(file_path, "rb") as f:
                content = await f.read()

            _LOGGER.info(
                "Printing %d copies of %s to %s:%s%s (SSL=%s)",
                copies,
                msg_file_path,
                host,
                port,
                base_path,
                ssl,
            )

            message = {
                "operation-attributes-tag": {
                    "requesting-user-name": "Home Assistant",
                    "job-name": "Attendance Doc",
                    "document-format": "application/pdf",
                    "copies": copies,
                },
                "data": content,
            }

            await ipp.execute(IppOperation.PRINT_JOB, message)
            _LOGGER.info(
                "Successfully printed %d copies of %s to %s",
                copies,
                msg_file_path,
                entity_id,
            )

            # Update last job for real prints too
            coordinator = config_entry.runtime_data
            coordinator.async_set_last_job(
                {
                    "entity_id": entity_id,
                    "file_path": msg_file_path,
                    "copies": copies,
                    "timestamp": str(datetime.now()),
                    "status": "success",
                }
            )

        except Exception as e:
            _LOGGER.error("Failed to print %s: %s", msg_file_path, e)
            raise HomeAssistantError(f"Failed to print: {e}") from e
        finally:
            # Cleanup the file
            try:
                path_obj = Path(file_path)
                if path_obj.exists():
                    path_obj.unlink()
            except Exception as e:
                _LOGGER.warning("Failed to remove temporary file %s: %s", file_path, e)

    hass.services.async_register("ipp_printer_service", "print_pdf", async_print_pdf)
