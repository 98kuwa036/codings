"""Support for Nature Remo climate devices."""
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    AC_FAN_AUTO,
    AC_MODE_AUTO,
    AC_MODE_BLOW,
    AC_MODE_COOL,
    AC_MODE_DRY,
    AC_MODE_WARM,
    AC_SWING_AUTO,
    APPLIANCE_TYPE_AC,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Mapping Nature Remo modes to Home Assistant HVAC modes
NATURE_TO_HA_MODE = {
    AC_MODE_COOL: HVACMode.COOL,
    AC_MODE_WARM: HVACMode.HEAT,
    AC_MODE_DRY: HVACMode.DRY,
    AC_MODE_BLOW: HVACMode.FAN_ONLY,
    AC_MODE_AUTO: HVACMode.AUTO,
}

HA_TO_NATURE_MODE = {v: k for k, v in NATURE_TO_HA_MODE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nature Remo climate from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    climate_devices = []

    _LOGGER.debug("Setting up climate entities, found %d appliances", len(coordinator.data.get("appliances", [])))

    for appliance in coordinator.data.get("appliances", []):
        appliance_type = appliance.get("type")
        _LOGGER.debug("Checking appliance %s with type %s", appliance.get("nickname"), appliance_type)

        if appliance_type == APPLIANCE_TYPE_AC:
            _LOGGER.info("Adding climate entity for %s (id: %s)", appliance.get("nickname"), appliance.get("id"))
            climate_devices.append(
                NatureRemoClimate(coordinator, api, appliance["id"])
            )
        else:
            _LOGGER.debug("Skipping non-AC appliance: %s (type: %s)", appliance.get("nickname"), appliance_type)

    _LOGGER.info("Added %d climate entities", len(climate_devices))
    async_add_entities(climate_devices)


class NatureRemoClimate(CoordinatorEntity, ClimateEntity):
    """Representation of a Nature Remo climate device."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator, api, appliance_id):
        """Initialize the climate device."""
        super().__init__(coordinator)
        self._api = api
        self._appliance_id = appliance_id
        self._attr_unique_id = appliance_id

    @property
    def _appliance(self):
        """Return the appliance data."""
        for appliance in self.coordinator.data.get("appliances", []):
            if appliance["id"] == self._appliance_id:
                return appliance
        return None

    @property
    def name(self):
        """Return the name of the climate device."""
        if self._appliance:
            return self._appliance.get("nickname", "Air Conditioner")
        return "Air Conditioner"

    @property
    def device_info(self):
        """Return device information."""
        if self._appliance:
            device_id = self._appliance.get("device", {}).get("id")
            device_name = self._appliance.get("device", {}).get("name", "Unknown")
            return {
                "identifiers": {(DOMAIN, device_id)},
                "name": device_name,
                "manufacturer": "Nature",
                "model": "Nature Remo",
            }
        return None

    @property
    def hvac_mode(self):
        """Return current HVAC mode."""
        if not self._appliance:
            return None

        settings = self._appliance.get("settings")
        if not settings:
            return HVACMode.OFF

        button = settings.get("button")
        if button == "power-off" or button == "":
            return HVACMode.OFF

        mode = settings.get("mode")
        return NATURE_TO_HA_MODE.get(mode, HVACMode.AUTO)

    @property
    def hvac_modes(self):
        """Return the list of available HVAC modes."""
        if not self._appliance:
            return []

        modes = [HVACMode.OFF]
        aircon = self._appliance.get("aircon", {})
        range_data = aircon.get("range", {})

        # modes is a dict like {"cool": {...}, "warm": {...}}
        if "modes" in range_data and isinstance(range_data["modes"], dict):
            for mode_name in range_data["modes"].keys():
                if mode_name in NATURE_TO_HA_MODE:
                    modes.append(NATURE_TO_HA_MODE[mode_name])

        return modes

    @property
    def current_temperature(self):
        """Return the current temperature."""
        if not self._appliance:
            return None

        device = self._appliance.get("device")
        if device and "newest_events" in device:
            if "te" in device["newest_events"]:
                return device["newest_events"]["te"]["val"]

        return None

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if not self._appliance:
            return None

        settings = self._appliance.get("settings")
        if settings:
            temp = settings.get("temp")
            if temp:
                try:
                    return float(temp)
                except (ValueError, TypeError):
                    pass

        return None

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        if not self._appliance:
            return 16

        aircon = self._appliance.get("aircon", {})
        range_data = aircon.get("range", {})
        settings = self._appliance.get("settings", {})
        current_mode = settings.get("mode", AC_MODE_AUTO)

        # modes is a dict like {"cool": {"temp": [...], "vol": [...]}}
        if "modes" in range_data and isinstance(range_data["modes"], dict):
            mode_settings = range_data["modes"].get(current_mode, {})
            temps = mode_settings.get("temp", [])
            if temps:
                try:
                    return min(float(t) for t in temps if t)
                except (ValueError, TypeError):
                    pass

        return 16

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        if not self._appliance:
            return 30

        aircon = self._appliance.get("aircon", {})
        range_data = aircon.get("range", {})
        settings = self._appliance.get("settings", {})
        current_mode = settings.get("mode", AC_MODE_AUTO)

        # modes is a dict like {"cool": {"temp": [...], "vol": [...]}}
        if "modes" in range_data and isinstance(range_data["modes"], dict):
            mode_settings = range_data["modes"].get(current_mode, {})
            temps = mode_settings.get("temp", [])
            if temps:
                try:
                    return max(float(t) for t in temps if t)
                except (ValueError, TypeError):
                    pass

        return 30

    @property
    def fan_mode(self):
        """Return the fan setting."""
        if not self._appliance:
            return None

        settings = self._appliance.get("settings")
        if settings:
            return settings.get("vol", AC_FAN_AUTO)

        return None

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        if not self._appliance:
            return []

        aircon = self._appliance.get("aircon", {})
        range_data = aircon.get("range", {})
        settings = self._appliance.get("settings", {})
        current_mode = settings.get("mode", AC_MODE_AUTO)

        # modes is a dict like {"cool": {"temp": [...], "vol": [...]}}
        if "modes" in range_data and isinstance(range_data["modes"], dict):
            mode_settings = range_data["modes"].get(current_mode, {})
            return mode_settings.get("vol", [AC_FAN_AUTO])

        return [AC_FAN_AUTO]

    @property
    def swing_mode(self):
        """Return the swing setting."""
        if not self._appliance:
            return None

        settings = self._appliance.get("settings")
        if settings:
            return settings.get("dir", AC_SWING_AUTO)

        return None

    @property
    def swing_modes(self):
        """Return the list of available swing modes."""
        if not self._appliance:
            return []

        aircon = self._appliance.get("aircon", {})
        range_data = aircon.get("range", {})
        settings = self._appliance.get("settings", {})
        current_mode = settings.get("mode", AC_MODE_AUTO)

        # modes is a dict like {"cool": {"temp": [...], "vol": [...], "dir": [...]}}
        if "modes" in range_data and isinstance(range_data["modes"], dict):
            mode_settings = range_data["modes"].get(current_mode, {})
            return mode_settings.get("dir", [AC_SWING_AUTO])

        return [AC_SWING_AUTO]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self._api.update_aircon_settings(
                self._appliance_id,
                button="power-off",
            )
        else:
            nature_mode = HA_TO_NATURE_MODE.get(hvac_mode)
            if nature_mode:
                await self._api.update_aircon_settings(
                    self._appliance_id,
                    operation_mode=nature_mode,
                    button="",
                )

        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            await self._api.update_aircon_settings(
                self._appliance_id,
                temperature=str(temperature),
            )
            await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        await self._api.update_aircon_settings(
            self._appliance_id,
            air_volume=fan_mode,
        )
        await self.coordinator.async_request_refresh()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        await self._api.update_aircon_settings(
            self._appliance_id,
            air_direction=swing_mode,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        settings = self._appliance.get("settings", {})
        mode = settings.get("mode", AC_MODE_AUTO)

        await self._api.update_aircon_settings(
            self._appliance_id,
            operation_mode=mode,
            button="",
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._api.update_aircon_settings(
            self._appliance_id,
            button="power-off",
        )
        await self.coordinator.async_request_refresh()
