"""The Dnake Home MQTT integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .core.mqtt import DnakeMqttClient
from .core.device_manager import DeviceManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "fan", "sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dnake Home MQTT from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.info("Setting up Dnake Home MQTT integration")

    # 1. Initialize MQTT Client
    mqtt_client = DnakeMqttClient(hass, entry.data)
    if not await mqtt_client.async_start():
        _LOGGER.error("Failed to start MQTT client")
        return False

    # 2. Initialize Device Manager
    device_manager = DeviceManager(hass, entry, mqtt_client)
    await device_manager.async_setup()

    # Store in hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "mqtt_client": mqtt_client,
        "device_manager": device_manager,
    }

    # 3. Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return True

    mqtt_client = data.get("mqtt_client")
    device_manager = data.get("device_manager")

    if device_manager:
        await device_manager.async_unload()
    
    if mqtt_client:
        await mqtt_client.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
