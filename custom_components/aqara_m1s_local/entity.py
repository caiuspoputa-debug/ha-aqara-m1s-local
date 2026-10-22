"""Push entities and bounded discovery for verified stock inventory members."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity

from .const import DATA_STOCK, DOMAIN


class StockEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry, runtime, key, name, did=None, model=None):
        self.entry, self.runtime, self.did, self.model = entry, runtime, did, model
        self._attr_name = name
        self._attr_unique_id = (
            f"{entry.entry_id}_{did + '_' + model + '_' if did else ''}{key}"
        )
        hub_id = (DOMAIN, runtime.client.host)
        if did:
            self._attr_device_info = {
                "identifiers": {(DOMAIN, f"{entry.entry_id}_{did}")},
                "via_device": hub_id,
                "name": f"Aqara {model} {did[5:]}",
                "manufacturer": "Aqara / LUMI",
                "model": model,
            }
        else:
            self._attr_device_info = {
                "identifiers": {hub_id},
                "name": entry.title,
                "manufacturer": "Aqara",
                "model": "M1S stock",
            }

    @property
    def child(self):
        child = self.runtime.children.get(self.did)
        return child if child is not None and child.model == self.model else None

    @property
    def available(self):
        if self.did:
            child = self.child
            return child is not None and self.runtime.child_live(child)
        return True

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.runtime.listen(self._updated))

    def _updated(self):
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        if not self.did:
            return None
        child = self.child
        return {
            "stock_model": self.model,
            "inventory_present": bool(child and child.present),
            "last_report": child.last_report.isoformat()
            if child and child.last_report
            else None,
            "validation": "model_contract_lab_validated_not_this_device"
            if self.model == "lumi.remote.b1acn01"
            else "protocol_mapping_not_lab_validated",
        }


class ChildFieldEntity(StockEntity):
    def __init__(self, entry, runtime, did, model, descriptor):
        super().__init__(
            entry,
            runtime,
            descriptor.key,
            descriptor.key.replace("_", " ").capitalize(),
            did,
            model,
        )
        self.descriptor = descriptor
        if descriptor.key.startswith("raw_"):
            self._attr_entity_registry_enabled_default = False
            self._attr_entity_category = "diagnostic"

    @property
    def available(self):
        child = self.child
        return (
            super().available
            and child.observed.get(self.descriptor.key) == self.runtime.mqtt.epoch
        )

    @property
    def value(self):
        child = self.child
        return child.values.get(self.descriptor.key) if child else None


def discover(hass, entry, async_add_entities, platform, factory):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    seen = set()

    def update():
        entities = []
        for did, child in runtime.children.items():
            if not child.present:
                continue
            for descriptor in child.fields:
                identity = (did, child.model, descriptor.key)
                if (
                    descriptor.platform == platform
                    and identity not in seen
                    and len(seen) < 1024
                ):
                    seen.add(identity)
                    entities.append(
                        factory(entry, runtime, did, child.model, descriptor)
                    )
        if entities:
            async_add_entities(entities)

    entry.async_on_unload(runtime.listen(update))
    update()


def discover_inventory(hass, entry, async_add_entities, factory):
    runtime = hass.data[DOMAIN][DATA_STOCK][entry.entry_id]
    seen = set()

    def update():
        entities = []
        for did, child in runtime.children.items():
            identity = (did, child.model)
            if child.present and identity not in seen:
                seen.add(identity)
                entities.extend(factory(entry, runtime, did, child.model))
        if entities:
            async_add_entities(entities)

    entry.async_on_unload(runtime.listen(update))
    update()
