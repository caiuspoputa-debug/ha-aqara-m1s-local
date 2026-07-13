import socket
import threading
import time
from dataclasses import dataclass, field

IAC = 255
DONT = 254
DO = 253
WONT = 252
WILL = 251


@dataclass
class AqaraM1SClient:
    host: str
    port: int = 23
    username: str = "admin"
    password: str = ""
    timeout: float = 8.0
    _sock: socket.socket | None = field(default=None, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _command_id: int = field(default=0, init=False, repr=False)

    def _negotiate(self, data: bytes) -> bytes:
        out = bytearray()
        i = 0
        while i < len(data):
            if data[i] == IAC and i + 2 < len(data):
                i += 3
                continue
            out.append(data[i])
            i += 1
        return bytes(out)

    def _reply_negotiation(self, sock: socket.socket, data: bytes) -> None:
        i = 0
        replies = bytearray()
        while i < len(data):
            if data[i] == IAC and i + 2 < len(data):
                cmd = data[i + 1]
                opt = data[i + 2]
                if cmd == WILL:
                    replies += bytes([IAC, DONT, opt])
                elif cmd == DO:
                    replies += bytes([IAC, WONT, opt])
                i += 3
            else:
                i += 1
        if replies:
            sock.sendall(replies)

    def _read_some(self, sock: socket.socket, seconds: float = 0.5) -> str:
        end = time.monotonic() + seconds
        chunks = []
        while time.monotonic() < end:
            try:
                data = sock.recv(4096)
                if not data:
                    raise ConnectionError("Telnet connection closed by hub")
                self._reply_negotiation(sock, data)
                chunks.append(self._negotiate(data))
            except socket.timeout:
                break
        return b"".join(chunks).decode("latin1", errors="ignore")

    def _read_until_any(self, sock: socket.socket, markers, timeout: float = 8.0) -> str:
        end = time.monotonic() + timeout
        text = ""
        while time.monotonic() < end:
            text += self._read_some(sock, min(0.4, max(0.05, end - time.monotonic())))
            low = text.lower()
            for marker in markers:
                if marker.lower() in low:
                    return text
        return text

    def _close_locked(self) -> None:
        sock = self._sock
        self._sock = None
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass

    def close(self) -> None:
        with self._lock:
            self._close_locked()

    def _connect_locked(self) -> socket.socket:
        if self._sock is not None:
            return self._sock

        sock = socket.create_connection((self.host, int(self.port)), timeout=self.timeout)
        sock.settimeout(0.35)

        try:
            initial = self._read_until_any(sock, ["login:", "#", "$"], timeout=4)
            if "login:" in initial.lower():
                sock.sendall((self.username + "\n").encode())
                after_user = self._read_until_any(sock, ["password:", "#", "$"], timeout=4)
                if "password:" in after_user.lower():
                    sock.sendall((self.password + "\n").encode())
                    prompt = self._read_until_any(sock, ["#", "$"], timeout=5)
                    if "#" not in prompt and "$" not in prompt:
                        raise ConnectionError("Telnet login did not reach a shell prompt")
            self._sock = sock
            return sock
        except Exception:
            try:
                sock.close()
            except OSError:
                pass
            raise

    def _run_command_locked(self, command: str) -> str:
        sock = self._connect_locked()

        # Discard any delayed prompt/output left from the previous command.
        try:
            self._read_some(sock, 0.05)
        except ConnectionError:
            self._close_locked()
            raise

        self._command_id += 1
        marker = f"__M1S_DONE_{self._command_id}__"
        sock.sendall((command + f"\necho {marker}$?\n").encode())
        output = self._read_until_any(sock, [marker], timeout=self.timeout)
        if marker not in output:
            raise TimeoutError(f"Command did not finish within {self.timeout} seconds")
        return output

    def run_command(self, command: str) -> str:
        with self._lock:
            last_error: Exception | None = None
            for attempt in range(2):
                try:
                    return self._run_command_locked(command)
                except (OSError, ConnectionError, TimeoutError) as err:
                    last_error = err
                    self._close_locked()
                    if attempt == 0:
                        continue
            assert last_error is not None
            raise last_error

    def list_sounds(self) -> list[str]:
        out = self.run_command('find /data/musics -type f -name "*.wav" 2>/dev/null')
        sounds = []
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("/data/musics/") and line.endswith(".wav"):
                sounds.append(line)
        return sorted(set(sounds))
