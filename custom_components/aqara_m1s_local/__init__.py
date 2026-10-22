"""Aqara M1S Local: stock-service adapter, not a coordinator replacement."""

from __future__ import annotations

import probatio as vol
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError

from .catalog import sound_for_option
from .client import AqaraM1SClient
from .const import (
    CONF_AUDIO_LIMIT,
    CONF_CHILD_CONTROL,
    CONF_MQTT_PORT,
    CONF_MQTT_TRANSPORT,
    CONF_STALE_SECONDS,
    DATA_CLIENTS,
    DATA_STOCK,
    DEFAULT_MQTT_PORT,
    DEFAULT_PORT,
    DOMAIN,
    SERVICE_PLAY_SOUND,
    SERVICE_REFRESH,
)
from .mqtt_client import AqaraM1SMqttClient
from .registry import RegistryCleanup
from .runtime import StockRuntime
from .telnet_mqtt import stream_factory

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]
_SELECTOR = {
    vol.Optional("entry_id"): str,
    vol.Optional("host"): str,
}


def _register_services(hass):
    if hass.services.has_service(DOMAIN, SERVICE_PLAY_SOUND):
        return

    def resolve(data):
        entries = hass.data[DOMAIN][DATA_STOCK]
        matches = [
            runtime
            for entry_id, runtime in entries.items()
            if ("entry_id" not in data or entry_id == data["entry_id"])
            and ("host" not in data or runtime.client.host == data["host"])
        ]
        if len(matches) != 1:
            raise HomeAssistantError(
                "Specify one configured M1S using entry_id or host"
            )
        return matches[0]

    async def play(call):
        runtime = resolve(call.data)
        path = call.data.get("sound_path")
        option = (
            f"{call.data.get('sound_type', 'doorbell')}/{call.data.get('sound_id', 1)}"
        )
        if path is not None:
            sound = next((s for s in runtime.sounds.values() if s.path == path), None)
            if sound is None:
                raise HomeAssistantError(
                    "This WAV has no available native catalog mapping"
                )
            if (
                "sound_type" in call.data
                and sound.family != call.data["sound_type"]
                or "sound_id" in call.data
                and sound.index != call.data["sound_id"]
            ):
                raise HomeAssistantError(
                    "Conflicting sound path and native catalog selection"
                )
            option = sound.option
        try:
            sound = sound_for_option(option)
            await runtime.async_play_sound(
                sound.index,
                call.data.get("volume"),
                sound_type=sound.family,
            )
        except (OSError, ValueError, TimeoutError, ConnectionError) as err:
            raise HomeAssistantError(
                "Native playback was not confirmed; it was not retried"
            ) from err

    async def refresh(call):
        await resolve(call.data).async_refresh_inventory()

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_SOUND,
        play,
        schema=vol.Schema(
            {
                **_SELECTOR,
                vol.Optional("sound_id"): vol.All(int, vol.Range(min=1, max=10)),
                vol.Optional("sound_type"): vol.In(("doorbell", "welcome", "alarm")),
                vol.Optional("sound_path"): str,
                vol.Optional("volume"): vol.All(int, vol.Range(min=1, max=100)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH, refresh, schema=vol.Schema(_SELECTOR)
    )


async def async_setup_entry(hass, entry):
    data = hass.data.setdefault(DOMAIN, {})
    for key in (DATA_STOCK, DATA_CLIENTS):
        data.setdefault(key, {})
    client = AqaraM1SClient(
        entry.data["host"],
        entry.data.get("port", DEFAULT_PORT),
        entry.data.get("username", "admin"),
        entry.data.get("password", ""),
    )
    transport = entry.options.get(CONF_MQTT_TRANSPORT, "telnet")
    factory = (
        stream_factory(
            hass.async_add_executor_job,
            host=client.host,
            port=client.port,
            username=client.username,
            password=client.password,
        )
        if transport == "telnet"
        else None
    )
    mqtt = AqaraM1SMqttClient(
        client.host,
        entry.data.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT),
        stream_factory=factory,
    )
    runtime = StockRuntime(
        client,
        mqtt,
        hass.async_add_executor_job,
        audio_limit=entry.options.get(CONF_AUDIO_LIMIT, 5),
        allow_child_control=entry.options.get(CONF_CHILD_CONTROL, False),
        stale_seconds=entry.options.get(CONF_STALE_SECONDS, 86400),
    )
    runtime.mqtt_transport = transport
    data[DATA_STOCK][entry.entry_id] = runtime
    data[DATA_CLIENTS][entry.entry_id] = client
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        cleaner = RegistryCleanup(hass, entry, runtime)
        entry.async_on_unload(runtime.listen(cleaner.update))
        await runtime.async_start()
    except BaseException:
        try:
            await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        finally:
            await runtime.async_close()
            data[DATA_STOCK].pop(entry.entry_id, None)
            data[DATA_CLIENTS].pop(entry.entry_id, None)
        raise
    entry.async_on_unload(entry.add_update_listener(_reload))
    _register_services(hass)
    return True


async def _reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    data = hass.data[DOMAIN]
    runtime = data[DATA_STOCK].pop(entry.entry_id)
    await runtime.async_close()
    data[DATA_CLIENTS].pop(entry.entry_id, None)
    if not data[DATA_STOCK]:
        for service in (SERVICE_PLAY_SOUND, SERVICE_REFRESH):
            hass.services.async_remove(DOMAIN, service)
    return True
