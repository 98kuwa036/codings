"""The CUPS integration."""
import logging
from datetime import timedelta
from typing import Any

from pyipp import IPP, IPPError
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_BASE_PATH,
    DEFAULT_BASE_PATH,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SERVICE_CANCEL_ALL_JOBS,
    SERVICE_CANCEL_JOB,
    SERVICE_PAUSE_JOB,
    SERVICE_PAUSE_PRINTER,
    SERVICE_RESUME_JOB,
    SERVICE_RESUME_PRINTER,
    UPDATE_INTERVAL,
)
from .ipp_operations import IPPOperations

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Service schemas
SERVICE_JOB_SCHEMA = vol.Schema(
    {
        vol.Required("job_id"): cv.positive_int,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CUPS from a config entry."""
    session = async_get_clientsession(
        hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    )

    ipp = IPP(
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        base_path=entry.data.get(CONF_BASE_PATH, DEFAULT_BASE_PATH),
        tls=entry.data.get(CONF_SSL, DEFAULT_SSL),
        session=session,
    )

    coordinator = CUPSDataUpdateCoordinator(hass, ipp)
    await coordinator.async_config_entry_first_refresh()

    # Create IPP operations handler for job management
    ipp_ops = IPPOperations(
        session=session,
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        base_path=entry.data.get(CONF_BASE_PATH, DEFAULT_BASE_PATH),
        tls=entry.data.get(CONF_SSL, DEFAULT_SSL),
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "ipp": ipp,
        "coordinator": coordinator,
        "ipp_ops": ipp_ops,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def handle_pause_printer(call: ServiceCall) -> None:
        """Handle pause printer service call."""
        _LOGGER.info("Pause printer service called for %s", entry.title)
        success = await ipp_ops.pause_printer()
        if success:
            _LOGGER.info("Successfully paused printer %s", entry.title)
            # Request coordinator refresh to update status
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to pause printer %s", entry.title)

    async def handle_resume_printer(call: ServiceCall) -> None:
        """Handle resume printer service call."""
        _LOGGER.info("Resume printer service called for %s", entry.title)
        success = await ipp_ops.resume_printer()
        if success:
            _LOGGER.info("Successfully resumed printer %s", entry.title)
            # Request coordinator refresh to update status
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to resume printer %s", entry.title)

    async def handle_cancel_all_jobs(call: ServiceCall) -> None:
        """Handle cancel all jobs service call."""
        _LOGGER.info("Cancel all jobs service called for %s", entry.title)
        success = await ipp_ops.purge_jobs()
        if success:
            _LOGGER.info("Successfully cancelled all jobs on printer %s", entry.title)
            # Request coordinator refresh to update queue
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to cancel all jobs on printer %s", entry.title)

    async def handle_pause_job(call: ServiceCall) -> None:
        """Handle pause job service call."""
        job_id = call.data.get("job_id")
        _LOGGER.info("Pause job %s service called for %s", job_id, entry.title)
        success = await ipp_ops.hold_job(job_id)
        if success:
            _LOGGER.info(
                "Successfully paused job %s on printer %s", job_id, entry.title
            )
            # Request coordinator refresh to update queue
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to pause job %s on printer %s", job_id, entry.title
            )

    async def handle_resume_job(call: ServiceCall) -> None:
        """Handle resume job service call."""
        job_id = call.data.get("job_id")
        _LOGGER.info("Resume job %s service called for %s", job_id, entry.title)
        success = await ipp_ops.release_job(job_id)
        if success:
            _LOGGER.info(
                "Successfully resumed job %s on printer %s", job_id, entry.title
            )
            # Request coordinator refresh to update queue
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to resume job %s on printer %s", job_id, entry.title
            )

    async def handle_cancel_job(call: ServiceCall) -> None:
        """Handle cancel job service call."""
        job_id = call.data.get("job_id")
        _LOGGER.info("Cancel job %s service called for %s", job_id, entry.title)
        success = await ipp_ops.cancel_job(job_id)
        if success:
            _LOGGER.info(
                "Successfully cancelled job %s on printer %s", job_id, entry.title
            )
            # Request coordinator refresh to update queue
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to cancel job %s on printer %s", job_id, entry.title
            )

    # Register services only once
    if not hass.services.has_service(DOMAIN, SERVICE_PAUSE_PRINTER):
        hass.services.async_register(
            DOMAIN, SERVICE_PAUSE_PRINTER, handle_pause_printer
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RESUME_PRINTER):
        hass.services.async_register(
            DOMAIN, SERVICE_RESUME_PRINTER, handle_resume_printer
        )

    if not hass.services.has_service(DOMAIN, SERVICE_CANCEL_ALL_JOBS):
        hass.services.async_register(
            DOMAIN, SERVICE_CANCEL_ALL_JOBS, handle_cancel_all_jobs
        )

    if not hass.services.has_service(DOMAIN, SERVICE_PAUSE_JOB):
        hass.services.async_register(
            DOMAIN, SERVICE_PAUSE_JOB, handle_pause_job, schema=SERVICE_JOB_SCHEMA
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RESUME_JOB):
        hass.services.async_register(
            DOMAIN, SERVICE_RESUME_JOB, handle_resume_job, schema=SERVICE_JOB_SCHEMA
        )

    if not hass.services.has_service(DOMAIN, SERVICE_CANCEL_JOB):
        hass.services.async_register(
            DOMAIN, SERVICE_CANCEL_JOB, handle_cancel_job, schema=SERVICE_JOB_SCHEMA
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # Unregister services if this is the last entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_PAUSE_PRINTER)
            hass.services.async_remove(DOMAIN, SERVICE_RESUME_PRINTER)
            hass.services.async_remove(DOMAIN, SERVICE_CANCEL_ALL_JOBS)
            hass.services.async_remove(DOMAIN, SERVICE_PAUSE_JOB)
            hass.services.async_remove(DOMAIN, SERVICE_RESUME_JOB)
            hass.services.async_remove(DOMAIN, SERVICE_CANCEL_JOB)

    return unload_ok


class CUPSDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching CUPS printer data."""

    def __init__(self, hass: HomeAssistant, ipp: IPP) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.ipp = ipp

    async def _async_update_data(self):
        """Fetch data from IPP."""
        try:
            printer = await self.ipp.printer()

            _LOGGER.debug(
                "Fetched printer data: %s (state: %s)",
                printer.info.name,
                printer.state.printer_state,
            )

            # Log marker levels for debugging
            if printer.markers:
                for marker in printer.markers:
                    _LOGGER.debug(
                        "Marker: %s (%s %s) - Level: %s%%",
                        marker.name,
                        marker.color,
                        marker.marker_type,
                        marker.level,
                    )

            return {
                "printer": printer,
            }

        except IPPError as err:
            raise UpdateFailed(f"Error communicating with printer: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
