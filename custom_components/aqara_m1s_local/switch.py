from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError

from .entity import ChildFieldEntity, discover


async def async_setup_entry(hass, entry, async_add_entities):
    discover(hass, entry, async_add_entities, "switch", ChildSwitch)


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
