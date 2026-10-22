from typing import ClassVar

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.exceptions import HomeAssistantError

from .const import DATA_STOCK, DOMAIN
from .entity import StockEntity
from .registry import track_entities


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    track_entities(runtime, "light", async_add_entities)(
        [StockRing(entry, hass.data[DOMAIN][DATA_STOCK][entry.entry_id])]
    )


class StockRing(StockEntity, LightEntity):
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_assumed_state = True

    def __init__(self, entry, runtime):
        super().__init__(entry, runtime, "ring_light", "Ring light")

    @property
    def is_on(self):
        return None if self.runtime.ring is None else self.runtime.ring[1] > 0

    @property
    def brightness(self):
        return self.runtime.ring[1] if self.runtime.ring else None

    @property
    def rgb_color(self):
        return self.runtime.ring[0] if self.runtime.ring else None

    @property
    def extra_state_attributes(self):
        return {
            "state_source": "last_rpc_accepted_request_not_physical_readback",
            "request_cache_stale": self.runtime.ring_stale,
            "physical_state_known": False,
        }

    async def async_turn_on(self, **kwargs):
        rgb = kwargs.get(ATTR_RGB_COLOR, self.rgb_color or (255, 255, 255))
        brightness = kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255)
        try:
            await self.runtime.async_ring(rgb, brightness)
        except (OSError, ValueError, TimeoutError, ConnectionError) as err:
            raise HomeAssistantError(
                "Stock ring command was not confirmed; remaining steps were cancelled"
            ) from err

    async def async_turn_off(self, **kwargs):
        try:
            await self.runtime.async_ring(self.rgb_color or (255, 255, 255), 0)
        except (OSError, ValueError, TimeoutError, ConnectionError) as err:
            raise HomeAssistantError(
                "Stock ring OFF outcome is unknown; no retry was sent"
            ) from err
