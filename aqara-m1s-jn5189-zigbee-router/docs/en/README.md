# Converting Aqara M1S Gen 1 into a Zigbee Router — complete guide

This repository documents a confirmed conversion of an **Aqara Hub M1S Gen 1** (`lumi.gateway.aeu01`) from its original Aqara coordinator firmware to an **NXP JN5189 BDB Zigbee Router** for Zigbee2MQTT.

## Tested configuration

| Item | Value |
|---|---|
| Hub | Aqara M1S Gen 1 |
| Zigbee SoC | NXP JN5189 |
| UART | `/dev/ttyS1` |
| Reset GPIO | `18` |
| ISP GPIO | `33` |
| SDK | `SDK_2_6_16_JN5189DK6.zip` |
| IDE | MCUXpresso IDE 25.6.136 |
| Example | `jn5189dk6_zigbee_router_bm` |
| Target | Zigbee2MQTT |
| Tested channel | 24 |

## Final behavior

Preserved: Linux, Wi-Fi, persistent Telnet, HomeKit, sound playback, and Zigbee routing.

Lost or changed: the original Aqara coordinator role, its old Zigbee network, and original RGB ring control. RGB was controlled by the coordinator firmware.

## Mandatory backup

Back up at least:

```text
/bin/mzigbee_agent
/bin/zigbee_msnger
/etc/mzigbeeAgent.conf
/data/zigbee/coordinator.info
/data/zigbee/networkBak.info
```

Never publish MiIO tokens, Zigbee network keys, HomeKit secrets, passwords, or private certificates.

## Build environment

Import the NXP SDK example:

```text
wireless_examples → zigbee_router
```

Install missing Python dependencies if needed:

```cmd
python -m pip install lxml pycryptodome
```

## Remove the single-channel restriction

In the project preprocessor symbols, remove:

```text
SINGLE_CHANNEL=12
```

The router configuration enables channels 11–26.

## One-time PDM compatibility reset

Old Aqara persistent data could override the NXP router startup state. Add a custom magic field:

```c
typedef struct
{
    uint32_t       u32Magic;
    teNodeState    eNodeState;
    teNodeState    eNodePrevState;
} tsDeviceDesc;
```

Then initialize, read PDM, and clear it once if the magic does not match:

```c
sDeviceDesc.u32Magic = 0;
sDeviceDesc.eNodeState = E_STARTUP;
sDeviceDesc.eNodePrevState = E_STARTUP;

PDM_eReadDataFromRecord(PDM_ID_APP_ROUTER,
                        &sDeviceDesc,
                        sizeof(tsDeviceDesc),
                        &u16ByteRead);

if (sDeviceDesc.u32Magic != 0x52545231UL)
{
    PDM_vDeleteAllDataRecords();
    sDeviceDesc.u32Magic = 0x52545231UL;
    sDeviceDesc.eNodeState = E_STARTUP;
    sDeviceDesc.eNodePrevState = E_STARTUP;
    PDM_eSaveRecordData(PDM_ID_APP_ROUTER,
                        &sDeviceDesc,
                        sizeof(tsDeviceDesc));
}
```

The patch is available in `patches/jn5189-router-pdm-magic.patch`.

## Build output

Perform a full clean build. Expected:

```text
Build Finished. 0 errors, 0 warnings.
```

Use:

```text
zigbee_ota_build/jn5189dk6_zigbee_router_bm.bin
```

## Transfer and verify

Serve the build directory:

```cmd
py -3 -m http.server 8000 --bind 0.0.0.0
```

Download on the hub:

```sh
wget -O /data/jn5189dk6_zigbee_router_bm.bin \
  http://PC_IP:8000/jn5189dk6_zigbee_router_bm.bin
```

Verify MD5 or SHA-256 on both systems before flashing.

## Flash

Enable Zigbee2MQTT Permit Join, start `mzigbee_agent` temporarily, and run:

```sh
zigbee_msnger zgb_ota /data/jn5189dk6_zigbee_router_bm.bin
```

Do not interrupt power.

## Zigbee2MQTT result

```text
Manufacturer: Lumi United Technology Co., Ltd
Model: BDB-Router
Type: Router
Support: Unsupported
```

`Unsupported` only means no dedicated converter exists; routing still works.

## Persistent service shutdown

Install `scripts/post_init.sh` as `/data/scripts/post_init.sh`. It keeps Telnet enabled and repeatedly stops `app_monitor.sh` and `mzigbee_agent` so they cannot reclaim `/dev/ttyS1`.

Expected log after reboot:

```text
Telnet enabled after Wi-Fi became available.
Stopped app_monitor.sh and mzigbee_agent; JN5189 remains a Zigbee router.
```

## Recovery warning

Restoring the original coordinator may require an exact compatible Aqara `ControlBridge.bin` or a complete hardware dump. Recovery is not guaranteed.
