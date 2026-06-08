from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME

from .const import DOMAIN, DEFAULT_PORT, DEFAULT_NAME, OPT_AUDIO_URL, OPT_SELECTED_SOUND, BUILTIN_SOUNDS
from .client import AqaraM1SClient

class AqaraM1SLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            name = user_input.get(CONF_NAME) or f"Aqara M1S {host}"
            audio_url = user_input.get(OPT_AUDIO_URL, "")

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            client = AqaraM1SClient(host, port)
            try:
                await client.test_connection()
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=name,
                    data={CONF_HOST: host, CONF_PORT: port, CONF_NAME: name},
                    options={OPT_AUDIO_URL: audio_url, OPT_SELECTED_SOUND: "bell"},
                )

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Optional(OPT_AUDIO_URL, default=""): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return AqaraM1SLocalOptionsFlow(config_entry)

class AqaraM1SLocalOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = dict(self.config_entry.options)
        schema = vol.Schema({
            vol.Optional(OPT_AUDIO_URL, default=current.get(OPT_AUDIO_URL, "")): str,
            vol.Optional(OPT_SELECTED_SOUND, default=current.get(OPT_SELECTED_SOUND, "bell")): vol.In(list(BUILTIN_SOUNDS.keys())),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
