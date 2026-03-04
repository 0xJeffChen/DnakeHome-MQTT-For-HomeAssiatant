"""Configuration Schemas for Dnake Home MQTT."""
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_BROKER,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PUB_TOPIC,
    CONF_SUB_TOPIC,
    CONF_ACCOUNT,
    CONF_GATEWAY,
    CONF_DISPLAY,
    DEFAULT_PORT,
    DEFAULT_PUBLISH_TOPIC,
    DEFAULT_SUBSCRIBE_TOPIC,
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BROKER): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PUB_TOPIC, default=DEFAULT_PUBLISH_TOPIC): cv.string,
        vol.Optional(CONF_SUB_TOPIC, default=DEFAULT_SUBSCRIBE_TOPIC): cv.string,
        vol.Optional(CONF_ACCOUNT): cv.string,
        vol.Optional(CONF_GATEWAY): cv.string,
        vol.Optional(CONF_DISPLAY): cv.string,
    }
)

DEVICE_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("devNo"): cv.positive_int,
        vol.Required("devType"): cv.positive_int,
        vol.Optional("name"): cv.string,
    }
)
