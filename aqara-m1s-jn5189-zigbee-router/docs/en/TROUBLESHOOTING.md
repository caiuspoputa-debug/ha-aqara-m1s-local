# Troubleshooting

## `No module named lxml`

```cmd
python -m pip install lxml pycryptodome
```

## Router does not appear

Check Permit Join, restart Zigbee2MQTT after channel changes, remove `SINGLE_CHANNEL`, apply the PDM patch, and stop `mzigbee_agent`.

## Agent keeps restarting

```sh
killall -9 app_monitor.sh
killall -9 mzigbee_agent
```

## Sound works, RGB does not

Expected: sound is handled by Linux, while RGB depended on coordinator firmware.
