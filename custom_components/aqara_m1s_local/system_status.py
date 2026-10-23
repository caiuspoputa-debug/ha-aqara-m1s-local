"""Small fixed read-only system snapshot; no addresses, routes or credentials."""

import math

COMMAND = r"""
if read -r up rest < /proc/uptime; then printf 'uptime %s\n' "$up"; fi
if read -r load rest < /proc/loadavg; then printf 'load_1m %s\n' "$load"; fi
total=0; available=0; free=0; buffers=0; cached=0
while read -r key value rest; do
  case "$key" in
    MemTotal:) total=$value;; MemAvailable:) available=$value;;
    MemFree:) free=$value;; Buffers:) buffers=$value;; Cached:) cached=$value;;
  esac
done < /proc/meminfo
if [ "$available" -eq 0 ]; then available=$((free+buffers+cached)); fi
if [ "$total" -gt 0 ]; then printf 'memory_used_pct %s\n' "$((100*(total-available)/total))"; fi
basis=0; zigbee=0; miio=0; broker=0; helpers=0
test -r /proc/self/comm || exit 1
for f in /proc/[0-9]*/comm; do
  read -r name < "$f" 2>/dev/null || continue
  case "$name" in
    ha_basis|mha_basis) basis=1;; mzigbee_agent) zigbee=1;; miio_client) miio=1;;
    mosquitto) broker=1;; nc) helpers=$((helpers+1));;
  esac
done
printf 'ha_basis_present %s\nmzigbee_agent_present %s\nmiio_client_present %s\nmosquitto_present %s\nmqtt_relay_helpers %s\n' "$basis" "$zigbee" "$miio" "$broker" "$helpers"
read -r wifi < /sys/class/net/wlan0/operstate 2>/dev/null || wifi=unknown
read -r carrier < /sys/class/net/wlan0/carrier 2>/dev/null || carrier=unknown
printf 'wifi_operstate %s\nwifi_carrier %s\n' "$wifi" "$carrier"
"""
NUMBERS = {
    "uptime": (0, 1e10),
    "load_1m": (0, 1000),
    "memory_used_pct": (0, 100),
    "mqtt_relay_helpers": (0, 256),
}
PRESENCE = (
    "ha_basis_present",
    "mzigbee_agent_present",
    "miio_client_present",
    "mosquitto_present",
)


def parse_snapshot(output):
    if not isinstance(output, str) or len(output) > 4096:
        raise ValueError("Invalid system snapshot")
    result = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        key, value = parts
        if key in NUMBERS:
            try:
                number = float(value)
            except ValueError:
                continue
            low, high = NUMBERS[key]
            if math.isfinite(number) and low <= number <= high:
                result[key] = number
        elif key in PRESENCE or key == "wifi_carrier":
            if value in ("0", "1"):
                result[key] = value == "1"
        elif key == "wifi_operstate" and value in (
            "up",
            "down",
            "unknown",
            "dormant",
            "lowerlayerdown",
            "notpresent",
            "testing",
        ):
            result[key] = value
    return result
