#!/bin/bash

printf "\n\n"
printf "evms.sh version 1.23"

mkdir -p logs/canLogs
mkdir -p logs/gpsLogs
mkdir -p logs/systemLogs
mkdir -p logs/appLogs

if [[ $1 = "can0" ]]; then
  printf "setting up ip link on can0\n"
	sudo ip link set can0 type can bitrate 250000
	sudo ip link set up can0
	printf "starting evms.py can0\n"
	sudo python3 ./evms.py can0 usb # > bootlogpy.txt

elif [[ $1 = "can1" ]]; then
    printf "setting up ip link on can1\n"
	sudo ip link set can1 type can bitrate 250000
	sudo ip link set up can1
		printf "starting evms.py can1\n"
	sudo python3 ./evms.py can1

elif [[ $1 = "can2" ]]; then
    printf "setting up ip link on can2\n"
	sudo ip link set can2 type can bitrate 250000
	sudo ip link set up can2
		printf "starting evms.py can2\n"
	sudo python3 ./evms.py can2

elif [[ $1 = "link" ]]; then
  printf "setting up link for vcan0\n"
  sudo ip link add dev vcan0 type vcan
	sudo ip link set up vcan0

elif [[ $1 = 'vcan0' ]]; then
	sudo ip link add dev vcan0 type vcan
	sudo ip link set up vcan0
	sudo python3 ./evms.py vcan0 usb

elif [[ $1 = "sim" ]]; then
  printf "setting up ip link on vcan0\n"
	sudo ip link add dev vcan0 type vcan
	sudo ip link set up vcan0
	printf "starting evms.py vcan0\n"
	sudo python3 ./evms.py vcan0 $2

else
  printf "Usage: ./evms.sh <can-interface> <simulation-file>\n"
  printf "   where, \n"
  printf "      arg1 can be: can0, can1, can2, link, sim\n"
  printf "      arg2 is the filename if replaying from a previously generated systemLog file\n\n"
fi
