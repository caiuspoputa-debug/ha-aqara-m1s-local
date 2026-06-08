from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import CONF_NAME

from .const import DOMAIN, DATA_CLIENTS, BUILTIN_SOUNDS, OPT_AUDIO_URL, OPT_SELECTED_SOUND
from . import device_info

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([
        BuiltinSoundButton(hass, entry, "bell", "Play Bell"),
        BuiltinSoundButton(hass, entry, "alarm", "Play Alarm"),
        BuiltinSoundButton(hass, entry, "disarm", "Play Disarm"),
        BuiltinSoundButton(hass, entry, "arm_ok", "Play Arm OK"),
        PlaySelectedButton(hass, entry),
        PlayCustomUrlButton(hass, entry),
    ])

class BaseM1SButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, key: str, name: str) -> None:
        self.hass = hass
        self.entry = entry
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = device_info(entry)

    @property
    def client(self):
        return self.hass.data[DOMAIN][DATA_CLIENTS][self.entry.entry_id]

class BuiltinSoundButton(BaseM1SButton):
    def __init__(self, hass, entry, sound_key: str, name: str) -> None:
        super().__init__(hass, entry, f"play_{sound_key}", name)
        self.sound_key = sound_key

    async def async_press(self) -> None:
        await self.client.play_file(BUILTIN_SOUNDS[self.sound_key])

class PlaySelectedButton(BaseM1SButton):
    def __init__(self, hass, entry) -> None:
        super().__init__(hass, entry, "play_selected_sound", "Play Selected Sound")

    async def async_press(self) -> None:
        sound = self.entry.options.get(OPT_SELECTED_SOUND, "bell")
        await self.client.play_file(BUILTIN_SOUNDS[sound])

class PlayCustomUrlButton(BaseM1SButton):
    def __init__(self, hass, entry) -> None:
        super().__init__(hass, entry, "play_custom_url", "Play Custom URL")

    async def async_press(self) -> None:
        url = self.entry.options.get(OPT_AUDIO_URL, "")
        if url:
            await self.client.play_url(url)
