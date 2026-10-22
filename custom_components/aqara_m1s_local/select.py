from homeassistant.components.select import SelectEntity

from .const import DATA_STOCK, DOMAIN
from .entity import StockEntity
from .registry import track_entities


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    track_entities(runtime, "select", async_add_entities)(
        [NativeCatalog(entry, runtime)]
    )


class NativeCatalog(StockEntity, SelectEntity):
    def __init__(self, entry, runtime):
        super().__init__(entry, runtime, "sound_select", "Native stock sound")

    @property
    def options(self):
        return list(self.runtime.sounds)

    @property
    def current_option(self):
        return self.runtime.selected_sound

    @property
    def available(self):
        return self.runtime.capabilities_valid and bool(self.runtime.sounds)

    async def async_select_option(self, option):
        if not self.available or option not in self.runtime.sounds:
            raise ValueError("Native catalog entry unavailable")
        self.runtime.selected_sound = option
        self.runtime.notify()
