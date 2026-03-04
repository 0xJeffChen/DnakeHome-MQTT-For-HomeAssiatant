"""Sensor entities for Dnake Home."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
)
from homeassistant.core import callback, HomeAssistant

from .base import DnakeBaseEntity
from ..const import (
    DEVICE_TYPE_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = [
    ("temp", "Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, 100),
    ("relativeHumid", "Humidity", PERCENTAGE, SensorDeviceClass.HUMIDITY, 100),
    ("concnPM2Dot5", "PM2.5", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorDeviceClass.PM25, 1),
    ("concnPM1Dot0", "PM1.0", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorDeviceClass.PM1, 1),
    ("concnPM10", "PM10", CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, SensorDeviceClass.PM10, 1),
]

class DnakeSensor(DnakeBaseEntity, SensorEntity):
    """Dnake Air Quality Sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, 
        hass: HomeAssistant, 
        config_entry, 
        dev_no: int, 
        dev_type: int, 
        name: str,
        sensor_key: str,
        sensor_name: str,
        unit: str,
        device_class: str,
        factor: float
    ):
        """Initialize the sensor entity."""
        # Use suffix for unique_id
        super().__init__(hass, config_entry, dev_no, dev_type, name, unique_id_suffix=sensor_key)
        
        self._sensor_key = sensor_key
        self._factor = factor
        self._attr_name = f"{name} {sensor_name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @callback
    def _handle_update(self, data: Dict[str, Any]):
        """Handle device state update."""
        reports = data.get("reports", {})
        if not reports:
            return

        if self._sensor_key in reports:
            raw_value = reports[self._sensor_key]
            if raw_value is not None:
                self._attr_native_value = raw_value / self._factor
                self.async_write_ha_state()
