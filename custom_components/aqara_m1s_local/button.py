from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_CLIENTS, DATA_SELECTED_SOUND


@dataclass
class SoundButton:
    key: str
    name: str
    path: str | None


DEFAULT_BUTTONS = [
    SoundButton("play_bell", "Play Bell", "/data/musics/music-scene/door_bell_1.wav"),
    SoundButton("play_alarm", "Play Alarm", "/data/musics/music-scene/alarm.wav"),
    SoundButton("play_arm_ok", "Play Arm OK", "/data/musics/music-scene/arm_ok.wav"),
    SoundButton("play_disarm", "Play Disarm", "/data/musics/music-scene/disarm.wav"),
    SoundButton("play_selected", "Play Selected Sound", None),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    client = hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id]
    entities = [AqaraM1SSoundButton(hass, entry, client, item) for item in DEFAULT_BUTTONS]
    async_add_entities(entities)


class AqaraM1SSoundButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client, item: SoundButton):
        self.hass = hass
        self.entry = entry
        self.client = client
        self.item = item
        self._attr_name = item.name
        self._attr_unique_id = f"{entry.entry_id}_{item.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.client.host)},
            "name": entry.data.get("name", f"Aqara M1S {self.client.host}"),
            "manufacturer": "Aqara",
            "model": "M1S",
        }

    async def async_press(self) -> None:
        path = self.item.path
        if path is None:
            path = self.hass.data[DOMAIN][DATA_SELECTED_SOUND].get(self.entry.entry_id)
        if not path:
            return
        await self.hass.async_add_executor_job(self.client.run_command, f'aplay "{path}"')
