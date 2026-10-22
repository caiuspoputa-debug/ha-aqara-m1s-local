"""Configure an already accessible stock lab hub; never enable access remotely."""

from __future__ import annotations

import ipaddress
import re

import probatio as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import TextSelector

from .const import (
    CONF_AUDIO_LIMIT,
    CONF_CHILD_CONTROL,
    CONF_MQTT_PORT,
    CONF_STALE_SECONDS,
    DEFAULT_MQTT_PORT,
    DEFAULT_PORT,
    DOMAIN,
)


def validate_host(value):
    value = value.strip().lower()
    try:
        ipaddress.ip_address(value)
    except ValueError:
        if len(value) > 253 or not all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part)
            for part in value.rstrip(".").split(".")
        ):
            raise vol.Invalid("Host must be an IP address or hostname")
    return value


def login_field(value):
    if (
        not isinstance(value, str)
        or len(value) > 256
        or any(c in value for c in "\r\n\0")
    ):
        raise vol.Invalid("Invalid login field")
    return value


class AqaraM1SLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return M1SOptionsFlow()

    async def async_step_user(self, user_input=None):
        schema = vol.Schema(
            {
                vol.Required("host"): str,
                vol.Optional("port", default=DEFAULT_PORT): vol.All(
                    int, vol.Range(min=1, max=65535)
                ),
                vol.Optional(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): vol.All(
                    int, vol.Range(min=1, max=65535)
                ),
                vol.Optional("username", default="admin"): str,
                vol.Optional("password", default=""): TextSelector(
                    {"type": "password"}
                ),
                vol.Optional("name", default="Aqara M1S Stock Lab"): str,
            }
        )
        if user_input is not None:
            try:
                data = schema(user_input)
                data["host"] = validate_host(data["host"])
                data["username"] = login_field(data["username"])
                data["password"] = login_field(data["password"])
            except vol.Invalid:
                return self.async_show_form(
                    step_id="user", data_schema=schema, errors={"base": "invalid_input"}
                )
            await self.async_set_unique_id(data["host"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=data.pop("name"), data=data)
        return self.async_show_form(step_id="user", data_schema=schema)


class M1SOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_AUDIO_LIMIT, default=options.get(CONF_AUDIO_LIMIT, 5)
                ): vol.All(int, vol.Range(min=1, max=100)),
                vol.Optional(
                    CONF_CHILD_CONTROL, default=options.get(CONF_CHILD_CONTROL, False)
                ): bool,
                vol.Optional(
                    CONF_STALE_SECONDS, default=options.get(CONF_STALE_SECONDS, 86400)
                ): vol.All(int, vol.Range(min=60, max=604800)),
            }
        )
        if user_input is not None:
            try:
                data = schema(user_input)
            except vol.Invalid:
                return self.async_show_form(
                    step_id="init", data_schema=schema, errors={"base": "invalid_input"}
                )
            return self.async_create_entry(title="", data=data)
        return self.async_show_form(step_id="init", data_schema=schema)
