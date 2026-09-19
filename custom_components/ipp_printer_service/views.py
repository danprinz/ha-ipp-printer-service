import logging
import os
import uuid

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)


class IPPPrintUploadView(HomeAssistantView):
    """View to handle file uploads for IPP printing."""

    url = "/api/ipp_printer_service/upload"
    name = "api:ipp_printer_service:upload"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Handle file upload."""
        try:
            reader = await request.multipart()
            file = await reader.next()

            if not file:
                return web.Response(status=400, text="No file uploaded")

            filename = file.filename
            if not filename.lower().endswith(".pdf"):
                return web.Response(status=400, text="Only PDF files are allowed")

            # Create a temporary directory if it doesn't exist
            temp_dir = request.app["hass"].config.path(
                "www", "ipp_printer_service_temp"
            )
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            # Generate a unique filename
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(temp_dir, unique_filename)

            # Write the file
            import aiofiles

            size = 0
            async with aiofiles.open(file_path, "wb") as f:
                while True:
                    chunk = await file.read_chunk()
                    if not chunk:
                        break
                    await f.write(chunk)
                    size += len(chunk)

            return web.json_response({"file_path": file_path})

        except Exception as e:
            _LOGGER.error(f"Error uploading file: {e}")
            return web.Response(status=500, text=str(e))
