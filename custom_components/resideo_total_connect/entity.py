"""Base class for Resideo Total Connect entities."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from total_connect_client.location import TotalConnectLocation
from total_connect_client.zone import TotalConnectZone

from .const import DOMAIN
from .coordinator import TotalConnectDataUpdateCoordinator
from .util import (
    get_location_device_manufacturer,
    get_location_device_model,
    get_location_device_name,
    get_zone_device_manufacturer,
    get_zone_device_model,
)


class TotalConnectEntity(CoordinatorEntity[TotalConnectDataUpdateCoordinator]):
    """Representation of a Total Connect entity."""

    _attr_has_entity_name = True


class TotalConnectLocationEntity(TotalConnectEntity):
    """Representation of a Total Connect location entity."""

    def __init__(
        self,
        coordinator: TotalConnectDataUpdateCoordinator,
        location: TotalConnectLocation,
    ) -> None:
        """Initialize the Total Connect location entity."""
        super().__init__(coordinator)
        self._location = location
        self.device = device = location.devices[location.security_device_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.serial_number)},
            manufacturer=get_location_device_manufacturer(location=location),
            model=get_location_device_model(location=location),
            name=get_location_device_name(location=location),
            serial_number=device.serial_number,
        )


class TotalConnectZoneEntity(TotalConnectEntity):
    """Representation of a Total Connect zone entity."""

    def __init__(
        self,
        coordinator: TotalConnectDataUpdateCoordinator,
        location: TotalConnectLocation,
        zone: TotalConnectZone,
        key: str,
    ) -> None:
        """Initialize the Total Connect zone entity."""
        super().__init__(coordinator)
        self._location_id = location.location_id
        self._zone = zone
        self._attr_unique_id = f"{location.location_id}_{zone.zoneid}_{key}"
        identifier = zone.sensor_serial_number or f"zone_{zone.zoneid}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            manufacturer=get_zone_device_manufacturer(location=location, zone=zone),
            model=get_zone_device_model(location=location, zone=zone),
            name=zone.description,
            serial_number=zone.sensor_serial_number,
            via_device=(DOMAIN, location.devices[location.security_device_id].serial_number),
        )
