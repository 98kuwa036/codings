"""Config flow for Nature Remo integration."""
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NatureRemoAPI
from .const import DOMAIN, ERROR_AUTH_INVALID, ERROR_CANNOT_CONNECT, ERROR_UNKNOWN

_LOGGER = logging.getLogger(__name__)


class NatureRemoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nature Remo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            access_token = user_input[CONF_ACCESS_TOKEN]

            try:
                # Validate the access token
                session = async_get_clientsession(self.hass)
                api = NatureRemoAPI(access_token, session)
                user_info = await api.get_user()

                # Set unique ID based on user nickname
                await self.async_set_unique_id(user_info["nickname"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Nature Remo ({user_info['nickname']})",
                    data={CONF_ACCESS_TOKEN: access_token},
                )

            except aiohttp.ClientResponseError as err:
                if err.status == 401:
                    errors["base"] = ERROR_AUTH_INVALID
                else:
                    errors["base"] = ERROR_CANNOT_CONNECT
                _LOGGER.error("Authentication failed: %s", err)

            except aiohttp.ClientError as err:
                errors["base"] = ERROR_CANNOT_CONNECT
                _LOGGER.error("Connection failed: %s", err)

            except Exception as err:  # pylint: disable=broad-except
                errors["base"] = ERROR_UNKNOWN
                _LOGGER.exception("Unexpected error: %s", err)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCESS_TOKEN): str,
                }
            ),
            errors=errors,
        )
