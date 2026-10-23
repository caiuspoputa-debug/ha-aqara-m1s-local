"""Stock catalog discovery, restricted to native basis_cli sound families."""

import re
from dataclasses import dataclass

from .stock_protocol import integer

COMMAND = r"""
test -x /bin/basis_cli || exit 1
printf 'M1S_STOCK_CATALOG_V1\n'
/bin/busybox find /data/musics/music-scene -type f -name '*.wav'
"""
PREFIX = "/data/musics/music-scene/"
FAMILIES = {
    "doorbell": ("door_bell", 4, 1),
    "welcome": ("welcome", 10, 2),
    "alarm": ("alarm", 9, 0),
}


@dataclass(frozen=True)
class Sound:
    family: str
    index: int

    @property
    def option(self):
        return f"{self.family}/{self.index}"

    @property
    def path(self):
        return f"{PREFIX}{FAMILIES[self.family][0]}_{self.index}.wav"

    @property
    def key(self):
        # Preserve old scene-button identities, but use the native playback route.
        return "play_music_scene_" + self.path[len(PREFIX) :].replace(".", "_")

    def plan(self, volume):
        integer(volume, 1, 100)
        # Stock system_sing type 2 uses a combined bank: 1..10 are alarms,
        # 11..20 doorbells, 21..30 welcome. The public catalog stays 1-based.
        wire_index = self.index + 20 if self.family == "welcome" else self.index
        return (
            f"{FAMILIES[self.family][2]};{wire_index};0;1;{volume}",
            ("-sys", "-s", self.family, str(wire_index), "0", str(volume)),
        )


def parse_catalog(output):
    if not isinstance(output, str) or len(output) > 65536:
        raise ValueError("Invalid stock sound catalog")
    lines = output.splitlines()
    if not lines or lines[0] != "M1S_STOCK_CATALOG_V1" or len(lines) > 1025:
        raise ValueError("Missing or oversized stock catalog")
    sounds = {}
    for family, (stem, maximum, _) in FAMILIES.items():
        for index in range(1, maximum + 1):
            sound = Sound(family, index)
            if sound.path in lines[1:]:
                sounds[sound.option] = sound
    return sounds


def sound_for_option(option):
    if not isinstance(option, str):
        raise ValueError("Invalid native sound")  # noqa: TRY004
    match = re.fullmatch(r"(doorbell|welcome|alarm)/([1-9]|10)", option)
    if match is None or int(match[2]) > FAMILIES[match[1]][1]:
        raise ValueError("Unsupported native sound")
    return Sound(match[1], int(match[2]))
