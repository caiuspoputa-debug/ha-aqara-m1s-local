# Aqara M1S Local

## v0.3.4

Stable playback cleanup:

- Uses `aplay -x 1` everywhere, so each WAV plays once.
- Creates one Play button for every WAV found under `/data/musics`.
- Keeps `select.sound` plus `Play Selected Sound`.
- Removes the misleading local playback volume slider.
- Removes `setprop persist.sys.volume` from local WAV playback.

Important volume note:

Local WAV playback uses direct `aplay`, which bypasses the Aqara/HomeKit audio backend.
That means HomeKit volume and `persist.sys.volume` do not affect these local sounds.
For local custom WAVs, volume must be controlled by lowering the WAV file amplitude.

Use HomeKit for light, official volume and alarm control.
Use Aqara M1S Local for local WAV playback and diagnostics.
