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
mkdir -p maps

echo Nebcloud! | sudo -S ./play_51422_candump_can0_to_vcan0.sh

echo "setting up can interface"
echo Nebcloud! | sudo -S ip link set vcan0 type vcan bitrate 250000
sudo ip link set up vcan0

printf "python3 evms.py vcan0 usb\n\n"
sudo python3 evms.py vcan0 usb

