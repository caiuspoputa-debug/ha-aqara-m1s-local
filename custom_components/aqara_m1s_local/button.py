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
    SoundButton("play_door_bell_1", "Play Door Bell 1", "/data/musics/music-scene/door_bell_1.wav"),
    SoundButton("play_door_bell_2", "Play Door Bell 2", "/data/musics/music-scene/door_bell_2.wav"),
    SoundButton("play_door_bell_3", "Play Door Bell 3", "/data/musics/music-scene/door_bell_3.wav"),
    SoundButton("play_door_bell_4", "Play Door Bell 4", "/data/musics/music-scene/door_bell_4.wav"),
    SoundButton("play_alarm", "Play Alarm", "/data/musics/music-scene/alarm.wav"),
    SoundButton("play_alarm_1", "Play Alarm 1", "/data/musics/music-scene/alarm_1.wav"),
    SoundButton("play_alarm_2", "Play Alarm 2", "/data/musics/music-scene/alarm_2.wav"),
    SoundButton("play_alarm_3", "Play Alarm 3", "/data/musics/music-scene/alarm_3.wav"),
    SoundButton("play_alarm_4", "Play Alarm 4", "/data/musics/music-scene/alarm_4.wav"),
    SoundButton("play_alarm_5", "Play Alarm 5", "/data/musics/music-scene/alarm_5.wav"),
    SoundButton("play_alarm_6", "Play Alarm 6", "/data/musics/music-scene/alarm_6.wav"),
    SoundButton("play_alarm_7", "Play Alarm 7", "/data/musics/music-scene/alarm_7.wav"),
    SoundButton("play_alarm_8", "Play Alarm 8", "/data/musics/music-scene/alarm_8.wav"),
    SoundButton("play_alarm_9", "Play Alarm 9", "/data/musics/music-scene/alarm_9.wav"),
    SoundButton("play_arm_ok", "Play Arm OK", "/data/musics/music-scene/arm_ok.wav"),
    SoundButton("play_arm_start", "Play Arm Start", "/data/musics/music-scene/arm_start.wav"),
    SoundButton("play_disarm", "Play Disarm", "/data/musics/music-scene/disarm.wav"),
    SoundButton("play_welcome_1", "Play Welcome 1", "/data/musics/music-scene/welcome_1.wav"),
    SoundButton("play_welcome_2", "Play Welcome 2", "/data/musics/music-scene/welcome_2.wav"),
    SoundButton("play_welcome_3", "Play Welcome 3", "/data/musics/music-scene/welcome_3.wav"),
    SoundButton("play_welcome_4", "Play Welcome 4", "/data/musics/music-scene/welcome_4.wav"),
    SoundButton("play_connected", "Play Connected", "/data/musics/music-us/connected.wav"),
    SoundButton("play_binding_success", "Play Binding Success", "/data/musics/music-us/binding_success.wav"),
    SoundButton("play_join_success", "Play Join Success", "/data/musics/music-us/join_success.wav"),
    SoundButton("play_add_sensor", "Play Add Sensor", "/data/musics/music-us/add_sensor.wav"),
    SoundButton("play_factory_reset", "Play Factory Reset", "/data/musics/music-us/factory_reset.wav"),
    SoundButton("play_wrong_key", "Play Wrong Key", "/data/musics/music-us/wrong_key.wav"),
    SoundButton("play_deleted", "Play Deleted", "/data/musics/music-us/deleted.wav"),
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
