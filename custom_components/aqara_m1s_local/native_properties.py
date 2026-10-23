"""Explicit stock M1S property contracts, not every model shipped in firmware."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Property:
    key: str
    siid: int
    piid: int
    name: str
    kind: str = "integer"
    platform: str = "sensor"
    minimum: int = 0
    maximum: int = 100
    step: int = 1
    unit: str | None = None
    writable: bool = False
    read: bool = True
    choices: tuple = ()
    advanced: bool = False

    def validate(self, value, *, writing=False):
        if writing and not self.writable:
            raise ValueError("Read-only native property")
        if self.kind == "bool":
            if type(value) is not bool:
                raise ValueError("Boolean property required")
        elif self.kind == "string":
            if (
                not isinstance(value, str)
                or len(value) > 8192
                or any(c in value for c in "\x00\r\n")
            ):
                raise ValueError("Invalid native string")
            if self.key == "indicator_schedule" and not re.fullmatch(
                r"(?:[01][0-9]|2[0-3]):[0-5][0-9]-(?:[01][0-9]|2[0-3]):[0-5][0-9]",
                value,
            ):
                raise ValueError("Expected HH:MM-HH:MM")
        elif type(value) is not int or not self.minimum <= value <= self.maximum:
            raise ValueError("Native integer outside its contract")
        elif writing and (value - self.minimum) % self.step:
            raise ValueError("Invalid native property step")
        if self.choices and value not in self.choices:
            raise ValueError("Unsupported native choice")
        return value


PROPERTIES = [
    Property("ring_on", 2, 1, "Ring on", kind="bool", platform="light", writable=True),
    Property(
        "ring_brightness", 2, 3, "Ring brightness", platform="light", writable=True
    ),
    Property(
        "ring_color",
        2,
        4,
        "Ring color",
        platform="light",
        minimum=1,
        maximum=0xFFFFFF,
        writable=True,
    ),
    Property(
        "guard_mode",
        3,
        1,
        "Native guard mode",
        platform="select",
        maximum=4,
        writable=True,
    ),
    Property(
        "alarm_status",
        3,
        22,
        "Native alarm status",
        choices=(0, 1, 2, 3, 4, 11, 12, 13, 14, 15, 16),
    ),
    Property(
        "hub_button_code", 4, 1, "Last hub button code", maximum=65535, advanced=True
    ),
    Property(
        "system_language",
        5,
        1,
        "System language",
        kind="string",
        platform="select",
        writable=True,
    ),
    Property(
        "system_volume",
        5,
        2,
        "Hub system volume",
        platform="number",
        unit="%",
        writable=True,
    ),
    Property(
        "indicator_night_off",
        6,
        1,
        "Night indicator suppression",
        platform="switch",
        maximum=1,
        writable=True,
    ),
    Property(
        "indicator_schedule",
        6,
        2,
        "Indicator suppression schedule",
        kind="string",
        platform="text",
        writable=True,
    ),
    Property(
        "deletion_protection",
        7,
        1,
        "Accidental deletion protection",
        platform="switch",
        maximum=1,
        writable=True,
    ),
    Property(
        "last_audio_request",
        9,
        1,
        "Last native audio request",
        kind="string",
        advanced=True,
    ),
    Property(
        "audio_repeat",
        9,
        3,
        "Native audio repeat",
        platform="switch",
        maximum=1,
        writable=True,
    ),
    Property(
        "audio_catalog", 9, 5, "Native audio catalog", kind="string", advanced=True
    ),
    Property(
        "language_catalog",
        9,
        6,
        "Native language catalog",
        kind="string",
        advanced=True,
    ),
    Property(
        "weather_binding",
        16,
        1,
        "Weather sensor association",
        kind="string",
        advanced=True,
    ),
    Property(
        "stop_audio",
        9,
        4,
        "Stop native audio",
        maximum=1,
        writable=True,
        read=False,
        choices=(1,),
    ),
    Property(
        "stop_alarm_preview",
        3,
        28,
        "Stop alarm preview",
        kind="bool",
        writable=True,
        read=False,
    ),
]
for index in range(6):
    PROPERTIES.append(
        Property(
            f"custom_guard_{index + 1}",
            3,
            index + 3,
            f"Custom guard {index + 1}",
            platform="switch",
            maximum=1,
            writable=True,
            advanced=True,
        )
    )
for index, mode in enumerate(("basic", "home", "away", "sleep")):
    for offset, suffix, name, maximum, step, unit in (
        (9, "delay", "delay", 60, 5, "s"),
        (10, "duration", "alarm duration", 2147483647, 1, "s"),
        (11, "volume", "alarm volume", 100, 1, "%"),
    ):
        PROPERTIES.append(
            Property(
                f"{mode}_{suffix}",
                3,
                offset + index * 3,
                f"{mode.capitalize()} {name}",
                platform="number",
                maximum=maximum,
                step=step,
                unit=unit,
                writable=True,
            )
        )
    PROPERTIES.append(
        Property(
            f"{mode}_sound",
            3,
            24 + index,
            f"{mode.capitalize()} alarm sound",
            kind="string",
            platform="select",
            writable=True,
        )
    )

BY_KEY = {prop.key: prop for prop in PROPERTIES}
READ_PROPERTIES = tuple(prop for prop in PROPERTIES if prop.read)
READ_KEYS = tuple(prop.key for prop in READ_PROPERTIES)
GUARD_CHOICES = ("0", "1", "2", "3")


def catalogs(values):
    sounds = {}
    languages = ()
    try:
        data = json.loads(values.get("audio_catalog", ""))
        if isinstance(data, dict):
            for family in ("alarm", "doorbell", "welcome"):
                options = data.get(family)
                if isinstance(options, list) and len(options) <= 128:
                    sounds[family] = tuple(
                        x
                        for x in options
                        if isinstance(x, str)
                        and re.fullmatch(r"[A-Za-z0-9_. -]{1,80}", x)
                    )
    except (ValueError, TypeError):
        pass
    try:
        data = json.loads(values.get("language_catalog", ""))
        if isinstance(data, dict) and isinstance(data.get("language"), list):
            languages = tuple(
                x
                for x in data["language"]
                if isinstance(x, str) and re.fullmatch(r"[a-z]{2}(?:-[A-Za-z]{2})?", x)
            )
    except (ValueError, TypeError):
        pass
    return sounds, languages


def options_for(key, values):
    if key == "guard_mode":
        # Keep native numeric modes explicit; 0 is not a promise of full disarming.
        return list(GUARD_CHOICES)
    sounds, languages = catalogs(values)
    if key == "system_language":
        return list(languages)
    return list(sounds.get("alarm", ())) if key.endswith("_sound") else []


def validate_write(key, value, values):
    prop = BY_KEY[key]
    prop.validate(value, writing=True)
    if prop.platform == "select" and str(value) not in options_for(key, values):
        raise ValueError("Choice not present in the current native catalog")
    return prop, value
