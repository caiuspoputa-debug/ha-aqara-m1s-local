import asyncio
import re
import socketserver
import threading
import unittest
from unittest.mock import patch

from helpers import module

client = module("client")
mqtt = module("mqtt_client")
system = module("system_status")


class FramingTests(unittest.TestCase):
    def test_local_synthetic_telnet_login_echo_and_two_commands(self):
        commands = []

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                self.wfile.write(b"login:")
                self.wfile.flush()
                if self.rfile.readline() != b"admin\n":
                    return
                self.wfile.write(b"Password:")
                self.wfile.flush()
                if self.rfile.readline() != b"\n":
                    return
                self.wfile.write(b"\r\n# ")
                self.wfile.flush()
                while raw := self.rfile.readline():
                    frame = raw.decode()
                    commands.append(frame)
                    begin, end = re.findall(r"'(M1S_(?:BEGIN|END)_[0-9a-f]+)'", frame)
                    self.wfile.write(
                        raw + f"\r\n{begin}\r\npayload\r\n{end}:0\r\n# ".encode()
                    )
                    self.wfile.flush()

        with socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            instance = client.AqaraM1SClient(
                "127.0.0.1", server.server_address[1], timeout=2
            )
            try:
                for _ in range(2):
                    result = instance.run_result("printf payload")
                    self.assertEqual(result.output, "payload")
                    self.assertEqual(result.returncode, 0)
            finally:
                instance.close()
                server.shutdown()
                thread.join(timeout=2)
        self.assertEqual(len(commands), 2)
        self.assertNotEqual(commands[0], commands[1])

    def test_shell_echo_cannot_complete_command(self):
        echoed = "printf '\\n%s\\n' 'BEGIN'; ( command ); printf '\\n%s:%s\\n' 'END' \"$?\"\n"
        self.assertIsNone(client.AqaraM1SClient.parse_result(echoed, "BEGIN", "END"))
        self.assertIsNone(
            client.AqaraM1SClient.parse_result(
                echoed + "\nBEGIN\nbody\n", "BEGIN", "END"
            )
        )
        result = client.AqaraM1SClient.parse_result(
            echoed + "\nBEGIN\nbody\nEND:0\n# ", "BEGIN", "END"
        )
        self.assertEqual(result.output, "body")
        self.assertEqual(result.returncode, 0)

    def test_nonzero_exit_framed(self):
        self.assertEqual(
            client.AqaraM1SClient.parse_result(
                "\nB\nfailed\nE:127\n", "B", "E"
            ).returncode,
            127,
        )

    def test_no_retry_after_command_send(self):
        instance = client.AqaraM1SClient("example.local")

        class Socket:
            def __init__(self):
                self.sent = []

            def sendall(self, raw):
                self.sent.append(raw)

            def close(self):
                pass

        sock = instance._sock = Socket()
        with (
            patch.object(instance, "_connect"),
            patch.object(instance, "_read", side_effect=TimeoutError()),
            self.assertRaises(TimeoutError),
        ):
            instance.run_result("/bin/basis_cli -argb -s 1")
        self.assertEqual(len(sock.sent), 1)
        self.assertIsNone(instance._sock)

    def test_fragmented_iac_and_subnegotiation(self):
        instance = client.AqaraM1SClient("example.local")
        self.assertEqual(instance._decode(b"hello\xff"), b"hello")
        self.assertEqual(instance._decode(b"\xfb"), b"")
        self.assertEqual(instance._decode(b"\x01world"), b"world")
        self.assertEqual(instance._decode(b"\xff\xfa\x18data\xff"), b"")
        self.assertEqual(instance._decode(b"\xf0tail"), b"tail")

    def test_system_snapshot_allowlist_and_bounds(self):
        raw = "uptime 100\nload_1m 0.2\nmemory_used_pct 33\nha_basis_present 1\nwifi_operstate up\nIP 192.0.2.1\n"
        result = system.parse_snapshot(raw)
        self.assertEqual(result["uptime"], 100)
        self.assertTrue(result["ha_basis_present"])
        self.assertNotIn("IP", result)
        self.assertEqual(
            system.parse_snapshot("uptime nan\nload_1m inf\nmemory_used_pct 101\n"), {}
        )


