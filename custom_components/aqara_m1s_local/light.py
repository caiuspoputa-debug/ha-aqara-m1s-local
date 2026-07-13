from __future__ import annotations

import json
import time

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
)

from .const import (
    DATA_MQTT_CLIENTS,
    DOMAIN,
    MQTT_TOPIC_RGB,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    mqtt_client = hass.data[DOMAIN][
        DATA_MQTT_CLIENTS
    ][entry.entry_id]
    async_add_entities(
        [AqaraM1SRingLight(entry, mqtt_client)]
    )


class AqaraM1SRingLight(LightEntity):
    _attr_name = "Ring Light"
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        mqtt_client,
    ) -> None:
        self.entry = entry
        self.mqtt_client = mqtt_client

        self._attr_unique_id = (
            f"{entry.entry_id}_ring_light"
        )
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_available = (
            mqtt_client.connected
        )
        self._attr_device_info = {
            "identifiers": {
                (DOMAIN, mqtt_client.host)
            },
            "name": entry.data.get(
                "name",
                (
                    "Aqara M1S "
                    f"{mqtt_client.host}"
                ),
            ),
            "manufacturer": "Aqara",
            "model": "M1S",
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.mqtt_client.add_message_listener(
                self._handle_mqtt_message
            )
        )
        self.async_on_remove(
            self.mqtt_client.add_status_listener(
                self._handle_status
            )
        )

    async def async_turn_on(self, **kwargs) -> None:
        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = tuple(
                int(value)
                for value in kwargs[
                    ATTR_RGB_COLOR
                ]
            )

        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = int(
                kwargs[ATTR_BRIGHTNESS]
            )
        elif (
            not self._attr_is_on
            and self._attr_brightness == 0
        ):
            self._attr_brightness = 255

        self._attr_is_on = True
        transition_ms = int(
            float(
                kwargs.get(
                    ATTR_TRANSITION,
                    0.5,
                )
            )
            * 1000
        )
        await self._publish_rgb(
            transition_ms
        )
        self.async_write_ha_state()

    async def async_turn_off(
        self,
        **kwargs,
    ) -> None:
        self._attr_is_on = False
        transition_ms = int(
            float(
                kwargs.get(
                    ATTR_TRANSITION,
                    0.5,
                )
            )
            * 1000
        )
        await self._publish_raw_rgb(
            0,
            0,
            0,
            transition_ms,
        )
        self.async_write_ha_state()

    async def _publish_rgb(
        self,
        transition_ms: int = 500,
    ) -> None:
        brightness = max(
            0,
            min(
                255,
                int(
                    self._attr_brightness
                    if self._attr_brightness
                    is not None
                    else 255
                ),
            ),
        )
        red, green, blue = (
            self._attr_rgb_color
            or (255, 255, 255)
        )

        await self._publish_raw_rgb(
            round(red * brightness / 255),
            round(green * brightness / 255),
            round(blue * brightness / 255),
            transition_ms,
        )

    async def _publish_raw_rgb(
        self,
        red: int,
        green: int,
        blue: int,
        transition_ms: int,
    ) -> None:
        payload = {
            "cmd": "control",
            "data": {
                "blue": max(
                    0,
                    min(255, int(blue)),
                ),
                "breath": max(
                    0,
                    min(
                        60000,
                        int(transition_ms),
                    ),
                ),
                "green": max(
                    0,
                    min(255, int(green)),
                ),
                "red": max(
                    0,
                    min(255, int(red)),
                ),
            },
            "id": (
                int(time.time() * 1000)
                & 0x7FFFFFFF
            ),
            "type": "rgb",
            "ver": 1,
        }
        await self.mqtt_client.publish_json(
            MQTT_TOPIC_RGB,
            payload,
        )

    def _handle_status(
        self,
        connected: bool,
    ) -> None:
        self._attr_available = connected
        self.async_write_ha_state()

    def _handle_mqtt_message(
        self,
        topic: str,
        raw_payload: bytes,
    ) -> None:
        if topic != MQTT_TOPIC_RGB:
            return

        try:
            payload = json.loads(
                raw_payload.decode("utf-8")
            )
            if payload.get("type") != "rgb":
                return
            data = payload.get("data") or {}
            red = int(data.get("red", 0))
            green = int(
                data.get("green", 0)
            )
            blue = int(data.get("blue", 0))
        except (
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            return

        maximum = max(red, green, blue)
        self._attr_is_on = maximum > 0

        if maximum > 0:
            self._attr_brightness = maximum
            self._attr_rgb_color = (
                round(red * 255 / maximum),
                round(green * 255 / maximum),
                round(blue * 255 / maximum),
            )

        self.async_write_ha_state()
