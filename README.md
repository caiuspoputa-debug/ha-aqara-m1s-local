# Aqara M1S Local

Home Assistant custom integration for local Aqara M1S audio control over a root Telnet shell.

## Stable version

This version intentionally keeps the same stable architecture as v0.1: **button platform only**.
No `select`, no `text`, no options flow. This avoids breaking the config entry.

## Features

- UI config flow for multiple hubs
- Built-in sound buttons
- Button for `/local/test.wav`
- Services for `play_url`, `play_builtin`, and `run_command`

## Hub requirement

On the Aqara M1S hub, start a no-login shell on port 2323:

```sh
telnetd -p 2323 -l /bin/sh
```

## Audio URL example

Put a WAV file in Home Assistant:

```text
/config/www/test.wav
```

Use URL:

```text
http://HA_IP:8123/local/test.wav
```

Then call service:

```yaml
service: aqara_m1s_local.play_url
data:
  url: "http://HA_IP:8123/local/test.wav"
```

## Built-in sound examples

```yaml
service: aqara_m1s_local.play_builtin
data:
  sound: bell
```

```yaml
service: aqara_m1s_local.play_builtin
data:
  sound: /data/musics/music-scene/alarm.wav
```
