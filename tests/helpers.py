"""Synthetic fixtures only. No connection to a hub or Home Assistant instance."""

import asyncio
import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "aqara-m1s-060-testdeps"))
PACKAGE = "m1s060"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components" / "aqara_m1s_local")]
sys.modules.setdefault(PACKAGE, package)


def module(name):
    return importlib.import_module(f"{PACKAGE}.{name}")


CommandResult = module("client").CommandResult
Message = module("mqtt_client").Message
BUTTON = "lumi.1234"
PLUG = "lumi.5678"
INVENTORY = json.dumps(
    {
        "devInfo": [
            {"did": BUTTON, "model": "lumi.remote.b1acn01"},
            {"did": PLUG, "model": "lumi.plug"},
        ]
    }
)


def cli_output(method, name, value, request_id=123):
    return (
        "Send >> "
        + json.dumps(
            {
                "_to": 1,
                "method": method,
                "params": {"name": name, "value": value},
                "id": request_id,
            }
        )
        + "\n>>> "
        + json.dumps({"_from": 1, "id": request_id, "result": ["ok"]})
        + "\n"
    )


class FakeClient:
    def __init__(self, host="example.local", port=23, username="admin", password=""):
        self.host, self.port, self.username, self.password = (
            host,
            port,
            username,
            password,
        )
        self.commands, self.argv = [], []
        self.inventory = INVENTORY
        self.closed = False
        self.fail_step = None
        self.active = 0
        self.max_active = 0

    def run_result(self, command):
        self.commands.append(command)
        if "device.info" in command:
            if isinstance(self.inventory, Exception):
                raise self.inventory
            return CommandResult(self.inventory, 0)
        return CommandResult(
            "uptime 100\nha_basis_present 1\nmzigbee_agent_present 1\nwifi_operstate up\n",
            0,
        )

    def run_argv(self, *args, timeout=None):
        self.argv.append(args)
        if len(self.argv) == self.fail_step:
            raise TimeoutError("Synthetic lost ACK")
        if args[1] == "-argb":
            name = "argb_toggle" if args[2] == "-s" else "argb_colour"
            return CommandResult(cli_output("basis.argb", name, args[3]), 0)
        return CommandResult(
            cli_output("basis.system", "system_sing", f"1;1;0;1;{args[-1]}"), 0
        )

    def close(self):
        self.closed = True


class FakeMQTT:
    def __init__(self, *args):
        self.connected, self.epoch = True, 1
        self.messages, self.statuses, self.published = [], [], []
        self.started = self.stopped = False
        self.publish_error = None

    def _add(self, collection, callback):
        collection.append(callback)
        return lambda: collection.remove(callback)

    def add_message_listener(self, callback):
        return self._add(self.messages, callback)

    def add_status_listener(self, callback):
        return self._add(self.statuses, callback)

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    async def publish_json(self, topic, payload):
        self.published.append((topic, payload))
        if self.publish_error:
            raise self.publish_error


async def executor(function, *args):
    return function(*args)


def message(
    did=BUTTON,
    values=None,
    *,
    cmd="report",
    retained=False,
    duplicate=False,
    packet_id=None,
    epoch=1,
    **extra,
):
    document = {
        "cmd": cmd,
        "did": did,
        "params": [
            {"res_name": key, "value": value}
            for key, value in (values or {"13.1.85": 1}).items()
        ],
        **extra,
    }
    return Message(
        "zigbee/send",
        json.dumps(document).encode(),
        retained,
        duplicate,
        packet_id,
        epoch,
    )


