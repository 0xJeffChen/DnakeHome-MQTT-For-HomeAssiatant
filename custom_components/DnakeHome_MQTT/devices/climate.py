"""Climate entities for Dnake Home."""
import logging
import uuid
import json
from typing import Any, Dict, Optional

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import callback, HomeAssistant

from .base import DnakeBaseEntity
from ..const import (
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_HEATER,
    CONF_ACCOUNT,
    CONF_GATEWAY,
)

_LOGGER = logging.getLogger(__name__)

# Mappings
HVAC_MODE_TO_DNAKE = {
    HVACMode.COOL: 3,
    HVACMode.HEAT: 4,
    HVACMode.FAN_ONLY: 7,
}
DNAKE_TO_HVAC_MODE = {v: k for k, v in HVAC_MODE_TO_DNAKE.items()}

FAN_MODE_TO_DNAKE = {
    FAN_LOW: 1,
    FAN_MEDIUM: 2,
    FAN_HIGH: 3,
    FAN_AUTO: 5,
}
DNAKE_TO_FAN_MODE = {v: k for k, v in FAN_MODE_TO_DNAKE.items()}


class DnakeClimate(DnakeBaseEntity, ClimateEntity):
    """Dnake Air Conditioner."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 16.0
    _attr_max_temp = 30.0
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
    _attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE |
        ClimateEntityFeature.FAN_MODE | 
        ClimateEntityFeature.TURN_ON | 
        ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, hass: HomeAssistant, config_entry, dev_no: int, dev_type: int, name: str):
        """Initialize the climate entity."""
        super().__init__(hass, config_entry, dev_no, dev_type, name)
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_fan_mode = FAN_AUTO
        self._attr_target_temperature = 26.0
        self._attr_current_temperature = 26.0

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self._send_command({"powerOn": 0})
        else:
            dnake_mode = HVAC_MODE_TO_DNAKE.get(hvac_mode, 7)
            await self._send_command({
                "powerOn": 1,
                "airMode": dnake_mode
            })
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return

        ctrl_data = {"temp": int(round(temp * 100))}

        # Turn on if off
        if self._attr_hvac_mode == HVACMode.OFF:
            ctrl_data["powerOn"] = 1
            ctrl_data["airMode"] = 3  # Default to COOL
            self._attr_hvac_mode = HVACMode.COOL

        await self._send_command(ctrl_data)
        self._attr_target_temperature = temp
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str):
        """Set new target fan mode."""
        dnake_fan = FAN_MODE_TO_DNAKE.get(fan_mode, 5)
        ctrl_data = {"windSpeed": dnake_fan}

        if self._attr_hvac_mode == HVACMode.OFF:
            ctrl_data["powerOn"] = 1
            ctrl_data["airMode"] = 3
            self._attr_hvac_mode = HVACMode.COOL

        await self._send_command(ctrl_data)
        self._attr_fan_mode = fan_mode
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
                "devType": DEVICE_TYPE_CLIMATE,
                "cmd": "AirCondition",
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

        # Power & Mode
        if "powerOn" in reports:
            if reports["powerOn"] == 0:
                self._attr_hvac_mode = HVACMode.OFF
            else:
                air_mode = reports.get("airMode")
                self._attr_hvac_mode = DNAKE_TO_HVAC_MODE.get(air_mode, HVACMode.COOL)

        # Temperature
        if "temp" in reports:
            self._attr_target_temperature = reports["temp"] / 100.0

        if "tempIndoor" in reports and reports["tempIndoor"] != 0:
            self._attr_current_temperature = reports["tempIndoor"] / 100.0

        # Fan Speed
        if "windSpeed" in reports:
            self._attr_fan_mode = DNAKE_TO_FAN_MODE.get(reports["windSpeed"], FAN_AUTO)

        self.async_write_ha_state()


class DnakeHeater(DnakeBaseEntity, ClimateEntity):
    """Dnake Floor Heater."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0
    _attr_min_temp = 5.0
    _attr_max_temp = 35.0
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | 
        ClimateEntityFeature.TURN_ON | 
        ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, hass: HomeAssistant, config_entry, dev_no: int, dev_type: int, name: str):
        """Initialize the heater entity."""
        super().__init__(hass, config_entry, dev_no, dev_type, name)
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 25.0
        self._attr_current_temperature = 26.0

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        await self._send_command({"powerOn": 1 if hvac_mode == HVACMode.HEAT else 0})
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self._send_command({"temp": int(round(temp * 100))})
        self._attr_target_temperature = temp
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
                "devCh": 3,
                "devType": DEVICE_TYPE_HEATER,
                "cmd": "AirHeater",
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
            self._attr_hvac_mode = HVACMode.HEAT if reports["powerOn"] == 1 else HVACMode.OFF

        # Note: Heater might have temp updates too, but original code didn't show them clearly in _handle_status_update
        # except for generic structure. Assuming it follows similar pattern if fields exist.
        if "temp" in reports:
             self._attr_target_temperature = reports["temp"] / 100.0
             
        if "tempIndoor" in reports and reports["tempIndoor"] != 0:
            self._attr_current_temperature = reports["tempIndoor"] / 100.0

        self.async_write_ha_state()
