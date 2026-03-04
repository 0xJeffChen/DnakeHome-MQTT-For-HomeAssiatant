"""Support for Dnake Fan devices."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    EVENT_DEVICE_DISCOVERED,
    DEVICE_TYPE_FAN,
)
from .devices.fan import DnakeFan

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dnake fan platform."""

    @callback
    def _create_entity(dev_no: int, dev_type: int, name: str):
        if dev_type == DEVICE_TYPE_FAN:
            return DnakeFan(hass, entry, dev_no, dev_type, name)
        return None

    # 1. Add existing devices
    devices = entry.data.get("devices", {})
    entities = []
    
    for dev_no_str, info in devices.items():
        dev_type = info.get("type")
        if dev_type == DEVICE_TYPE_FAN:
            entity = _create_entity(
                int(dev_no_str),
                dev_type,
                info.get("name", f"Fan {dev_no_str}")
            )
            if entity:
                entities.append(entity)

    if entities:
        async_add_entities(entities)

    # 2. Listen for new devices
    @callback
    def _handle_discovery(event):
        data = event.data
        if data.get("platform") != "fan":
            return
            
        dev_no = data.get("dev_no")
        dev_type = data.get("dev_type")
        
        _LOGGER.info("Discovered fan device: %s", dev_no)
        entity = _create_entity(dev_no, dev_type, data.get("name"))
        if entity:
            async_add_entities([entity])

    entry.async_on_unload(
        hass.bus.async_listen(EVENT_DEVICE_DISCOVERED, _handle_discovery)
    )
