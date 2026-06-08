from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import _play_builtin, _play_url
from .const import DOMAIN

BUTTONS = [
    ("bell", "Play Bell", "bell"),
    ("alarm", "Play Alarm", "alarm"),
    ("disarm", "Play Disarm", "disarm"),
    ("arm_ok", "Play Arm OK", "arm_ok"),
    ("welcome_1", "Play Welcome 1", "welcome_1"),
    ("door_bell_2", "Play Doorbell 2", "door_bell_2"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entities = [AqaraM1SButton(hass, entry, key, name, sound) for key, name, sound in BUTTONS]
    entities.append(AqaraM1SDefaultUrlButton(hass, entry))
    async_add_entities(entities)


class AqaraM1SButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, key: str, name: str, sound: str) -> None:
        self.hass = hass
        self.entry = entry
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


class AqaraM1SDefaultUrlButton(ButtonEntity):
    """Button that plays /local/test.wav from the HA base URL.

    For any other URL, use the service aqara_m1s_local.play_url.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_name = f"{entry.data.get(CONF_NAME)} Play HA test.wav"
        self._attr_unique_id = f"{entry.entry_id}_play_ha_test_wav"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get(CONF_NAME),
            "manufacturer": "Aqara",
            "model": "Hub M1S Local",
            "configuration_url": f"http://{entry.data.get(CONF_HOST)}",
        }

    async def async_press(self) -> None:
        base = self.hass.config.api.base_url
        if not base:
            # Fallback for typical HA local URL used in this project.
            base = "http://192.168.0.20:8123"
        url = base.rstrip("/") + "/local/test.wav"
        await self.hass.async_add_executor_job(
            _play_url,
            self.entry.data[CONF_HOST],
            self.entry.data[CONF_PORT],
            url,
        )
