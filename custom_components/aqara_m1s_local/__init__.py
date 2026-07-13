from __future__ import annotations

from pathlib import PurePosixPath
import re
import shlex

from homeassistant.components import button, light, select, sensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr

from .client import AqaraM1SClient
from .const import (
    CONF_MQTT_PORT,
    DATA_CLIENTS,
    DATA_MQTT_CLIENTS,
    DATA_SELECTED_SOUND,
    DATA_SOUND_MAP,
    DEFAULT_MQTT_PORT,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
    SERVICE_PLAY_SOUND,
    SERVICE_PLAY_URL,
    SERVICE_RUN_COMMAND,
)
from .mqtt_client import AqaraM1SMqttClient

PLATFORMS = [
    button.DOMAIN,
    light.DOMAIN,
    sensor.DOMAIN,
    select.DOMAIN,
]


def _official_scene_sound(path: str) -> tuple[str, int] | None:
    """Map supported music-scene filenames to basis_cli parameters.

    These routes are handled by mha_basis and therefore respect the hub's
    official 1-100 volume property.
    """
    sound_path = PurePosixPath(path)
    if sound_path.parent.as_posix() != "/data/musics/music-scene":
        return None

    filename = sound_path.name

    match = re.fullmatch(r"door_bell_(\d+)\.wav", filename)
    if match:
        return "doorbell", int(match.group(1))

    match = re.fullmatch(r"welcome_(\d+)\.wav", filename)
    if match:
        return "welcome", int(match.group(1))

    match = re.fullmatch(r"alarm_(\d+)\.wav", filename)
    if match:
        return "alarm", int(match.group(1))

    return None


def build_play_command(path: str) -> str:
    """Build the safest available playback command for a WAV path.

    Recognized music-scene files use the official basis.system/system_sing
    route through mha_basis. Other files keep the previous direct ALSA
    fallback so existing Chinese, US and miscellaneous buttons still work.
    """
    official = _official_scene_sound(path)
    if official is not None:
        sound_type, index = official
        return (
            'V="$(getprop persist.sys.volume)"; '
            'case "$V" in ""|*[!0-9]*) V=50;; esac; '
            '[ "$V" -lt 1 ] && V=1; '
            '[ "$V" -gt 100 ] && V=100; '
            f'/bin/basis_cli -sys -s {sound_type} {index} 0 "$V"'
        )

    return f"aplay -x 1 {shlex.quote(path)}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    mqtt_port = entry.data.get(
        CONF_MQTT_PORT,
        DEFAULT_MQTT_PORT,
    )
    username = entry.data.get(
        CONF_USERNAME,
        DEFAULT_USERNAME,
    )
    password = entry.data.get(
        CONF_PASSWORD,
        DEFAULT_PASSWORD,
    )

    client = AqaraM1SClient(
        host=host,
        port=port,
        username=username,
        password=password,
    )
    mqtt_client = AqaraM1SMqttClient(
        host=host,
        port=mqtt_port,
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(DATA_CLIENTS, {})
    hass.data[DOMAIN].setdefault(
        DATA_MQTT_CLIENTS,
        {},
    )
    hass.data[DOMAIN].setdefault(
        DATA_SELECTED_SOUND,
        {},
    )
    hass.data[DOMAIN].setdefault(
        DATA_SOUND_MAP,
        {},
    )

    hass.data[DOMAIN][DATA_CLIENTS][
        entry.entry_id
    ] = client
    hass.data[DOMAIN][DATA_MQTT_CLIENTS][
        entry.entry_id
    ] = mqtt_client
    hass.data[DOMAIN][DATA_SELECTED_SOUND][
        entry.entry_id
    ] = (
        "/data/musics/music-scene/"
        "door_bell_1.wav"
    )
    hass.data[DOMAIN][DATA_SOUND_MAP][
        entry.entry_id
    ] = {}

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, host)},
        name=entry.data.get(
            "name",
            f"Aqara M1S {host}",
        ),
        manufacturer="Aqara",
        model="M1S",
    )

    await mqtt_client.start()
    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    async def _get_client(
        call: ServiceCall,
    ) -> AqaraM1SClient:
        call_host = call.data.get("host")
        if call_host:
            for configured_client in hass.data[
                DOMAIN
            ][DATA_CLIENTS].values():
                if configured_client.host == call_host:
                    return configured_client
            return AqaraM1SClient(
                host=call_host,
                port=call.data.get(
                    "port",
                    DEFAULT_PORT,
                ),
                username=call.data.get(
                    "username",
                    DEFAULT_USERNAME,
                ),
                password=call.data.get(
                    "password",
                    DEFAULT_PASSWORD,
                ),
            )
        return hass.data[DOMAIN][DATA_CLIENTS][
            entry.entry_id
        ]

    async def play_url(call: ServiceCall) -> None:
        selected_client = await _get_client(call)
        url = call.data["url"]
        command = (
            f'wget -q "{url}" '
            "-O /tmp/ha_audio.wav "
            "&& aplay -x 1 /tmp/ha_audio.wav"
        )
        await hass.async_add_executor_job(
            selected_client.run_command,
            command,
        )

    async def play_sound(
        call: ServiceCall,
    ) -> None:
        selected_client = await _get_client(call)
        path = call.data["path"]
        await hass.async_add_executor_job(
            selected_client.run_command,
            build_play_command(path),
        )

    async def run_command(
        call: ServiceCall,
    ) -> None:
        selected_client = await _get_client(call)
        await hass.async_add_executor_job(
            selected_client.run_command,
            call.data["command"],
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_URL,
        play_url,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_SOUND,
        play_sound,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_COMMAND,
        run_command,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    unloaded = (
        await hass.config_entries.async_unload_platforms(
            entry,
            PLATFORMS,
        )
    )
    if not unloaded:
        return False

    mqtt_client = hass.data[DOMAIN][
        DATA_MQTT_CLIENTS
    ].pop(entry.entry_id, None)
    if mqtt_client:
        await mqtt_client.stop()

    hass.data[DOMAIN][DATA_CLIENTS].pop(
        entry.entry_id,
        None,
    )
    hass.data[DOMAIN][DATA_SELECTED_SOUND].pop(
        entry.entry_id,
        None,
    )
    hass.data[DOMAIN][DATA_SOUND_MAP].pop(
        entry.entry_id,
        None,
    )
    return True
