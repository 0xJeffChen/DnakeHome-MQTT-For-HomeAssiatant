"""Device Manager for Dnake Home MQTT."""
import json
import logging
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant, callback
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send
import uuid

from ..const import (
    DOMAIN,
    EVENT_MQTT_MESSAGE_RECEIVED,
    EVENT_DEVICE_DISCOVERED,
    EVENT_DEVICE_STATE_UPDATE,
    ATTR_DEV_NO,
    ATTR_DEV_TYPE,
    ATTR_DEV_CH,
    ATTR_CMD_TYPE,
    ATTR_VALUE,
    DEVICE_TYPE_MAP,
    CONF_ACCOUNT,
    CONF_GATEWAY,
    DEVICE_TYPE_HEATER,
)

_LOGGER = logging.getLogger(__name__)

class DeviceManager:
    """Manages Dnake devices and state updates."""

    def __init__(self, hass: HomeAssistant, config_entry, mqtt_client):
        """Initialize the device manager."""
        self.hass = hass
        self._config_entry = config_entry
        self._mqtt_client = mqtt_client
        self._devices: Dict[str, Any] = {}
        self._unsub_mqtt = None
        self._unsub_heartbeat = None

    async def async_setup(self):
        """Set up the device manager."""
        self._unsub_mqtt = self.hass.bus.async_listen(
            EVENT_MQTT_MESSAGE_RECEIVED, self._handle_mqtt_message
        )
        
        # Start heartbeat
        self._unsub_heartbeat = async_track_time_interval(
            self.hass,
            self._async_heartbeat,
            timedelta(minutes=1)
        )
        
        # Initial poll
        await self._async_heartbeat(None)
        
        _LOGGER.info("Device Manager started")

    async def async_unload(self):
        """Unload the device manager."""
        if self._unsub_mqtt:
            self._unsub_mqtt()
        if self._unsub_heartbeat:
            self._unsub_heartbeat()

    async def _async_heartbeat(self, _now):
        """Send heartbeat to query device status."""
        account = self._config_entry.data[CONF_ACCOUNT]
        gateway = self._config_entry.data[CONF_GATEWAY]
        
        # Construct device list for query
        # We query all known devices or just ask for everything?
        # Original code used `entry.data.get("devices")` to build the list.
        # If we want to support dynamic discovery, maybe we should ask for all?
        # But the protocol seems to require a list of devices to query?
        # The original code:
        # device_list = [ { "devType": 0, "devNo": ..., "devCh": ... } ... ]
        # It seems it queries status for KNOWN devices.
        
        # If we rely on persistence, we use config_entry data.
        current_devices = self._config_entry.data.get("devices", {})
        
        if not current_devices:
            # If no devices known, maybe we can't query? 
            # Or maybe there's a broadcast query?
            # Assuming we need to wait for spontaneous reports or manual config if list is empty.
            return

        device_list = []
        for dev_no_str, info in current_devices.items():
            dev_type = info.get("type")
            dev_no = int(dev_no_str)
            device_list.append({
                "devType": 0, # Protocol seems to use 0 here?
                "devNo": dev_no,
                "devCh": 3 if dev_type == DEVICE_TYPE_HEATER else 1
            })

        payload = {
            "fromDev": account,
            "toDev": gateway,
            "data": {
                "devList": device_list,
                "action": "readDev",
                "cmd": "AirFresh", # Original code used "AirFresh" for all? Or just an example?
                # "cmd" might be irrelevant for readDev or it might be specific.
                # Original code used "AirFresh" in the example snippet.
                "uuid": uuid.uuid4().hex
            }
        }
        
        _LOGGER.debug("Sending heartbeat query")
        await self._mqtt_client.async_publish(payload)

    @callback
    def _handle_mqtt_message(self, event):
        """Handle incoming MQTT messages."""
        try:
            payload = json.loads(event.data.get("payload", "{}"))
        except json.JSONDecodeError:
            _LOGGER.warning("Received invalid JSON payload")
            return

        # Check if message is valid (from gateway, to display/account)
        # This check should probably be done here or in mqtt.py
        # But DeviceManager might not know gateway/account unless passed in config.
        # For now, let's process the structure.
        
        data = payload.get("data", {})
        action = data.get("action")
        
        # Handle cmtDevInfo (Status update / Discovery)
        if action == "cmtDevInfo":
            dev_list = data.get("devList", [])
            for item in dev_list:
                self._process_device_update(item)

    def _process_device_update(self, data: Dict[str, Any]):
        """Process a single device update."""
        dev_no = data.get(ATTR_DEV_NO)
        dev_type = data.get(ATTR_DEV_TYPE)

        if not dev_no or not dev_type:
            return

        device_id = f"{dev_type}_{dev_no}"
        
        # Check if device is known
        if device_id not in self._devices:
            self._register_new_device(dev_no, dev_type, data)

        # Dispatch state update
        async_dispatcher_send(
            self.hass,
            f"{EVENT_DEVICE_STATE_UPDATE}_{device_id}",
            data
        )

    def _register_new_device(self, dev_no: int, dev_type: int, data: Dict[str, Any]):
        """Register a new device and notify platforms."""
        device_info_def = DEVICE_TYPE_MAP.get(dev_type)
        if not device_info_def:
            _LOGGER.debug("Unknown device type: %s", dev_type)
            return

        device_id = f"{dev_type}_{dev_no}"
        self._devices[device_id] = {
            "dev_no": dev_no,
            "dev_type": dev_type,
            "info": device_info_def,
            "last_data": data
        }

        _LOGGER.info("Discovered new device: %s (Type: %s)", dev_no, device_info_def["name"])
        
        # Persist to config entry if not already present
        # We need to use async_update_entry to save changes
        current_data = dict(self._config_entry.data)
        devices = dict(current_data.get("devices", {}))
        dev_no_str = str(dev_no)
        
        if dev_no_str not in devices:
            devices[dev_no_str] = {
                "type": dev_type,
                "platform": device_info_def["platform"],
                "name": f"Dnake_{device_info_def['name']}_{dev_no}"
            }
            current_data["devices"] = devices
            self.hass.config_entries.async_update_entry(self._config_entry, data=current_data)
        
        # Notify platforms to create entity
        self.hass.bus.async_fire(
            EVENT_DEVICE_DISCOVERED,
            {
                "platform": device_info_def["platform"],
                "dev_no": dev_no,
                "dev_type": dev_type,
                "name": f"Dnake_{device_info_def['name']}_{dev_no}",
                "device_info": device_info_def
            }
        )
