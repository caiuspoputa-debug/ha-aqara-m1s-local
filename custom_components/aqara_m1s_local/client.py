"""Existing authorized shell transport, with exact framing and no write replay."""

from __future__ import annotations

import re
import secrets
import shlex
import socket
import threading
import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommandResult:
    output: str
    returncode: int


@dataclass
class AqaraM1SClient:
    host: str
    port: int = 23
    username: str = "admin"
    password: str = field(default="", repr=False)
    timeout: float = 8
    _sock: socket.socket | None = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False
    )
    _iac: bytearray = field(default_factory=bytearray, init=False, repr=False)

    def _decode(self, raw: bytes) -> bytes:
        """Preserve fragmented Telnet negotiation, including subnegotiation."""
        self._iac.extend(raw)
        result = bytearray()
        while self._iac:
            if self._iac[0] != 255:
                result.append(self._iac.pop(0))
                continue
            if len(self._iac) < 2:
                break
            command = self._iac[1]
            if command == 255:
                result.append(255)
                del self._iac[:2]
            elif command in (251, 252, 253, 254):
                if len(self._iac) < 3:
                    break
                if command in (251, 253) and self._sock:
                    self._sock.sendall(
                        bytes((255, 254 if command == 251 else 252, self._iac[2]))
                    )
                del self._iac[:3]
            elif command == 250:
                end = self._iac.find(b"\xff\xf0", 2)
                if end < 0:
                    if len(self._iac) > 4096:
                        raise ValueError("Oversized Telnet negotiation")
                    break
                del self._iac[: end + 2]
            else:
                del self._iac[:2]
        return bytes(result)

    def _read(self, deadline, predicate, maximum=131072):
        output = ""
        while time.monotonic() < deadline:
            self._sock.settimeout(min(0.25, max(0.01, deadline - time.monotonic())))
            try:
                raw = self._sock.recv(4096)
            except TimeoutError:
                continue
            if not raw:
                raise ConnectionError("Hub closed the shell connection")
            output += (
                self._decode(raw).decode("utf-8", errors="replace").replace("\r", "")
            )
            if len(output) > maximum:
                raise ValueError("Shell output exceeded its limit")
            if predicate(output):
                return output
        raise TimeoutError("Hub command deadline exceeded; outcome may be unknown")

    def _connect(self):
        if self._sock:
            return
        for value in (self.username, self.password):
            if any(c in value for c in "\r\n\0"):
                raise ValueError("Invalid login field")
        self._sock = socket.create_connection(
            (self.host, self.port), timeout=self.timeout
        )
        self._iac.clear()
        prompt = lambda text: re.search(r"(?:^|\n)[^\n]*[#$]\s*$", text) is not None
        output = self._read(
            time.monotonic() + self.timeout,
            lambda text: "login:" in text.lower() or prompt(text),
            16384,
        )
        if "login:" in output.lower():
            self._sock.sendall((self.username + "\n").encode())
            output = self._read(
                time.monotonic() + self.timeout,
                lambda text: "password:" in text.lower() or prompt(text),
                16384,
            )
            if "password:" in output.lower():
                self._sock.sendall((self.password + "\n").encode())
                self._read(time.monotonic() + self.timeout, prompt, 16384)

    @staticmethod
    def parse_result(output, begin, end):
        """Only standalone output lines count; echoed commands cannot finish a call."""
        start = re.search(rf"(?:^|\n){re.escape(begin)}\n", output)
        if start is None:
            return None
        finish = re.search(
            rf"(?:^|\n){re.escape(end)}:(\d{{1,3}})\n", output[start.end() :]
        )
        if finish is None:
            return None
        code = int(finish.group(1))
        if code > 255:
            raise ValueError("Invalid shell return code")
        return CommandResult(
            output[start.end() : start.end() + finish.start()].strip("\n"), code
        )

    def run_result(self, command: str, timeout: float | None = None) -> CommandResult:
        if (
            not isinstance(command, str)
            or not command
            or "\0" in command
            or len(command) > 8192
        ):
            raise ValueError("Invalid command")
        with self._lock:
            try:
                self._connect()
                nonce = secrets.token_hex(16)
                begin, end = f"M1S_BEGIN_{nonce}", f"M1S_END_{nonce}"
                framed = f"printf '\\n%s\\n' '{begin}'; ( {command} ); printf '\\n%s:%s\\n' '{end}' \"$?\"\n"
                self._sock.sendall(framed.encode())
                output = self._read(
                    time.monotonic() + (timeout or self.timeout),
                    lambda text: self.parse_result(text, begin, end) is not None,
                )
                return self.parse_result(output, begin, end)
            except BaseException:
                self._close_locked()
                # A timed-out mutation may already have happened. Never resend it.
                raise

    def run_argv(self, *argv: str, timeout=None):
        return self.run_result(shlex.join(argv), timeout)

    def run_command(self, command):
        result = self.run_result(command)
        if result.returncode:
            raise RuntimeError(f"Hub command exited with status {result.returncode}")
        return result.output

    def _close_locked(self):
        sock, self._sock = self._sock, None
        self._iac.clear()
        if sock:
            try:
                sock.close()
            except OSError:
                pass

    def close(self):
        with self._lock:
            self._close_locked()
