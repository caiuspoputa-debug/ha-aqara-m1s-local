from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_CLIENTS, DATA_SELECTED_SOUND


FALLBACK_SOUNDS = [
    "/data/musics/music-scene/door_bell_1.wav",
    "/data/musics/music-scene/door_bell_2.wav",
    "/data/musics/music-scene/door_bell_3.wav",
    "/data/musics/music-scene/door_bell_4.wav",
    "/data/musics/music-scene/alarm.wav",
    "/data/musics/music-scene/arm_ok.wav",
    "/data/musics/music-scene/arm_start.wav",
    "/data/musics/music-scene/disarm.wav",
    "/data/musics/music-scene/welcome_1.wav",
    "/data/musics/music-scene/welcome_2.wav",
    "/data/musics/music-scene/welcome_3.wav",
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    client = hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id]
    sounds = await hass.async_add_executor_job(client.list_sounds)
    if not sounds:
        sounds = FALLBACK_SOUNDS
    async_add_entities([AqaraM1SSoundSelect(hass, entry, client, sounds)])


class AqaraM1SSoundSelect(SelectEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client, sounds: list[str]):
        self.hass = hass
        self.entry = entry
        self.client = client
        self._sounds = sounds
        self._attr_name = "Sound"
        self._attr_unique_id = f"{entry.entry_id}_sound_select"
        self._attr_options = sounds
        current = hass.data[DOMAIN][DATA_SELECTED_SOUND].get(entry.entry_id)
        self._attr_current_option = current if current in sounds else sounds[0]
        hass.data[DOMAIN][DATA_SELECTED_SOUND][entry.entry_id] = self._attr_current_option
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.client.host)},
            "name": entry.data.get("name", f"Aqara M1S {self.client.host}"),
            "manufacturer": "Aqara",
            "model": "M1S",
        }

    async def async_select_option(self, option: str) -> None:
        if option not in self._sounds:
            return
        self._attr_current_option = option
        self.hass.data[DOMAIN][DATA_SELECTED_SOUND][self.entry.entry_id] = option
        self.async_write_ha_state()
