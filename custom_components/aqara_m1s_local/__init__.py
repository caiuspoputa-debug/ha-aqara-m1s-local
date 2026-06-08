from __future__ import annotations

import logging
import socket

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall

from .const import BUILTIN_SOUNDS, DEFAULT_TIMEOUT, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Keep v0.1 architecture: button only. This is the stable part that already worked.
PLATFORMS = ["button"]


def _run_command(host: str, port: int, command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run a command through the no-login telnet shell on the hub."""
    with socket.create_connection((host, int(port)), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall((command.rstrip() + "\n").encode())
        try:
            return sock.recv(4096).decode(errors="ignore")
        except Exception:
            return ""


def _play_builtin(host: str, port: int, sound: str) -> str:
    """Play a built-in sound by key or a full path."""
    path = BUILTIN_SOUNDS.get(sound, sound)
    return _run_command(host, port, f"aplay '{path}'")


def _play_url(host: str, port: int, url: str) -> str:
    """Download a WAV file and play it."""
    # keep this deliberately simple for BusyBox shell
    safe_url = str(url).replace("'", "")
    command = f"wget '{safe_url}' -O /tmp/ha_audio.wav && aplay /tmp/ha_audio.wav"
    return _run_command(host, port, command)


def _get_entry_data(hass: HomeAssistant, entry_id: str | None):
    entries = hass.data.get(DOMAIN, {})
    if entry_id:
        return entries.get(entry_id)
    if entries:
        return next(iter(entries.values()))
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aqara M1S Local from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_play_builtin(call: ServiceCall) -> None:
        data = _get_entry_data(hass, call.data.get("entry_id"))
        if not data:
            raise ValueError("No Aqara M1S Local device configured")
        await hass.async_add_executor_job(
            _play_builtin,
            data[CONF_HOST],
            data[CONF_PORT],
            call.data["sound"],
        )

    async def handle_play_url(call: ServiceCall) -> None:
        data = _get_entry_data(hass, call.data.get("entry_id"))
        if not data:
            raise ValueError("No Aqara M1S Local device configured")
        await hass.async_add_executor_job(
            _play_url,
            data[CONF_HOST],
            data[CONF_PORT],
            call.data["url"],
        )

    async def handle_run_command(call: ServiceCall) -> None:
        data = _get_entry_data(hass, call.data.get("entry_id"))
        if not data:
            raise ValueError("No Aqara M1S Local device configured")
        await hass.async_add_executor_job(
            _run_command,
            data[CONF_HOST],
            data[CONF_PORT],
            call.data["command"],
        )

    # Register services once, even with multiple hubs.
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
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
