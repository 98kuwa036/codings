"""The Nature Remo integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NatureRemoAPI
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.REMOTE,
    Platform.SWITCH,
    Platform.LIGHT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nature Remo from a config entry."""
    access_token = entry.data[CONF_ACCESS_TOKEN]
    session = async_get_clientsession(hass)
    api = NatureRemoAPI(access_token, session)

    coordinator = NatureRemoDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class NatureRemoDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Nature Remo data."""

    def __init__(self, hass: HomeAssistant, api: NatureRemoAPI) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            devices = await self.api.get_devices()
            appliances = await self.api.get_appliances()

            _LOGGER.debug("Fetched %d devices from Nature Remo API", len(devices))
            _LOGGER.debug("Fetched %d appliances from Nature Remo API", len(appliances))

            # Log appliance types for debugging
            for appliance in appliances:
                _LOGGER.debug(
                    "Appliance: %s (type: %s, id: %s)",
                    appliance.get("nickname"),
                    appliance.get("type"),
                    appliance.get("id"),
                )

            return {
                "devices": devices,
                "appliances": appliances,
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
