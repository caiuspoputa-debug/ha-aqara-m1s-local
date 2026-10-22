import unittest

from helpers import INVENTORY, cli_output, module

p = module("stock_protocol")


class ProtocolTests(unittest.TestCase):
    def test_logical_ring_exact_plan(self):
        plan = p.ring_plan((255, 0, 0), 128)
        self.assertEqual(
            [step[0] for step in plan], ["argb_toggle", "argb_colour", "argb_toggle"]
        )
        self.assertEqual(int(plan[1][1]), (50 << 24) | (255 << 16))
        self.assertEqual(plan[0][2], ("-argb", "-s", "0"))
        self.assertEqual(plan[-1][2], ("-argb", "-s", "1"))

    def test_black_and_zero_only_turn_off(self):
        for rgb, brightness in (((0, 0, 0), 255), ((255, 255, 255), 0)):
            self.assertEqual(len(p.ring_plan(rgb, brightness)), 1)

    def test_ring_rejects_invalid_channels(self):
        for rgb, brightness in (
            ((256, 0, 0), 255),
            ((True, 0, 0), 255),
            ((1, 2), 255),
            ((1, 2, 3), -1),
        ):
            with (
                self.subTest(rgb=rgb, brightness=brightness),
                self.assertRaises(ValueError),
            ):
                p.ring_plan(rgb, brightness)

    def test_native_ack(self):
        output = cli_output("basis.system", "system_sing", "1;1;0;1;5")
        self.assertEqual(
            p.validate_cli(output, 0, "basis.system", "system_sing", "1;1;0;1;5"), 123
        )

    def test_native_ack_rejects_ambiguity(self):
        good = cli_output("basis.argb", "argb_toggle", "0")
        mutations = [
            (good, 1),
            (good.replace('"id": 123', '"id": 124', 1), 0),
            (good + good, 0),
            ("\n".join(reversed(good.splitlines())), 0),
            (good.replace('["ok"]', '["error"]'), 0),
            (good.replace('"_from": 1', '"_from": true'), 0),
            (good.replace('"id": 123', '"id": true'), 0),
            (good.replace('"argb_toggle"', '"other"'), 0),
            (good.replace('"id": 123', '"id": 123, "id": 123', 1), 0),
            (good.split(">>>")[0], 0),
        ]
        for output, code in mutations:
            with self.subTest(output=output), self.assertRaises(ValueError):
                p.validate_cli(output, code, "basis.argb", "argb_toggle", "0")

    def test_inventory_allowlist(self):
        parsed = p.parse_inventory(INVENTORY)
        self.assertEqual(len(parsed), 2)
        raw = '{"devInfo":[{"did":"lumi.1","model":"lumi.plug","password":"not-exported"}]}'
        self.assertNotIn("password", str(p.parse_inventory(raw)))

    def test_inventory_identity_canonicalization(self):
        self.assertIn(
            "lumi.ab",
            p.parse_inventory('{"devInfo":[{"did":"lumi.AB","model":"lumi.plug"}]}'),
        )
        with self.assertRaises(ValueError):
            p.parse_inventory(
                '{"devInfo":[{"did":"lumi.AB","model":"lumi.plug"},{"did":"lumi.ab","model":"lumi.plug"}]}'
            )

    def test_inventory_rejects_invalid_or_duplicate(self):
        for raw in (
            "{}",
            '{"devInfo":{}}',
            '{"devInfo":[{"did":"lumi.0","model":"lumi.plug"}]}',
            '{"devInfo":[{"did":"lumi.1","model":"a"},{"did":"lumi.1","model":"a"}]}',
            '{"devInfo":[{"did":"x;reboot","model":"a"}]}',
            '{"devInfo":[],"devInfo":[]}',
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                p.parse_inventory(raw)

    def test_json_bounds(self):
        for raw in (
            '{"v": NaN}',
            '{"v": Infinity}',
            "{}\0",
            " " * 65537,
            '{"a":1,"a":2}',
        ):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                p.decode_json(raw)

    def test_all_heartbeat_members(self):
        doc = {
            "cmd": "heartbeat",
            "params": [
                {"did": "lumi.1", "res_list": [{"res_name": "0.1.85", "value": 1234}]},
                {"did": "lumi.2", "res_list": [{"res_name": "3.1.85", "value": 1}]},
            ],
        }
        self.assertEqual(len(p.reports(doc)), 2)

    def test_command_echoes_are_not_reports(self):
        for command in ("write", "write_ack", "control", "ping"):
            self.assertEqual(
                p.reports({"cmd": command, "did": "lumi.1", "params": []}), []
            )
        self.assertEqual(p.reports({"cmd": []}), [])

    def test_adversarial_numeric_and_nested_json_are_bounded(self):
        self.assertEqual(
            p.reports(
                {
                    "cmd": "report",
                    "did": "lumi.1",
                    "params": [{"res_name": "0.1.85", "value": 10**400}],
                }
            ),
            [("lumi.1", {})],
        )
        with self.assertRaises(ValueError):
            p.decode_json("[" * 10000 + "]" * 10000)

    def test_mi_spec_and_errors(self):
        result = p.reports(
            {
                "cmd": "read_rsp",
                "did": "lumi.1",
                "mi_spec": [
                    {"siid": 2, "piid": 3, "value": 7},
                    {"res_name": "0.1.85", "value": 1234, "error_code": -1},
                ],
            }
        )
        self.assertEqual(result, [("lumi.1", {"2.3": 7})])

    def test_model_specific_conversions(self):
        fields = {f.key: f for f in p.PROFILES["lumi.weather"]}
        self.assertEqual(p.decode_value(fields["temperature"], 2345), 23.45)
        self.assertEqual(p.decode_value(fields["humidity"], 5600), 56)
        self.assertEqual(p.decode_value(fields["battery_voltage"], 3000), 3)
        self.assertEqual(p.decode_value(fields["pressure"], 100125), 1001.25)
        with self.assertRaises(ValueError):
            p.decode_value(fields["humidity"], 10001)
        with self.assertRaises(ValueError):
            p.decode_value(fields["temperature"], float("inf"))

    def test_switch_encoder_is_model_bound(self):
        payload = p.child_write("lumi.1", "lumi.plug", "switch", True, 8)
        self.assertEqual(payload["params"], [{"res_name": "4.1.85", "value": 1}])
        for did, model, value in (
            ("lumi.0", "lumi.plug", True),
            ("lumi.1", "unknown", True),
            ("lumi.1", "lumi.plug", "on"),
        ):
            with self.assertRaises(ValueError):
                p.child_write(did, model, "switch", value, 1)
