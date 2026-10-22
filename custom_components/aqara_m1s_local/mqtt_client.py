"""Bounded MQTT 3.1.1 transport for the existing local stock tunnel."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)
MAX_PACKET = 131072
TOPICS = ("zigbee/send", "ioctl/send", "broker/ping")


def _encode_remaining_length(value):
    if not 0 <= value <= MAX_PACKET:
        raise ValueError("MQTT packet exceeds limit")
    result = bytearray()
    while True:
        digit, value = value % 128, value // 128
        result.append(digit | (128 if value else 0))
        if not value:
            return bytes(result)


def _encode_utf8(value):
    raw = value.encode("utf-8")
    if not raw or len(raw) > 65535 or "\0" in value:
        raise ValueError("Invalid MQTT string")
    return len(raw).to_bytes(2, "big") + raw


@dataclass(frozen=True)
class Message:
    topic: str
    payload: bytes
    retained: bool
    duplicate: bool
    packet_id: int | None
    epoch: int


class AqaraM1SMqttClient:
    def __init__(self, host, port=1884, *, stream_factory=None):
        self.host, self.port = host, port
        self.connected = False
        self.epoch = 0
        self._reader = self._writer = self._runner = self._ping_task = None
        self._write_lock = asyncio.Lock()
        self._messages, self._statuses = [], []
        self._packet_id = secrets.randbelow(65535) + 1
        self._ping_sent = None
        self._stream_factory = stream_factory
        self.last_error = None

    def _listen(self, listeners, callback):
        listeners.append(callback)

        def remove():
            if callback in listeners:
                listeners.remove(callback)

        return remove

    def add_message_listener(self, callback):
        return self._listen(self._messages, callback)

    def add_status_listener(self, callback):
        return self._listen(self._statuses, callback)

    async def start(self):
        if self._runner is None:
            self._runner = asyncio.create_task(self._connection_loop())

    async def stop(self):
        if self._runner:
            self._runner.cancel()
            await asyncio.gather(self._runner, return_exceptions=True)
            self._runner = None
        await self._close_connection()

    async def publish_json(self, topic, payload):
        if topic != "zigbee/recv":
            raise ValueError("Unsupported stock publication topic")
        if not self.connected:
            raise ConnectionError("Stock MQTT is disconnected")
        raw = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
        body = _encode_utf8(topic) + raw
        # QoS0 and never retained: reconnect must not replay actuator commands.
        await self._write(b"\x30" + _encode_remaining_length(len(body)) + body)

    async def _connection_loop(self):
        delay = 1
        while True:
            try:
                await self._connect()
                delay = 1
                await self._read_loop()
            except asyncio.CancelledError:
                raise
            except (
                TimeoutError,
                OSError,
                ValueError,
                asyncio.IncompleteReadError,
            ) as err:
                self.last_error = type(err).__name__
                _LOGGER.warning(
                    "Stock MQTT disconnected; retrying without replaying commands"
                )
            finally:
                await self._close_connection()
            await asyncio.sleep(delay)
            delay = min(30, delay * 2)

    async def _connect(self):
        connection = (
            self._stream_factory()
            if self._stream_factory
            else asyncio.open_connection(self.host, self.port)
        )
        self._reader, self._writer = await asyncio.wait_for(connection, 8)
        body = (
            _encode_utf8("MQTT")
            + b"\x04\x02\x00\x1e"
            + _encode_utf8("ha_m1s_" + secrets.token_hex(5))
        )
        await self._write(b"\x10" + _encode_remaining_length(len(body)) + body)
        header, body = await asyncio.wait_for(self._read_packet(), 8)
        if header != 0x20 or body != b"\0\0":
            raise ValueError("Stock broker rejected the clean MQTT session")
        self._packet_id = self._packet_id % 65535 + 1
        subscription = self._packet_id.to_bytes(2, "big") + b"".join(
            _encode_utf8(t) + b"\0" for t in TOPICS
        )
        await self._write(
            b"\x82" + _encode_remaining_length(len(subscription)) + subscription
        )
        deadline = time.monotonic() + 8
        self.epoch += 1
        pending = []
        while True:
            header, body = await asyncio.wait_for(
                self._read_packet(), max(0.01, deadline - time.monotonic())
            )
            if header == 0x90:
                if body[:2] != self._packet_id.to_bytes(2, "big") or body[2:] != bytes(
                    len(TOPICS)
                ):
                    raise ValueError("Invalid or rejected stock MQTT SUBACK")
                break
            if header >> 4 != 3 or len(pending) >= 32:
                raise ValueError("Unexpected MQTT subscription response")
            pending.append((header, body))
        self._set_connected(True)
        self.last_error = None
        for header, body in pending:
            await self._dispatch(header, body)
        self._ping_sent = None
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def _ping_loop(self):
        try:
            while self.connected:
                await asyncio.sleep(15)
                if self._ping_sent is not None:
                    self._writer.close()
                    return
                self._ping_sent = time.monotonic()
                await self._write(b"\xc0\0")
        except (TimeoutError, OSError):
            if self._writer:
                self._writer.close()

    async def _read_loop(self):
        while True:
            header, body = await asyncio.wait_for(self._read_packet(), 45)
            if header == 0xD0 and not body:
                self._ping_sent = None
            elif header >> 4 == 3:
                await self._dispatch(header, body)
            else:
                raise ValueError("Unsupported broker packet")

    async def _dispatch(self, header, body):
        qos = (header >> 1) & 3
        if qos > 1 or len(body) < 2:
            raise ValueError("Unsupported MQTT PUBLISH")
        length = int.from_bytes(body[:2], "big")
        cursor = 2 + length
        if not length or cursor + (2 if qos else 0) > len(body):
            raise ValueError("Truncated MQTT PUBLISH")
        topic = body[2:cursor].decode("utf-8")
        if "\0" in topic:
            raise ValueError("Invalid topic")
        packet_id = None
        if qos:
            packet_id = int.from_bytes(body[cursor : cursor + 2], "big")
            if packet_id == 0:
                raise ValueError("Invalid MQTT packet id")
            cursor += 2
        if topic in TOPICS:
            message = Message(
                topic,
                body[cursor:],
                bool(header & 1),
                bool(header & 8),
                packet_id,
                self.epoch,
            )
            for callback in tuple(self._messages):
                try:
                    callback(message)
                except Exception:
                    _LOGGER.exception("Stock message listener failed")
        if qos:
            await self._write(b"\x40\x02" + packet_id.to_bytes(2, "big"))

    async def _read_packet(self):
        if self._reader is None:
            raise ConnectionError("MQTT stream closed")
        header = (await self._reader.readexactly(1))[0]
        remaining = 0
        for shift in range(0, 28, 7):
            digit = (await self._reader.readexactly(1))[0]
            remaining |= (digit & 127) << shift
            if remaining > MAX_PACKET:
                raise ValueError("Oversized MQTT packet")
            if not digit & 128:
                return header, await self._reader.readexactly(remaining)
        raise ValueError("Malformed MQTT length")

    async def _write(self, packet):
        async with self._write_lock:
            if self._writer is None:
                raise ConnectionError("MQTT writer closed")
            self._writer.write(packet)
            await asyncio.wait_for(self._writer.drain(), 5)

    async def _close_connection(self):
        self._set_connected(False)
        if self._ping_task:
            self._ping_task.cancel()
            await asyncio.gather(self._ping_task, return_exceptions=True)
            self._ping_task = None
        writer, self._writer = self._writer, None
        self._reader = None
        if writer:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), 2)
            except (TimeoutError, OSError):
                pass

    def _set_connected(self, state):
        if state == self.connected:
            return
        self.connected = state
        for callback in tuple(self._statuses):
            try:
                callback(state)
            except Exception:
                _LOGGER.exception("Stock status listener failed")
