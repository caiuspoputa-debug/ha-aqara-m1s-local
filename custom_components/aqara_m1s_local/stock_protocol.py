"""Bounded stock contracts. No transport, device access or implicit writes."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

MAX_JSON = 65536
DID = re.compile(r"lumi\.[0-9a-fA-F]{1,16}\Z")
MODEL = re.compile(r"[A-Za-z0-9_.-]{1,96}\Z")
RESOURCE = re.compile(r"[0-9]{1,3}\.[0-9]{1,3}(?:\.[0-9]{1,4})?\Z")
BUTTON_ACTIONS = {1: "single", 2: "double", 16: "hold", 17: "release"}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def decode_json(raw: str | bytes):
    if not isinstance(raw, (str, bytes)) or len(raw) > MAX_JSON:
        raise ValueError("Invalid or oversized stock payload")
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if "\0" in raw:
            raise ValueError("NUL in stock payload")
        return json.loads(
            raw, object_pairs_hook=_object, parse_constant=_invalid_constant
        )
    except (UnicodeError, RecursionError) as err:
        raise ValueError("Invalid stock JSON encoding or depth") from err


def _invalid_constant(_):
    raise ValueError("Non-finite JSON")


def finite_number(value):
    if type(value) is int:
        return -(2**63) <= value <= 2**64 - 1
    return type(value) is float and math.isfinite(value)


def integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("Integer outside supported range")
    return value


def ring_plan(rgb, brightness):
    if not isinstance(rgb, (tuple, list)) or len(rgb) != 3:
        raise ValueError("RGB requires three channels")
    red, green, blue = (integer(v, 0, 255) for v in rgb)
    brightness = integer(brightness, 0, 255)
    if not brightness or not max(rgb):
        return [("argb_toggle", "0", ("-argb", "-s", "0"))]
    percent = max(1, min(100, round(brightness * 100 / 255)))
    argb = (percent << 24) | (red << 16) | (green << 8) | blue
    return [
        ("argb_toggle", "0", ("-argb", "-s", "0")),
        ("argb_colour", str(argb), ("-argb", "-c", str(argb))),
        ("argb_toggle", "1", ("-argb", "-s", "1")),
    ]


def validate_cli(output, exit_code, method, name, value):
    """Require the exact request, one correlated RPC ACK and process exit 0."""
    if (
        exit_code != 0
        or not isinstance(output, str)
        or len(output) > 16384
        or "\0" in output
    ):
        raise ValueError("Stock command failed or output invalid")
    request = response = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Send >>"):
            if request is not None or response is not None:
                raise ValueError("Unexpected stock request sequence")
            request = decode_json(line[7:].strip())
            if not isinstance(request, dict) or set(request) != {
                "_to",
                "method",
                "params",
                "id",
            }:
                raise ValueError("Invalid stock request")
            integer(request["id"], 0, 2**32 - 1)
            if (
                type(request["_to"]) is not int
                or request["_to"] != 1
                or request["method"] != method
                or request["params"] != {"name": name, "value": value}
            ):
                raise ValueError("Stock request does not match intended operation")
        elif line.startswith(">>>"):
            if request is None or response is not None:
                raise ValueError("Unexpected stock response sequence")
            response = decode_json(line[3:].strip())
            if not isinstance(response, dict) or set(response) != {
                "_from",
                "id",
                "result",
            }:
                raise ValueError("Stock RPC error or invalid ACK")
            integer(response["id"], 0, 2**32 - 1)
            if (
                type(response["_from"]) is not int
                or response["_from"] != 1
                or response["id"] != request["id"]
                or response["result"] != ["ok"]
            ):
                raise ValueError("Stock RPC ACK mismatch")
    if request is None or response is None:
        raise ValueError("Missing stock request or ACK")
    return request["id"]


def parse_inventory(raw):
    document = decode_json(raw)
    if (
        not isinstance(document, dict)
        or not isinstance(document.get("devInfo"), list)
        or len(document["devInfo"]) > 256
    ):
        raise ValueError("Invalid device.info inventory")
    devices = {}
    for entry in document["devInfo"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid inventory member")  # noqa: TRY004
        did, model = entry.get("did"), entry.get("model")
        if (
            not isinstance(did, str)
            or not DID.fullmatch(did)
            or did == "lumi.0"
            or not isinstance(model, str)
            or not MODEL.fullmatch(model)
            or did.lower() in devices
        ):
            raise ValueError("Invalid or duplicate inventory identity")
        did = did.lower()
        devices[did] = {"did": did, "model": model}
    return devices


def reports(document):
    """Normalize every heartbeat member, not just the first. Never consume echoes."""
    if not isinstance(document, dict):
        return []
    command = document.get("cmd")
    if not isinstance(command, str):
        return []
    if command == "heartbeat":
        members = document.get("params")
        if not isinstance(members, list) or len(members) > 256:
            return []
        return [
            (d.get("did"), _properties(d.get("res_list")))
            for d in members
            if isinstance(d, dict)
        ]
    if command not in {"report", "read_rsp", "write_rsp"}:
        return []
    key = "params" if command == "report" else "results"
    return [
        (document.get("did"), _properties(document.get(key, document.get("mi_spec"))))
    ]


def _properties(items):
    result = {}
    if not isinstance(items, list) or len(items) > 256:
        return result
    for item in items:
        if not isinstance(item, dict) or (
            "error_code" in item
            and (type(item["error_code"]) is not int or item["error_code"] != 0)
        ):
            continue
        resource = item.get("res_name")
        if (
            resource is None
            and type(item.get("siid")) is int
            and type(item.get("piid")) is int
        ):
            resource = f"{item['siid']}.{item['piid']}"
        value = item.get("value")
        if not isinstance(resource, str) or not RESOURCE.fullmatch(resource):
            continue
        if (
            finite_number(value)
            or isinstance(value, str)
            and len(value) <= 128
            and not any(ord(c) < 32 for c in value)
            or type(value) is bool
        ):
            result[resource] = value
    return result


@dataclass(frozen=True)
class Field:
    key: str
    resource: str
    platform: str = "sensor"
    unit: str | None = None
    device_class: str | None = None
    scale: float = 1
    writable: bool = False


VOLTAGE = Field(
    "battery_voltage", "8.0.2001", unit="V", device_class="voltage", scale=0.001
)
PROFILES = {}


def _profile(models, *fields):
    for model in models.split():
        PROFILES[model] = tuple(fields)


# Protocol facts from the pinned AqaraGateway model tables; see PROVENANCE.md.
_profile(
    "lumi.sensor_switch lumi.sensor_switch.aq2 lumi.remote.b1acn01 lumi.remote.b1acn02 lumi.sensor_switch.aq3 lumi.sensor_86sw1 lumi.remote.b186acn01 lumi.remote.b186acn02 lumi.remote.b186acn03",
    Field("action", "13.1.85", "event"),
    VOLTAGE,
)
_profile(
    "lumi.sensor_86sw2 lumi.sensor_86sw2.es1 lumi.remote.b286acn01 lumi.remote.b286acn02 lumi.remote.b286opcn01",
    Field("left_action", "13.1.85", "event"),
    Field("right_action", "13.2.85", "event"),
    Field("both_action", "13.5.85", "event"),
    VOLTAGE,
)
_profile(
    "lumi.sensor_ht",
    Field(
        "temperature", "0.1.85", unit="\u00b0C", device_class="temperature", scale=0.01
    ),
    Field("humidity", "0.2.85", unit="%", device_class="humidity", scale=0.01),
    VOLTAGE,
)
_profile(
    "lumi.weather lumi.sensor_ht.agl02",
    *PROFILES["lumi.sensor_ht"],
    Field("pressure", "0.3.85", unit="hPa", device_class="pressure", scale=0.01),
)
_profile(
    "lumi.sensor_magnet lumi.sensor_magnet.aq2 lumi.magnet.akr01 lumi.magnet.ac01",
    Field("contact", "3.1.85", "binary_sensor", device_class="door"),
    VOLTAGE,
)
_profile(
    "lumi.sensor_wleak.aq1 lumi.flood.agl02",
    Field("water_leak", "3.1.85", "binary_sensor", device_class="moisture"),
    VOLTAGE,
)
_profile(
    "lumi.sensor_motion",
    Field("motion", "3.1.85", "binary_sensor", device_class="motion"),
    VOLTAGE,
)
_profile(
    "lumi.sensor_motion.aq2 lumi.motion.ac02",
    *PROFILES["lumi.sensor_motion"],
    Field("illuminance", "0.4.85", unit="lx", device_class="illuminance"),
)
_profile(
    "lumi.plug lumi.plug.mitw01 lumi.plug.mmeu01 lumi.plug.maus01 lumi.ctrl_86plug lumi.ctrl_86plug.aq1 lumi.plug.macn01",
    Field("switch", "4.1.85", "switch", writable=True),
    Field("power", "0.12.85", unit="W", device_class="power"),
    Field("energy", "0.13.85", unit="kWh", device_class="energy", scale=0.001),
)
_profile(
    "lumi.relay.c2acn01 lumi.ctrl_ln2 lumi.ctrl_ln2.aq1 lumi.switch.b2nacn02",
    Field("channel_1", "4.1.85", "switch", writable=True),
    Field("channel_2", "4.2.85", "switch", writable=True),
    Field("power", "0.12.85", unit="W", device_class="power"),
    Field("energy", "0.13.85", unit="kWh", device_class="energy", scale=0.001),
    Field("left_action", "13.1.85", "event"),
    Field("right_action", "13.2.85", "event"),
    Field("both_action", "13.5.85", "event"),
)
_profile(
    "lumi.ctrl_ln1 lumi.ctrl_ln1.aq1 lumi.switch.b1nacn02",
    *PROFILES["lumi.plug"],
    Field("action", "13.1.85", "event"),
)
_profile(
    "lumi.ctrl_neutral1 lumi.switch.b1lacn02 lumi.switch.l1acn1 lumi.switch.b1lacn01",
    Field("switch", "4.1.85", "switch", writable=True),
    Field("action", "13.1.85", "event"),
)
_profile(
    "lumi.ctrl_neutral2",
    Field("channel_1", "4.1.85", "switch", writable=True),
    Field("channel_2", "4.2.85", "switch", writable=True),
    Field("left_action", "13.1.85", "event"),
    Field("right_action", "13.2.85", "event"),
    Field("both_action", "13.5.85", "event"),
)


def decode_value(field, value):
    if field.platform in {"binary_sensor", "switch"}:
        if type(value) in (int, bool) and value in (0, 1):
            return bool(value)
        raise ValueError("Invalid binary state")
    if not finite_number(value):
        raise ValueError("Invalid numerical measurement")
    converted = value * field.scale
    if field.key == "temperature" and not -40 <= converted <= 125:
        raise ValueError("Invalid temperature")
    if field.key == "humidity" and not 0 <= converted <= 100:
        raise ValueError("Invalid humidity")
    return converted


def child_write(did, model, field_key, value, request_id):
    if not isinstance(did, str) or not DID.fullmatch(did) or did == "lumi.0":
        raise ValueError("Invalid child destination")
    field = next(
        (f for f in PROFILES.get(model, ()) if f.key == field_key and f.writable), None
    )
    if field is None or type(value) is not bool:
        raise ValueError("Unsupported child control")
    integer(request_id, 1, 65535)
    return {
        "cmd": "write",
        "did": did,
        "id": request_id,
        "params": [{"res_name": field.resource, "value": int(value)}],
    }
