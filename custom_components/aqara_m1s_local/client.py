from __future__ import annotations

import asyncio
import shlex

class AqaraM1SClient:
    def __init__(self, host: str, port: int = 2323) -> None:
        self.host = host
        self.port = int(port)

    async def test_connection(self) -> None:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout=5)
        writer.close()
        await writer.wait_closed()

    async def run_command(self, command: str) -> None:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout=5)
        writer.write((command.strip() + "\n").encode())
        await asyncio.wait_for(writer.drain(), timeout=5)
        writer.close()
        await writer.wait_closed()

    async def play_file(self, path: str) -> None:
        await self.run_command(f"aplay {shlex.quote(path)}")

    async def play_url(self, url: str) -> None:
        qurl = shlex.quote(url)
        await self.run_command(f"wget {qurl} -O /tmp/ha_audio.wav && aplay /tmp/ha_audio.wav")
