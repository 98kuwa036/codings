"""Support for Nature Remo remote controls."""
import logging
from typing import Any, Iterable

from homeassistant.components.remote import RemoteEntity
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
    """Set up Nature Remo remote from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    remotes = []

    for appliance in coordinator.data.get("appliances", []):
        appliance_type = appliance.get("type")
        # IR type appliances are generic remote controls
        if appliance_type == APPLIANCE_TYPE_IR:
            remotes.append(
                NatureRemoRemote(coordinator, api, appliance["id"])
            )

    async_add_entities(remotes)


class NatureRemoRemote(CoordinatorEntity, RemoteEntity):
    """Representation of a Nature Remo remote control."""

    def __init__(self, coordinator, api, appliance_id):
        """Initialize the remote."""
        super().__init__(coordinator)
        self._api = api
        self._appliance_id = appliance_id
        self._attr_unique_id = f"{appliance_id}_remote"

    @property
    def _appliance(self):
        """Return the appliance data."""
        for appliance in self.coordinator.data.get("appliances", []):
            if appliance["id"] == self._appliance_id:
                return appliance
        return None

    @property
    def name(self):
        """Return the name of the remote."""
        if self._appliance:
            return self._appliance.get("nickname", "Remote Control")
        return "Remote Control"

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
        """Return true if remote is on."""
        # IR remotes are always "on" (ready to send signals)
        return True

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self._appliance:
            return {}

        signals = self._appliance.get("signals", [])
        signal_names = [signal["name"] for signal in signals]

        return {
            "available_commands": signal_names,
            "signal_count": len(signals),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the remote on (no-op for IR remotes)."""
        _LOGGER.info("Turn on called for %s (no-op)", self.name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the remote off (no-op for IR remotes)."""
        _LOGGER.info("Turn off called for %s (no-op)", self.name)

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a command to the remote."""
        if not self._appliance:
            _LOGGER.error("Appliance not found for remote %s", self._appliance_id)
            return

        signals = self._appliance.get("signals", [])

        for cmd in command:
            # Find the signal by name
            signal_id = None
            for signal in signals:
                if signal["name"] == cmd:
                    signal_id = signal["id"]
                    break

            if signal_id:
                try:
                    await self._api.send_signal(signal_id)
                    _LOGGER.info(
                        "Sent command '%s' (signal_id: %s) for %s",
                        cmd,
                        signal_id,
                        self.name,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to send command '%s' for %s: %s",
                        cmd,
                        self.name,
                        err,
                    )
            else:
                _LOGGER.warning(
                    "Command '%s' not found in signals for %s", cmd, self.name
                )

    async def async_learn_command(self, **kwargs: Any) -> None:
        """Learn a command from the remote."""
        _LOGGER.warning(
            "Learning commands is not supported via Home Assistant. "
            "Please use the Nature Remo app to add new signals."
        )
