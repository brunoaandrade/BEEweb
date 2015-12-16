# coding=utf-8
from __future__ import absolute_import

import os
from octoprint.server.util.iwlistparse import get_ssid_list

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.server.api import api
from octoprint.server import printer, NO_CONTENT
from flask import Blueprint, jsonify, request, make_response

WIFI_CMODE_SCRIPT = 'wifi_client_mode.sh'

#~~ BVC custom API
api = Blueprint("beeapi", __name__)

@api.route("/printer", methods=["GET"])
def getConnectedPrinter():

	if printer is not None:
		printer_name = printer.get_printer_name()
	else:
		printer_name = ''

	return jsonify({
		"printer": printer_name
	})

@api.route("/wifi/list", methods=["GET"])
def getAvailableHotspots():

	networks = get_ssid_list('wlan0', '/Users/dpacheco/Desktop/iwlist_scan.txt')

	return jsonify({
		"wifi_networks": networks
	})


@api.route("/wifi/connect", methods=["POST"])
def connectNetwork():

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	data = request.json

	# writes the wpa_supplicant configuration file
	import re
	regex_net = re.compile(r'ssid=".+"', re.IGNORECASE)
	regex_pass = re.compile(r'psk=".+"', re.IGNORECASE)

	lines = []
	with open('/etc/wpa_supplicant/wpa_supplicant.conf') as infile:
		for line in infile:
			if 'ssid' in line:
				line = regex_net.sub('ssid="%s"' % data['network'], line)
			if 'psk' in line:
				line = regex_pass.sub('psk="%s"' % data['password'], line)

			lines.append(line)

	from os.path import expanduser
	home = expanduser("~")
	with open(home + '/wpa_supplicant_update.conf', 'w') as outfile:
		for line in lines:
			outfile.write(line)

	# Executes the shell script to change the wi-fi mode
	import os.path
	script_path = home + '/' + WIFI_CMODE_SCRIPT
	if os.path.isfile(script_path):
		try:
			import subprocess
			subprocess.call([script_path])
		except:
			print ('Error executing wi-fi client mode script.')

	return NO_CONTENT


