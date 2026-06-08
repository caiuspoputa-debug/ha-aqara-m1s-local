from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, BUILTIN_SOUNDS
from . import _play_builtin

BUTTONS = [
    ("bell", "Play Bell", "bell"),
    ("alarm", "Play Alarm", "alarm"),
    ("disarm", "Play Disarm", "disarm"),
    ("arm_ok", "Play Arm OK", "arm_ok"),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([AqaraM1SButton(hass, entry, key, name, sound) for key, name, sound in BUTTONS])


class AqaraM1SButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, key: str, name: str, sound: str) -> None:
        self.hass = hass
        self.entry = entry
        self.key = key
        self.sound = sound
        self._attr_name = f"{entry.data.get(CONF_NAME)} {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get(CONF_NAME),
            "manufacturer": "Aqara",
            "model": "Hub M1S Local",
            "configuration_url": f"http://{entry.data.get(CONF_HOST)}",
        }

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            _play_builtin,
            self.entry.data[CONF_HOST],
            self.entry.data[CONF_PORT],
            self.sound,
        )
