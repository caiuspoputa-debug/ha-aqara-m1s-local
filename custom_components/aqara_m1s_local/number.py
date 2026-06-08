from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_CLIENTS, DATA_PLAYBACK_VOLUME


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    client = hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id]
    async_add_entities([AqaraM1SPlaybackVolumeNumber(hass, entry, client)])


class AqaraM1SPlaybackVolumeNumber(NumberEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client):
        self.hass = hass
        self.entry = entry
        self.client = client
        self._attr_name = "Local Playback Volume"
        self._attr_unique_id = f"{entry.entry_id}_local_playback_volume"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_mode = "slider"
        self._attr_native_value = hass.data[DOMAIN][DATA_PLAYBACK_VOLUME].get(entry.entry_id, 20)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.client.host)},
            "name": entry.data.get("name", f"Aqara M1S {self.client.host}"),
            "manufacturer": "Aqara",
            "model": "M1S",
        }

    async def async_set_native_value(self, value: float) -> None:
        value = int(max(0, min(100, value)))
        self.hass.data[DOMAIN][DATA_PLAYBACK_VOLUME][self.entry.entry_id] = value
        self._attr_native_value = value
        await self.hass.async_add_executor_job(self.client.run_command, f"setprop persist.sys.volume {value}")
        self.async_write_ha_state()
