#!/bin/sh
#
# Newport Electric Boats LLC
# Startup script for the EVMS 
#
#

ver="0.2.0"

echo "evms-start.sh version: $ver"
cd /home/neb/evms/

mkdir -p logs/canLogs
mkdir -p logs/gpsLogs
mkdir -p logs/systemLogs
mkdir -p logs/appLogs

#if [[ $1 = "sim" ]]; then
printf "python3 evms.py vcan0 usb"
echo Nebcloud! | sudo -S python3 evms.py vcan0 usb
#else
#  printf "python3 evms.py can0 usb"
#  echo Nebcloud! | sudo -S python3 evms.py can0 usb
#fi

