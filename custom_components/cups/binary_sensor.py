"""Support for CUPS binary sensors."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_PRINTER_STATE,
    ATTR_PRINTER_STATE_MESSAGE,
    ATTR_PRINTER_STATE_REASONS,
    DOMAIN,
    PRINTER_STATE_STOPPED,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CUPS binary sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    binary_sensors = [
        CUPSConnectivitySensor(coordinator, entry),
    ]

    _LOGGER.info(
        "Added %d binary sensor entities for printer %s",
        len(binary_sensors),
        entry.title,
    )
    async_add_entities(binary_sensors)


class CUPSBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for CUPS binary sensors."""

    def __init__(self, coordinator, entry):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        """Return device information."""
        printer = self.coordinator.data.get("printer")
        if not printer:
            return None

        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": printer.info.name or self._entry.title,
            "manufacturer": (
                printer.info.make_and_model.split()[0]
                if printer.info.make_and_model
                else "Unknown"
            ),
            "model": printer.info.make_and_model or "Unknown",
            "sw_version": printer.info.printer_firmware_string_version,
            "configuration_url": (
                printer.info.printer_uri_supported[0]
                if printer.info.printer_uri_supported
                else None
            ),
        }


class CUPSConnectivitySensor(CUPSBinarySensorBase):
    """Representation of a CUPS printer connectivity sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Connectivity"
        self._attr_unique_id = f"{entry.entry_id}_connectivity"

    @property
    def is_on(self):
        """Return true if the printer is online."""
        printer = self.coordinator.data.get("printer")
        if not printer:
            return False

        # Printer is considered offline if state is STOPPED and has specific reasons
        if printer.state.printer_state == PRINTER_STATE_STOPPED:
            # Check if stopped due to connectivity issues
            reasons = printer.state.printer_state_reasons or []
            offline_reasons = [
                "connecting-to-device",
                "offline-report",
                "shutdown",
            ]
            for reason in reasons:
                if any(offline in reason.lower() for offline in offline_reasons):
                    return False

        # If we can get printer data, it's online
        return True

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        printer = self.coordinator.data.get("printer")
        if not printer:
            return {}

        return {
            ATTR_PRINTER_STATE: printer.state.printer_state,
            ATTR_PRINTER_STATE_MESSAGE: printer.state.printer_state_message,
            ATTR_PRINTER_STATE_REASONS: printer.state.printer_state_reasons,
        }
