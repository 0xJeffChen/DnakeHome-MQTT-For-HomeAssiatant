"""Config flow for Dnake Home MQTT."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_BROKER,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PUB_TOPIC,
    CONF_SUB_TOPIC,
    CONF_ACCOUNT,
    CONF_GATEWAY,
    CONF_DISPLAY,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_PUBLISH_TOPIC,
    DEFAULT_SUBSCRIBE_TOPIC,
    DEFAULT_ACCOUNT,
    DEFAULT_GATEWAY,
    DEFAULT_DISPLAY,
)

_LOGGER = logging.getLogger(__name__)

class DnakeHomeMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dnake Home MQTT."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate input here if needed (e.g. try to connect)
            # For now, just create entry
            return self.async_create_entry(
                title=f"Dnake MQTT ({user_input[CONF_BROKER]})", 
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_BROKER, default=DEFAULT_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_USERNAME): str,
                vol.Optional(CONF_PASSWORD): str,
                vol.Optional(CONF_SUB_TOPIC, default=DEFAULT_SUBSCRIBE_TOPIC): str,
                vol.Optional(CONF_PUB_TOPIC, default=DEFAULT_PUBLISH_TOPIC): str,
                vol.Required(CONF_ACCOUNT, default=DEFAULT_ACCOUNT): str,
                vol.Required(CONF_GATEWAY, default=DEFAULT_GATEWAY): str,
                vol.Optional(CONF_DISPLAY, default=DEFAULT_DISPLAY): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DnakeHomeMQTTOptionsFlowHandler(config_entry)


class DnakeHomeMQTTOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Dnake Home MQTT options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SUB_TOPIC,
                    default=self.config_entry.options.get(
                        CONF_SUB_TOPIC, 
                        self.config_entry.data.get(CONF_SUB_TOPIC, DEFAULT_SUBSCRIBE_TOPIC)
                    ),
                ): str,
                vol.Optional(
                    CONF_PUB_TOPIC,
                    default=self.config_entry.options.get(
                        CONF_PUB_TOPIC, 
                        self.config_entry.data.get(CONF_PUB_TOPIC, DEFAULT_PUBLISH_TOPIC)
                    ),
                ): str,
            }),
        )
