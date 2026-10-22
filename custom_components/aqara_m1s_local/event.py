from typing import ClassVar

from homeassistant.components.event import EventEntity

from .entity import ChildFieldEntity, discover


async def async_setup_entry(hass, entry, async_add_entities):
    discover(hass, entry, async_add_entities, "event", ChildAction)


class ChildAction(ChildFieldEntity, EventEntity):
    _attr_event_types: ClassVar[list[str]] = ["single", "double", "hold", "release"]
    _attr_device_class = "button"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.runtime.listen(self._action, events=True))

    @property
    def available(self):
        child = self.child
        return bool(
            child
            and child.present
            and self.runtime.inventory_valid
            and self.runtime.mqtt.connected
        )

    def _action(self, did, key, action):
        if did == self.did and key == self.descriptor.key and self.child:
            self._trigger_event(action)
            self.async_write_ha_state()
            self.hass.bus.async_fire(
                "aqara_m1s_local_action",
                {
                    "entry_id": self.entry.entry_id,
                    "device_id": self.device_entry.id if self.device_entry else None,
                    "channel": key,
                    "action": action,
                },
            )
