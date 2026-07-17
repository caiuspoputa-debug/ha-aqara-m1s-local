# Depanare

## `No module named lxml`

```cmd
python -m pip install lxml pycryptodome
```

## Routerul nu apare

Verificați Permit Join, restartul Zigbee2MQTT după schimbarea canalului, eliminarea `SINGLE_CHANNEL`, patch-ul PDM și oprirea `mzigbee_agent`.

## Agentul reapare

```sh
killall -9 app_monitor.sh
killall -9 mzigbee_agent
```

## Sunetul merge, RGB nu

Comportament așteptat: sunetul este pe partea Linux, iar RGB depindea de firmware-ul coordinatorului.
