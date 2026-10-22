import unittest
from unittest.mock import patch

from helpers import (
    BUTTON,
    Entry,
    FakeClient,
    FakeMQTT,
    Hass,
    ha_stubs,
    message,
    module,
)

ha_stubs()
integration = module("__init__")
flow = module("config_flow")
HomeAssistantError = __import__(
    "homeassistant.exceptions", fromlist=["HomeAssistantError"]
).HomeAssistantError


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass, self.entry = Hass(), Entry()
        self.patches = [
            patch.object(integration, "AqaraM1SClient", FakeClient),
            patch.object(integration, "AqaraM1SMqttClient", FakeMQTT),
        ]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        for entry_id in list(
            self.hass.data.get("aqara_m1s_local", {}).get("stock", {})
        ):
            entry = self.entry if entry_id == self.entry.entry_id else Entry(entry_id)
            await integration.async_unload_entry(self.hass, entry)
        for item in self.patches:
            item.stop()

    async def setup(self, entry=None):
        entry = entry or self.entry
        await integration.async_setup_entry(self.hass, entry)
        await self.hass.drain()
        return self.hass.data["aqara_m1s_local"]["stock"][entry.entry_id]

    async def test_every_platform_imports_and_discovers_inventory(self):
        runtime = await self.setup()
        self.assertGreater(len(self.hass.entities), 20)
        ids = [entity._attr_unique_id for entity in self.hass.entities]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any(BUTTON in identity for identity in ids))
        self.assertNotIn("media_player", integration.PLATFORMS)
        self.assertTrue(runtime.mqtt.started)

    async def test_button_event_is_exposed_once(self):
        runtime = await self.setup()
        runtime.receive(message())
        self.assertEqual(len(self.hass.events), 1)
        self.assertEqual(self.hass.events[0][0], "aqara_m1s_local_action")
        self.assertEqual(self.hass.events[0][1]["action"], "single")
        runtime.receive(message(retained=True))
        self.assertEqual(len(self.hass.events), 1)

    async def test_services_route_to_configured_entry_not_last_setup(self):
        first = await self.setup()
        second = await self.setup(Entry("two", "second.local"))
        await self.hass.services.call("play_sound", {"entry_id": "one", "volume": 2})
        self.assertEqual(len(first.client.argv), 1)
        self.assertEqual(second.client.argv, [])
        with self.assertRaises(HomeAssistantError):
            await self.hass.services.call("play_sound", {})
        with self.assertRaises(HomeAssistantError):
            await self.hass.services.call(
                "play_sound", {"host": "not-configured.local"}
            )

    async def test_service_refuses_unmapped_wav_without_playing(self):
        runtime = await self.setup()
        with self.assertRaises(HomeAssistantError):
            await self.hass.services.call(
                "play_sound", {"sound_path": "/data/musics/unknown.wav"}
            )
        self.assertEqual(runtime.client.argv, [])
        await self.hass.services.call(
            "play_sound", {"sound_path": "/data/musics/music-scene/door_bell_1.wav"}
        )
        self.assertEqual(len(runtime.client.argv), 1)

    async def test_services_removed_after_last_unload(self):
        runtime = await self.setup()
        await integration.async_unload_entry(self.hass, self.entry)
        self.assertEqual(self.hass.services.handlers, {})
        self.assertTrue(runtime.client.closed)
        self.assertFalse(runtime._tasks)

    async def test_setup_failure_rolls_back_runtime(self):
        self.hass.config_entries.async_forward_entry_setups = __import__(
            "unittest.mock", fromlist=["AsyncMock"]
        ).AsyncMock(side_effect=RuntimeError("Synthetic platform setup failure"))
        with self.assertRaises(RuntimeError):
            await integration.async_setup_entry(self.hass, self.entry)
        self.assertEqual(self.hass.data["aqara_m1s_local"]["stock"], {})

    async def test_options_use_real_probatio_schema(self):
        options = flow.M1SOptionsFlow()
        options.config_entry = self.entry
        result = await options.async_step_init()
        self.assertEqual(result["data_schema"]({})["native_audio_limit"], 5)
        with self.assertRaises(flow.vol.Invalid):
            result["data_schema"]({"native_audio_limit": 101})

    async def test_config_schema_and_unique_host(self):
        config = flow.AqaraM1SLocalConfigFlow()
        result = await config.async_step_user()
        validated = result["data_schema"]({"host": "Example.Local"})
        self.assertEqual(validated["host"], "Example.Local")
        self.assertEqual(validated["mqtt_port"], 1884)
        for invalid in ("http://hub.local/", "user@hub.local", "a;reboot", ""):
            with self.subTest(host=invalid):
                rejected = await config.async_step_user({"host": invalid})
                self.assertEqual(rejected["errors"], {"base": "invalid_input"})
        created = await config.async_step_user({"host": "Example.Local"})
        self.assertEqual(created["type"], "create_entry")
        self.assertNotIn("name", created["data"])
        self.assertEqual(created["data"]["host"], "example.local")

    async def test_inventory_presence_does_not_mean_online(self):
        runtime = await self.setup()
        presence = [
            e
            for e in self.hass.entities
            if isinstance(e, module("binary_sensor").InventoryPresence)
        ]
        self.assertEqual(len(presence), 2)
        self.assertTrue(all(e.is_on for e in presence))
        self.assertTrue(
            all(not e.extra_state_attributes["means_online"] for e in presence)
        )
        events = [
            e for e in self.hass.entities if isinstance(e, module("event").ChildAction)
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(runtime.counters["button_events"], 0)

    async def test_invalid_inventory_marks_children_unavailable_not_deleted(self):
        runtime = await self.setup()
        runtime.receive(message())
        before = len(self.hass.entities)
        runtime.client.inventory = "{}"
        await runtime.async_refresh_inventory()
        await self.hass.drain()
        self.assertEqual(len(self.hass.entities), before)
        child_entities = [e for e in self.hass.entities if e.did]
        self.assertTrue(all(not e.available for e in child_entities))
