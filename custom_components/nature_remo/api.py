"""API client for Nature Remo."""
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_VERSION

_LOGGER = logging.getLogger(__name__)


class NatureRemoAPI:
    """Nature Remo API client."""

    def __init__(self, access_token: str, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._access_token = access_token
        self._session = session
        self._base_url = f"{API_BASE_URL}/{API_VERSION}"

    @property
    def headers(self) -> dict[str, str]:
        """Return the headers for API requests."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make a request to the Nature Remo API."""
        url = f"{self._base_url}/{endpoint}"
        _LOGGER.debug("Making %s request to %s", method, url)

        try:
            # Nature Remo API uses form-urlencoded for POST requests
            if method == "POST" and data:
                async with self._session.request(
                    method,
                    url,
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data=data,
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                async with self._session.request(
                    method,
                    url,
                    headers=self.headers,
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error making request to %s: %s", url, err)
            raise

    async def get_user(self) -> dict[str, Any]:
        """Get user information."""
        return await self._request("GET", "users/me")

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get all devices."""
        return await self._request("GET", "devices")

    async def get_appliances(self) -> list[dict[str, Any]]:
        """Get all appliances."""
        return await self._request("GET", "appliances")

    async def update_temperature_offset(
        self, device_id: str, offset: int
    ) -> dict[str, Any]:
        """Update temperature offset for a device."""
        return await self._request(
            "POST",
            f"devices/{device_id}/temperature_offset",
            {"offset": offset},
        )

    async def update_humidity_offset(
        self, device_id: str, offset: int
    ) -> dict[str, Any]:
        """Update humidity offset for a device."""
        return await self._request(
            "POST",
            f"devices/{device_id}/humidity_offset",
            {"offset": offset},
        )

    async def send_signal(self, signal_id: str) -> dict[str, Any]:
        """Send an IR signal."""
        return await self._request("POST", f"signals/{signal_id}/send")

    async def update_aircon_settings(
        self,
        appliance_id: str,
        temperature: str | None = None,
        operation_mode: str | None = None,
        air_volume: str | None = None,
        air_direction: str | None = None,
        button: str | None = None,
    ) -> dict[str, Any]:
        """Update air conditioner settings."""
        data = {}
        if temperature is not None:
            data["temperature"] = temperature
        if operation_mode is not None:
            data["operation_mode"] = operation_mode
        if air_volume is not None:
            data["air_volume"] = air_volume
        if air_direction is not None:
            data["air_direction"] = air_direction
        if button is not None:
            data["button"] = button

        return await self._request(
            "POST",
            f"appliances/{appliance_id}/aircon_settings",
            data,
        )

    async def send_tv_signal(
        self, appliance_id: str, button: str
    ) -> dict[str, Any]:
        """Send TV infrared signal."""
        return await self._request(
            "POST",
            f"appliances/{appliance_id}/tv",
            {"button": button},
        )

    async def send_light_signal(
        self, appliance_id: str, button: str
    ) -> dict[str, Any]:
        """Send light infrared signal."""
        return await self._request(
            "POST",
            f"appliances/{appliance_id}/light",
            {"button": button},
        )

    async def create_appliance(
        self,
        device_id: str,
        nickname: str,
        image: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Create a new appliance."""
        data = {
            "device": device_id,
            "nickname": nickname,
            "image": image,
        }
        if model:
            data["model"] = model

        return await self._request("POST", "appliances", data)

    async def delete_appliance(self, appliance_id: str) -> dict[str, Any]:
        """Delete an appliance."""
        return await self._request("POST", f"appliances/{appliance_id}/delete")

    async def update_appliance(
        self,
        appliance_id: str,
        nickname: str | None = None,
        image: str | None = None,
    ) -> dict[str, Any]:
        """Update an appliance."""
        data = {}
        if nickname:
            data["nickname"] = nickname
        if image:
            data["image"] = image

        return await self._request("POST", f"appliances/{appliance_id}", data)

    async def get_appliance_signals(self, appliance_id: str) -> list[dict[str, Any]]:
        """Get all signals for an appliance."""
        appliances = await self.get_appliances()
        for appliance in appliances:
            if appliance["id"] == appliance_id:
                return appliance.get("signals", [])
        return []

    async def create_signal(
        self,
        appliance_id: str,
        name: str,
        message: str,
        image: str,
    ) -> dict[str, Any]:
        """Create a new signal."""
        return await self._request(
            "POST",
            f"appliances/{appliance_id}/signals",
            {
                "name": name,
                "message": message,
                "image": image,
            },
        )

    async def delete_signal(self, signal_id: str) -> dict[str, Any]:
        """Delete a signal."""
        return await self._request("POST", f"signals/{signal_id}/delete")

    async def update_signal(
        self,
        signal_id: str,
        name: str | None = None,
        image: str | None = None,
    ) -> dict[str, Any]:
        """Update a signal."""
        data = {}
        if name:
            data["name"] = name
        if image:
            data["image"] = image

        return await self._request("POST", f"signals/{signal_id}", data)

    async def get_smart_meter_data(self) -> list[dict[str, Any]]:
        """Get smart meter data from appliances."""
        appliances = await self.get_appliances()
        smart_meter_data = []

        for appliance in appliances:
            if appliance.get("type") == "EL_SMART_METER":
                smart_meter_data.append(appliance)

        return smart_meter_data
