"""Fan entities for Dnake Home."""
import logging
import uuid
import json
from typing import Any, Dict, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import callback, HomeAssistant

from .base import DnakeBaseEntity
from ..const import (
    DEVICE_TYPE_FAN,
    CONF_ACCOUNT,
    CONF_GATEWAY,
)

_LOGGER = logging.getLogger(__name__)

# Speed mapping: 1=Low, 2=Medium, 3=High
SPEED_TO_DNAKE = {
    100: 3,  # High
    66: 2,   # Medium
    33: 1,   # Low
}
DNAKE_TO_SPEED = {v: k for k, v in SPEED_TO_DNAKE.items()}


class DnakeFan(DnakeBaseEntity, FanEntity):
    """Dnake Fresh Air Fan."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED |
        FanEntityFeature.TURN_OFF |
        FanEntityFeature.TURN_ON
    )

    def __init__(self, hass: HomeAssistant, config_entry, dev_no: int, dev_type: int, name: str):
        """Initialize the fan entity."""
        super().__init__(hass, config_entry, dev_no, dev_type, name)
        self._attr_percentage = 0
        self._attr_is_on = False

    async def async_turn_on(self, percentage: Optional[int] = None, preset_mode: Optional[str] = None, **kwargs):
        """Turn on the fan."""
        if percentage is None:
            percentage = 66  # Default to Medium
            
        await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs):
        """Turn the fan off."""
        await self._send_command({"powerOn": 0})
        self._attr_is_on = False
        self._attr_percentage = 0
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int):
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        # Map percentage to 1, 2, 3
        if percentage <= 33:
            speed = 1
        elif percentage <= 66:
            speed = 2
        else:
            speed = 3
            
        await self._send_command({"powerOn": 1, "windSpeed": speed})
        self._attr_percentage = percentage
        self._attr_is_on = True
        self.async_write_ha_state()

    async def _send_command(self, data_updates: Dict[str, Any]):
        """Send command to device."""
        account = self._config_entry.data[CONF_ACCOUNT]
        gateway = self._config_entry.data[CONF_GATEWAY]
        
        payload = {
            "fromDev": account,
            "toDev": gateway,
            "data": {
                "action": "ctrlDev",
                "devNo": self._dev_no,
                "devCh": 1,
                "devType": DEVICE_TYPE_FAN,
                "cmd": "NewFan",
                "uuid": uuid.uuid4().hex
            }
        }
        payload["data"].update(data_updates)
        await self.async_send_command(payload)

    @callback
    def _handle_update(self, data: Dict[str, Any]):
        """Handle device state update."""
        reports = data.get("reports", {})
        if not reports:
            return

        if "powerOn" in reports:
            self._attr_is_on = reports["powerOn"] == 1
            if not self._attr_is_on:
                self._attr_percentage = 0

        if "windSpeed" in reports and self._attr_is_on:
            speed = reports["windSpeed"]
            self._attr_percentage = DNAKE_TO_SPEED.get(speed, 66)

        self.async_write_ha_state()
