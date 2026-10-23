"""Common availability and validation for the explicit native property entities."""

from homeassistant.exceptions import HomeAssistantError

from .entity import StockEntity
from .native_properties import PROPERTIES


class NativeEntity(StockEntity):
    def __init__(self, entry, runtime, prop):
        super().__init__(entry, runtime, "native_" + prop.key, prop.name)
        self.prop = prop
        self._attr_entity_category = "config" if prop.writable else "diagnostic"
        self._attr_entity_registry_enabled_default = not prop.advanced

    @property
    def available(self):
        return self.runtime.native_has(self.prop.key)

    @property
    def value(self):
        return self.runtime.native_values.get(self.prop.key)

    @property
    def extra_state_attributes(self):
        return {
            "siid": self.prop.siid,
            "piid": self.prop.piid,
            "state_source": "native_get_properties",
            "readback_pending": self.prop.key in self.runtime.native_pending,
        }

    async def async_write(self, value):
        try:
            await self.runtime.async_set_native(self.prop.key, value)
        except (OSError, ValueError, TimeoutError, ConnectionError) as err:
            raise HomeAssistantError(
                "Native command was not confirmed; no retry was sent"
            ) from err


def entities(entry, runtime, platform, factory):
    return [
        factory(entry, runtime, prop)
        for prop in PROPERTIES
        if prop.platform == platform and prop.read
    ]
