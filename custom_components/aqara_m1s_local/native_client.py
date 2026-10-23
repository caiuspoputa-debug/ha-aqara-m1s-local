"""Bounded authenticated MiIO property transport; credentials stay in memory."""

from __future__ import annotations

import base64
import secrets
import socket
import threading
import time
from datetime import UTC, datetime

from .native_properties import BY_KEY


class NativeError(ConnectionError):
    """A native operation failed; mutation outcomes must not be replayed."""


class NativeProperties:
    def __init__(self, shell, *, timeout=3, message_codec=None, socket_factory=None):
        self.shell = shell
        self.timeout = timeout
        self.ip = None
        self._codec = message_codec
        self._socket_factory = socket_factory or socket.socket
        self._token = self._did = self._device_id = None
        self._device_time = self._handshake_time = 0
        self._id = secrets.randbelow(7000) + 1000
        self._lock = threading.RLock()
        self._closed = False

    def _credentials(self):
        if self._token is not None:
            return
        token = self.shell.run_argv("/bin/busybox", "base64", "/data/miio/device.token")
        did = self.shell.run_argv("/bin/getprop", "persist.sys.miio_did")
        if token.returncode or did.returncode:
            raise NativeError("Existing native credentials are unavailable")
        try:
            raw = base64.b64decode("".join(token.output.split()), validate=True)
        except ValueError as err:
            raise NativeError("Invalid native credential format") from err
        if len(raw) == 17 and raw[-1:] in (b"\x00", b"\n"):
            raw = raw[:16]
        if len(raw) != 16 or not did.output.strip().isdecimal():
            raise NativeError("Invalid native credential format")
        self._token, self._did = raw, did.output.strip()

    def _message(self):
        if self._codec is None:
            from miio.protocol import Message

            self._codec = Message
        return self._codec

    def _rpc(self, method, params):
        if self._closed:
            raise NativeError("Native transport is closed")
        if method not in ("get_properties", "set_properties"):
            raise ValueError("Unsupported native method")
        self._credentials()
        codec = self._message()
        self._id = self._id % 9998 + 1
        request_id = self._id
        try:
            with self._socket_factory(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.shell.host, 54321))
                if (
                    self._device_id is None
                    or time.monotonic() - self._handshake_time > 30
                ):
                    sock.send(bytes.fromhex("21310020" + "ff" * 28))
                    hello = sock.recv(4096)
                    if len(hello) != 32 or hello[:4] != b"\x21\x31\x00\x20":
                        raise NativeError("Invalid native discovery response")
                    self._device_id = hello[8:12]
                    if int.from_bytes(self._device_id, "big") != int(self._did):
                        raise NativeError(
                            "Native identity does not match authenticated shell"
                        )
                    self._device_time = int.from_bytes(hello[12:16], "big")
                    self._handshake_time = time.monotonic()
                timestamp = (
                    self._device_time + int(time.monotonic() - self._handshake_time) + 1
                )
                payload = {"id": request_id, "method": method, "params": params}
                packet = codec.build(
                    {
                        "data": {"value": payload},
                        "header": {
                            "value": {
                                "length": 0,
                                "unknown": 0,
                                "device_id": self._device_id,
                                "ts": datetime.fromtimestamp(timestamp, UTC),
                            }
                        },
                        "checksum": 0,
                    },
                    token=self._token,
                )
                # Exactly one application request. Never replay a timed-out write.
                sock.send(packet)
                reply = sock.recv(4096)
                if (
                    len(reply) < 33
                    or reply[:2] != b"\x21\x31"
                    or int.from_bytes(reply[2:4], "big") != len(reply)
                ):
                    raise NativeError("Invalid native response frame")
                if reply[8:12] != self._device_id:
                    raise NativeError("Native response identity mismatch")
                parsed = codec.parse(reply, token=self._token)
                document = parsed.data.value
                if (
                    not isinstance(document, dict)
                    or document.get("id") != request_id
                    or "error" in document
                ):
                    raise NativeError(
                        "Native response rejected or does not match request"
                    )
                result = document.get("result")
                if not isinstance(result, list):
                    raise NativeError("Invalid native property response")
                self.ip = sock.getpeername()[0]
                return result
        except NativeError:
            self._device_id = self._token = self._did = None
            raise
        except Exception:  # noqa: BLE001 - sanitize third-party codec errors at the credential boundary
            self._device_id = self._token = self._did = None
            # Do not log library exceptions, raw payloads or credential material.
            raise NativeError("Native request failed; no retry was sent") from None

    def _results(self, result, keys, *, writing=False):
        accepted = {}
        for key in keys:
            prop = BY_KEY[key]
            matches = [
                item
                for item in result
                if isinstance(item, dict)
                and item.get("did", self._did) == self._did
                and item.get("siid") == prop.siid
                and item.get("piid") == prop.piid
            ]
            if (
                len(matches) != 1
                or type(matches[0].get("code")) is not int
                or matches[0]["code"] != 0
            ):
                if writing:
                    raise NativeError("Native property write was not acknowledged")
                continue
            if writing:
                accepted[key] = True
            elif "value" in matches[0]:
                try:
                    accepted[key] = prop.validate(matches[0]["value"])
                except ValueError:
                    continue
        return accepted

    def read(self, keys):
        keys = tuple(keys)
        if (
            not keys
            or len(keys) > 64
            or any(key not in BY_KEY or not BY_KEY[key].read for key in keys)
        ):
            raise ValueError("Invalid native read selection")
        with self._lock:
            if self._closed:
                raise NativeError("Native transport is closed")
            values = {}
            for offset in range(0, len(keys), 6):
                batch = keys[offset : offset + 6]
                self._credentials()
                params = [
                    {
                        "did": self._did,
                        "siid": BY_KEY[key].siid,
                        "piid": BY_KEY[key].piid,
                    }
                    for key in batch
                ]
                values.update(self._results(self._rpc("get_properties", params), batch))
            return values

    def write(self, items):
        items = tuple(items)
        if not items or len(items) > 4 or len({key for key, _ in items}) != len(items):
            raise ValueError("Invalid native write selection")
        for key, value in items:
            BY_KEY[key].validate(value, writing=True)
        with self._lock:
            if self._closed:
                raise NativeError("Native transport is closed")
            self._credentials()
            params = [
                {
                    "did": self._did,
                    "siid": BY_KEY[key].siid,
                    "piid": BY_KEY[key].piid,
                    "value": value,
                }
                for key, value in items
            ]
            self._results(
                self._rpc("set_properties", params),
                [key for key, _ in items],
                writing=True,
            )

    def close(self):
        self._closed = True
        with self._lock:
            self._token = self._did = self._device_id = None
            self.ip = None
