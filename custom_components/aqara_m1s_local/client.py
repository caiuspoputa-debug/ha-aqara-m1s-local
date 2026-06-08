import socket
import time
from dataclasses import dataclass

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
        end = time.time() + seconds
        chunks = []
        while time.time() < end:
            try:
                data = sock.recv(4096)
                if not data:
                    break
                self._reply_negotiation(sock, data)
                chunks.append(self._negotiate(data))
            except socket.timeout:
                break
        return b"".join(chunks).decode("latin1", errors="ignore")

    def _read_until_any(self, sock: socket.socket, markers, timeout: float = 8.0) -> str:
        end = time.time() + timeout
        text = ""
        while time.time() < end:
            text += self._read_some(sock, 0.4)
            low = text.lower()
            for marker in markers:
                if marker.lower() in low:
                    return text
        return text

    def run_command(self, command: str) -> str:
        marker = "__M1S_DONE__"
        with socket.create_connection((self.host, int(self.port)), timeout=self.timeout) as sock:
            sock.settimeout(0.8)

            initial = self._read_until_any(sock, ["login:", "#", "$"], timeout=4)

            if "login:" in initial.lower():
                sock.sendall((self.username + "\n").encode())
                after_user = self._read_until_any(sock, ["password:", "#", "$"], timeout=4)
                if "password:" in after_user.lower():
                    sock.sendall((self.password + "\n").encode())
                    self._read_until_any(sock, ["#", "$"], timeout=5)

            sock.sendall((command + f"\necho {marker}$?\n").encode())
            output = self._read_until_any(sock, [marker], timeout=self.timeout)

            try:
                sock.sendall(b"exit\n")
            except Exception:
                pass

        return output

    def test(self) -> bool:
        try:
            out = self.run_command("echo ok")
            return "ok" in out
        except Exception:
            return False

    def list_sounds(self) -> list[str]:
        out = self.run_command('find /data/musics -type f -name "*.wav" 2>/dev/null')
        sounds = []
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("/data/musics/") and line.endswith(".wav"):
                sounds.append(line)
        return sorted(set(sounds))
