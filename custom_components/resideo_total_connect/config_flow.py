"""Adds config flow for Resideo Total Connect integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_LOCATION, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from total_connect_client.client import TotalConnectClient
from total_connect_client.exceptions import AuthenticationError

from .const import AUTO_BYPASS, CODE_REQUIRED, CONF_CODE, CONF_USER_CODES, DOMAIN

PASSWORD_DATA_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): cv.string})


class TotalConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Total Connect config flow."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.username = None
        self.password = None
        self.usercodes = {}
        self.client = None

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            # Validate user input
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            try:
                client = await self.hass.async_add_executor_job(
                    TotalConnectClient, username, password, None
                )
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            else:
                # username/password valid so show user locations
                self.username = username
                self.password = password
                self.client = client
                return await self.async_step_locations()

        data_schema = vol.Schema(
            {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_locations(self, user_entry=None):
        """Handle the user locations and associated usercodes."""
        errors = {}
        if user_entry is not None:
            for location_id in self.usercodes:
                if self.usercodes[location_id] is None:
                    valid = await self.hass.async_add_executor_job(
                        self.client.locations[location_id].set_usercode,
                        user_entry[CONF_CODE],
                    )
                    if valid:
                        self.usercodes[location_id] = user_entry[CONF_CODE]
                    else:
                        errors[CONF_LOCATION] = "usercode"
                    break

            complete = True
            for location_id in self.usercodes:
                if self.usercodes[location_id] is None:
                    complete = False

            if not errors and complete:
                return self.async_create_entry(
                    title=self.username,
                    data={
                        CONF_USERNAME: self.username,
                        CONF_PASSWORD: self.password,
                        CONF_USER_CODES: self.usercodes,
                    },
                )
        else:
            # Force the loading of locations using I/O
            number_locations = await self.hass.async_add_executor_job(
                self.client.get_number_locations,
            )
            if number_locations < 1:
                return self.async_abort(reason="no_locations")
            for location_id in self.client.locations:
                self.usercodes[location_id] = None

        # show the next location that needs a usercode
        for location_id in self.usercodes:
            if self.usercodes[location_id] is None:
                location_for_user = location_id
                break

        return self.async_show_form(
            step_id="locations",
            data_schema=vol.Schema({vol.Required(CONF_CODE): cv.string}),
            errors=errors,
            description_placeholders={
                "username": self.username,
                "location_name": self.client.locations[location_for_user].location_name,
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an authentication error or no usercode."""
        self.username = entry_data[CONF_USERNAME]
        self.usercodes = entry_data[CONF_USER_CODES]

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        errors = {}
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=PASSWORD_DATA_SCHEMA,
            )

        try:
            await self.hass.async_add_executor_job(
                TotalConnectClient,
                self.username,
                user_input[CONF_PASSWORD],
                self.usercodes,
            )
        except AuthenticationError:
            errors["base"] = "invalid_auth"
            return self.async_show_form(
                step_id="reauth_confirm",
                errors=errors,
                data_schema=PASSWORD_DATA_SCHEMA,
            )

        existing_entry = await self.async_set_unique_id(self.username)
        new_entry = {
            CONF_USERNAME: self.username,
            CONF_PASSWORD: user_input[CONF_PASSWORD],
            CONF_USER_CODES: self.usercodes,
        }
        self.hass.config_entries.async_update_entry(existing_entry, data=new_entry)

        self.hass.async_create_task(
            self.hass.config_entries.async_reload(existing_entry.entry_id)
        )

        return self.async_abort(reason="reauth_successful")

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> TotalConnectOptionsFlowHandler:
        """Get options flow."""
        return TotalConnectOptionsFlowHandler(config_entry)


class TotalConnectOptionsFlowHandler(OptionsFlow):
    """Total Connect options flow handler."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        AUTO_BYPASS,
                        default=self.config_entry.options.get(AUTO_BYPASS, False),
                    ): bool,
                    vol.Required(
                        CODE_REQUIRED,
                        default=self.config_entry.options.get(CODE_REQUIRED, False),
                    ): bool,                }
            ),
        )
