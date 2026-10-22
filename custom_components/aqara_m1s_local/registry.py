"""Reconcile only this integration entry after authoritative stock discovery."""

import re

from homeassistant.helpers import entity_registry as er

from .const import CONF_CLEANUP, DOMAIN


def track_entities(runtime, platform, async_add_entities):
    def add(entities):
        entities = list(entities)
        for entity in entities:
            runtime.entity_catalog[(platform, entity._attr_unique_id)] = (
                entity.did,
                entity.model,
            )
        async_add_entities(entities)

    return add


class RegistryCleanup:
    def __init__(self, hass, entry, runtime):
        self.hass, self.entry, self.runtime = hass, entry, runtime
        self._generation = -1
        self._missing = {}

    def update(self):
        runtime = self.runtime
        if not self.entry.options.get(CONF_CLEANUP, True):
            self._missing.clear()
            return
        if not runtime.inventory_valid or not runtime.capabilities_valid:
            self._missing.clear()
            return
        if self._generation == runtime.inventory_generation:
            return
        self._generation = runtime.inventory_generation
        registry = er.async_get(self.hass)
        current_missing = {}
        for registered in er.async_entries_for_config_entry(
            registry, self.entry.entry_id
        ):
            if registered.platform != DOMAIN:
                continue
            identity = (registered.domain, registered.unique_id)
            definition = runtime.entity_catalog.get(identity)
            if definition is not None:
                did, model = definition
                child = runtime.children.get(did)
                if did is None:
                    # Sound buttons can disappear after a successful catalog refresh.
                    key = registered.unique_id.removeprefix(self.entry.entry_id + "_")
                    if not key.startswith("play_music_scene_") or any(
                        s.key == key for s in runtime.sounds.values()
                    ):
                        continue
                elif child and child.present and child.model == model:
                    continue
            else:
                # Raw resources are learned from live reports. Silence after restart
                # is not evidence that a present child stopped exposing a resource.
                suffix = registered.unique_id.removeprefix(self.entry.entry_id + "_")
                child_prefix = next(
                    (
                        f"{c.did}_{c.model}_raw_"
                        for c in runtime.children.values()
                        if c.present and suffix.startswith(f"{c.did}_{c.model}_raw_")
                    ),
                    None,
                )
                if child_prefix:
                    continue
            suffix = registered.unique_id.removeprefix(self.entry.entry_id + "_")
            is_child = (
                definition is not None
                and definition[0] is not None
                or re.match(r"lumi\.[0-9a-f]+_", suffix)
            )
            if is_child:
                misses = self._missing.get(identity, 0) + 1
                current_missing[identity] = misses
                if misses < 2:
                    continue
            registry.async_remove(registered.entity_id)
            runtime.counters["obsolete_entities_removed"] += 1
            runtime.entity_catalog.pop(identity, None)
        self._missing = current_missing
