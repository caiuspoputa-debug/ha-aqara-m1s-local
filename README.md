# Aqara M1S Local

Home Assistant custom integration for local Aqara M1S audio control over a root Telnet shell.

## Features

- UI config flow for multiple hubs
- Built-in sound buttons
- Built-in sound selector
- Custom Audio URL text field
- Play Custom URL button
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