def ha_stubs():
    """Small API test doubles, not an actual HA boot or integration test."""

    def make(name):
        mod = sys.modules.setdefault(name, types.ModuleType(name))
        mod.__path__ = []
        return mod

    make("homeassistant")
    make("homeassistant.components")
    make("homeassistant.helpers")

    class Entity:
        _attr_entity_registry_enabled_default = True
        device_entry = types.SimpleNamespace(id="synthetic-device-id")

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

        async def async_added_to_hass(self):
            pass

        def async_on_remove(self, callback):
            self._removers = getattr(self, "_removers", []) + [callback]

        def async_write_ha_state(self):
            self._writes = getattr(self, "_writes", 0) + 1

    class RestoreEntity(Entity):
        async def async_get_last_state(self):
            return None

    make("homeassistant.helpers.entity").Entity = Entity
    make("homeassistant.helpers.restore_state").RestoreEntity = RestoreEntity
    make("homeassistant.helpers.selector").TextSelector = lambda config: str
    for domain, class_name in (
        ("light", "LightEntity"),
        ("number", "NumberEntity"),
        ("select", "SelectEntity"),
        ("button", "ButtonEntity"),
        ("sensor", "SensorEntity"),
        ("binary_sensor", "BinarySensorEntity"),
        ("switch", "SwitchEntity"),
    ):
        make(f"homeassistant.components.{domain}").__dict__[class_name] = type(
            class_name, (Entity,), {}
        )

    class EventEntity(RestoreEntity):
        def _trigger_event(self, action):
            self.last_event = action

    make("homeassistant.components.event").EventEntity = EventEntity
    light = make("homeassistant.components.light")
    light.ATTR_BRIGHTNESS, light.ATTR_RGB_COLOR = "brightness", "rgb_color"
    light.ColorMode = types.SimpleNamespace(RGB="rgb")
    make("homeassistant.components.number").NumberMode = types.SimpleNamespace(
        SLIDER="slider"
    )
    make("homeassistant.const").Platform = types.SimpleNamespace(
        **{
            name.upper(): name
            for name in (
                "binary_sensor",
                "button",
                "event",
                "light",
                "number",
                "select",
                "sensor",
                "switch",
            )
        }
    )
    make("homeassistant.exceptions").HomeAssistantError = type(
        "HomeAssistantError", (Exception,), {}
    )
    make("homeassistant.core").callback = lambda function: function

    class Flow:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

        async def async_set_unique_id(self, value):
            self.unique_id = value

        def _abort_if_unique_id_configured(self):
            pass

    flow = make("homeassistant.config_entries")
    flow.ConfigFlow = flow.OptionsFlow = Flow


class Entry:
    def __init__(self, entry_id="one", host="example.local", options=None):
        self.entry_id, self.title = entry_id, "Synthetic M1S"
        self.data = {"host": host}
        self.options = options or {}
        self.removers = []

    def async_on_unload(self, callback):
        self.removers.append(callback)

    def add_update_listener(self, callback):
        return lambda: None


class Services:
    def __init__(self):
        self.handlers = {}

    def has_service(self, domain, name):
        return (domain, name) in self.handlers

    def async_register(self, domain, name, handler, schema):
        self.handlers[domain, name] = (handler, schema)

    def async_remove(self, domain, name):
        self.handlers.pop((domain, name), None)

    async def call(self, name, data):
        handler, schema = self.handlers["aqara_m1s_local", name]
        return await handler(types.SimpleNamespace(data=schema(data)))


class Hass:
    def __init__(self):
        self.data, self.entities, self.entity_tasks = {}, [], []
        self.services = Services()
        self.events = []
        self.bus = types.SimpleNamespace(
            async_fire=lambda *args: self.events.append(args)
        )
        self.config_entries = types.SimpleNamespace(
            async_forward_entry_setups=self.forward,
            async_unload_platforms=self.unload,
            async_reload=AsyncMock(),
        )
        self.async_add_executor_job = executor

    async def forward(self, entry, platforms):
        def add(entities):
            for entity in entities:
                entity.hass = self
                entity.entity_id = "test." + entity._attr_unique_id.replace(".", "_")
                self.entities.append(entity)
                self.entity_tasks.append(
                    asyncio.create_task(entity.async_added_to_hass())
                )

        for platform in platforms:
            await module(platform).async_setup_entry(self, entry, add)
        await self.drain()

    async def drain(self):
        while self.entity_tasks:
            tasks, self.entity_tasks = self.entity_tasks, []
            await asyncio.gather(*tasks)

    async def unload(self, entry, platforms):
        for entity in self.entities:
            if entity.entry.entry_id != entry.entry_id:
                continue
            for remove in getattr(entity, "_removers", []):
                remove()
            entity._removers = []
        for remove in entry.removers:
            remove()
        entry.removers.clear()
        return True
