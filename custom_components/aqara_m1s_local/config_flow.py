from __future__ import annotations

import socket

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from .const import DEFAULT_PORT, DEFAULT_TIMEOUT, DOMAIN


def _test_shell(host: str, port: int) -> None:
    """Test that the no-login shell is open."""
    with socket.create_connection((host, int(port)), timeout=DEFAULT_TIMEOUT) as sock:
        sock.settimeout(DEFAULT_TIMEOUT)
        sock.sendall(b"echo M1S_OK\n")
        try:
            sock.recv(256)
        except Exception:
            # Some telnetd sessions do not answer immediately. Open socket is enough.
            pass


class AqaraM1SLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            name = user_input.get(CONF_NAME) or f"Aqara M1S {host}"

            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            try:
                await self.hass.async_add_executor_job(_test_shell, host, port)
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=name,
                    data={CONF_HOST: host, CONF_PORT: port, CONF_NAME: name},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(CONF_NAME): str,
                }
            ),
            errors=errors,
        )
