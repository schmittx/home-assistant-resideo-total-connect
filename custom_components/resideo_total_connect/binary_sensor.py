"""Support for Resideo Total Connect binary sensor entities."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from total_connect_client.location import TotalConnectLocation
from total_connect_client.zone import TotalConnectZone

from .coordinator import TotalConnectDataUpdateCoordinator
from .entity import TotalConnectLocationEntity, TotalConnectZoneEntity
from .util import get_security_zone_device_class

BYPASS = "bypass"
LOW_BATTERY = "low_battery"
TAMPER = "tamper"
POWER = "power"
ZONE = "zone"

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True)
class TotalConnectBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class to describe a Total Connect binary sensor entity."""

    is_on_fn: Callable[[TotalConnectLocation], bool]

BINARY_SENSORS: list[TotalConnectBinarySensorEntityDescription] = [
    TotalConnectBinarySensorEntityDescription(
        key=LOW_BATTERY,
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda location: location.is_low_battery(),
    ),
    TotalConnectBinarySensorEntityDescription(
        key=TAMPER,
        translation_key="tamper",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda location: location.is_cover_tampered(),
    ),
    TotalConnectBinarySensorEntityDescription(
        key=POWER,
        translation_key="power",
        device_class=BinarySensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda location: not location.is_ac_loss(),
    ),
    TotalConnectBinarySensorEntityDescription(
        key="smoke",
        device_class=BinarySensorDeviceClass.SMOKE,
        is_on_fn=lambda location: location.arming_state.is_triggered_fire(),
    ),
    TotalConnectBinarySensorEntityDescription(
        key="carbon_monoxide",
        translation_key="carbon_monoxide",
        device_class=BinarySensorDeviceClass.CO,
        is_on_fn=lambda location: location.arming_state.is_triggered_gas(),
    ),
    TotalConnectBinarySensorEntityDescription(
        key="police",
        translation_key="police",
        device_class=BinarySensorDeviceClass.SAFETY,
        is_on_fn=lambda location: location.arming_state.is_triggered_police(),
    ),
]

@dataclass(frozen=True, kw_only=True)
class TotalConnectZoneBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class to describe a Total Connect binary sensor entity."""

    device_class_fn: Callable[[TotalConnectZone], BinarySensorDeviceClass] | None = None
    is_on_fn: Callable[[TotalConnectZone], bool]

ZONE_BINARY_SENSORS: list[TotalConnectZoneBinarySensorEntityDescription] = [
    TotalConnectZoneBinarySensorEntityDescription(
        key=BYPASS,
        translation_key="bypass",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda zone: zone.is_bypassed(),
    ),
    TotalConnectZoneBinarySensorEntityDescription(
        key=LOW_BATTERY,
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda zone: zone.is_low_battery(),
    ),
    TotalConnectZoneBinarySensorEntityDescription(
        key=TAMPER,
        translation_key="tamper",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda zone: zone.is_tampered(),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a Total Connect binary sensor entity based on a config entry."""
    coordinator = entry.runtime_data
    entities: list[TotalConnectBinarySensorEntity | TotalConnectZoneBinarySensorEntity] = []

    for location in coordinator.client.locations.values():
        for description in BINARY_SENSORS:
            entities.append(
                TotalConnectBinarySensorEntity(
                    coordinator,
                    location,
                    description,
                )
            )
        for zone in location.zones.values():
            _LOGGER.debug(f"Found new zone\n- name: {zone.description}\n- location_id: {location.location_id}\n- partition_id: {zone.partition}\n- zone_id: {zone.zoneid}")
            entities.append(
                TotalConnectZoneBinarySensorEntity(
                    coordinator,
                    location,
                    zone,
                    TotalConnectZoneBinarySensorEntityDescription(
                        key=ZONE,
                        name=None,
                        device_class_fn=get_security_zone_device_class,
                        is_on_fn=lambda zone: zone.is_faulted() or zone.is_triggered(),
                    ),
                )
            )
            if not zone.is_type_button():
                for description in ZONE_BINARY_SENSORS:
                    entities.append(
                        TotalConnectZoneBinarySensorEntity(
                            coordinator,
                            location,
                            zone,
                            description,
                        )
                    )

    async_add_entities(entities)


class TotalConnectBinarySensorEntity(TotalConnectLocationEntity, BinarySensorEntity):
    """Representation of a Total Connect binary sensor entity."""

    entity_description: TotalConnectBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: TotalConnectDataUpdateCoordinator,
        location: TotalConnectLocation,
        entity_description: TotalConnectBinarySensorEntityDescription,
    ) -> None:
        """Initialize the Total Connect binary sensor entity."""
        super().__init__(coordinator, location)
        self.entity_description = entity_description
        self._attr_unique_id = f"{location.location_id}_{entity_description.key}"

    @property
    def is_on(self) -> bool:
        """Return the state of the entity."""
        return self.entity_description.is_on_fn(self._location)


class TotalConnectZoneBinarySensorEntity(TotalConnectZoneEntity, BinarySensorEntity):
    """Representation of a Total Connect binary sensor entity."""

    entity_description: TotalConnectZoneBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: TotalConnectDataUpdateCoordinator,
        location: TotalConnectLocation,
        zone: TotalConnectZone,
        entity_description: TotalConnectZoneBinarySensorEntityDescription,
    ) -> None:
        """Initialize the Total Connect binary sensor entity."""
        super().__init__(coordinator, location, zone, entity_description.key)
        self.entity_description = entity_description

    @property
    def is_on(self) -> bool:
        """Return the state of the entity."""
        return self.entity_description.is_on_fn(self._zone)

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of this zone."""
        if self.entity_description.device_class_fn:
            return self.entity_description.device_class_fn(self._zone)
        return super().device_class
