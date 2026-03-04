"""Base entity for Dnake Home devices."""
import logging
from typing import Any, Dict, Optional

from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.const import CONF_NAME

from ..const import (
    DOMAIN,
    EVENT_DEVICE_STATE_UPDATE,
    ATTR_DEV_NO,
    ATTR_DEV_TYPE,
)

_LOGGER = logging.getLogger(__name__)

class DnakeBaseEntity(Entity):
    """Base class for all Dnake entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, config_entry, dev_no: int, dev_type: int, name: str, unique_id_suffix: str = ""):
        """Initialize the entity."""
        self.hass = hass
        self._config_entry = config_entry
        self._dev_no = dev_no
        self._dev_type = dev_type
        self._attr_name = name
        
        if unique_id_suffix:
            self._attr_unique_id = f"{DOMAIN}_{dev_type}_{dev_no}_{unique_id_suffix}"
        else:
            self._attr_unique_id = f"{DOMAIN}_{dev_type}_{dev_no}"
        
        # Device Info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{dev_type}_{dev_no}")},
            name=name,
            manufacturer="Dnake",
            model=f"Type {dev_type}",
            via_device=(DOMAIN, config_entry.entry_id),
        )
        
        self._unsub_dispatcher = None

    async def async_added_to_hass(self):
        """Run when entity is added to register update signal."""
        signal = f"{EVENT_DEVICE_STATE_UPDATE}_{self._dev_type}_{self._dev_no}"
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, signal, self._handle_update
        )

    async def async_will_remove_from_hass(self):
        """Clean up when entity is removed."""
        if self._unsub_dispatcher:
            self._unsub_dispatcher()

    @callback
    def _handle_update(self, data: Dict[str, Any]):
        """Handle device state update."""
        # Override in subclasses
        pass

    async def async_send_command(self, payload: Dict[str, Any]):
        """Send command to MQTT."""
        # This needs to call the MQTT client's publish method
        # We can access it via hass.data
        mqtt_client = self.hass.data[DOMAIN][self._config_entry.entry_id]["mqtt_client"]
        await mqtt_client.async_publish(payload)
