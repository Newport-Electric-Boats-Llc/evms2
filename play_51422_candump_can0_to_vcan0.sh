
echo "replaying candump file..."

echo "sudo ip link add dev vcan0 type vcan"
echo "sudo ip link set up vcan0"
echo "logfile=2022-05-14_evms_gps.log can0"
echo "canplayer -I $logfile vcan0=can0"

sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
logfile=./logs/2022-05-14_evms_can.log

canplayer -I $logfile vcan0=can0


