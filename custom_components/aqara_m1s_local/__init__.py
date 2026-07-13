from __future__ import annotations

from homeassistant.components import button, light, media_player, number, select, sensor
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
    DATA_PLAYBACK_VOLUME,
    DATA_RADIO_PLAYERS,
    DATA_SELECTED_SOUND,
    DATA_SOUND_MAP,
    DATA_SOUND_PLAYERS,
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
from .sound_player import AqaraM1SSoundPlayer

PLATFORMS = [
    button.DOMAIN,
    light.DOMAIN,
    media_player.DOMAIN,
    number.DOMAIN,
    sensor.DOMAIN,
    select.DOMAIN,
]



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
    DATA_SOUND_PLAYERS,
        {},
    )
    hass.data[DOMAIN].setdefault(
        DATA_PLAYBACK_VOLUME,
        {},
    )
    hass.data[DOMAIN].setdefault(
        DATA_RADIO_PLAYERS,
        {},
    )
    hass.data[DOMAIN].setdefault(
        DATA_SOUND_PLAYERS,
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
    hass.data[DOMAIN][DATA_PLAYBACK_VOLUME][
        entry.entry_id
    ] = 50
    hass.data[DOMAIN][DATA_SOUND_PLAYERS][entry.entry_id] = AqaraM1SSoundPlayer(
        hass, client
    )

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
        sound_player = hass.data[DOMAIN][DATA_SOUND_PLAYERS][entry.entry_id]
        await sound_player.async_play(
            path,
            hass.data[DOMAIN][DATA_PLAYBACK_VOLUME].get(entry.entry_id, 50),
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

    radio_player = hass.data[DOMAIN][DATA_RADIO_PLAYERS].pop(
        entry.entry_id,
        None,
    )
    if radio_player:
        await radio_player.async_shutdown()

    sound_player = hass.data[DOMAIN][DATA_SOUND_PLAYERS].pop(
        entry.entry_id,
        None,
    )
    if sound_player:
        await sound_player.async_stop()

    telnet_client = hass.data[DOMAIN][DATA_CLIENTS].pop(
        entry.entry_id,
        None,
    )
    if telnet_client:
        await hass.async_add_executor_job(telnet_client.close)
    hass.data[DOMAIN][DATA_SELECTED_SOUND].pop(
        entry.entry_id,
        None,
    )
    hass.data[DOMAIN][DATA_SOUND_MAP].pop(
        entry.entry_id,
        None,
    )
    hass.data[DOMAIN][DATA_PLAYBACK_VOLUME].pop(
        entry.entry_id,
        None,
    )
    return True
