#!/usr/bin/env bash

sudo apt-get install -y git python2.7 python-setuptools python-dev build-essential
sudo easy_install pip

# Downloads BEEwebPi in order to install settings files
echo "Installing settings files"
if [ ! -d BEEwebPi ]
then
    git clone https://github.com/beeverycreative/BEEwebPi.git
fi

# copies the files to the user directory
cp -R BEEwebPi/src/filesystem/home/pi/.beeweb ~/.beeweb
sudo cp BEEwebPi/src/filesystem/root/etc/init.d/beeweb /etc/init.d/
sudo cp BEEwebPi/src/filesystem/root/etc/default/beeweb /etc/default/beeweb
sudo sed -i 's/pi/vagrant/g' /etc/default/beeweb
sudo sed -i 's/\/home\/pi\/oprint\/bin\/beeweb/\/usr\/local\/bin\/beeweb/g' /etc/default/beeweb

# installs dependencies
python setup.py install

