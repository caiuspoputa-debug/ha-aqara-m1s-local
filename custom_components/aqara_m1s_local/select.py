from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUILTIN_SOUNDS, OPT_SELECTED_SOUND
from . import device_info

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([M1SSoundSelect(hass, entry)])

class M1SSoundSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Builtin Sound"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_builtin_sound"
        self._attr_options = list(BUILTIN_SOUNDS.keys())
        self._attr_device_info = device_info(entry)

    @property
    def current_option(self) -> str:
        return self.entry.options.get(OPT_SELECTED_SOUND, "bell")

    async def async_select_option(self, option: str) -> None:
        if option not in BUILTIN_SOUNDS:
            return
        new_options = dict(self.entry.options)
        new_options[OPT_SELECTED_SOUND] = option
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)
        self.async_write_ha_state()
