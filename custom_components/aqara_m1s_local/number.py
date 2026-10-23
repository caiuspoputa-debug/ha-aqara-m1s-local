import math

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DATA_STOCK, DOMAIN
from .entity import StockEntity
from .native_entity import NativeEntity, entities
from .registry import track_entities


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    track_entities(runtime, "number", async_add_entities)(
        [NativeVolume(entry, runtime)]
        + entities(entry, runtime, "number", PropertyNumber)
    )


class NativeVolume(StockEntity, RestoreEntity, NumberEntity):
    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:volume-high"

    def __init__(self, entry, runtime):
        super().__init__(
            entry, runtime, "sound_playback_volume", "Next sound request volume"
        )
        self._attr_native_max_value = runtime.audio_limit

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        restored = await self.async_get_last_state()
        if restored:
            try:
                value = float(restored.state)
                if math.isfinite(value):
                    self.runtime.volume = max(
                        1, min(self.runtime.audio_limit, round(value))
                    )
            except (TypeError, ValueError):
                pass

    @property
    def native_value(self):
        return self.runtime.volume

    @property
    def extra_state_attributes(self):
        return {
            "applies_to": "next_native_sound_request",
            "global_hardware_volume": False,
            "physically_tested_range": "1..5 percent",
            "writes_hub_when_changed": False,
        }

    async def async_set_native_value(self, value):
        if (
            not math.isfinite(value)
            or int(value) != value
            or not 1 <= value <= self.runtime.audio_limit
        ):
            raise ValueError("Volume outside configured native request range")
        self.runtime.volume = int(value)
        self.runtime.notify()


class PropertyNumber(NativeEntity, NumberEntity):
    def __init__(self, entry, runtime, prop):
        super().__init__(entry, runtime, prop)
        self._attr_native_min_value = prop.minimum
        self._attr_native_max_value = prop.maximum
        self._attr_native_step = prop.step
        self._attr_native_unit_of_measurement = prop.unit
        self._attr_mode = (
            NumberMode.SLIDER if prop.key == "system_volume" else NumberMode.BOX
        )

    @property
    def native_value(self):
        return self.value

    async def async_set_native_value(self, value):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or int(value) != value
        ):
            raise ValueError("Integer native value required")
        await self.async_write(int(value))
