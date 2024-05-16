"""Utilities for the Resideo Total Connect integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import ATTR_MANUFACTURER, ATTR_MODEL

from total_connect_client.location import TotalConnectLocation
from total_connect_client.zone import TotalConnectZone

from .const import (
    ATTR_ZONES,
    DEFAULT_MANUFACTURER,
    LOCATION_ZONE_DEVICE_INFO,
)


def get_location_device_manufacturer(location: TotalConnectLocation) -> str | None:
    """Return location device name."""
    return LOCATION_ZONE_DEVICE_INFO.get(location.location_id, {}).get(ATTR_MANUFACTURER, DEFAULT_MANUFACTURER)

def get_location_device_model(location: TotalConnectLocation) -> str | None:
    """Return location device name."""
    return LOCATION_ZONE_DEVICE_INFO.get(location.location_id, {}).get(ATTR_MODEL)

def get_location_device_name(location: TotalConnectLocation) -> str:
    """Return location device name."""
    return f"{location.location_name} {location.devices[location.security_device_id].name}"

def get_security_zone_device_class(zone: TotalConnectZone) -> BinarySensorDeviceClass:
    """Return the device class of a TotalConnect security zone."""
    if zone.is_type_carbon_monoxide():
        return BinarySensorDeviceClass.CO
    if zone.is_type_fire():
        return BinarySensorDeviceClass.SMOKE
    if zone.is_type_medical():
        return BinarySensorDeviceClass.SAFETY
    if zone.is_type_motion():
        return BinarySensorDeviceClass.MOTION
    if zone.is_type_temperature():
        return BinarySensorDeviceClass.PROBLEM
    if "door" in zone.description.lower():
        return BinarySensorDeviceClass.DOOR
    if "glass break" in zone.description.lower():
        return BinarySensorDeviceClass.SOUND
    if "window" in zone.description.lower():
        return BinarySensorDeviceClass.WINDOW
    return BinarySensorDeviceClass.PROBLEM

def get_zone_device_manufacturer(location: TotalConnectLocation, zone: TotalConnectZone) -> str | None:
    """Return zone manufacturer."""
    zones = LOCATION_ZONE_DEVICE_INFO.get(location.location_id, {}).get(ATTR_ZONES, {})
    return zones.get(zone.zoneid, {}).get(ATTR_MANUFACTURER, DEFAULT_MANUFACTURER)

def get_zone_device_model(location: TotalConnectLocation, zone: TotalConnectZone) -> str | None:
    """Return zone model."""
    zones = LOCATION_ZONE_DEVICE_INFO.get(location.location_id, {}).get(ATTR_ZONES, {})
    return zones.get(zone.zoneid, {}).get(ATTR_MODEL)
