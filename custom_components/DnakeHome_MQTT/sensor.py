"""Support for Dnake Sensor devices."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    EVENT_DEVICE_DISCOVERED,
    DEVICE_TYPE_SENSOR,
)
from .devices.sensor import DnakeSensor, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dnake sensor platform."""

    @callback
    def _create_entities(dev_no: int, dev_type: int, name: str):
        entities = []
        if dev_type == DEVICE_TYPE_SENSOR:
            for key, sensor_name, unit, device_class, factor in SENSOR_TYPES:
                entities.append(
                    DnakeSensor(
                        hass, 
                        entry, 
                        dev_no, 
                        dev_type, 
                        name,
                        key,
                        sensor_name,
                        unit,
                        device_class,
                        factor
                    )
                )
        return entities

    # 1. Add existing devices
    devices = entry.data.get("devices", {})
    entities = []
    
    for dev_no_str, info in devices.items():
        dev_type = info.get("type")
        if dev_type == DEVICE_TYPE_SENSOR:
            new_entities = _create_entities(
                int(dev_no_str),
                dev_type,
                info.get("name", f"Sensor {dev_no_str}")
            )
            entities.extend(new_entities)

    if entities:
        async_add_entities(entities)

    # 2. Listen for new devices
    @callback
    def _handle_discovery(event):
        data = event.data
        if data.get("platform") != "sensor":
            return
            
        dev_no = data.get("dev_no")
        dev_type = data.get("dev_type")
        
        _LOGGER.info("Discovered sensor device: %s", dev_no)
        new_entities = _create_entities(dev_no, dev_type, data.get("name"))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(
        hass.bus.async_listen(EVENT_DEVICE_DISCOVERED, _handle_discovery)
    )
