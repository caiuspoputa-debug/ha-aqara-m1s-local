# Aqara M1S Local v0.5.1

Maintenance release for HACS installation.

## Changes

- Keeps the `media_player` functionality introduced in v0.5.0.
- Sets the integration version to `0.5.1`.
- Enables HACS ZIP release installation with:
  - `zip_release: true`
  - `filename: aqara_m1s_local_v0_5_1.zip`
- Ensures the HACS filename matches the GitHub release asset exactly.

## HACS release requirements

Create the GitHub release with:

- Tag: `v0.5.1`
- Asset: `aqara_m1s_local_v0_5_1.zip`


## v0.5.0

Adds an Aqara M1S **Radio** media player entity.

- Appears as `media_player` target in Home Assistant Media Browser.
- Resolves Home Assistant media-source items, including Radio Browser stations.
- Streams internet radio through Home Assistant FFmpeg to the hub over local TCP.
- Supports Play, Stop, Turn Off, Volume Set, and Mute.
- Uses a dedicated TCP port (`12346`) and does not interfere with MQTT port `1884`.
- Starts and stops only the dedicated radio `nc` and `aplay` processes on the hub.
- Volume changes are applied by restarting the FFmpeg stream, causing a short reconnect gap.

Home Assistant OS and Container include FFmpeg. Other installation methods must provide FFmpeg in PATH.
## v0.4.6

Reducere suplimentară a întârzierii la comenzile Telnet.

- Menține o sesiune Telnet autentificată și persistentă pentru fiecare hub.
- Nu mai reconectează și autentifică la fiecare apăsare de buton.
- Serializează comenzile pentru a evita suprapunerea lor.
- Se reconectează automat o dată dacă hubul închide sesiunea.
- Închide conexiunea curat când integrarea este descărcată.
- Păstrează redarea rapidă prin link simbolic și ruta oficială `basis_cli`.


## v0.4.5

Corecție de performanță pentru redarea sunetelor.

- Înlocuiește copierea WAV-ului cu un link simbolic rapid:
  `ln -sf <sunet> /data/musics/music-scene/door_bell_99.wav`
- Elimină întârzierea mare dintre apăsarea butonului și pornirea sunetului.
- Păstrează redarea oficială prin `basis_cli`, `system_sing` și `mha_basis`.
- Toate sunetele continuă să respecte sliderul `Sound Playback Volume`.


## v0.4.4

Corecție pentru `Sound Playback Volume`.

- Repară `KeyError: 'playback_volume'`.
- Inițializează starea comună indiferent de ordinea de încărcare a platformelor.
- Butoanele folosesc implicit volumul 50 până când sliderul este restaurat.
- Păstrează redarea tuturor WAV-urilor prin `door_bell_99.wav` și `mha_basis`.


## v0.4.3

Această versiune mută **toate sunetele** pe ruta audio oficială
`mha_basis`, inclusiv fișierele din `music-ch`, `music-us`, `music-scene`
și sunetele personalizate.

### Control nou de volum

Integrarea adaugă entitatea:

```text
number.aqara_m1s_local_sound_playback_volume
```

Numele afișat este:

```text
Sound Playback Volume
```

Scala este `1–100`. Valoarea aleasă este folosită de toate butoanele de
sunet și este restaurată după repornirea Home Assistant.

### Cum funcționează

La apăsarea oricărui buton:

1. WAV-ul selectat este copiat temporar în slotul rezervat:

   ```text
   /data/musics/music-scene/door_bell_99.wav
   ```

2. Este redat prin:

   ```text
   /bin/basis_cli -sys -s doorbell 99 0 <volum>
   ```

3. Redarea trece prin `basis.system / system_sing` și `mha_basis`, nu prin
   `aplay`.

Prin urmare, toate sunetele respectă sliderul de volum al integrării.

### Compatibilitate

Sunt suportate:

- toate sunetele chinezești;
- toate sunetele americane;
- toate sunetele `music-scene`;
- `Play Selected Sound`;
- WAV-uri personalizate detectate sub `/data/musics`.

Slotul `door_bell_99.wav` este rezervat integrării și este suprascris la
fiecare redare.


## v0.4.2

