"""Support for Nature Remo lights."""
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import APPLIANCE_TYPE_LIGHT, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nature Remo light from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    lights = []

    for appliance in coordinator.data.get("appliances", []):
        if appliance.get("type") == APPLIANCE_TYPE_LIGHT:
            lights.append(
                NatureRemoLight(coordinator, api, appliance["id"])
            )

    async_add_entities(lights)


class NatureRemoLight(CoordinatorEntity, LightEntity):
    """Representation of a Nature Remo light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator, api, appliance_id):
        """Initialize the light."""
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
        """Return the name of the light."""
        if self._appliance:
            return self._appliance.get("nickname", "Light")
        return "Light"

    @property
    def device_info(self):
        """Return device information."""
        if self._appliance:
            device = self._appliance.get("device", {})
            device_id = device.get("id")
            device_name = device.get("name", "Unknown")
            return {
                "identifiers": {(DOMAIN, device_id)},
                "name": device_name,
                "manufacturer": "Nature",
                "model": "Nature Remo",
            }
        return None

    @property
    def is_on(self):
        """Return true if light is on."""
        if not self._appliance:
            return None

        light_state = self._appliance.get("light", {}).get("state", {})
        power = light_state.get("power")

        return power == "on"

    @property
    def brightness(self):
        """Return the brightness of the light."""
        if not self._appliance:
            return None

        light_state = self._appliance.get("light", {}).get("state", {})
        brightness = light_state.get("brightness")

        if brightness:
            # Map brightness level to 0-255 range
            # Assuming brightness levels are numeric strings
            try:
                level = int(brightness)
                # Adjust mapping based on your light's brightness range
                return int((level / 100) * 255)
            except (ValueError, TypeError):
                pass

        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self._appliance:
            return {}

        light_data = self._appliance.get("light", {})
        buttons = light_data.get("buttons", [])
        state = light_data.get("state", {})

        return {
            "available_buttons": [btn["name"] for btn in buttons],
            "last_button": state.get("last_button"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        try:
            # Check if brightness is provided
            if ATTR_BRIGHTNESS in kwargs:
                brightness = kwargs[ATTR_BRIGHTNESS]
                # Map 0-255 to light's brightness range
                brightness_level = str(int((brightness / 255) * 100))

                # Try to set brightness if supported
                await self._api.send_light_signal(
                    self._appliance_id,
                    button=f"bright-{brightness_level}",
                )
            else:
                await self._api.send_light_signal(
                    self._appliance_id,
                    button="on",
                )

            await self.coordinator.async_request_refresh()
            _LOGGER.info("Turned on %s", self.name)

        except Exception as err:
            _LOGGER.error("Failed to turn on %s: %s", self.name, err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        try:
            await self._api.send_light_signal(
                self._appliance_id,
                button="off",
            )
            await self.coordinator.async_request_refresh()
            _LOGGER.info("Turned off %s", self.name)

        except Exception as err:
            _LOGGER.error("Failed to turn off %s: %s", self.name, err)
