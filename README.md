# Aqara M1S Local

## v0.3.2

- Creates one Play button for every WAV found under `/data/musics`
- Keeps `select.sound` + `Play Selected Sound`
- Adds `number.local_playback_volume`
- All local playback uses `setprop persist.sys.volume <value>` before `aplay`
- Services `play_url` and `play_sound` now accept optional `volume`

Light, official volume and alarm stay via HomeKit.
