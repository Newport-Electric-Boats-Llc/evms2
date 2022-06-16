#!/bin/sh
#
# Newport Electric Boats LLC
# Startup script for the EVMS 
#
#

ver="0.4.0"

echo "evms-start.sh version: $ver"
cd /home/neb/evms2/

mkdir -p logs/canLogs
mkdir -p logs/gpsLogs
mkdir -p logs/systemLogs
mkdir -p logs/appLogs
echo "setting up can interface"
echo Nebcloud! | sudo -S ip link set can0 type can bitrate 250000
sudo ip link set up can0

printf "python3 evms.py vcan0 usb\n\n"
sudo python3 evms.py can0 usb

