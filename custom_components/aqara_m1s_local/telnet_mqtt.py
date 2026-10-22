"""MQTT over an already authorized Telnet session, without exposing a port."""

from __future__ import annotations

import asyncio
import base64

from .client import AqaraM1SClient


class TelnetMQTTWriter:
    def __init__(self, writer):
        self.raw = writer

    def write(self, data):
        # ASCII records avoid control-byte transformations in the stock PTY.
        for offset in range(0, len(data), 384):
            self.raw.write(base64.b64encode(data[offset : offset + 384]) + b"\n")

    async def drain(self):
        await self.raw.drain()

    def close(self):
        self.raw.close()

    async def wait_closed(self):
        await self.raw.wait_closed()


class TelnetMQTTReader:
    def __init__(self, reader, writer):
        self.raw, self.writer = reader, writer
        self._pending = bytearray()
        self._decoded = bytearray()

    def _decode(self, raw):
        self._pending.extend(raw)
        result = bytearray()
        while self._pending:
            if self._pending[0] != 255:
                result.append(self._pending.pop(0))
                continue
            if len(self._pending) < 2:
                break
            command = self._pending[1]
            if command == 255:
                result.append(255)
                del self._pending[:2]
            elif command in (251, 252, 253, 254):
                if len(self._pending) < 3:
                    break
                if command in (251, 253):
                    self.writer.write(
                        bytes((255, 254 if command == 251 else 252, self._pending[2]))
                    )
                del self._pending[:3]
            elif command == 250:
                end = self._pending.find(b"\xff\xf0", 2)
                if end < 0:
                    if len(self._pending) > 4096:
                        raise ValueError("Oversized Telnet negotiation")
                    break
                del self._pending[: end + 2]
            else:
                del self._pending[:2]
        return result

    async def readexactly(self, count):
        if count < 0 or count > 131072:
            raise ValueError("Invalid Telnet MQTT read size")
        while len(self._decoded) < count:
            raw = await self.raw.read(4096)
            if not raw:
                partial = bytes(self._decoded)
                self._decoded.clear()
                raise asyncio.IncompleteReadError(partial, count)
            self._decoded.extend(self._decode(raw))
        result = bytes(self._decoded[:count])
        del self._decoded[:count]
        return result


def stream_factory(executor, *, host, port, username, password):
    """Each reconnect authenticates a new session; no install or persistent hook."""

    async def connect():
        client = AqaraM1SClient(host, port, username, password, timeout=3)
        job = asyncio.ensure_future(executor(client.open_mqtt_socket))
        try:
            sock = await asyncio.shield(job)
        except asyncio.CancelledError:
            # Executor cancellation cannot stop socket I/O; reclaim its result.
            try:
                abandoned = await job
                abandoned.close()
            except (OSError, ValueError, TimeoutError):
                pass
            raise
        try:
            reader, writer = await asyncio.open_connection(sock=sock)
        except BaseException:
            sock.close()
            raise
        return TelnetMQTTReader(reader, writer), TelnetMQTTWriter(writer)

    return connect
