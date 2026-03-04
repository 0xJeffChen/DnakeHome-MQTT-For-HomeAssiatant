"""MQTT Client wrapper for Dnake Home."""
import asyncio
import logging
import json
from typing import Any, Callable, Dict, Optional

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

from ..const import (
    DOMAIN,
    EVENT_MQTT_MESSAGE_RECEIVED,
    CONF_BROKER,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SUB_TOPIC,
    CONF_PUB_TOPIC,
    DEFAULT_KEEPALIVE,
)

_LOGGER = logging.getLogger(__name__)

class DnakeMqttClient:
    """MQTT Client wrapper."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize the MQTT client."""
        self.hass = hass
        self._config = config
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._sub_topic = config.get(CONF_SUB_TOPIC)
        self._pub_topic = config.get(CONF_PUB_TOPIC)
        
        # Initialize client
        client_id = f"dnake_home_{config.get(CONF_BROKER)}_{config.get(CONF_PORT)}"
        self._client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=client_id)
        
        if config.get(CONF_USERNAME) and config.get(CONF_PASSWORD):
            self._client.username_pw_set(config[CONF_USERNAME], config[CONF_PASSWORD])
            
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        
        # Register cleanup
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.async_stop)

    async def async_start(self):
        """Start the MQTT client."""
        broker = self._config[CONF_BROKER]
        port = self._config[CONF_PORT]
        
        try:
            _LOGGER.info("Connecting to MQTT broker %s:%s", broker, port)
            # Use run_in_executor for blocking connect call
            await self.hass.async_add_executor_job(
                self._client.connect, broker, port, DEFAULT_KEEPALIVE
            )
            self._client.loop_start()
            return True
        except Exception as err:
            _LOGGER.error("Failed to connect to MQTT broker: %s", err)
            return False

    async def async_stop(self, event=None):
        """Stop the MQTT client."""
        if self._client:
            _LOGGER.info("Stopping MQTT client")
            self._client.loop_stop()
            self._client.disconnect()

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Handle connection established."""
        if rc == 0:
            _LOGGER.info("Connected to MQTT broker")
            self._connected = True
            client.subscribe(self._sub_topic)
            _LOGGER.info("Subscribed to topic: %s", self._sub_topic)
        else:
            _LOGGER.error("Failed to connect to MQTT broker, return code: %s", rc)
            self._connected = False

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Handle disconnection."""
        _LOGGER.warning("Disconnected from MQTT broker, return code: %s", rc)
        self._connected = False

    def _on_message(self, client, userdata, msg):
        """Handle incoming messages."""
        try:
            payload = msg.payload.decode("utf-8")
            _LOGGER.debug("Received message on %s: %s", msg.topic, payload)
            
            # Fire event on HA bus
            self.hass.loop.call_soon_threadsafe(
                self.hass.bus.fire,
                EVENT_MQTT_MESSAGE_RECEIVED,
                {"topic": msg.topic, "payload": payload}
            )
        except Exception as err:
            _LOGGER.error("Error processing message: %s", err)

    async def async_publish(self, payload: Dict[str, Any]):
        """Publish message to MQTT broker."""
        if not self._connected:
            _LOGGER.warning("Cannot publish message: MQTT client not connected")
            return

        try:
            json_payload = json.dumps(payload)
            _LOGGER.debug("Publishing to %s: %s", self._pub_topic, json_payload)
            await self.hass.async_add_executor_job(
                self._client.publish, self._pub_topic, json_payload
            )
        except Exception as err:
            _LOGGER.error("Error publishing message: %s", err)
