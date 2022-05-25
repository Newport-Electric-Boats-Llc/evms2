# first argument is the path to the can logfile you want to use
# second argument is the can channel (can0, can1, can2) that the can logfile uses

echo
echo "play.sh version 1.1"
echo
echo "playing back file: " $1
echo "on vcan0 interface"
echo "originally recorded on " $2 "interface"
echo

canplayer -I $1 vcan0=$2
