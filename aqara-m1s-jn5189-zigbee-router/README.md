# Aqara M1S Gen 1 JN5189 Zigbee Router

Conversie experimentală a unui **Aqara Hub M1S Gen 1** (`lumi.gateway.aeu01`) din coordinator Aqara într-un **Zigbee Router** pentru o rețea existentă Zigbee2MQTT.

- [Documentație română](docs/ro/README.md)
- [English documentation](docs/en/README.md)

## Rezultat confirmat

- JN5189 rulează firmware NXP BDB Router.
- Routerul se alătură automat unei rețele Zigbee2MQTT.
- Scanarea nu este limitată la un singur canal.
- Nodul apare ca `Lumi United Technology Co., Ltd / BDB-Router`.
- Linux, Wi-Fi, HomeKit și sunetele hubului rămân funcționale.
- Rolul original de coordinator Aqara este pierdut.
- Controlul original al inelului RGB nu mai este disponibil.
- `mzigbee_agent` și `app_monitor.sh` sunt oprite persistent.

## Hardware testat

- Aqara Hub M1S Gen 1
- Model: `lumi.gateway.aeu01`
- Zigbee SoC: NXP JN5189
- UART: `/dev/ttyS1`
- GPIO reset: `18`
- GPIO ISP: `33`

## Firmware

Binarul compilat local trebuie copiat manual în:

```text
firmware/jn5189dk6_zigbee_router_bm.bin
```

Binarul nu este inclus în această arhivă deoarece se află pe PC-ul utilizatorului și trebuie verificată separat licența NXP înainte de redistribuire.

## Avertisment

Procedura poate bloca JN5189 și poate elimina definitiv funcțiile Zigbee originale ale hubului. Nu continuați fără backup și acces Telnet persistent.
