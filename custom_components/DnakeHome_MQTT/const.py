"""Constants for the Dnake Home MQTT integration."""
from typing import Final

DOMAIN: Final = "dnake_home_mqtt"

# Configuration Keys
CONF_BROKER: Final = "broker"
CONF_PORT: Final = "port"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_PUB_TOPIC: Final = "pub_topic"
CONF_SUB_TOPIC: Final = "sub_topic"
CONF_ACCOUNT: Final = "account"
CONF_GATEWAY: Final = "gateway"
CONF_DISPLAY: Final = "display"

# Default Values
DEFAULT_HOST: Final = "192.168.5.100"
DEFAULT_PORT: Final = 1883
DEFAULT_PUBLISH_TOPIC: Final = "dnake/home/control"
DEFAULT_SUBSCRIBE_TOPIC: Final = "dnake/home/status"
DEFAULT_ACCOUNT: Final = "default_account"
DEFAULT_GATEWAY: Final = "default_gateway"
DEFAULT_DISPLAY: Final = "default_display"
DEFAULT_KEEPALIVE: Final = 60

# Device Types
DEVICE_TYPE_FAN: Final = 1792
DEVICE_TYPE_CLIMATE: Final = 1536
DEVICE_TYPE_SENSOR: Final = 3077
DEVICE_TYPE_HEATER: Final = 2048

DEVICE_TYPE_MAP: Final = {
    DEVICE_TYPE_FAN: {"platform": "fan", "name": "Fresh Air System"},
    DEVICE_TYPE_CLIMATE: {"platform": "climate", "name": "Air Conditioner"},
    DEVICE_TYPE_SENSOR: {"platform": "sensor", "name": "Air Quality Monitor"},
    DEVICE_TYPE_HEATER: {"platform": "climate", "name": "Floor Heating"},
}

# Events
EVENT_MQTT_MESSAGE_RECEIVED: Final = f"{DOMAIN}_mqtt_message_received"
EVENT_DEVICE_DISCOVERED: Final = f"{DOMAIN}_device_discovered"
EVENT_DEVICE_STATE_UPDATE: Final = f"{DOMAIN}_device_state_update"

# Attributes
ATTR_DEV_NO: Final = "devNo"
ATTR_DEV_TYPE: Final = "devType"
ATTR_DEV_CH: Final = "devCh"
ATTR_CMD_TYPE: Final = "cmdType"
ATTR_VALUE: Final = "value"
