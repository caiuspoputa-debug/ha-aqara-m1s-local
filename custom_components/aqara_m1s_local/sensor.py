from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Callable, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
)

from .const import (
    DATA_CLIENTS,
    DATA_MQTT_CLIENTS,
    DOMAIN,
    MQTT_TOPIC_ZIGBEE,
)


@dataclass
class SensorDef:
    key: str
    name: str
    command: str
    parser: Callable[
        [str],
        str | int | float | None,
    ]
    unit: str | None = None
    device_class: str | None = None


def last_number(text: str):
    numbers = []
    for part in text.replace(
        "\r",
        "\n",
    ).split():
        try:
            numbers.append(float(part))
        except Exception:
            pass
    return numbers[-1] if numbers else None


def parse_wifi_ip(text: str):
    addresses = re.findall(
        (
            r"(?<!\d)"
            r"(?:\d{1,3}\.){3}\d{1,3}"
            r"(?!\d)"
        ),
        text,
    )
    for address in addresses:
        octets = address.split(".")
        if all(
            0 <= int(octet) <= 255
            for octet in octets
        ):
            if not address.startswith("127."):
                return address
    return None


def _coerce_number(value: Any):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def _find_illuminance_resource(
    node: Any,
    inherited_did: str | None = None,
):
    if isinstance(node, dict):
        did = node.get("did", inherited_did)

        if (
            node.get("res_name") == "0.3.85"
            and did == "lumi.0"
        ):
            return _coerce_number(
                node.get("value")
            )

        for value in node.values():
            result = _find_illuminance_resource(
                value,
                did,
            )
            if result is not None:
                return result

    elif isinstance(node, list):
        for item in node:
            result = _find_illuminance_resource(
                item,
                inherited_did,
            )
            if result is not None:
                return result

    return None


SENSORS = [
    SensorDef(
        "temperature",
        "Temperature",
        "getprop persist.sys.temperature",
        last_number,
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
    ),
    SensorDef(
        "volume",
        "Volume Property",
        "getprop persist.sys.volume",
        last_number,
        PERCENTAGE,
        None,
    ),
    SensorDef(
        "uptime",
        "Uptime Seconds",
        (
            "cat /proc/uptime "
            "| cut -d ' ' -f1"
        ),
        last_number,
        "s",
        None,
    ),
    SensorDef(
        "wifi_ip",
        "WiFi IP",
        "ifconfig wlan0 | grep 'inet addr'",
        parse_wifi_ip,
        None,
        None,
    ),
    SensorDef(
        "homekit_process",
        "HomeKit Process",
        (
            "ps w | grep homekitserver "
            "| grep -v grep"
        ),
        lambda text: (
            "running"
            if "homekitserver" in text
            else "stopped"
        ),
    ),
    SensorDef(
        "zigbee_process",
        "Zigbee Process",
        (
            "ps w | grep mzigbee_agent "
            "| grep -v grep"
        ),
        lambda text: (
            "running"
            if "mzigbee_agent" in text
            else "stopped"
        ),
    ),
    SensorDef(
        "mqtt_process",
        "MQTT Process",
        (
            "ps w | grep mosquitto "
            "| grep -v grep"
        ),
        lambda text: (
            "running"
            if "mosquitto" in text
            else "stopped"
        ),
    ),
    SensorDef(
        "telnet_process",
        "Telnet Process",
        (
            "ps w | grep telnetd "
            "| grep -v grep"
        ),
        lambda text: (
            "running"
            if "telnetd" in text
            else "stopped"
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client = hass.data[DOMAIN][DATA_CLIENTS][
        entry.entry_id
    ]
    mqtt_client = hass.data[DOMAIN][
        DATA_MQTT_CLIENTS
    ][entry.entry_id]

    entities = [
        AqaraM1SSensor(
            hass,
            entry,
            client,
            sensor,
        )
        for sensor in SENSORS
    ]
    entities.append(
        AqaraM1SIlluminanceRawSensor(
            entry,
            mqtt_client,
        )
    )
    async_add_entities(entities, True)


class AqaraM1SSensor(SensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client,
        sensor: SensorDef,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.sensor = sensor

        self._attr_name = sensor.name
        self._attr_unique_id = (
            f"{entry.entry_id}_{sensor.key}"
        )
        self._attr_native_unit_of_measurement = (
            sensor.unit
        )
        self._attr_device_class = (
            sensor.device_class
        )
        self._attr_device_info = {
            "identifiers": {
                (DOMAIN, self.client.host)
            },
            "name": entry.data.get(
                "name",
                (
                    "Aqara M1S "
                    f"{self.client.host}"
                ),
            ),
            "manufacturer": "Aqara",
            "model": "M1S",
        }

    async def async_update(self) -> None:
        try:
            output = (
                await self.hass.async_add_executor_job(
                    self.client.run_command,
                    self.sensor.command,
                )
            )
            self._attr_native_value = (
                self.sensor.parser(output)
            )
        except Exception:
            self._attr_native_value = None
            self._attr_available = False
            return

        self._attr_available = True


class AqaraM1SIlluminanceRawSensor(
    SensorEntity
):
    _attr_name = "Illuminance Raw"
    _attr_icon = "mdi:brightness-5"
    _attr_state_class = (
        SensorStateClass.MEASUREMENT
    )
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        mqtt_client,
    ) -> None:
        self.entry = entry
        self.mqtt_client = mqtt_client

        self._attr_unique_id = (
            f"{entry.entry_id}"
            "_illuminance_raw"
        )
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

    async def async_added_to_hass(
        self,
    ) -> None:
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

        self._attr_available = self.mqtt_client.connected
        self.async_write_ha_state()

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
        if topic != MQTT_TOPIC_ZIGBEE:
            return

        try:
            payload = json.loads(
                raw_payload.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return

        value = _find_illuminance_resource(
            payload
        )
        if value is None:
            return

        self._attr_native_value = value
        self.async_write_ha_state()