class MQTTTests(unittest.IsolatedAsyncioTestCase):
    async def test_subscription_rejection_never_marks_connected(self):
        sessions = []

        async def broker(reader, writer):
            sessions.append(asyncio.current_task())
            helper = mqtt.AqaraM1SMqttClient("unused")
            helper._reader = reader
            try:
                await helper._read_packet()
                writer.write(b"\x20\x02\0\0")
                await writer.drain()
                _, body = await helper._read_packet()
                writer.write(b"\x90\x05" + body[:2] + b"\0\x80\0")
                await writer.drain()
                await reader.read()
            finally:
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(broker, "127.0.0.1", 0)
        instance = mqtt.AqaraM1SMqttClient(
            "127.0.0.1", server.sockets[0].getsockname()[1]
        )
        try:
            with self.assertRaises(ValueError):
                await instance._connect()
            self.assertFalse(instance.connected)
        finally:
            await instance._close_connection()
            server.close()
            await server.wait_closed()
            await asyncio.gather(*sessions, return_exceptions=True)

    async def test_oversized_packet_rejected_before_body_read(self):
        instance = mqtt.AqaraM1SMqttClient("example.local")
        instance._reader = asyncio.StreamReader()
        instance._reader.feed_data(b"\x30\xff\xff\x7f")
        with self.assertRaises(ValueError):
            await instance._read_packet()

    async def test_truncated_packet_and_qos2(self):
        instance = mqtt.AqaraM1SMqttClient("example.local")
        for header, body in ((0x30, b"\0\x10a"), (0x34, b"\0\x01a\0\x01{}")):
            with self.subTest(header=header), self.assertRaises(ValueError):
                await instance._dispatch(header, body)

    async def test_publish_retained_metadata_and_qos1_ack(self):
        instance = mqtt.AqaraM1SMqttClient("example.local")
        events, writes = [], []
        instance.add_message_listener(events.append)

        async def write(raw):
            writes.append(raw)

        instance._write = write
        await instance._dispatch(0x3B, mqtt._encode_utf8("zigbee/send") + b"\0\x07{}")
        self.assertTrue(events[0].retained)
        self.assertTrue(events[0].duplicate)
        self.assertEqual(events[0].packet_id, 7)
        self.assertEqual(writes, [b"\x40\x02\0\x07"])

    async def test_offline_publish_is_not_queued(self):
        instance = mqtt.AqaraM1SMqttClient("example.local")
        with self.assertRaises(ConnectionError):
            await instance.publish_json("zigbee/recv", {"cmd": "write"})
        with self.assertRaises(ValueError):
            await instance.publish_json("arbitrary/topic", {})

    async def test_local_synthetic_broker_handshake_and_cleanup(self):
        received = []
        ready = asyncio.Event()
        sessions = []

        async def broker(reader, writer):
            sessions.append(asyncio.current_task())
            helper = mqtt.AqaraM1SMqttClient("unused")
            helper._reader = reader
            try:
                header, body = await helper._read_packet()
                self.assertEqual(header, 0x10)
                writer.write(b"\x20\x02\0\0")
                await writer.drain()
                header, body = await helper._read_packet()
                self.assertEqual(header, 0x82)
                # Interleaving one retained PUBLISH before SUBACK is legal.
                data = mqtt._encode_utf8("zigbee/send") + b"{}"
                writer.write(b"\x31" + mqtt._encode_remaining_length(len(data)) + data)
                writer.write(b"\x90\x05" + body[:2] + b"\0\0\0")
                await writer.drain()
                ready.set()
                header, body = await helper._read_packet()
                self.assertEqual(header, 0x30)  # commands are QoS0, non-retained
                received.append(body)
                await reader.read()
            except asyncio.IncompleteReadError:
                pass
            finally:
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(broker, "127.0.0.1", 0)
        instance = mqtt.AqaraM1SMqttClient(
            "127.0.0.1", server.sockets[0].getsockname()[1]
        )
        messages = []
        instance.add_message_listener(messages.append)
        try:
            await instance.start()
            await asyncio.wait_for(ready.wait(), 2)
            for _ in range(100):
                if instance.connected:
                    break
                await asyncio.sleep(0.01)
            self.assertTrue(instance.connected)
            await instance.publish_json(
                "zigbee/recv", {"cmd": "write", "did": "lumi.1"}
            )
            for _ in range(100):
                if received:
                    break
                await asyncio.sleep(0.01)
            self.assertEqual(len(received), 1)
            self.assertTrue(messages[0].retained)
        finally:
            await instance.stop()
            server.close()
            await server.wait_closed()
            await asyncio.gather(*sessions, return_exceptions=True)
        self.assertFalse(instance.connected)
        self.assertIsNone(instance._runner)
