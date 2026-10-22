import asyncio
import json
import unittest

from helpers import (
    BUTTON,
    INVENTORY,
    PLUG,
    FakeClient,
    FakeMQTT,
    Message,
    executor,
    message,
    module,
)

Runtime = module("runtime").StockRuntime


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client, self.mqtt = FakeClient(), FakeMQTT()
        self.runtime = Runtime(self.client, self.mqtt, executor)
        await self.runtime.async_refresh_inventory()

    async def asyncTearDown(self):
        await self.runtime.async_close()

    async def test_button_without_voltage(self):
        events = []
        self.runtime.listen(lambda *args: events.append(args), events=True)
        for value in (1, 1, 1, 1, 2, 16, 17):
            self.runtime.receive(message(values={"13.1.85": value}))
        self.assertEqual(
            [e[-1] for e in events], ["single"] * 4 + ["double", "hold", "release"]
        )
        self.assertNotIn("battery_voltage", self.runtime.children[BUTTON].values)

    async def test_retained_wrong_epoch_and_ack_do_not_trigger(self):
        for item in (
            message(retained=True),
            message(epoch=0),
            message(cmd="write_ack"),
        ):
            self.runtime.receive(item)
        self.assertEqual(self.runtime.counters["button_events"], 0)
        self.assertFalse(self.runtime.child_live(self.runtime.children[BUTTON]))

    async def test_qos1_duplicate_does_not_retrigger(self):
        self.runtime.receive(message(packet_id=12))
        self.runtime.receive(message(packet_id=12, duplicate=True))
        self.assertEqual(self.runtime.counters["button_events"], 1)
        self.runtime.receive(message(packet_id=13))
        self.assertEqual(self.runtime.counters["button_events"], 2)

    async def test_zseq_duplicate(self):
        self.runtime.receive(message(zseq=44))
        self.runtime.receive(message(zseq=44))
        self.assertEqual(self.runtime.counters["button_events"], 1)
        self.runtime.receive(message(zseq=45))
        self.assertEqual(self.runtime.counters["button_events"], 2)

    async def test_inventory_is_not_liveness(self):
        self.assertTrue(self.runtime.inventory_valid)
        self.assertEqual(self.runtime.diagnostics()["children_present"], 2)
        self.assertEqual(
            self.runtime.diagnostics()["children_observed_this_session"], 0
        )
        self.assertEqual(self.runtime.diagnostics()["radio_ready"], "not_proven")

    async def test_reports_and_reconnect(self):
        self.runtime.receive(message())
        child = self.runtime.children[BUTTON]
        self.assertTrue(self.runtime.child_live(child))
        self.mqtt.connected = False
        self.runtime.connection_changed(False)
        self.assertFalse(self.runtime.child_live(child))
        self.mqtt.connected = True
        self.mqtt.epoch = 2
        self.runtime.connection_changed(True)
        self.assertFalse(self.runtime.child_live(child))
        self.runtime.receive(message(epoch=2))
        self.assertTrue(self.runtime.child_live(child))

    async def test_expired_report(self):
        self.runtime.receive(message())
        child = self.runtime.children[BUTTON]
        child.last_monotonic -= 86401
        self.assertFalse(self.runtime.child_live(child))

    async def test_invalid_inventory_preserves_old_but_gates_control(self):
        self.runtime.receive(message())
        self.client.inventory = '{"bad":true}'
        await self.runtime.async_refresh_inventory()
        self.assertIn(BUTTON, self.runtime.children)
        self.assertFalse(self.runtime.inventory_valid)
        self.assertFalse(self.runtime.child_live(self.runtime.children[BUTTON]))

    async def test_removed_child_not_deleted_or_reactivated_by_report(self):
        self.client.inventory = '{"devInfo":[]}'
        await self.runtime.async_refresh_inventory()
        self.runtime.receive(message())
        self.assertFalse(self.runtime.children[BUTTON].present)
        self.assertEqual(self.runtime.counters["button_events"], 0)

    async def test_readded_child_requires_new_report(self):
        self.runtime.receive(message())
        self.client.inventory = '{"devInfo":[]}'
        await self.runtime.async_refresh_inventory()
        self.client.inventory = INVENTORY
        await self.runtime.async_refresh_inventory()
        self.assertFalse(self.runtime.child_live(self.runtime.children[BUTTON]))
        self.runtime.receive(message())
        self.assertTrue(self.runtime.child_live(self.runtime.children[BUTTON]))

    async def test_unknown_child_does_not_become_actuator(self):
        self.runtime.receive(message("lumi.abcd", {"4.1.85": 1}))
        self.assertNotIn("lumi.abcd", self.runtime.children)

    async def test_invalid_inventory_does_not_fire_cached_child_action(self):
        self.client.inventory = "{}"
        await self.runtime.async_refresh_inventory()
        self.runtime.receive(message())
        self.assertEqual(self.runtime.counters["button_events"], 0)

    async def test_no_commands_after_close(self):
        await self.runtime.async_close()
        with self.assertRaises(ConnectionError):
            await self.runtime.async_play_sound()
        self.assertEqual(self.client.argv, [])

    async def test_unknown_reports_schedule_at_most_one_refresh(self):
        self.runtime._last_refresh_request = 0
        for _ in range(100):
            self.runtime.receive(message("lumi.abcd"))
        self.assertEqual(len(self.runtime._tasks), 1)

    async def test_gateway_fields_do_not_become_current_together(self):
        self.runtime.receive(message("lumi.0", {"0.3.85": 12, "8.0.2024": 25}))
        self.mqtt.epoch = 2
        self.runtime.receive(message("lumi.0", {"0.3.85": 14}, epoch=2))
        self.assertEqual(self.runtime.gateway_observed["ambient_light_raw"], 2)
        self.assertEqual(self.runtime.gateway_observed["zigbee_channel"], 1)

    async def test_unknown_resource_is_read_only(self):
        self.runtime.receive(message(values={"9.9.9": 12}))
        descriptor = self.runtime.children[BUTTON].raw_fields["9.9.9"]
        self.assertFalse(descriptor.writable)
        self.assertEqual(descriptor.platform, "sensor")

    async def test_gateway_is_not_child_radio(self):
        self.runtime.receive(message("lumi.0", {"0.3.85": 12, "8.0.2024": 25}))
        self.assertEqual(self.runtime.gateway["ambient_light_raw"], 12)
        self.assertEqual(self.runtime.counters["child_reports"], 0)
        self.assertIsNone(self.runtime.last_child_report)

    async def test_all_heartbeat_children(self):
        payload = {
            "cmd": "heartbeat",
            "params": [
                {"did": BUTTON, "res_list": [{"res_name": "8.0.2001", "value": 3000}]},
                {"did": PLUG, "res_list": [{"res_name": "4.1.85", "value": 1}]},
            ],
        }
        self.runtime.receive(
            Message("zigbee/send", json.dumps(payload).encode(), False, False, None, 1)
        )
        self.assertTrue(self.runtime.children[PLUG].values["switch"])
        self.assertEqual(self.runtime.children[BUTTON].values["battery_voltage"], 3)
        self.assertEqual(self.runtime.counters["button_events"], 0)

    async def test_ring_failure_does_not_send_on_or_retry(self):
        self.client.fail_step = 2
        with self.assertRaises(TimeoutError):
            await self.runtime.async_ring((255, 0, 0), 255)
        self.assertEqual(len(self.client.argv), 2)
        self.assertEqual(self.runtime.last_command, "failed_or_outcome_unknown")
        self.assertIsNone(self.runtime.ring)

    async def test_ring_sequence_and_cached_assumption(self):
        await self.runtime.async_ring((0, 0, 255), 255)
        self.assertEqual(len(self.client.argv), 3)
        self.assertFalse(self.runtime.ring_stale)
        self.assertEqual(
            self.runtime.last_command, "rpc_accepted_not_physical_readback"
        )

    async def test_native_one_shot_and_volume_cap(self):
        await self.runtime.async_play_sound(volume=2)
        self.assertEqual(
            self.client.argv[-1],
            ("/bin/basis_cli", "-sys", "-s", "doorbell", "1", "0", "2"),
        )
        with self.assertRaises(ValueError):
            await self.runtime.async_play_sound(volume=50)
        with self.assertRaises(ValueError):
            await self.runtime.async_play_sound(sound_id=2)
        self.assertEqual(len(self.client.argv), 1)

    async def test_ring_audio_share_lock(self):
        await asyncio.gather(
            self.runtime.async_ring((255, 0, 0), 255), self.runtime.async_play_sound()
        )
        self.assertEqual(
            [a[1] for a in self.client.argv], ["-argb", "-argb", "-argb", "-sys"]
        )

    async def test_child_write_opt_in_and_no_optimistic_state(self):
        self.runtime.receive(message(PLUG, {"4.1.85": 0}))
        with self.assertRaises(ValueError):
            await self.runtime.async_child_switch(PLUG, "switch", True)
        self.runtime.allow_child_control = True
        await self.runtime.async_child_switch(PLUG, "switch", True)
        self.assertFalse(self.runtime.children[PLUG].values["switch"])
        self.assertEqual(
            self.runtime.children[PLUG].pending["switch"], "sent_unconfirmed"
        )
        self.runtime.receive(message(PLUG, {"4.1.85": 1}, cmd="write_ack"))
        self.assertFalse(self.runtime.children[PLUG].values["switch"])
        self.runtime.receive(message(PLUG, {"4.1.85": 1}))
        self.assertTrue(self.runtime.children[PLUG].values["switch"])

    async def test_child_write_not_replayed_on_transport_failure(self):
        self.runtime.receive(message(PLUG, {"4.1.85": 0}))
        self.runtime.allow_child_control = True
        self.mqtt.publish_error = ConnectionError()
        with self.assertRaises(ConnectionError):
            await self.runtime.async_child_switch(PLUG, "switch", True)
        self.assertEqual(len(self.mqtt.published), 1)
        self.assertEqual(
            self.runtime.children[PLUG].pending["switch"], "outcome_unknown"
        )

    async def test_public_diagnostics_redaction(self):
        raw = json.dumps(self.runtime.diagnostics())
        for secret in (self.client.host, BUTTON, PLUG, "password", "username"):
            self.assertNotIn(secret, raw)

    async def test_close_cleans_background_tasks(self):
        await self.runtime.async_start()
        await self.runtime.async_close()
        self.assertTrue(self.mqtt.stopped)
        self.assertTrue(self.client.closed)
        self.assertEqual(self.mqtt.messages, [])
        self.assertEqual(self.mqtt.statuses, [])
        self.assertFalse(self.runtime._tasks)
