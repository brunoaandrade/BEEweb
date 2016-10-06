#!/usr/bin/env bash

sudo apt-get install -y git python2.7 python-setuptools python-dev build-essential
sudo easy_install pip

# Downloads BEEwebPi in order to install settings files
echo "Installing settings files"
if [ -f BEEwebPi ]
then
    cd BEEwebPi/
    git pull origin master
    cd ..
else
    git clone https://github.com/beeverycreative/BEEwebPi.git
fi

# copies the files to the user directory
cp -R BEEwebPi/src/filesystem/home/pi/.beeweb ~/.beeweb

# installs dependencies
python setup.py install

