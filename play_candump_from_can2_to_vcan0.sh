

sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
./play.sh candump-2021-10-27_180441.txt can2

./evms.sh # no argument used for simulation (can data playing on vcan0)

