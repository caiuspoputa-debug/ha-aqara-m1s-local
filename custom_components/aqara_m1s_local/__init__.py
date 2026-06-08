from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import Platform

from .const import DOMAIN, DATA_CLIENTS, BUILTIN_SOUNDS, DEFAULT_PORT
from .client import AqaraM1SClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SELECT, Platform.TEXT]

SERVICE_PLAY_URL = "play_url"
SERVICE_PLAY_BUILTIN = "play_builtin"
SERVICE_RUN_COMMAND = "run_command"

SERVICE_PLAY_URL_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required("url"): cv.url,
})

SERVICE_PLAY_BUILTIN_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required("sound"): vol.In(list(BUILTIN_SOUNDS.keys())),
})

SERVICE_RUN_COMMAND_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required("command"): cv.string,
})

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_CLIENTS, {})

    async def handle_play_url(call: ServiceCall) -> None:
        client = AqaraM1SClient(call.data[CONF_HOST], call.data[CONF_PORT])
        await client.play_url(call.data["url"])

    async def handle_play_builtin(call: ServiceCall) -> None:
        client = AqaraM1SClient(call.data[CONF_HOST], call.data[CONF_PORT])
        await client.play_file(BUILTIN_SOUNDS[call.data["sound"]])

    async def handle_run_command(call: ServiceCall) -> None:
        client = AqaraM1SClient(call.data[CONF_HOST], call.data[CONF_PORT])
        await client.run_command(call.data["command"])

    hass.services.async_register(DOMAIN, SERVICE_PLAY_URL, handle_play_url, schema=SERVICE_PLAY_URL_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PLAY_BUILTIN, handle_play_builtin, schema=SERVICE_PLAY_BUILTIN_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_RUN_COMMAND, handle_run_command, schema=SERVICE_RUN_COMMAND_SCHEMA)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    client = AqaraM1SClient(host, port)
    hass.data.setdefault(DOMAIN, {}).setdefault(DATA_CLIENTS, {})[entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN][DATA_CLIENTS].pop(entry.entry_id, None)
    return unload_ok

def device_info(entry: ConfigEntry) -> DeviceInfo:
    host = entry.data.get(CONF_HOST)
    name = entry.data.get("name", "Aqara M1S Local")
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=name,
        manufacturer="Aqara",
        model="M1S Local",
        configuration_url=f"telnet://{host}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
    )
