"""Support for Resideo Total Connect button entities."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from total_connect_client.location import TotalConnectLocation
from total_connect_client.zone import TotalConnectZone

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TotalConnectDataUpdateCoordinator
from .entity import TotalConnectLocationEntity, TotalConnectZoneEntity

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True)
class TotalConnectButtonEntityDescription(ButtonEntityDescription):
    """Class to describe a Total Connect button entity."""

    entity_category: str[EntityCategory] | None = EntityCategory.DIAGNOSTIC
    press_fn: Callable[[TotalConnectLocation], None]


BUTTONS: tuple[TotalConnectButtonEntityDescription, ...] = (
    TotalConnectButtonEntityDescription(
        key="clear_bypass",
        translation_key="clear_bypass",
        press_fn=lambda location: location.clear_bypass(),
    ),
    TotalConnectButtonEntityDescription(
        key="bypass_all",
        translation_key="bypass_all",
        press_fn=lambda location: location.zone_bypass_all(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a Total Connect button entity based on a config entry."""
    coordinator = entry.runtime_data
    entities: list[TotalConnectButtonEntity | TotalConnectZoneButtonEntity] = []

    for location_id, location in coordinator.client.locations.items():
        for description in BUTTONS:
            entities.append(
                TotalConnectButtonEntity(
                    coordinator,
                    location,
                    description,
                )
            )
        for zone in location.zones.values():
            _LOGGER.debug(f"Found new zone\n- name: {zone.description}\n- location_id: {location.location_id}\n- partition_id: {zone.partition}\n- zone_id: {zone.zoneid}")
            if zone.can_be_bypassed:
                entities.append(
                    TotalConnectZoneButtonEntity(
                        coordinator,
                        location,
                        zone,
                        TotalConnectButtonEntityDescription(
                            key="bypass",
                            translation_key="bypass",
                            press_fn=lambda zone: zone.bypass(),
                        ),
                    )
                )

    async_add_entities(entities)


class TotalConnectButtonEntity(TotalConnectLocationEntity, ButtonEntity):
    """Representation of a Total Connect button entity."""

    entity_description: TotalConnectButtonEntityDescription

    def __init__(
        self,
        coordinator: TotalConnectDataUpdateCoordinator,
        location: TotalConnectLocation,
        entity_description: TotalConnectButtonEntityDescription,
    ) -> None:
        """Initialize the Total Connect button entity."""
        super().__init__(coordinator, location)
        self.entity_description = entity_description
        self._attr_unique_id = f"{location.location_id}_{entity_description.key}"

    def press(self) -> None:
        """Press the button."""
        self.entity_description.press_fn(self._location)


class TotalConnectZoneButtonEntity(TotalConnectZoneEntity, ButtonEntity):
    """Representation of a Total Connect button entity."""

    entity_description: TotalConnectButtonEntityDescription

    def __init__(
        self,
        coordinator: TotalConnectDataUpdateCoordinator,
        location: TotalConnectLocation,
        zone: TotalConnectZone,
        entity_description: TotalConnectButtonEntityDescription,
    ) -> None:
        """Initialize the Total Connect button entity."""
        super().__init__(coordinator, location, zone, entity_description.key)
        self.entity_description = entity_description

    def press(self) -> None:
        """Press the button."""
        self.entity_description.press_fn(self._zone)
