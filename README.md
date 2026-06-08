# Aqara M1S Local

Home Assistant custom integration for local Aqara M1S audio control over a root Telnet shell.

## Features

- UI config flow for multiple hubs
- Built-in sound buttons
- Built-in sound selector
- Play selected sound button
- Play custom URL button
- Services for `play_url`, `play_builtin`, and `run_command`

## Hub requirement

On the Aqara M1S hub, start a no-login shell on port 2323:

```sh
telnetd -p 2323 -l /bin/sh
```

## Audio URL

Set the URL when adding the integration or via Configure/Options.

Example:

```text
http://HA_IP:8123/local/test.wav
```

## Notes

v0.2.1 removes the Home Assistant `text` entity platform to avoid setup failures on HA versions where `Platform.TEXT` is unavailable or incompatible.
