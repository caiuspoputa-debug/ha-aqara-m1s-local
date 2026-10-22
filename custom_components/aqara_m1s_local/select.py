from typing import ClassVar

from homeassistant.components.select import SelectEntity

from .const import DATA_STOCK, DOMAIN
from .entity import StockEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [NativeCatalog(entry, hass.data[DOMAIN][DATA_STOCK][entry.entry_id])]
    )


class NativeCatalog(StockEntity, SelectEntity):
    _attr_options: ClassVar[list[str]] = ["doorbell/1"]
    _attr_current_option = "doorbell/1"

    def __init__(self, entry, runtime):
        super().__init__(entry, runtime, "sound_select", "Validated native sound")

    async def async_select_option(self, option):
        if option != "doorbell/1":
            raise ValueError("Native catalog entry not validated")
