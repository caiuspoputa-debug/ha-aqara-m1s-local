Aqara M1S Local
v0.4.1
This release fixes MQTT entity availability after startup and extends the existing integration. It does not require
HomeKit for the new MQTT features.
Added
`light.ring_light`
On/off
RGB color
Brightness implemented by scaling RGB values
Transition mapped to the hub's `breath` field
Publishes directly to the hub topic `ioctl/recv`
`sensor.illuminance_raw`
Reads gateway resource `0.3.85` from `zigbee/send`
The raw scale reacts to ambient light, but it has not yet been
calibrated or proven to be physical lux
Configurable MQTT tunnel port, default `1884`
Automatic MQTT reconnect
Wi-Fi IP parser fixed so it returns the address rather than the shell
command text
Existing features retained
Telnet diagnostics
One button per WAV under `/data/musics`
Selected-sound playback
Temperature, uptime, process and stored-volume sensors
Services for WAV playback and shell commands
Important volume status
`Volume Property` remains a read-only sensor.
We confirmed the official live-volume path:
```text
set_properties: siid=5, piid=2
-> mha_master
-> basis.system / system_volume
-> mha_basis
```
However, this integration does not yet have an independent, proven and
safe transport into that internal agent path. `setprop persist.sys.volume` only changes stored state and is not presented as a
working live-volume control.
Hub prerequisites
The hub must already provide:
Telnet on port `23`
The local one-client MQTT tunnel on port `1884`
Internal Mosquitto on `127.0.0.1:1883`
The tunnel accepts one LAN MQTT client at a time. Stop manual Paho,
MQTT Explorer or command-line subscribers before reloading this
integration, otherwise Home Assistant cannot own the tunnel connection.
Upgrade
Copy:
```text
custom_components/aqara_m1s_local
```
over the existing folder, restart Home Assistant, then reload the
integration.
Existing config entries use MQTT port `1884` automatically. A new entry
also shows the MQTT port in the setup form.
First test
Stop any manual subscriber connected to hub port `1884`.
Restart Home Assistant.
Open the Aqara M1S device.
Test `Ring Light` with a low brightness and a simple RGB color.
Cover and uncover the hub to verify `Illuminance Raw` changes.
Confirmed protocol mappings
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
