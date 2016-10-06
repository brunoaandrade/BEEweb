#!/usr/bin/env bash

sudo apt-get install python2.7

# Downloads BEEwebPi in order to install settings files
echo "Installing settings files"
if [ -f BEEwebPi ]
then
    cd BEEwebPi/
    git pull origin master
else
    git clone https://github.com/beeverycreative/BEEwebPi.git
    cd BEEwebPi/
fi

# copies the files to the user directory
cp -R src/filesystem/home/pi/.beeweb ~/.beeweb

# installs dependencies
cd ../BEEweb
python setup.py install

