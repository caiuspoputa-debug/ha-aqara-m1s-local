# Aqara M1S Local

## v0.3.3

- Fixes local playback repeating 3 times.
- All local playback now uses `aplay -x 1`.
- Keeps one Play button for every WAV found under `/data/musics`.
- Keeps `select.sound` + `Play Selected Sound`.
- Keeps `number.local_playback_volume`, but note: firmware `aplay` may not fully obey volume on all hubs.

Light, official volume and alarm stay via HomeKit.
