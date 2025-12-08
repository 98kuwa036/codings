"""Config flow for CUPS integration."""
import logging
from typing import Any

import voluptuous as vol
from pyipp import IPP, IPPError

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_BASE_PATH,
    DEFAULT_BASE_PATH,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_HOST,
    ERROR_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass, verify_ssl=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL))

    ipp = IPP(
        host=data[CONF_HOST],
        port=data.get(CONF_PORT, DEFAULT_PORT),
        base_path=data.get(CONF_BASE_PATH, DEFAULT_BASE_PATH),
        tls=data.get(CONF_SSL, DEFAULT_SSL),
        session=session,
    )

    printer_info = await ipp.printer()

    return {
        "title": printer_info.info.name or data[CONF_HOST],
        "printer_name": printer_info.info.name,
        "printer_uri": printer_info.info.printer_uri_supported[0] if printer_info.info.printer_uri_supported else None,
    }


class CUPSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CUPS."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._discovery_info = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                # Set unique ID based on printer URI
                if info.get("printer_uri"):
                    await self.async_set_unique_id(info["printer_uri"])
                    self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

            except IPPError:
                errors["base"] = ERROR_CANNOT_CONNECT
                _LOGGER.error("Cannot connect to CUPS/IPP server")
            except Exception as err:  # pylint: disable=broad-except
                errors["base"] = ERROR_UNKNOWN
                _LOGGER.exception("Unexpected exception: %s", err)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(CONF_SSL, default=DEFAULT_SSL): bool,
                    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                    vol.Optional(CONF_BASE_PATH, default=DEFAULT_BASE_PATH): str,
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: dict[str, Any]
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        _LOGGER.debug("Zeroconf discovery: %s", discovery_info)

        # Extract host and port from discovery
        host = discovery_info.get("host")
        port = discovery_info.get("port", DEFAULT_PORT)

        # Determine if SSL should be used based on service type
        use_ssl = "_ipps._tcp.local." in discovery_info.get("type", "")

        self._discovery_info = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_SSL: use_ssl,
            CONF_VERIFY_SSL: DEFAULT_VERIFY_SSL,
            CONF_BASE_PATH: discovery_info.get("properties", {}).get("rp", DEFAULT_BASE_PATH),
        }

        try:
            info = await validate_input(self.hass, self._discovery_info)

            # Set unique ID and abort if already configured
            if info.get("printer_uri"):
                await self.async_set_unique_id(info["printer_uri"])
                self._abort_if_unique_id_configured()

            self.context["title_placeholders"] = {"name": info["title"]}

            return await self.async_step_zeroconf_confirm()

        except (IPPError, Exception) as err:
            _LOGGER.error("Error during zeroconf setup: %s", err)
            return self.async_abort(reason=ERROR_CANNOT_CONNECT)

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm zeroconf discovery."""
        if user_input is not None:
            info = await validate_input(self.hass, self._discovery_info)
            return self.async_create_entry(
                title=info["title"],
                data=self._discovery_info,
            )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "name": self.context.get("title_placeholders", {}).get("name", "Printer")
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return CUPSOptionsFlowHandler(config_entry)


class CUPSOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle CUPS options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PORT,
                        default=self.config_entry.data.get(CONF_PORT, DEFAULT_PORT),
                    ): int,
                    vol.Optional(
                        CONF_SSL,
                        default=self.config_entry.data.get(CONF_SSL, DEFAULT_SSL),
                    ): bool,
                    vol.Optional(
                        CONF_VERIFY_SSL,
                        default=self.config_entry.data.get(
                            CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_BASE_PATH,
                        default=self.config_entry.data.get(
                            CONF_BASE_PATH, DEFAULT_BASE_PATH
                        ),
                    ): str,
                }
            ),
        )
