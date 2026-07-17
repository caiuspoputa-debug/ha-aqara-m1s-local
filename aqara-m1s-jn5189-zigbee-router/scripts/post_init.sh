#!/bin/sh
LOG_FILE="/tmp/post_init.log"
log_message(){ echo "$(date) $1" >> "$LOG_FILE"; }
wait_for_wifi(){
 i=0
 while [ "$i" -lt 120 ]; do
  IP="$(ifconfig wlan0 2>/dev/null | grep 'inet addr')"
  [ "$IP" != "" ] && return 0
  sleep 2
  i=$((i+2))
 done
 return 1
}
fw_manager.sh -r &
(
 sleep 15
 i=0
 while [ "$i" -lt 12 ]; do
  killall -9 app_monitor.sh 2>/dev/null
  killall -9 mzigbee_agent 2>/dev/null
  sleep 5
  i=$((i+1))
 done
 log_message "Stopped app_monitor.sh and mzigbee_agent; JN5189 remains a Zigbee router."
) &
(
 if wait_for_wifi; then
  sleep 5
  fw_manager.sh -t -k &
  log_message "Telnet enabled after Wi-Fi became available."
 else
  fw_manager.sh -t -k &
  log_message "Wi-Fi timeout; Telnet start attempted anyway."
 fi
) &
exit 0
