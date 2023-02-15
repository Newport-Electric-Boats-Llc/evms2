# Newport Electric Boats, LLC
# packages and tools used in EVMS system
# script version 0.1.4

# First make sure the system is up-to-date
sudo apt update -y
sudo apt upgrade -y

# install packages
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

#setup access to the /dev/tty* ports
sudo usermod -a -G dialout neb


sudo mv /etc/xdg/autostart/upg-notifier-autostart.desktop /etc/xdg/autostart/upg-notifier-autostart.desktop_disabled

echo "Touchscreen driver available at: https://www.eeti.com/drivers_Linux.html"


#sudo apt install
#don't need these:
#python3-pandas
#python3-matplotlib


