from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError

from .const import DATA_STOCK, DOMAIN
from .entity import ChildFieldEntity, discover
from .native_entity import NativeEntity, entities
from .registry import track_entities


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    track_entities(runtime, "switch", async_add_entities)(
        entities(entry, runtime, "switch", PropertySwitch)
    )
    discover(hass, entry, async_add_entities, "switch", ChildSwitch)


class PropertySwitch(NativeEntity, SwitchEntity):
    @property
    def is_on(self):
        return None if self.value is None else self.value == 1

    async def async_turn_on(self, **kwargs):
        await self.async_write(1)

    async def async_turn_off(self, **kwargs):
        await self.async_write(0)


class ChildSwitch(ChildFieldEntity, SwitchEntity):
    _attr_entity_registry_enabled_default = False

    @property
    def available(self):
        return super().available and self.runtime.allow_child_control

    @property
    def is_on(self):
        return self.value

    @property
    def extra_state_attributes(self):
        return {
            **super().extra_state_attributes,
            "command_status": self.child.pending.get(self.descriptor.key)
            if self.child
            else None,
            "control_physically_validated": False,
            "state_source": "stock_report_not_own_command",
        }

    async def _set(self, value):
        try:
            await self.runtime.async_child_switch(self.did, self.descriptor.key, value)
        except (OSError, ValueError, TimeoutError, ConnectionError) as err:
            raise HomeAssistantError(
                "Child command not confirmed; no retry was sent"
            ) from err

    async def async_turn_on(self, **kwargs):
        await self._set(True)

    async def async_turn_off(self, **kwargs):
        await self._set(False)
