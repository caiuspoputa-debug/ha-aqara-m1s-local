from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_CLIENTS


@dataclass
class SensorDef:
    key: str
    name: str
    command: str
    parser: Callable[[str], str | int | float | None]
    unit: str | None = None
    device_class: str | None = None


def last_number(text: str):
    nums = []
    for part in text.replace("\r", "\n").split():
        try:
            nums.append(float(part))
        except Exception:
            pass
    return nums[-1] if nums else None


def first_clean_line(text: str):
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "__M1S_DONE__", "echo ")):
            return line
    return None


SENSORS = [
    SensorDef("temperature", "Temperature", "getprop persist.sys.temperature", last_number, UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    SensorDef("volume", "Volume Property", "getprop persist.sys.volume", last_number, PERCENTAGE, None),
    SensorDef("uptime", "Uptime Seconds", "cat /proc/uptime | cut -d ' ' -f1", last_number, "s", None),
    SensorDef("wifi_ip", "WiFi IP", "ifconfig wlan0 | grep 'inet addr' | cut -d: -f2 | awk '{print $1}'", first_clean_line, None, None),
    SensorDef("homekit_process", "HomeKit Process", "ps w | grep homekitserver | grep -v grep", lambda t: "running" if "homekitserver" in t else "stopped", None, None),
    SensorDef("zigbee_process", "Zigbee Process", "ps w | grep mzigbee_agent | grep -v grep", lambda t: "running" if "mzigbee_agent" in t else "stopped", None, None),
    SensorDef("mqtt_process", "MQTT Process", "ps w | grep mosquitto | grep -v grep", lambda t: "running" if "mosquitto" in t else "stopped", None, None),
    SensorDef("telnet_process", "Telnet Process", "ps w | grep telnetd | grep -v grep", lambda t: "running" if "telnetd" in t else "stopped", None, None),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    client = hass.data[DOMAIN][DATA_CLIENTS][entry.entry_id]
    async_add_entities([AqaraM1SSensor(hass, entry, client, sensor) for sensor in SENSORS], True)


class AqaraM1SSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client, sensor: SensorDef):
        self.hass = hass
        self.entry = entry
        self.client = client
        self.sensor = sensor
        self._attr_name = sensor.name
        self._attr_unique_id = f"{entry.entry_id}_{sensor.key}"
        self._attr_native_unit_of_measurement = sensor.unit
        self._attr_device_class = sensor.device_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.client.host)},
            "name": entry.data.get("name", f"Aqara M1S {self.client.host}"),
            "manufacturer": "Aqara",
            "model": "M1S",
        }

    async def async_update(self):
        try:
            output = await self.hass.async_add_executor_job(self.client.run_command, self.sensor.command)
            self._attr_native_value = self.sensor.parser(output)
        except Exception as exc:
            self._attr_native_value = None
            self._attr_available = False
            return
        self._attr_available = True
