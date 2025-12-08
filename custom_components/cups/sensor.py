"""Support for CUPS printer sensors."""
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_MARKER_COLOR,
    ATTR_MARKER_INDEX,
    ATTR_MARKER_LEVEL,
    ATTR_MARKER_NAME,
    ATTR_MARKER_TYPE,
    ATTR_PRINTER_INFO,
    ATTR_PRINTER_LOCATION,
    ATTR_PRINTER_MAKE_MODEL,
    ATTR_PRINTER_NAME,
    ATTR_PRINTER_STATE,
    ATTR_PRINTER_STATE_MESSAGE,
    ATTR_PRINTER_STATE_REASONS,
    ATTR_PRINTER_URI,
    ATTR_SERIAL_NUMBER,
    ATTR_UPTIME,
    DOMAIN,
    PRINTER_STATE_IDLE,
    PRINTER_STATE_PROCESSING,
    PRINTER_STATE_STOPPED,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CUPS sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    sensors = []

    # Add printer state sensor
    sensors.append(CUPSPrinterStateSensor(coordinator, entry))

    # Add marker sensors (ink/toner levels)
    printer = coordinator.data.get("printer")
    if printer and printer.markers:
        for index, marker in enumerate(printer.markers):
            sensors.append(CUPSMarkerLevelSensor(coordinator, entry, index))

    # Add queue length sensor
    sensors.append(CUPSQueueLengthSensor(coordinator, entry))

    _LOGGER.info("Added %d sensor entities for printer %s", len(sensors), entry.title)
    async_add_entities(sensors)


class CUPSSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for CUPS sensors."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
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
            "manufacturer": printer.info.make_and_model.split()[0] if printer.info.make_and_model else "Unknown",
            "model": printer.info.make_and_model or "Unknown",
            "sw_version": printer.info.printer_firmware_string_version,
            "configuration_url": printer.info.printer_uri_supported[0] if printer.info.printer_uri_supported else None,
        }


class CUPSPrinterStateSensor(CUPSSensorBase):
    """Representation of a CUPS printer state sensor."""

    _attr_icon = "mdi:printer"

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Status"
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        printer = self.coordinator.data.get("printer")
        if not printer:
            return None

        state = printer.state.printer_state
        if state == PRINTER_STATE_IDLE:
            return "idle"
        elif state == PRINTER_STATE_PROCESSING:
            return "printing"
        elif state == PRINTER_STATE_STOPPED:
            return "stopped"
        else:
            return "unknown"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        printer = self.coordinator.data.get("printer")
        if not printer:
            return {}

        attributes = {
            ATTR_PRINTER_NAME: printer.info.name,
            ATTR_PRINTER_URI: printer.info.printer_uri_supported[0] if printer.info.printer_uri_supported else None,
            ATTR_PRINTER_STATE: printer.state.printer_state,
            ATTR_PRINTER_STATE_MESSAGE: printer.state.printer_state_message,
            ATTR_PRINTER_STATE_REASONS: printer.state.printer_state_reasons,
            ATTR_PRINTER_MAKE_MODEL: printer.info.make_and_model,
        }

        if printer.info.printer_location:
            attributes[ATTR_PRINTER_LOCATION] = printer.info.printer_location

        if printer.info.printer_info:
            attributes[ATTR_PRINTER_INFO] = printer.info.printer_info

        if printer.info.printer_serial_number:
            attributes[ATTR_SERIAL_NUMBER] = printer.info.printer_serial_number

        if printer.info.printer_up_time:
            attributes[ATTR_UPTIME] = printer.info.printer_up_time

        return attributes


class CUPSMarkerLevelSensor(CUPSSensorBase):
    """Representation of a CUPS marker level sensor (ink/toner)."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, entry, marker_index):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._marker_index = marker_index
        self._update_attributes()

    def _update_attributes(self):
        """Update sensor attributes based on marker."""
        marker = self._get_marker()
        if marker:
            # Create a descriptive name
            color_name = marker.color.replace("#", "").title() if marker.color else ""
            type_name = marker.marker_type.replace("-", " ").title() if marker.marker_type else "Level"

            if color_name:
                self._attr_name = f"{color_name} {type_name}"
            else:
                self._attr_name = type_name

            self._attr_unique_id = f"{self._entry.entry_id}_marker_{self._marker_index}"

            # Set icon based on marker type
            if "toner" in marker.marker_type.lower():
                self._attr_icon = "mdi:printer-3d-nozzle"
            elif "ink" in marker.marker_type.lower():
                self._attr_icon = "mdi:water"
            elif "waste" in marker.marker_type.lower():
                self._attr_icon = "mdi:delete"
            else:
                self._attr_icon = "mdi:square"

    def _get_marker(self):
        """Get the marker for this sensor."""
        printer = self.coordinator.data.get("printer")
        if not printer or not printer.markers:
            return None

        if self._marker_index < len(printer.markers):
            return printer.markers[self._marker_index]

        return None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        marker = self._get_marker()
        if marker and marker.level is not None:
            return marker.level
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        marker = self._get_marker()
        if not marker:
            return {}

        return {
            ATTR_MARKER_INDEX: self._marker_index,
            ATTR_MARKER_NAME: marker.name,
            ATTR_MARKER_TYPE: marker.marker_type,
            ATTR_MARKER_COLOR: marker.color,
            ATTR_MARKER_LEVEL: marker.level,
        }

    async def async_update(self):
        """Update the entity."""
        await super().async_update()
        self._update_attributes()


class CUPSQueueLengthSensor(CUPSSensorBase):
    """Representation of a CUPS print queue length sensor."""

    _attr_icon = "mdi:file-document-multiple"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Print Queue"
        self._attr_unique_id = f"{entry.entry_id}_queue_length"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Note: This would require fetching job list, which is not in current pyipp Printer object
        # For now, return 0. Can be enhanced later with job management
        return 0
