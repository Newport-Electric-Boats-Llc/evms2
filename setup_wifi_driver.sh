#https://www.geeksforgeeks.org/installing-realtek-rtl8821ce-driver-to-use-the-wireless-network-interface-in-ubuntu/

echo "SETUP for the rtl8821ce Wi-Fi Driver on the BMAX SBC"
echo "be sure to run this script with SUDO"
read -n 1 -p "Press any key to continue:" VAR


cd /home/neb/Downloads/

sudo apt update
sudo apt install git build-essential dkms


git clone https://github.com/tomaspinho/rtl8821ce
cd rtl8821ce
chmod +x dkms-install.sh
chmod +x dkms-remove.sh
sudo ./dkms-install.sh

