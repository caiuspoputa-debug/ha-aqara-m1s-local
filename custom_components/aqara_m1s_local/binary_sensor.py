from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DATA_STOCK, DOMAIN
from .entity import ChildFieldEntity, StockEntity, discover, discover_inventory
from .system_status import PRESENCE


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    async_add_entities(
        [
            StockStatus(entry, runtime, key, name)
            for key, name in (
                ("mqtt", "Stock MQTT connection"),
                ("inventory", "Valid stock inventory"),
            )
        ]
    )
    async_add_entities(
        [SystemBinary(entry, runtime, key) for key in (*PRESENCE, "wifi_carrier")]
    )
    discover(hass, entry, async_add_entities, "binary_sensor", ChildBinary)
    discover_inventory(
        hass,
        entry,
        async_add_entities,
        lambda e, r, did, model: [InventoryPresence(e, r, did, model)],
    )


class StockStatus(StockEntity, BinarySensorEntity):
    _attr_entity_category = "diagnostic"

    def __init__(self, entry, runtime, key, name):
        super().__init__(entry, runtime, key, name)
        self.key = key
        if key == "mqtt":
            self._attr_device_class = "connectivity"

    @property
    def is_on(self):
        return (
            self.runtime.mqtt.connected
            if self.key == "mqtt"
            else self.runtime.inventory_valid
        )


class ChildBinary(ChildFieldEntity, BinarySensorEntity):
    def __init__(self, entry, runtime, did, model, descriptor):
        super().__init__(entry, runtime, did, model, descriptor)
        self._attr_device_class = descriptor.device_class

    @property
    def is_on(self):
        return self.value


class InventoryPresence(StockEntity, BinarySensorEntity):
    _attr_entity_category = "diagnostic"

    def __init__(self, entry, runtime, did, model):
        super().__init__(
            entry,
            runtime,
            "inventory_presence",
            "Present in stock inventory",
            did,
            model,
        )

    @property
    def available(self):
        return self.runtime.inventory_valid

    @property
    def is_on(self):
        return bool(self.child and self.child.present)

    @property
    def extra_state_attributes(self):
        return {**super().extra_state_attributes, "means_online": False}


class SystemBinary(StockEntity, BinarySensorEntity):
    _attr_entity_category = "diagnostic"

    def __init__(self, entry, runtime, key):
        super().__init__(entry, runtime, key, key.replace("_", " ").capitalize())
        self.key = key

    @property
    def available(self):
        import time

        return (
            self.key in self.runtime.system
            and time.monotonic() - self.runtime.system_time < 180
        )

    @property
    def is_on(self):
        return self.runtime.system.get(self.key)

    @property
    def extra_state_attributes(self):
        return {"means_radio_ready": False}