This release fixes scene-sound playback so supported files use Aqara's
official `mha_basis` audio route instead of direct `aplay`.

### Official-volume scene playback

The following filename patterns now respect the hub's current official
volume (`persist.sys.volume`, 1-100):

```text
/data/musics/music-scene/door_bell_N.wav
/data/musics/music-scene/welcome_N.wav
/data/musics/music-scene/alarm_N.wav
```

They are played through:

```text
/bin/basis_cli -sys -s <doorbell|welcome|alarm> <index> 0 <volume>
```

This reaches `basis.system / system_sing` in `mha_basis`, which is the same
audio path used by the hub's official volume confirmation.

Examples:

```text
door_bell_1.wav -> basis_cli -sys -s doorbell 1 0 <current volume>
welcome_4.wav   -> basis_cli -sys -s welcome 4 0 <current volume>
alarm_3.wav     -> basis_cli -sys -s alarm 3 0 <current volume>
```

The volume is read at button-press time, so a HomeKit or Aqara volume change
is applied immediately to the next sound.

### Compatibility fallback

Other files, including `music-us`, `music-ch`, and scene filenames without a
confirmed `system_sing` mapping, continue using direct `aplay`. They remain
functional but do not yet follow the hub's official volume.

Each sound button now exposes diagnostic attributes:

```text
playback_route
respects_hub_volume
file_path
```

To use custom content while keeping official volume control, replace the
contents of a supported `door_bell_N.wav`, `welcome_N.wav`, or `alarm_N.wav`
file while keeping its recognized filename.


# Aqara M1S Local

## v0.4.1

This release fixes MQTT entity availability after startup and extends the existing integration. It does **not** require
HomeKit for the new MQTT features.

### Added

- `light.ring_light`
  - On/off
  - RGB color
  - Brightness implemented by scaling RGB values
  - Transition mapped to the hub's `breath` field
  - Publishes directly to the hub topic `ioctl/recv`
- `sensor.illuminance_raw`
  - Reads gateway resource `0.3.85` from `zigbee/send`
  - The raw scale reacts to ambient light, but it has not yet been
    calibrated or proven to be physical lux
- Configurable MQTT tunnel port, default `1884`
- Automatic MQTT reconnect
- Wi-Fi IP parser fixed so it returns the address rather than the shell
  command text

### Existing features retained

- Telnet diagnostics
- One button per WAV under `/data/musics`
- Selected-sound playback
- Temperature, uptime, process and stored-volume sensors
- Services for WAV playback and shell commands

## Important volume status

`Volume Property` remains a read-only sensor.

We confirmed the official live-volume path:

```text
set_properties: siid=5, piid=2
-> mha_master
-> basis.system / system_volume
-> mha_basis
```

However, this integration does not yet have an independent, proven and
safe transport into that internal agent path. `setprop
persist.sys.volume` only changes stored state and is not presented as a
working live-volume control.

## Hub prerequisites

The hub must already provide:

- Telnet on port `23`
- The local one-client MQTT tunnel on port `1884`
- Internal Mosquitto on `127.0.0.1:1883`

The tunnel accepts **one LAN MQTT client at a time**. Stop manual Paho,
MQTT Explorer or command-line subscribers before reloading this
integration, otherwise Home Assistant cannot own the tunnel connection.

## Upgrade

Copy:

```text
custom_components/aqara_m1s_local
```

over the existing folder, restart Home Assistant, then reload the
integration.

Existing config entries use MQTT port `1884` automatically. A new entry
also shows the MQTT port in the setup form.

## First test

1. Stop any manual subscriber connected to hub port `1884`.
2. Restart Home Assistant.
3. Open the Aqara M1S device.
4. Test `Ring Light` with a low brightness and a simple RGB color.
5. Cover and uncover the hub to verify `Illuminance Raw` changes.

## Confirmed protocol mappings

```text
MQTT LED command topic: ioctl/recv
MQTT gateway reports:   zigbee/send
Gateway illumination:   did=lumi.0, res_name=0.3.85
```

RGB command example:

```json
{
  "cmd": "control",
  "data": {
    "blue": 80,
    "breath": 500,
    "green": 105,
    "red": 245
  },
  "id": 50001,
  "type": "rgb",
  "ver": 1
}
```
