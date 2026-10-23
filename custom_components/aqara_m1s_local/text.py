from homeassistant.components.text import TextEntity, TextMode

from .const import DATA_STOCK, DOMAIN
from .native_entity import NativeEntity, entities
from .registry import track_entities


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    track_entities(runtime, "text", async_add_entities)(
        entities(entry, runtime, "text", PropertyText)
    )


class PropertyText(NativeEntity, TextEntity):
    _attr_native_min = 11
    _attr_native_max = 11
    _attr_pattern = r"(?:[01][0-9]|2[0-3]):[0-5][0-9]-(?:[01][0-9]|2[0-3]):[0-5][0-9]"
    _attr_mode = TextMode.TEXT

    @property
    def native_value(self):
        return self.value

    async def async_set_value(self, value):
        await self.async_write(value)
