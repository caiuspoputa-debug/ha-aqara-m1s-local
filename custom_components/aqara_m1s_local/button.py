from __future__ import annotations

from pathlib import PurePosixPath
import re

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_CLIENTS,
    DATA_PLAYBACK_VOLUME,
    DATA_SELECTED_SOUND,
    DOMAIN,
)
from . import build_play_command


FALLBACK_SOUNDS = [
    "/data/musics/music-scene/door_bell_1.wav",
    "/data/musics/music-scene/alarm.wav",
    "/data/musics/music-scene/arm_ok.wav",
    "/data/musics/music-scene/disarm.wav",
]


def label_for_path(path: str) -> str:
    p = PurePosixPath(path)
    parent = p.parent.name.replace("music-", "").replace("_", " ").title()
    name = p.stem.replace("_", " ").replace("-", " ").title()
    return f"Play {parent} {name}"


def key_for_path(path: str) -> str:
    key = path.replace("/data/musics/", "").replace("/", "_").replace(".", "_")
    return re.sub(r"[^a-zA-Z0-9_]+", "_", key).lower()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(
        DATA_PLAYBACK_VOLUME,
        {},
    )
    hass.data[DOMAIN][DATA_PLAYBACK_VOLUME].setdefault(
        entry.entry_id,
        50,
    )

    client = hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id]
    sounds = await hass.async_add_executor_job(client.list_sounds)
    if not sounds:
        sounds = FALLBACK_SOUNDS

    entities = [AqaraM1SSelectedSoundButton(hass, entry, client)]
    entities += [AqaraM1SSoundButton(hass, entry, client, path) for path in sounds]
    async_add_entities(entities)


class AqaraM1SSelectedSoundButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client):
        self.hass = hass
        self.entry = entry
        self.client = client
        self._attr_name = "Play Selected Sound"
        self._attr_unique_id = f"{entry.entry_id}_play_selected_sound"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.client.host)},
            "name": entry.data.get("name", f"Aqara M1S {self.client.host}"),
            "manufacturer": "Aqara",
            "model": "M1S",
        }

    async def async_press(self) -> None:
        path = self.hass.data[DOMAIN][DATA_SELECTED_SOUND].get(self.entry.entry_id)
        if not path:
            return
        volume = self.hass.data.get(DOMAIN, {}).get(
            DATA_PLAYBACK_VOLUME,
            {},
        ).get(
            self.entry.entry_id,
            50,
        )
        command = build_play_command(path, volume)
        await self.hass.async_add_executor_job(
            self.client.run_command,
            command,
        )


class AqaraM1SSoundButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client, path: str):
        self.hass = hass
        self.entry = entry
        self.client = client
        self.path = path
        self._attr_name = label_for_path(path)
        self._attr_unique_id = f"{entry.entry_id}_play_{key_for_path(path)}"
        self._attr_extra_state_attributes = {
            "file_path": path,
            "playback_route": "mha_basis_staged_slot",
            "respects_playback_volume": True,
            "staging_slot": (
                "/data/musics/music-scene/"
                "door_bell_99.wav"
            ),
        }
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.client.host)},
            "name": entry.data.get("name", f"Aqara M1S {self.client.host}"),
            "manufacturer": "Aqara",
            "model": "M1S",
        }

    async def async_press(self) -> None:
        volume = self.hass.data.get(DOMAIN, {}).get(
            DATA_PLAYBACK_VOLUME,
            {},
        ).get(
            self.entry.entry_id,
            50,
        )
        command = build_play_command(self.path, volume)
        await self.hass.async_add_executor_job(
            self.client.run_command,
            command,
        )
