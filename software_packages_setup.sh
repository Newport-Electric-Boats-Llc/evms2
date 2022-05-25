# packages and tools as of build on March 10 2022
# to develop and run on BMAX EVMS system on
# Ubuntu 20.04.4 LTS (Focal Fossa)

# First make sure the system is up-to-date
# script version 0.1.4

sudo apt update -y
sudo apt upgrade -y

sudo apt install -y python3-serial python3-can python3-nmea2
sudo apt install -y python3-gi python3-gi-cairo
sudo apt install -y can-utils
sudo apt install -y gir1.2-gtk-3.0
#sudo apt install -y glade
sudo apt install -y numpy-stl
sudo apt install -y openssh-server
sudo apt install -y boto3
sudo apt install -y awscli
sudo apt install -y net-tools
sudo apt install -y python3-pip


#sudo pip install mpl_interactions #pan/zoom of map file..
sudo pip install python-dateutil
sudo pip install pytz
sudo pip install plotly
sudo pip install pandas
sudo pip install -U kaleido
sudo pip install boto3
sudo apt install -y lightdm



#sudo pip install pillow
#sudo apt install python-pil.imagetk
sudo apt remove update-notifier update-notifier-common


echo "disabling the upgrade notifier..."
sudo mv /etc/xdg/autostart/upg-notifier-autostart.desktop /etc/xdg/autostart/upg-notifier-autostart.desktop_disabled

echo " "
echo "wireless driver and touchscren drivers: "
echo "https://www.geeksforgeeks.org/installing-realtek-rtl8821ce-driver-to-use-the-wireless-network-interface-in-ubuntu/"
echo "Touchscreen driver available at: https://www.eeti.com/drivers_Linux.html"


#sudo apt install
#don't need these:
#python3-pandas
#python3-matplotlib









