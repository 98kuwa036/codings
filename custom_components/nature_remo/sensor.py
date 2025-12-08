"""Support for Nature Remo sensors."""
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nature Remo sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    sensors = []

    # Add device sensors (temperature, humidity, illuminance, motion)
    for device in coordinator.data.get("devices", []):
        device_id = device["id"]
        device_name = device["name"]

        # Temperature sensor
        if "newest_events" in device and "te" in device["newest_events"]:
            sensors.append(
                NatureRemoTemperatureSensor(coordinator, device_id, device_name)
            )

        # Humidity sensor
        if "newest_events" in device and "hu" in device["newest_events"]:
            sensors.append(
                NatureRemoHumiditySensor(coordinator, device_id, device_name)
            )

        # Illuminance sensor
        if "newest_events" in device and "il" in device["newest_events"]:
            sensors.append(
                NatureRemoIlluminanceSensor(coordinator, device_id, device_name)
            )

        # Motion sensor
        if "newest_events" in device and "mo" in device["newest_events"]:
            sensors.append(
                NatureRemoMotionSensor(coordinator, device_id, device_name)
            )

    # Add smart meter sensors
    for appliance in coordinator.data.get("appliances", []):
        if appliance.get("type") == "EL_SMART_METER":
            appliance_id = appliance["id"]
            appliance_name = appliance["nickname"]

            # Instantaneous power sensor
            if "smart_meter" in appliance:
                sensors.append(
                    NatureRemoPowerSensor(coordinator, appliance_id, appliance_name)
                )
                sensors.append(
                    NatureRemoEnergySensor(coordinator, appliance_id, appliance_name)
                )

    async_add_entities(sensors)


class NatureRemoSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Nature Remo sensors."""

    def __init__(self, coordinator, device_id, device_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "Nature",
            "model": "Nature Remo",
        }


class NatureRemoTemperatureSensor(NatureRemoSensorBase):
    """Representation of a Nature Remo temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, device_id, device_name):
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Temperature"
        self._attr_unique_id = f"{device_id}_temperature"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        for device in self.coordinator.data.get("devices", []):
            if device["id"] == self._device_id:
                if "newest_events" in device and "te" in device["newest_events"]:
                    return device["newest_events"]["te"]["val"]
        return None


class NatureRemoHumiditySensor(NatureRemoSensorBase):
    """Representation of a Nature Remo humidity sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, device_id, device_name):
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Humidity"
        self._attr_unique_id = f"{device_id}_humidity"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        for device in self.coordinator.data.get("devices", []):
            if device["id"] == self._device_id:
                if "newest_events" in device and "hu" in device["newest_events"]:
                    return device["newest_events"]["hu"]["val"]
        return None


class NatureRemoIlluminanceSensor(NatureRemoSensorBase):
    """Representation of a Nature Remo illuminance sensor."""

    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = LIGHT_LUX

    def __init__(self, coordinator, device_id, device_name):
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Illuminance"
        self._attr_unique_id = f"{device_id}_illuminance"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        for device in self.coordinator.data.get("devices", []):
            if device["id"] == self._device_id:
                if "newest_events" in device and "il" in device["newest_events"]:
                    return device["newest_events"]["il"]["val"]
        return None


class NatureRemoMotionSensor(NatureRemoSensorBase):
    """Representation of a Nature Remo motion sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, device_id, device_name):
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, device_name)
        self._attr_name = f"{device_name} Motion"
        self._attr_unique_id = f"{device_id}_motion"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        for device in self.coordinator.data.get("devices", []):
            if device["id"] == self._device_id:
                if "newest_events" in device and "mo" in device["newest_events"]:
                    return device["newest_events"]["mo"]["created_at"]
        return None


class NatureRemoPowerSensor(NatureRemoSensorBase):
    """Representation of a Nature Remo smart meter power sensor."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator, appliance_id, appliance_name):
        """Initialize the sensor."""
        super().__init__(coordinator, appliance_id, appliance_name)
        self._attr_name = f"{appliance_name} Power"
        self._attr_unique_id = f"{appliance_id}_power"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        for appliance in self.coordinator.data.get("appliances", []):
            if appliance["id"] == self._device_id:
                if "smart_meter" in appliance:
                    smart_meter = appliance["smart_meter"]
                    if "echonetlite_properties" in smart_meter:
                        for prop in smart_meter["echonetlite_properties"]:
                            if prop["epc"] == 231:  # Instantaneous power
                                return prop.get("val")
        return None


class NatureRemoEnergySensor(NatureRemoSensorBase):
    """Representation of a Nature Remo smart meter energy sensor."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, coordinator, appliance_id, appliance_name):
        """Initialize the sensor."""
        super().__init__(coordinator, appliance_id, appliance_name)
        self._attr_name = f"{appliance_name} Energy"
        self._attr_unique_id = f"{appliance_id}_energy"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        for appliance in self.coordinator.data.get("appliances", []):
            if appliance["id"] == self._device_id:
                if "smart_meter" in appliance:
                    smart_meter = appliance["smart_meter"]
                    if "echonetlite_properties" in smart_meter:
                        for prop in smart_meter["echonetlite_properties"]:
                            if prop["epc"] == 224:  # Cumulative energy
                                val = prop.get("val")
                                coefficient = smart_meter.get("coefficient", 1)
                                if val is not None:
                                    return val * coefficient
        return None
