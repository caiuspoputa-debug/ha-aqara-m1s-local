from homeassistant.components.select import SelectEntity

from .const import DATA_STOCK, DOMAIN
from .entity import StockEntity
from .native_entity import NativeEntity, entities
from .native_properties import options_for
from .registry import track_entities


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    track_entities(runtime, "select", async_add_entities)(
        [NativeCatalog(entry, runtime)]
        + entities(entry, runtime, "select", PropertySelect)
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


class PropertySelect(NativeEntity, SelectEntity):
    @property
    def options(self):
        return options_for(self.prop.key, self.runtime.native_values)

    @property
    def current_option(self):
        value = str(self.value) if self.value is not None else None
        return value if value in self.options else None

    @property
    def available(self):
        return super().available and bool(self.options)

    @property
    def extra_state_attributes(self):
        attributes = super().extra_state_attributes
        if self.prop.key == "guard_mode":
            attributes.update(
                native_mode=self.value, native_mode_zero_is_not_full_disarm=True
            )
        return attributes

    async def async_select_option(self, option):
        if option not in self.options:
            raise ValueError("Option is not in the current stock catalog")
        await self.async_write(int(option) if self.prop.key == "guard_mode" else option)
