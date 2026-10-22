from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError

from .catalog import sound_for_option
from .const import DATA_STOCK, DOMAIN
from .entity import StockEntity
from .registry import track_entities


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    add = track_entities(runtime, "button", async_add_entities)
    add([RefreshInventory(entry, runtime)])

    def update():
        if not runtime.capabilities_valid:
            return
        entities = [StockSound(entry, runtime)] if runtime.sounds else []
        entities += [
            StockSound(entry, runtime, sound) for sound in runtime.sounds.values()
        ]
        add(
            e
            for e in entities
            if ("button", e._attr_unique_id) not in runtime.entity_catalog
        )

    entry.async_on_unload(runtime.listen(update))
    update()


class StockSound(StockEntity, ButtonEntity):
    _attr_icon = "mdi:bell-ring"

    def __init__(self, entry, runtime, sound=None):
        super().__init__(
            entry,
            runtime,
            sound.key if sound else "play_selected_sound",
            f"Play {sound.option}" if sound else "Play selected native sound",
        )
        self.sound = sound

    @property
    def available(self):
        option = self.sound.option if self.sound else self.runtime.selected_sound
        return self.runtime.capabilities_valid and option in self.runtime.sounds

    @property
    def extra_state_attributes(self):
        return {
            "playback_route": "basis_cli_ha_basis_local",
            "once": True,
            "completion_observed": False,
            "catalog_entry": self.sound.option
            if self.sound
            else self.runtime.selected_sound,
            "physically_tested": (
                self.sound.option if self.sound else self.runtime.selected_sound
            )
            == "doorbell/1",
        }

    async def async_press(self):
        try:
            sound = self.sound or sound_for_option(self.runtime.selected_sound)
            await self.runtime.async_play_sound(sound.index, sound_type=sound.family)
        except (OSError, ValueError, TimeoutError, ConnectionError) as err:
            raise HomeAssistantError(
                "Native playback was not confirmed; no retry was sent"
            ) from err


class RefreshInventory(StockEntity, ButtonEntity):
    _attr_entity_category = "diagnostic"
    _attr_icon = "mdi:refresh"

    def __init__(self, entry, runtime):
        super().__init__(entry, runtime, "refresh_inventory", "Refresh stock inventory")

    async def async_press(self):
        await self.runtime.async_refresh_catalog()
        await self.runtime.async_refresh_inventory()
