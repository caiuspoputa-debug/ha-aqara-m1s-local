# Conversie Aqara M1S Gen 1 în Zigbee Router — ghid complet

## 1. Scop

Folosirea cipului NXP JN5189 din Aqara Hub M1S Gen 1 ca **router Zigbee**, nu ca coordinator. Routerul se alătură unei rețele existente coordonate de Zigbee2MQTT.

## 2. Configurația testată

| Element | Valoare |
|---|---|
| Hub | Aqara M1S Gen 1 |
| Model | `lumi.gateway.aeu01` |
| IP din test | `192.168.0.104` |
| SoC Zigbee | NXP JN5189 |
| UART | `/dev/ttyS1` |
| GPIO reset | `18` |
| GPIO ISP | `33` |
| SDK | `SDK_2_6_16_JN5189DK6.zip` |
| IDE | MCUXpresso IDE 25.6.136 |
| Proiect | `jn5189dk6_zigbee_router_bm` |
| Coordinator țintă | Zigbee2MQTT |
| Canal testat | 24 |

Adresele IP sunt exemple și trebuie adaptate.

## 3. Ce s-a păstrat

- Linux-ul hubului;
- Wi-Fi;
- Telnet persistent;
- HomeKit;
- sunetele;
- funcția de router Zigbee;
- asocierea automată cu Zigbee2MQTT.

## 4. Ce s-a pierdut sau schimbat

- rolul de coordinator Aqara;
- dispozitivele din vechea rețea Aqara;
- protocolul original dintre `mzigbee_agent` și coordinator;
- controlul original al inelului RGB, gestionat de firmware-ul Zigbee original.

## 5. Acces Telnet persistent

Fișierul final este inclus în `scripts/post_init.sh` și instalat pe hub în:

```text
/data/scripts/post_init.sh
```

Scriptul pornește serviciile normale, așteaptă Wi-Fi, activează Telnet și oprește repetat `app_monitor.sh` și `mzigbee_agent` pentru a nu ocupa UART-ul JN5189.

## 6. Identificarea hardware

Configurația Aqara observată:

```text
chip : jn5189
nxp_uart : /dev/ttyS1
dataPath : /data/zigbee/
pinReset : 18,hight,out
pinIsp : 33,low,out
```

Stările normale observate:

```text
gpio18 = 0
gpio33 = 1
```

## 7. Backup obligatoriu

Copiați cel puțin:

```text
/bin/mzigbee_agent
/bin/zigbee_msnger
/etc/mzigbeeAgent.conf
/data/zigbee/coordinator.info
/data/zigbee/networkBak.info
```

Nu publicați tokenul MiIO, cheia rețelei Zigbee, secrete HomeKit, parole sau certificate private.

## 8. Mediul de dezvoltare

Folosiți SDK-ul NXP care conține Wireless/Zigbee pentru JN5189:

```text
SDK_2_6_16_JN5189DK6.zip
```

Importați exemplul:

```text
wireless_examples → zigbee_router
```

Proiectul rezultat:

```text
jn5189dk6_zigbee_router_bm
```

Dacă build-ul eșuează cu `No module named lxml`:

```cmd
python -m pip install lxml pycryptodome
```

## 9. Eliminarea limitării de canal

În:

```text
Project Properties → C/C++ Build → Settings
→ MCU C Compiler → Preprocessor → Defined symbols
```

ștergeți:

```text
SINGLE_CHANNEL=12
```

În `router.zpscfg`, configurația routerului activează canalele 11–26.

## 10. Asocierea automată

Exemplul NXP pornește network steering la `BDB_EVENT_INIT_SUCCESS` când starea este `E_STARTUP`, apoi reîncearcă la lipsa unei rețele sau la eșec de rejoin.

## 11. Problema PDM și remedierea

Datele persistente rămase de la firmware-ul Aqara puteau suprascrie starea de pornire. S-a adăugat o semnătură proprie în `tsDeviceDesc`.

### `app_common.h`

```c
typedef struct
{
    uint32_t       u32Magic;
    teNodeState    eNodeState;
    teNodeState    eNodePrevState;
} tsDeviceDesc;
```

### `APP_vInitialiseRouter()`

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

La prima pornire sunt șterse datele PDM incompatibile. La pornirile următoare, contextul rețelei Zigbee este păstrat. Patch-ul este în `patches/jn5189-router-pdm-magic.patch`.

## 12. Build

Executați un Clean build complet. Rezultatul valid observat:

```text
Build Finished. 0 errors, 0 warnings.
```

Fișierul folosit:

```text
zigbee_ota_build/jn5189dk6_zigbee_router_bm.bin
```

Nu s-au folosit imaginile Zigbee OTA criptate `*.ota`.

## 13. De ce BIN brut

`mzigbee_agent` conține suport ISP pentru JN5189 și mesajul intern:

```text
Firmware file not recognised as valid image - programming raw
```

Acest lucru indică suport pentru programarea unei imagini binare brute.

## 14. Transferul pe hub

Pe PC:

```cmd
cd /d "C:\cale\catre\jn5189dk6_zigbee_router_bm\zigbee_ota_build"
py -3 -m http.server 8000 --bind 0.0.0.0
```

Pe hub:

```sh
wget -O /data/jn5189dk6_zigbee_router_bm.bin \
  http://IP_PC:8000/jn5189dk6_zigbee_router_bm.bin
```

Verificați hash-ul pe ambele sisteme:

```sh
md5sum /data/jn5189dk6_zigbee_router_bm.bin
```

```cmd
certutil -hashfile "...\jn5189dk6_zigbee_router_bm.bin" MD5
```

## 15. Flash

Înainte de flash:

- activați Permit Join;
- reporniți Zigbee2MQTT dacă ați schimbat canalul;
- porniți temporar `mzigbee_agent`;
- nu întrerupeți alimentarea.

Comanda folosită:

```sh
zigbee_msnger zgb_ota /data/jn5189dk6_zigbee_router_bm.bin
```

Succesul a fost confirmat prin progres 5–95% și mesajul final de succes.

## 16. Rezultatul în Zigbee2MQTT

```text
Manufacturer: Lumi United Technology Co., Ltd
Model: BDB-Router
Type: Router
Support: Unsupported
```

`Unsupported` nu împiedică rutarea; înseamnă doar că nu există un converter dedicat.

## 17. Persistența după reboot

După asociere, `mzigbee_agent` și `app_monitor.sh` trebuie oprite persistent.

Verificare:

```sh
ps | grep -e mzigbee_agent -e app_monitor.sh
cat /tmp/post_init.log
```

Mesaje așteptate:

```text
Telnet enabled after Wi-Fi became available.
Stopped app_monitor.sh and mzigbee_agent; JN5189 remains a Zigbee router.
```

## 18. Reset hardware JN5189

Cu agentul oprit, resetul folosit a fost:

```sh
echo 1 > /sys/class/gpio/gpio18/value
sleep 1
echo 0 > /sys/class/gpio/gpio18/value
```

## 19. Recuperare

Restaurarea coordinatorului original poate necesita o imagine Aqara `ControlBridge.bin` exact compatibilă sau un dump hardware complet. Nu există garanție de recuperare fără acestea.

## 20. Verificări finale

- hubul revine în rețea după reboot;
- Telnet funcționează;
- HomeKit și sunetele funcționează;
- JN5189 apare în Zigbee2MQTT ca Router;
- harta Zigbee arată legături către alte dispozitive;
- `mzigbee_agent` nu rulează persistent;
- `app_monitor.sh` nu rulează persistent.
