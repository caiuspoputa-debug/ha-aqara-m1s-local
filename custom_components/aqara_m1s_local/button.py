from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError

from .const import DATA_STOCK, DOMAIN
from .entity import StockEntity


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    async_add_entities([StockSound(entry, runtime), RefreshInventory(entry, runtime)])


class StockSound(StockEntity, ButtonEntity):
    _attr_icon = "mdi:bell-ring"

    def __init__(self, entry, runtime):
        super().__init__(
            entry, runtime, "play_selected_sound", "Play native doorbell 1"
        )

    @property
    def extra_state_attributes(self):
        return {
            "playback_route": "basis_cli_ha_basis_local",
            "once": True,
            "completion_observed": False,
            "catalog_id": 1,
        }

    async def async_press(self):
        try:
            await self.runtime.async_play_sound()
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
        await self.runtime.async_refresh_inventory()
