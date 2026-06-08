from __future__ import annotations

import socket
import logging
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, DEFAULT_TIMEOUT, BUILTIN_SOUNDS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["button"]


def _run_command(host: str, port: int, command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    with socket.create_connection((host, int(port)), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall((command.rstrip() + "\n").encode())
        try:
            return sock.recv(4096).decode(errors="ignore")
        except Exception:
            return ""


def _play_builtin(host: str, port: int, sound: str) -> str:
    path = BUILTIN_SOUNDS.get(sound, sound)
    return _run_command(host, port, f"aplay {path}")


def _play_url(host: str, port: int, url: str) -> str:
    safe_url = url.replace("'", "")
    return _run_command(host, port, f"wget '{safe_url}' -O /tmp/ha_audio.wav && aplay /tmp/ha_audio.wav")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_play_builtin(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        sound = call.data["sound"]
        data = hass.data[DOMAIN].get(entry_id) if entry_id else next(iter(hass.data[DOMAIN].values()))
        if not data:
            raise ValueError("No Aqara M1S Local device configured")
        await hass.async_add_executor_job(_play_builtin, data[CONF_HOST], data[CONF_PORT], sound)

    async def handle_play_url(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        url = call.data["url"]
        data = hass.data[DOMAIN].get(entry_id) if entry_id else next(iter(hass.data[DOMAIN].values()))
        if not data:
            raise ValueError("No Aqara M1S Local device configured")
        await hass.async_add_executor_job(_play_url, data[CONF_HOST], data[CONF_PORT], url)

    async def handle_run_command(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        command = call.data["command"]
        data = hass.data[DOMAIN].get(entry_id) if entry_id else next(iter(hass.data[DOMAIN].values()))
        if not data:
            raise ValueError("No Aqara M1S Local device configured")
        await hass.async_add_executor_job(_run_command, data[CONF_HOST], data[CONF_PORT], command)

    if not hass.services.has_service(DOMAIN, "play_builtin"):
        hass.services.async_register(
            DOMAIN,
            "play_builtin",
            handle_play_builtin,
            schema=vol.Schema({vol.Optional("entry_id"): str, vol.Required("sound"): str}),
        )
        hass.services.async_register(
            DOMAIN,
            "play_url",
            handle_play_url,
            schema=vol.Schema({vol.Optional("entry_id"): str, vol.Required("url"): str}),
        )
        hass.services.async_register(
            DOMAIN,
            "run_command",
            handle_run_command,
            schema=vol.Schema({vol.Optional("entry_id"): str, vol.Required("command"): str}),
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
