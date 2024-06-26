"""The Resideo Total Connect integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from total_connect_client.client import TotalConnectClient
from total_connect_client.exceptions import (
    AuthenticationError,
    ServiceUnavailable,
    TotalConnectError,
)

from .const import AUTO_BYPASS, CONF_USER_CODES, DOMAIN

PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR]

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)
SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up upon config entry in user interface."""
    conf = entry.data
    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]
    bypass = entry.options.get(AUTO_BYPASS, False)

    if CONF_USER_CODES not in conf:
        # should only happen for those who used UI before we added usercodes
        raise ConfigEntryAuthFailed("No user codes in Total Connect configuration")

    temp_codes = conf[CONF_USER_CODES]
    usercodes = {int(code): temp_codes[code] for code in temp_codes}

    try:
        client = await hass.async_add_executor_job(
            TotalConnectClient, username, password, usercodes, bypass
        )
    except AuthenticationError as exception:
        raise ConfigEntryAuthFailed(
            "Total Connect authentication failed during setup"
        ) from exception

    coordinator = TotalConnectDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    bypass = entry.options.get(AUTO_BYPASS, False)
    client = hass.data[DOMAIN][entry.entry_id].client
    for location_id in client.locations:
        client.locations[location_id].auto_bypass_low_battery = bypass


class TotalConnectDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Class to fetch data from Total Connect."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, client: TotalConnectClient) -> None:
        """Initialize."""
        self.hass = hass
        self.client = client
        super().__init__(
            hass, logger=_LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL
        )

    async def _async_update_data(self) -> None:
        """Update data."""
        await self.hass.async_add_executor_job(self.sync_update_data)

    def sync_update_data(self) -> None:
        """Fetch synchronous data from Total Connect."""
        try:
            for location_id in self.client.locations:
                self.client.locations[location_id].get_panel_meta_data()
        except AuthenticationError as exception:
            # should only encounter if password changes during operation
            raise ConfigEntryAuthFailed(
                "Total Connect authentication failed during operation."
            ) from exception
        except ServiceUnavailable as exception:
            raise UpdateFailed(
                "Error connecting to Total Connect or the service is unavailable. "
                "Check https://status.resideo.com/ for outages."
            ) from exception
        except TotalConnectError as exception:
            raise UpdateFailed(exception) from exception
        except ValueError as exception:
            raise UpdateFailed("Unknown state from Total Connect") from exception
