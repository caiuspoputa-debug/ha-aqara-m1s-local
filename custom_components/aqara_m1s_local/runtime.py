"""Stock ownership, inventory and report state; independent of HA entities."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial

from .catalog import COMMAND as CATALOG_COMMAND
from .catalog import parse_catalog, sound_for_option
from .const import VERSION
from .native_properties import BY_KEY, READ_KEYS, validate_write
from .stock_protocol import (
    BUTTON_ACTIONS,
    PROFILES,
    Field,
    child_write,
    decode_json,
    decode_value,
    integer,
    parse_inventory,
    reports,
    ring_plan,
    validate_cli,
)
from .system_status import COMMAND as SYSTEM_COMMAND
from .system_status import parse_snapshot

_LOGGER = logging.getLogger(__name__)
INVENTORY_COMMAND = "head -c 65537 /data/zigbee/device.info"
GATEWAY_FIELDS = {
    "8.0.2024": Field("zigbee_channel", "8.0.2024"),
    "8.0.2080": Field("zigbee_version", "8.0.2080"),
    "8.0.2109": Field("pairing_status", "8.0.2109"),
}


@dataclass
class Child:
    did: str
    model: str
    present: bool = True
    values: dict = field(default_factory=dict)
    observed: dict = field(default_factory=dict)
    raw_fields: dict = field(default_factory=dict)
    last_report: datetime | None = None
    last_monotonic: float = 0
    epoch: int = -1
    pending: dict = field(default_factory=dict)

    @property
    def fields(self):
        return (*PROFILES.get(self.model, ()), *self.raw_fields.values())


class StockRuntime:
    def __init__(
        self,
        client,
        mqtt,
        executor,
        *,
        audio_limit=5,
        allow_child_control=False,
        stale_seconds=86400,
        native=None,
    ):
        self.client, self.mqtt, self.executor = client, mqtt, executor
        self.native = native
        self.native_values = {}
        self.native_time = 0
        self.native_available = False
        self.native_pending = {}
        self.native_generation = 0
        self.native_last_success = None
        self._native_lock = asyncio.Lock()
        self.audio_limit = integer(audio_limit, 1, 100)
        self.allow_child_control = allow_child_control
        self.stale_seconds = integer(stale_seconds, 60, 604800)
        self.volume = min(5, audio_limit)
        self.children = {}
        self.inventory_valid = False
        self.inventory_time = None
        self.inventory_generation = 0
        self.capabilities_valid = False
        self.sounds = {}
        self.selected_sound = None
        self.entity_catalog = {}
        self.shell_available = False
        self.gateway = {}
        self.gateway_epoch = -1
        self.gateway_observed = {}
        self.system = {}
        self.system_time = 0
        self.counters = Counter()
        self.last_child_report = None
        self.last_command = "not_requested"
        self.last_error = None
        self.ring = None
        self.ring_stale = True
        self._listeners, self._event_listeners, self._removers = [], [], []
        self._audio_light_lock = asyncio.Lock()
        self._refresh_lock = asyncio.Lock()
        self._request_id = 0
        self._events_seen = deque(maxlen=256)
        self._last_refresh_request = 0
        self._tasks = set()
        self._closed = False

    def listen(self, callback, *, events=False):
        listeners = self._event_listeners if events else self._listeners
        listeners.append(callback)

        def remove():
            if callback in listeners:
                listeners.remove(callback)

        return remove

    def notify(self):
        for callback in tuple(self._listeners):
            try:
                callback()
            except Exception:
                _LOGGER.exception("Stock state listener failed")

    def _task(self, coroutine):
        if self._closed:
            coroutine.close()
            return
        task = asyncio.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._task_done)

    def _task_done(self, task):
        self._tasks.discard(task)
        if not task.cancelled() and task.exception():
            _LOGGER.error(
                "Stock background operation failed (%s)",
                type(task.exception()).__name__,
            )

    async def async_start(self):
        self._removers = [
            self.mqtt.add_message_listener(self.receive),
            self.mqtt.add_status_listener(self.connection_changed),
        ]
        await self.async_refresh_catalog()
        await self.async_refresh_inventory()
        await self.async_refresh_system()
        await self.async_refresh_native()
        await self.mqtt.start()
        self._task(self._maintain())
        if self.native is not None:
            self._task(self._maintain_native())

    async def _maintain_native(self):
        while True:
            await asyncio.sleep(15)
            await self.async_refresh_native()

    @property
    def native_connected(self):
        return self.native_available and time.monotonic() - self.native_time < 45

    def native_has(self, key):
        return self.native_connected and key in self.native_values

    def _native_received(self, values):
        self.native_values = values
        self.native_time = time.monotonic()
        self.native_available = bool(values)
        self.native_generation += 1
        self.native_last_success = datetime.now(UTC)
        for key in list(self.native_pending):
            if values.get(key) == self.native_pending[key]:
                del self.native_pending[key]

    async def async_refresh_native(self):
        if self.native is None or self._closed:
            return
        async with self._native_lock:
            try:
                values = await self.executor(self.native.read, READ_KEYS)
            except (OSError, ValueError, TimeoutError, ConnectionError):
                self.native_available = False
                self.counters["native_read_errors"] += 1
            else:
                self._native_received(values)
            self.notify()

    async def async_set_native(self, key, value):
        if self._closed or self.native is None or not self.native_connected:
            raise ConnectionError("Native API unavailable; command not sent")
        prop, value = validate_write(key, value, self.native_values)
        if prop.read and key not in self.native_values:
            raise ValueError("Property was not returned by this hub")
        await self._native_write(((key, value),))

    async def _native_write(self, items):
        async with self._native_lock:
            if self._closed or not self.native_connected:
                raise ConnectionError("Native API unavailable; command not sent")
            self.last_command = "pending_native_write"
            self.native_pending.update(items)
            try:
                await self.executor(self.native.write, items)
            except asyncio.CancelledError:
                self.native_available = False
                self.last_command = "cancelled_outcome_unknown"
                self.notify()
                raise
            except (OSError, ValueError, TimeoutError, ConnectionError):
                self.native_available = False
                self.last_command = "failed_or_outcome_unknown"
                self.notify()
                raise
            self.last_command = "native_acknowledged_readback_pending"
            try:
                values = await self.executor(self.native.read, READ_KEYS)
            except (OSError, ValueError, TimeoutError, ConnectionError):
                self.native_available = False
                self.last_command = "native_acknowledged_readback_unavailable"
            else:
                self._native_received(values)
                readable = [key for key, _ in items if BY_KEY[key].read]
                self.last_command = (
                    "native_readback_confirmed"
                    if readable
                    and all(key not in self.native_pending for key in readable)
                    else "native_acknowledged_readback_pending"
                )
                for key, _ in items:
                    if not BY_KEY[key].read:
                        self.native_pending.pop(key, None)
            self.notify()

    async def _maintain(self):
        while True:
            await asyncio.sleep(60)
            await self.async_refresh_catalog()
            await self.async_refresh_inventory()
            await self.async_refresh_system()
            self.notify()

    async def async_close(self):
        self._closed = True
        for remove in self._removers:
            remove()
        self._removers.clear()
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.mqtt.stop()
        if self.native is not None:
            await self.executor(self.native.close)
        await self.executor(self.client.close)
        self._listeners.clear()
        self._event_listeners.clear()

    async def async_refresh_inventory(self):
        if self._closed or self._refresh_lock.locked():
            return
        async with self._refresh_lock:
            self._last_refresh_request = time.monotonic()
            try:
                result = await self.executor(self.client.run_result, INVENTORY_COMMAND)
                if result.returncode:
                    raise ValueError("Inventory read failed")
                devices = parse_inventory(result.output)
            except (OSError, ValueError, TimeoutError, ConnectionError, RecursionError):
                self.inventory_valid = False
                self.shell_available = False
                self.counters["inventory_errors"] += 1
                self.last_error = "inventory_unavailable_or_invalid"
            else:
                for did, child in self.children.items():
                    child.present = (
                        did in devices and child.model == devices[did]["model"]
                    )
                    if not child.present:
                        child.epoch = -1
                        child.observed.clear()
                        child.pending.clear()
                for did, device in devices.items():
                    old = self.children.get(did)
                    if old is None or old.model != device["model"]:
                        self.children[did] = Child(did, device["model"])
                    else:
                        old.present = True
                # Keep a bounded tombstone cache, without deleting HA registry entries.
                for did in list(self.children):
                    if len(self.children) <= 512:
                        break
                    if not self.children[did].present:
                        del self.children[did]
                self.inventory_valid = self.shell_available = True
                self.inventory_time = datetime.now(UTC)
                self.inventory_generation += 1
                self.last_error = None
            self.notify()

    async def async_refresh_catalog(self):
        try:
            result = await self.executor(self.client.run_result, CATALOG_COMMAND)
            if result.returncode:
                raise ValueError("Stock catalog unavailable")
            sounds = parse_catalog(result.output)
        except (OSError, ValueError, TimeoutError, ConnectionError):
            self.capabilities_valid = False
            self.counters["catalog_errors"] += 1
        else:
            self.sounds = sounds
            if self.selected_sound not in sounds:
                self.selected_sound = next(iter(sounds), None)
            self.capabilities_valid = True
        self.notify()

    def connection_changed(self, connected):
        # No cached values or retained events become live after a reconnect.
        self.ring_stale = True
        self._events_seen.clear()
        for child in self.children.values():
            child.pending.clear()
        self.notify()

    async def async_refresh_system(self):
        try:
            result = await self.executor(self.client.run_result, SYSTEM_COMMAND)
            if result.returncode:
                raise ValueError("System snapshot unavailable")
            self.system = parse_snapshot(result.output)
            self.system_time = time.monotonic()
        except (OSError, ValueError, TimeoutError, ConnectionError):
            self.system = {}
            self.counters["system_snapshot_errors"] += 1
        self.notify()

    def child_live(self, child):
        return (
            self.inventory_valid
            and child.present
            and self.mqtt.connected
            and child.epoch == self.mqtt.epoch
            and time.monotonic() - child.last_monotonic < self.stale_seconds
        )

    def receive(self, message):
        if self._closed or message.retained or message.epoch != self.mqtt.epoch:
            return
        self.counters["messages"] += 1
        if message.topic == "broker/ping":
            self.counters["broker_pings"] += 1
            self.notify()
            return
        try:
            document = decode_json(message.payload)
        except (ValueError, UnicodeError, RecursionError):
            self.counters["invalid_messages"] += 1
            return
        if not isinstance(document, dict):
            return
        for did, properties in reports(document):
            if isinstance(did, str):
                did = did.lower()
            if did == "lumi.0":
                for resource, value in properties.items():
                    if resource in GATEWAY_FIELDS:
                        if resource == "8.0.2024" and (
                            type(value) is not int or not 11 <= value <= 26
                        ):
                            continue
                        self.gateway[GATEWAY_FIELDS[resource].key] = value
                        self.gateway_observed[GATEWAY_FIELDS[resource].key] = (
                            message.epoch
                        )
                        self.gateway_epoch = message.epoch
                # Gateway housekeeping is not counted as child radio traffic.
                continue
            child = self.children.get(did) if isinstance(did, str) else None
            if child is None or not child.present:
                self.counters["unknown_child_reports"] += 1
                if time.monotonic() - self._last_refresh_request > 15:
                    self._last_refresh_request = time.monotonic()
                    self._task(self.async_refresh_inventory())
                continue
            if not self.inventory_valid:
                continue
            if not properties:
                continue
            now = datetime.now(UTC)
            child.last_report = now
            child.last_monotonic = time.monotonic()
            child.epoch = message.epoch
            self.last_child_report = now
            self.counters["child_reports"] += 1
            known = {f.resource: f for f in PROFILES.get(child.model, ())}
            for resource, value in properties.items():
                descriptor = known.get(resource)
                if descriptor is None:
                    # Unknown resources remain read-only, bounded, and opt-in in HA.
                    if resource not in child.raw_fields and len(child.raw_fields) >= 16:
                        continue
                    descriptor = child.raw_fields.setdefault(
                        resource, Field("raw_" + resource.replace(".", "_"), resource)
                    )
                    child.values[descriptor.key] = value
                    child.observed[descriptor.key] = message.epoch
                    continue
                if descriptor.platform == "event":
                    if (
                        document.get("cmd") != "report"
                        or type(value) is not int
                        or value not in BUTTON_ACTIONS
                    ):
                        continue
                    signature = None
                    if message.packet_id is not None:
                        signature = (message.epoch, did, resource, message.packet_id)
                    elif type(document.get("zseq")) is int:
                        signature = (
                            message.epoch,
                            did,
                            resource,
                            document["zseq"],
                            value,
                        )
                    if signature is not None:
                        now_mono = time.monotonic()
                        duplicate = any(
                            s == signature and now_mono - t < 2
                            for s, t in self._events_seen
                        )
                        if duplicate and (
                            message.duplicate or message.packet_id is None
                        ):
                            continue
                        self._events_seen.append((signature, now_mono))
                    action = BUTTON_ACTIONS[value]
                    child.values[descriptor.key] = action
                    child.observed[descriptor.key] = message.epoch
                    for callback in tuple(self._event_listeners):
                        try:
                            callback(did, descriptor.key, action)
                        except Exception:
                            _LOGGER.exception("Stock action listener failed")
                    self.counters["button_events"] += 1
                else:
                    try:
                        decoded = decode_value(descriptor, value)
                    except ValueError:
                        self.counters["invalid_measurements"] += 1
                        continue
                    child.values[descriptor.key] = decoded
                    child.observed[descriptor.key] = message.epoch
                    child.pending.pop(descriptor.key, None)
        self.notify()

    async def _cli(self, method, name, value, args):
        if self._closed:
            raise ConnectionError("Integration is unloading; command not sent")
        self.last_command = "pending"
        try:
            result = await self.executor(
                partial(self.client.run_argv, "/bin/basis_cli", *args, timeout=3)
            )
            validate_cli(result.output, result.returncode, method, name, value)
        except asyncio.CancelledError:
            self.last_command = "cancelled_outcome_unknown"
            self.ring_stale = True
            self.notify()
            raise
        except (OSError, ValueError, TimeoutError, ConnectionError):
            self.last_command = "failed_or_outcome_unknown"
            self.last_error = "native_rpc_not_confirmed"
            self.ring_stale = True
            self.notify()
            raise
        self.shell_available = True
        self.last_command = "rpc_accepted_not_physical_readback"
        self.last_error = None
        self.notify()

    async def async_ring(self, rgb, brightness):
        plan = ring_plan(rgb, brightness)
        async with self._audio_light_lock:
            if self.native is not None:
                if not all(
                    self.native_has(key)
                    for key in ("ring_on", "ring_color", "ring_brightness")
                ):
                    raise ConnectionError("Native ring readback unavailable")
                if brightness == 0 or max(rgb) == 0:
                    items = (("ring_on", False),)
                else:
                    color = int(rgb[0]) << 16 | int(rgb[1]) << 8 | int(rgb[2])
                    items = (
                        ("ring_color", color),
                        ("ring_brightness", max(1, round(brightness * 100 / 255))),
                        ("ring_on", True),
                    )
                await self._native_write(items)
                return
            for name, value, args in plan:
                await self._cli("basis.argb", name, value, args)
            self.ring = (tuple(rgb), brightness if max(rgb) else 0)
            self.ring_stale = False
            self.notify()

    async def async_play_sound(self, sound_id=1, volume=None, *, sound_type="doorbell"):
        if self._closed:
            raise ConnectionError("Integration is unloading; command not sent")
        integer(sound_id, 1, 10)
        sound = sound_for_option(f"{sound_type}/{sound_id}")
        if not self.capabilities_valid or sound.option not in self.sounds:
            raise ValueError("This sound is not in the current stock catalog")
        volume = self.volume if volume is None else integer(volume, 1, self.audio_limit)
        value, args = sound.plan(volume)
        async with self._audio_light_lock:
            await self._cli(
                "basis.system",
                "system_sing",
                value,
                args,
            )
            # Stock audio can change logical light state; refresh the native getter.
            self.ring_stale = True
            self.notify()
        if self.native is not None:
            await self.async_refresh_native()

    async def async_child_switch(self, did, key, state):
        child = self.children.get(did)
        if (
            self._closed
            or not self.allow_child_control
            or child is None
            or not self.child_live(child)
        ):
            raise ValueError(
                "Child control disabled, inventory stale or child not observed in this session"
            )
        self._request_id = self._request_id % 65535 + 1
        payload = child_write(did, child.model, key, state, self._request_id)
        child.pending[key] = "sent_unconfirmed"
        try:
            await self.mqtt.publish_json("zigbee/recv", payload)
        except (OSError, ValueError, TimeoutError, ConnectionError):
            child.pending[key] = "outcome_unknown"
            self.notify()
            raise
        self.notify()

    def diagnostics(self):
        """Allowlist only; no host, DID, credentials, raw payload or device names."""
        return {
            "version": VERSION,
            "mqtt_connected": self.mqtt.connected,
            "mqtt_transport": getattr(self, "mqtt_transport", "direct"),
            "mqtt_last_error": getattr(self.mqtt, "last_error", None),
            "catalog_valid": self.capabilities_valid,
            "native_sounds_available": len(self.sounds),
            "inventory_valid": self.inventory_valid,
            "shell_available": self.shell_available,
            "radio_ready": "not_proven",
            "children_present": sum(c.present for c in self.children.values()),
            "children_observed_this_session": sum(
                self.child_live(c) for c in self.children.values()
            ),
            "models": dict(
                Counter(c.model for c in self.children.values() if c.present)
            ),
            "counters": dict(self.counters),
            "last_command": self.last_command,
            "last_error": self.last_error,
            "child_control_enabled": self.allow_child_control,
            "native_audio_limit": self.audio_limit,
            "system": dict(self.system),
            "native_connected": self.native_connected,
            "native_properties_observed": sorted(self.native_values),
            "native_last_success": self.native_last_success.isoformat()
            if self.native_last_success
            else None,
            "physical_test_scope": "ring, native doorbell, one WXKG11LM; other profiles not lab-validated",
        }
