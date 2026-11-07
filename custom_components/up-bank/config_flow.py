import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .const import DOMAIN
from .up import UP

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)
_LOGGER = logging.getLogger(__name__)


class UpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            user_input[CONF_API_KEY] = api_key

            try:
                session = async_get_clientsession(self.hass)
                up = UP(api_key, session=session)
                valid = await up.test(api_key)

                if valid:
                    return self.async_create_entry(title="UP", data=user_input)
                errors["base"] = "invalid_auth"
            except ConnectionError:
                _LOGGER.exception("Connection error during Up Bank setup")
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during Up Bank setup")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
