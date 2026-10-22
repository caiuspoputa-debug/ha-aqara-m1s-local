"""Stock ownership, inventory and report state; independent of HA entities."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial

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
    "0.3.85": Field("ambient_light_raw", "0.3.85"),
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
    ):
        self.client, self.mqtt, self.executor = client, mqtt, executor
        self.audio_limit = integer(audio_limit, 1, 100)
        self.allow_child_control = allow_child_control
        self.stale_seconds = integer(stale_seconds, 60, 604800)
        self.volume = min(5, audio_limit)
        self.children = {}
        self.inventory_valid = False
        self.inventory_time = None
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
        await self.async_refresh_inventory()
        await self.async_refresh_system()
        await self.mqtt.start()
        self._task(self._maintain())

    async def _maintain(self):
        while True:
            await asyncio.sleep(60)
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
                self.last_error = None
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
            for name, value, args in plan:
                await self._cli("basis.argb", name, value, args)
            self.ring = (tuple(rgb), brightness if max(rgb) else 0)
            self.ring_stale = False
            self.notify()

    async def async_play_sound(self, sound_id=1, volume=None):
        # Only this native catalog entry was physically validated in .109 lab.
        integer(sound_id, 1, 1)
        volume = self.volume if volume is None else integer(volume, 1, self.audio_limit)
        async with self._audio_light_lock:
            await self._cli(
                "basis.system",
                "system_sing",
                f"1;1;0;1;{volume}",
                ("-sys", "-s", "doorbell", "1", "0", str(volume)),
            )
            # Stock audio can touch the logical light cache. There is no proven getter.
            self.ring_stale = True
            self.notify()

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
            "version": "0.6.0",
            "mqtt_connected": self.mqtt.connected,
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
            "physical_test_scope": "ring, native doorbell, one WXKG11LM; other profiles not lab-validated",
        }
