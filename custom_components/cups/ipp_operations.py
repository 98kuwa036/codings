"""IPP operations for CUPS integration."""
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# IPP operation IDs
IPP_OP_PAUSE_PRINTER = 0x0010
IPP_OP_RESUME_PRINTER = 0x0011
IPP_OP_PURGE_JOBS = 0x0012
IPP_OP_HOLD_JOB = 0x000C
IPP_OP_RELEASE_JOB = 0x000D
IPP_OP_CANCEL_JOB = 0x0008
IPP_OP_GET_JOBS = 0x000A

# IPP version
IPP_VERSION_1_1 = (1, 1)
IPP_VERSION_2_0 = (2, 0)

# IPP tags
IPP_TAG_OPERATION = 0x01
IPP_TAG_END = 0x03
IPP_TAG_URI = 0x45
IPP_TAG_INTEGER = 0x21
IPP_TAG_CHARSET = 0x47
IPP_TAG_LANGUAGE = 0x48
IPP_TAG_NAME = 0x42


class IPPOperationError(Exception):
    """Exception raised for IPP operation errors."""


class IPPOperations:
    """Handle IPP operations for printer and job management."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        base_path: str,
        tls: bool,
    ) -> None:
        """Initialize IPP operations handler."""
        self.session = session
        self.host = host
        self.port = port
        self.base_path = base_path
        self.tls = tls
        self._scheme = "https" if tls else "http"
        self._printer_uri = f"ipp{'s' if tls else ''}://{host}:{port}{base_path}"

    def _build_ipp_request(
        self,
        operation_id: int,
        request_id: int,
        attributes: dict[str, Any],
    ) -> bytes:
        """Build an IPP request packet."""
        # IPP version (2 bytes)
        version = IPP_VERSION_2_0
        request = bytearray()
        request.extend(version)

        # Operation ID (2 bytes)
        request.extend(operation_id.to_bytes(2, byteorder="big"))

        # Request ID (4 bytes)
        request.extend(request_id.to_bytes(4, byteorder="big"))

        # Operation attributes tag
        request.append(IPP_TAG_OPERATION)

        # charset attribute (required)
        self._add_attribute(
            request,
            IPP_TAG_CHARSET,
            "attributes-charset",
            "utf-8",
        )

        # natural-language attribute (required)
        self._add_attribute(
            request,
            IPP_TAG_LANGUAGE,
            "attributes-natural-language",
            "en",
        )

        # printer-uri or job-uri attribute (required)
        if "printer-uri" in attributes:
            self._add_attribute(
                request,
                IPP_TAG_URI,
                "printer-uri",
                attributes["printer-uri"],
            )

        if "job-uri" in attributes:
            self._add_attribute(
                request,
                IPP_TAG_URI,
                "job-uri",
                attributes["job-uri"],
            )

        # job-id attribute (for job operations)
        if "job-id" in attributes:
            self._add_integer_attribute(
                request,
                "job-id",
                attributes["job-id"],
            )

        # requesting-user-name (optional but recommended)
        if "requesting-user-name" in attributes:
            self._add_attribute(
                request,
                IPP_TAG_NAME,
                "requesting-user-name",
                attributes["requesting-user-name"],
            )

        # End of attributes
        request.append(IPP_TAG_END)

        return bytes(request)

    def _add_attribute(
        self,
        request: bytearray,
        tag: int,
        name: str,
        value: str,
    ) -> None:
        """Add a string attribute to IPP request."""
        # Value tag
        request.append(tag)

        # Name length (2 bytes)
        name_bytes = name.encode("utf-8")
        request.extend(len(name_bytes).to_bytes(2, byteorder="big"))

        # Name
        request.extend(name_bytes)

        # Value length (2 bytes)
        value_bytes = value.encode("utf-8")
        request.extend(len(value_bytes).to_bytes(2, byteorder="big"))

        # Value
        request.extend(value_bytes)

    def _add_integer_attribute(
        self,
        request: bytearray,
        name: str,
        value: int,
    ) -> None:
        """Add an integer attribute to IPP request."""
        # Value tag
        request.append(IPP_TAG_INTEGER)

        # Name length (2 bytes)
        name_bytes = name.encode("utf-8")
        request.extend(len(name_bytes).to_bytes(2, byteorder="big"))

        # Name
        request.extend(name_bytes)

        # Value length (2 bytes) - integers are always 4 bytes
        request.extend((4).to_bytes(2, byteorder="big"))

        # Value (4 bytes)
        request.extend(value.to_bytes(4, byteorder="big", signed=True))

    def _parse_ipp_response(self, response_data: bytes) -> dict[str, Any]:
        """Parse an IPP response packet."""
        if len(response_data) < 8:
            raise IPPOperationError("Response too short")

        # Parse version (2 bytes)
        version = (response_data[0], response_data[1])

        # Parse status code (2 bytes)
        status_code = int.from_bytes(response_data[2:4], byteorder="big")

        # Parse request ID (4 bytes)
        request_id = int.from_bytes(response_data[4:8], byteorder="big")

        _LOGGER.debug(
            "IPP response: version=%s, status=0x%04x, request_id=%d",
            version,
            status_code,
            request_id,
        )

        # Check status code
        # 0x0000 = successful-ok
        # 0x0001 = successful-ok-ignored-or-substituted-attributes
        # 0x0002 = successful-ok-conflicting-attributes
        if status_code > 0x00FF:
            raise IPPOperationError(
                f"IPP operation failed with status code 0x{status_code:04x}"
            )

        return {
            "version": version,
            "status_code": status_code,
            "request_id": request_id,
        }

    async def _send_ipp_request(
        self,
        operation_id: int,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        """Send an IPP request and parse the response."""
        import random

        request_id = random.randint(1, 2147483647)

        # Build request
        request_data = self._build_ipp_request(operation_id, request_id, attributes)

        # Send request
        url = f"{self._scheme}://{self.host}:{self.port}{self.base_path}"

        _LOGGER.debug("Sending IPP operation 0x%04x to %s", operation_id, url)

        try:
            async with self.session.post(
                url,
                data=request_data,
                headers={
                    "Content-Type": "application/ipp",
                },
            ) as response:
                response.raise_for_status()
                response_data = await response.read()

                # Parse response
                result = self._parse_ipp_response(response_data)

                _LOGGER.debug("IPP operation successful: %s", result)

                return result

        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error during IPP operation: %s", err)
            raise IPPOperationError(f"HTTP error: {err}") from err

    async def pause_printer(self, requesting_user: str = "home-assistant") -> bool:
        """Pause the printer."""
        attributes = {
            "printer-uri": self._printer_uri,
            "requesting-user-name": requesting_user,
        }

        try:
            await self._send_ipp_request(IPP_OP_PAUSE_PRINTER, attributes)
            return True
        except IPPOperationError as err:
            _LOGGER.error("Failed to pause printer: %s", err)
            return False

    async def resume_printer(self, requesting_user: str = "home-assistant") -> bool:
        """Resume the printer."""
        attributes = {
            "printer-uri": self._printer_uri,
            "requesting-user-name": requesting_user,
        }

        try:
            await self._send_ipp_request(IPP_OP_RESUME_PRINTER, attributes)
            return True
        except IPPOperationError as err:
            _LOGGER.error("Failed to resume printer: %s", err)
            return False

    async def purge_jobs(self, requesting_user: str = "home-assistant") -> bool:
        """Cancel all jobs on the printer."""
        attributes = {
            "printer-uri": self._printer_uri,
            "requesting-user-name": requesting_user,
        }

        try:
            await self._send_ipp_request(IPP_OP_PURGE_JOBS, attributes)
            return True
        except IPPOperationError as err:
            _LOGGER.error("Failed to purge jobs: %s", err)
            return False

    async def hold_job(
        self,
        job_id: int,
        requesting_user: str = "home-assistant",
    ) -> bool:
        """Pause a specific job."""
        job_uri = f"{self._printer_uri}/{job_id}"
        attributes = {
            "job-uri": job_uri,
            "job-id": job_id,
            "requesting-user-name": requesting_user,
        }

        try:
            await self._send_ipp_request(IPP_OP_HOLD_JOB, attributes)
            return True
        except IPPOperationError as err:
            _LOGGER.error("Failed to hold job %d: %s", job_id, err)
            return False

    async def release_job(
        self,
        job_id: int,
        requesting_user: str = "home-assistant",
    ) -> bool:
        """Resume a paused job."""
        job_uri = f"{self._printer_uri}/{job_id}"
        attributes = {
            "job-uri": job_uri,
            "job-id": job_id,
            "requesting-user-name": requesting_user,
        }

        try:
            await self._send_ipp_request(IPP_OP_RELEASE_JOB, attributes)
            return True
        except IPPOperationError as err:
            _LOGGER.error("Failed to release job %d: %s", job_id, err)
            return False

    async def cancel_job(
        self,
        job_id: int,
        requesting_user: str = "home-assistant",
    ) -> bool:
        """Cancel a specific job."""
        job_uri = f"{self._printer_uri}/{job_id}"
        attributes = {
            "job-uri": job_uri,
            "job-id": job_id,
            "requesting-user-name": requesting_user,
        }

        try:
            await self._send_ipp_request(IPP_OP_CANCEL_JOB, attributes)
            return True
        except IPPOperationError as err:
            _LOGGER.error("Failed to cancel job %d: %s", job_id, err)
            return False
