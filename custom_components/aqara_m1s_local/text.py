from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import OPT_AUDIO_URL
from . import device_info

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([M1SAudioUrlText(hass, entry)])

class M1SAudioUrlText(TextEntity):
    _attr_has_entity_name = True
    _attr_name = "Audio URL"
    _attr_native_min = 0
    _attr_native_max = 255
    _attr_mode = "text"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_audio_url"
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> str:
        return self.entry.options.get(OPT_AUDIO_URL, "")

    async def async_set_value(self, value: str) -> None:
        new_options = dict(self.entry.options)
        new_options[OPT_AUDIO_URL] = value
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)
        self.async_write_ha_state()
