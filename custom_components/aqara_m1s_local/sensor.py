from homeassistant.components.sensor import SensorEntity

from .const import DATA_STOCK, DOMAIN
from .entity import ChildFieldEntity, StockEntity, discover, discover_inventory
from .native_entity import NativeEntity, entities
from .native_properties import catalogs
from .registry import track_entities
from .runtime import GATEWAY_FIELDS


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    async_add_entities = track_entities(runtime, "sensor", async_add_entities)
    keys = (
        "children_present",
        "children_observed_this_session",
        "last_child_report",
        "last_command",
        "radio_ready",
    )
    async_add_entities(
        [HubSensor(entry, runtime, key) for key in keys]
        + [GatewaySensor(entry, runtime, f.key) for f in GATEWAY_FIELDS.values()]
        + [
            SystemSensor(entry, runtime, key)
            for key in ("uptime", "load_1m", "memory_used_pct", "wifi_operstate")
        ]
    )
    async_add_entities(
        entities(entry, runtime, "sensor", PropertySensor)
        + [HubAddress(entry, runtime)]
    )
    discover(hass, entry, async_add_entities, "sensor", ChildSensor)
    discover_inventory(
        hass,
        entry,
        async_add_entities,
        lambda e, r, did, model: [ChildLastReport(e, r, did, model)],
        platform="sensor",
    )


class HubSensor(StockEntity, SensorEntity):
    _attr_entity_category = "diagnostic"

    def __init__(self, entry, runtime, key):
        super().__init__(entry, runtime, key, key.replace("_", " ").capitalize())
        self.key = key
        if key == "last_child_report":
            self._attr_device_class = "timestamp"

    @property
    def native_value(self):
        if self.key == "last_child_report":
            return self.runtime.last_child_report
        return self.runtime.diagnostics().get(self.key)


class GatewaySensor(StockEntity, SensorEntity):
    _attr_entity_category = "diagnostic"

    def __init__(self, entry, runtime, key):
        super().__init__(entry, runtime, key, key.replace("_", " ").capitalize())
        self.key = key

    @property
    def available(self):
        return (
            self.runtime.mqtt.connected
            and self.runtime.gateway_observed.get(self.key) == self.runtime.mqtt.epoch
        )

    @property
    def native_value(self):
        return self.runtime.gateway.get(self.key)


class ChildSensor(ChildFieldEntity, SensorEntity):
    def __init__(self, entry, runtime, did, model, descriptor):
        super().__init__(entry, runtime, did, model, descriptor)
        self._attr_native_unit_of_measurement = descriptor.unit
        self._attr_device_class = descriptor.device_class
        if not descriptor.key.startswith("raw_"):
            self._attr_state_class = (
                "total_increasing" if descriptor.key == "energy" else "measurement"
            )

    @property
    def native_value(self):
        return self.value


class ChildLastReport(StockEntity, SensorEntity):
    _attr_device_class = "timestamp"
    _attr_entity_category = "diagnostic"

    def __init__(self, entry, runtime, did, model):
        super().__init__(
            entry, runtime, "last_report", "Last stock report received", did, model
        )

    @property
    def available(self):
        return bool(self.child and self.child.present and self.runtime.inventory_valid)

    @property
    def native_value(self):
        return self.child.last_report if self.child else None


class SystemSensor(StockEntity, SensorEntity):
    _attr_entity_category = "diagnostic"

    def __init__(self, entry, runtime, key):
        super().__init__(entry, runtime, key, key.replace("_", " ").capitalize())
        self.key = key
        self._attr_native_unit_of_measurement = {
            "uptime": "s",
            "memory_used_pct": "%",
        }.get(key)

    @property
    def available(self):
        import time

        return (
            self.key in self.runtime.system
            and time.monotonic() - self.runtime.system_time < 180
        )

    @property
    def native_value(self):
        return self.runtime.system.get(self.key)


class PropertySensor(NativeEntity, SensorEntity):
    @property
    def native_value(self):
        if self.prop.key == "audio_catalog":
            sounds, _ = catalogs(self.runtime.native_values)
            return sum(len(group) for group in sounds.values())
        if self.prop.key == "language_catalog":
            return ", ".join(catalogs(self.runtime.native_values)[1])
        if self.prop.key == "weather_binding":
            return "associated" if self.value else "not_associated"
        if isinstance(self.value, str):
            return self.value[:200] or "none"
        return self.value

    @property
    def extra_state_attributes(self):
        attributes = super().extra_state_attributes
        if self.prop.key == "audio_catalog":
            attributes["available_sounds"] = catalogs(self.runtime.native_values)[0]
        if self.prop.key == "hub_button_code":
            attributes["means_live_button_event"] = False
        return attributes


class HubAddress(StockEntity, SensorEntity):
    _attr_entity_category = "diagnostic"
    _attr_icon = "mdi:ip-network"

    def __init__(self, entry, runtime):
        super().__init__(entry, runtime, "hub_ip_address", "Hub IP address")

    @property
    def available(self):
        return self.runtime.native_connected and bool(
            self.runtime.native and self.runtime.native.ip
        )

    @property
    def native_value(self):
        return self.runtime.native.ip if self.runtime.native else None

    @property
    def extra_state_attributes(self):
        return {
            "source": "authenticated_native_api_peer",
            "configured_host": self.runtime.client.host,
        }
