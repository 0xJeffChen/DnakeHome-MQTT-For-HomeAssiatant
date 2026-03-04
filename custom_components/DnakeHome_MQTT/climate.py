"""Support for Dnake Climate devices."""
import logging
from typing import Dict, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    EVENT_DEVICE_DISCOVERED,
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_HEATER,
)
from .devices.climate import DnakeClimate, DnakeHeater

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Dnake climate platform."""
    
    @callback
    def _create_entity(dev_no: int, dev_type: int, name: str):
        """Create a climate entity."""
        if dev_type == DEVICE_TYPE_CLIMATE:
            return DnakeClimate(hass, entry, dev_no, dev_type, name)
        elif dev_type == DEVICE_TYPE_HEATER:
            return DnakeHeater(hass, entry, dev_no, dev_type, name)
        return None

    # 1. Add existing devices from config
    devices = entry.data.get("devices", {})
    entities = []
    
    for dev_no_str, info in devices.items():
        dev_type = info.get("type")
        if dev_type in [DEVICE_TYPE_CLIMATE, DEVICE_TYPE_HEATER]:
            entity = _create_entity(
                int(dev_no_str), 
                dev_type, 
                info.get("name", f"Climate {dev_no_str}")
            )
            if entity:
                entities.append(entity)
    
    if entities:
        async_add_entities(entities)

    # 2. Listen for new devices
    @callback
    def _handle_discovery(event):
        """Handle new device discovery."""
        data = event.data
        if data.get("platform") != "climate":
            return
            
        dev_no = data.get("dev_no")
        dev_type = data.get("dev_type")
        
        # Check if already added? 
        # HA handles unique_id collisions gracefully usually, but better to check if we can.
        # But here we just create and add.
        
        _LOGGER.info("Discovered climate device: %s", dev_no)
        entity = _create_entity(dev_no, dev_type, data.get("name"))
        if entity:
            async_add_entities([entity])

    entry.async_on_unload(
        hass.bus.async_listen(EVENT_DEVICE_DISCOVERED, _handle_discovery)
    )
