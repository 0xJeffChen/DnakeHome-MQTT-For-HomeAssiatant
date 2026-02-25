import voluptuous as vol
from homeassistant import config_entries
from .constant import *

class ExternalMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=f"Test {user_input[CONF_BROKER]}", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_BROKER, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_SUB_TOPIC, default=DEFAULT_SUBSCRIBE_TOPIC): str,
                vol.Required(CONF_PUB_TOPIC, default=DEFAULT_PUBLISH_TOPIC): str,
                vol.Required(CONF_ACCOUNT, default=DEFAULT_ACCOUNT): str,
                vol.Required(CONF_GATEWAY, default=DEFAULT_GATEWAY): str,
                vol.Required(CONF_DISPLAY, default=DEFAULT_DISPLAY): str,
            })
        )