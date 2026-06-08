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
## Tutorials

### Persistent Telnet/root

Explains how to enable persistent Telnet/root access on Aqara Hub M1S without flashing firmware, without modifying rootfs, and without breaking Wi-Fi or HomeKit.

* Romanian: [`docs/telnet_root_persistent_RO.txt`](docs/telnet_root_persistent_RO.txt)
* English: [`docs/telnet_root_persistent_EN.txt`](docs/telnet_root_persistent_EN.txt)

### Persistent Aqara Zigbee shutdown

Explains how to stop the Aqara Zigbee service permanently after boot, while keeping Telnet, HomeKit, light, sound, and MiIO services running.

Useful when the hub has no paired Zigbee devices and you want to reduce possible Zigbee noise near Zigbee2MQTT.

* Romanian: [`docs/stop_zigbee_persistent_RO.txt`](docs/stop_zigbee_persistent_RO.txt)
* English: [`docs/stop_zigbee_persistent_EN.txt`](docs/stop_zigbee_persistent_EN.txt)

### HomeKit cleanup and repair

Explains how to clean old HomeKit pairing data, restart HomeKit/mDNS, and make the hub appear again in Home Assistant as a HomeKit Device.

Use this when HomeKit pairing is broken, stuck, or the hub says it is already paired.

* Romanian: [`docs/homekit_cleanup_repair_RO.txt`](docs/homekit_cleanup_repair_RO.txt)
* English: [`docs/homekit_cleanup_repair_EN.txt`](docs/homekit_cleanup_repair_EN.txt)

### Custom WAV audio

Explains how to convert MP3/WAV files into the Aqara M1S-compatible WAV format, test playback with `aplay -x 1`, replace `arm_ok.wav`, and control local playback volume by lowering WAV amplitude.

* Romanian: [`docs/audio_wav_custom_RO.txt`](docs/audio_wav_custom_RO.txt)
* English: [`docs/audio_wav_custom_EN.txt`](docs/audio_wav_custom_EN.txt)

### HomeKit + local integration + automations architecture

Explains the final stable architecture:

* HomeKit handles light, RGB, brightness, official volume, and alarm control.

* Aqara M1S Local handles local WAV playback, `play_url`, internal sound buttons, and diagnostics.

* Zigbee can be disabled when not used.

* Home Assistant automations should preserve day/night volume logic and existing entity structure.

* Romanian: [`docs/architecture_ha_automations_RO.txt`](docs/architecture_ha_automations_RO.txt)

* English: [`docs/architecture_ha_automations_EN.txt`](docs/architecture_ha_automations_EN.txt)

