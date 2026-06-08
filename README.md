# Aqara M1S Local

Home Assistant custom integration for Aqara Hub M1S local Telnet/root access.

## v0.3.0

Stable scope:
- Telnet port 23 with normal login
- audio buttons
- sound selector from `/data/musics/**/*.wav`
- play selected sound
- services: `play_url`, `play_sound`, `run_command`
- sensors: temperature, volume property, uptime, Wi-Fi IP, process status

Not included:
- light entity. Use HomeKit for light, brightness and RGB.
- alarm entity. Use HomeKit for alarm control.
- lux sensor is not included yet because no stable local source was found.

## Install through HACS custom repository

Repository:
`https://github.com/caiuspoputa-debug/ha-aqara-m1s-local`

Category:
`Integration`
