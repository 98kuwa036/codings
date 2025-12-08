"""Support for Nature Remo switches."""
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import APPLIANCE_TYPE_IR, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nature Remo switch from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    switches = []

    for appliance in coordinator.data.get("appliances", []):
        appliance_type = appliance.get("type")

        # Create switches for IR appliances with on/off signals
        if appliance_type == APPLIANCE_TYPE_IR:
            signals = appliance.get("signals", [])
            signal_names = [s["name"].lower() for s in signals]

            # Check if there are on/off signals
            has_on = any("on" in name or "オン" in name for name in signal_names)
            has_off = any("off" in name or "オフ" in name for name in signal_names)

            if has_on and has_off:
                switches.append(
                    NatureRemoSwitch(coordinator, api, appliance["id"])
                )

    async_add_entities(switches)


class NatureRemoSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Nature Remo switch."""

    def __init__(self, coordinator, api, appliance_id):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api = api
        self._appliance_id = appliance_id
        self._attr_unique_id = f"{appliance_id}_switch"
        self._is_on = False

    @property
    def _appliance(self):
        """Return the appliance data."""
        for appliance in self.coordinator.data.get("appliances", []):
            if appliance["id"] == self._appliance_id:
                return appliance
        return None

    @property
    def name(self):
        """Return the name of the switch."""
        if self._appliance:
            return self._appliance.get("nickname", "Switch")
        return "Switch"

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
        """Return true if switch is on."""
        return self._is_on

    def _find_signal_id(self, keyword: str) -> str | None:
        """Find signal ID by keyword in signal name."""
        if not self._appliance:
            return None

        signals = self._appliance.get("signals", [])
        for signal in signals:
            signal_name = signal["name"].lower()
            if keyword in signal_name:
                return signal["id"]

        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        # Try to find "on" or "オン" signal
        signal_id = self._find_signal_id("on") or self._find_signal_id("オン")

        if signal_id:
            try:
                await self._api.send_signal(signal_id)
                self._is_on = True
                self.async_write_ha_state()
                _LOGGER.info("Turned on %s", self.name)
            except Exception as err:
                _LOGGER.error("Failed to turn on %s: %s", self.name, err)
        else:
            _LOGGER.warning("No 'on' signal found for %s", self.name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        # Try to find "off" or "オフ" signal
        signal_id = self._find_signal_id("off") or self._find_signal_id("オフ")

        if signal_id:
            try:
                await self._api.send_signal(signal_id)
                self._is_on = False
                self.async_write_ha_state()
                _LOGGER.info("Turned off %s", self.name)
            except Exception as err:
                _LOGGER.error("Failed to turn off %s: %s", self.name, err)
        else:
            _LOGGER.warning("No 'off' signal found for %s", self.name)
