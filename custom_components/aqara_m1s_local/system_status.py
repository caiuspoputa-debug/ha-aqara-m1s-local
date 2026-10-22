"""Small fixed read-only system snapshot; no addresses, routes or credentials."""

import math

COMMAND = r"""
printf 'uptime '; cut -d ' ' -f 1 /proc/uptime
printf 'load_1m '; cut -d ' ' -f 1 /proc/loadavg
awk '/^MemTotal:/ {t=$2} /^MemAvailable:/ {a=$2; found=1} END {if(t>0 && found) printf "memory_used_pct %.2f\n",100*(t-a)/t}' /proc/meminfo
for p in ha_basis mzigbee_agent miio_client; do
  if pidof "$p" >/dev/null 2>&1; then printf '%s_present 1\n' "$p"; else printf '%s_present 0\n' "$p"; fi
done
printf 'wifi_operstate '; cat /sys/class/net/wlan0/operstate 2>/dev/null || printf 'unknown\n'
printf 'wifi_carrier '; cat /sys/class/net/wlan0/carrier 2>/dev/null || printf 'unknown\n'
"""
NUMBERS = {"uptime": (0, 1e10), "load_1m": (0, 1000), "memory_used_pct": (0, 100)}
PRESENCE = ("ha_basis_present", "mzigbee_agent_present", "miio_client_present")


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
