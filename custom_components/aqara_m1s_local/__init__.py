from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import device_registry as dr
from homeassistant.components import button, sensor, select, number

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
    DATA_SOUND_MAP,
    DATA_PLAYBACK_VOLUME,
)
from .client import AqaraM1SClient

PLATFORMS = [button.DOMAIN, sensor.DOMAIN, select.DOMAIN, number.DOMAIN]


def build_play_command(path: str, volume: int | float | None = None) -> str:
    vol = int(volume if volume is not None else 20)
    vol = max(0, min(100, vol))
    return f'setprop persist.sys.volume {vol}; aplay -x 1 "{path}"'


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    username = entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    password = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)

    client = AqaraM1SClient(host=host, port=port, username=username, password=password)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_CLIENTS, {})
    hass.data[DOMAIN].setdefault(DATA_SELECTED_SOUND, {})
    hass.data[DOMAIN].setdefault(DATA_SOUND_MAP, {})
    hass.data[DOMAIN].setdefault(DATA_PLAYBACK_VOLUME, {})
    hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id] = client
    hass.data[DOMAIN][DATA_SELECTED_SOUND][entry.entry_id] = "/data/musics/music-scene/door_bell_1.wav"
    hass.data[DOMAIN][DATA_SOUND_MAP][entry.entry_id] = {}
    hass.data[DOMAIN][DATA_PLAYBACK_VOLUME][entry.entry_id] = 20

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

    def _volume(call: ServiceCall) -> int:
        return int(call.data.get("volume", hass.data[DOMAIN][DATA_PLAYBACK_VOLUME].get(entry.entry_id, 20)))

    async def play_url(call: ServiceCall) -> None:
        client = await _get_client(call)
        url = call.data["url"]
        vol = max(0, min(100, _volume(call)))
        cmd = f'setprop persist.sys.volume {vol}; wget -q "{url}" -O /tmp/ha_audio.wav && aplay -x 1 /tmp/ha_audio.wav'
        await hass.async_add_executor_job(client.run_command, cmd)

    async def play_sound(call: ServiceCall) -> None:
        client = await _get_client(call)
        path = call.data["path"]
        cmd = build_play_command(path, _volume(call))
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
        hass.data[DOMAIN][DATA_SOUND_MAP].pop(entry.entry_id, None)
        hass.data[DOMAIN][DATA_PLAYBACK_VOLUME].pop(entry.entry_id, None)
    return unloaded
