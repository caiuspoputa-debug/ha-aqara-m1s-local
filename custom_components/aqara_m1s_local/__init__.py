from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import device_registry as dr
from homeassistant.components import button, sensor, select

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DEFAULT_PASSWORD,
    SERVICE_PLAY_URL,
    SERVICE_PLAY_SOUND,
    SERVICE_RUN_COMMAND,
    DATA_CLIENTS,
    DATA_SELECTED_SOUND,
)
from .client import AqaraM1SClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [button.DOMAIN, sensor.DOMAIN, select.DOMAIN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    username = entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    password = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)

    client = AqaraM1SClient(host=host, port=port, username=username, password=password)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_CLIENTS, {})
    hass.data[DOMAIN].setdefault(DATA_SELECTED_SOUND, {})
    hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id] = client
    hass.data[DOMAIN][DATA_SELECTED_SOUND][entry.entry_id] = "/data/musics/music-scene/door_bell_1.wav"

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, host)},
        name=entry.data.get("name", f"Aqara M1S {host}"),
        manufacturer="Aqara",
        model="M1S",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _get_client(call: ServiceCall) -> AqaraM1SClient:
        call_host = call.data.get("host")
        if call_host:
            for c in hass.data[DOMAIN][DATA_CLIENTS].values():
                if c.host == call_host:
                    return c
            return AqaraM1SClient(
                host=call_host,
                port=call.data.get("port", DEFAULT_PORT),
                username=call.data.get("username", DEFAULT_USERNAME),
                password=call.data.get("password", DEFAULT_PASSWORD),
            )
        return hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id]

    async def play_url(call: ServiceCall) -> None:
        client = await _get_client(call)
        url = call.data["url"]
        cmd = f'wget -q "{url}" -O /tmp/ha_audio.wav && aplay /tmp/ha_audio.wav'
        await hass.async_add_executor_job(client.run_command, cmd)

    async def play_sound(call: ServiceCall) -> None:
        client = await _get_client(call)
        path = call.data["path"]
        cmd = f'aplay "{path}"'
        await hass.async_add_executor_job(client.run_command, cmd)

    async def run_command(call: ServiceCall) -> None:
        client = await _get_client(call)
        cmd = call.data["command"]
        await hass.async_add_executor_job(client.run_command, cmd)

    hass.services.async_register(DOMAIN, SERVICE_PLAY_URL, play_url)
    hass.services.async_register(DOMAIN, SERVICE_PLAY_SOUND, play_sound)
    hass.services.async_register(DOMAIN, SERVICE_RUN_COMMAND, run_command)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN][DATA_CLIENTS].pop(entry.entry_id, None)
        hass.data[DOMAIN][DATA_SELECTED_SOUND].pop(entry.entry_id, None)
    return unloaded
