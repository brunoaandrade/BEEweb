# coding=utf-8
from __future__ import absolute_import

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
from octoprint.server.util.iwlistparse import get_ssid_list
from octoprint.server.util.hostname_util import is_valid_hostname, update_hostname
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

	networks = get_ssid_list('wlan0', '/Users/dpacheco/Desktop/wlist_scan.txt')

	return jsonify({
		"wifi_networks": networks
	})


@api.route("/netconfig/save", methods=["POST"])
def saveNetworkConfig():

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	data = request.json
	network_name = data['network']
	new_hostname = data['hostname']
	password = data['password']

	# validates input data
	if network_name is None:
		return make_response("Invalid network name parameter.", 406)

	if not new_hostname or not is_valid_hostname(new_hostname):
		return make_response("Invalid hostname parameter.", 406)

	# writes the wpa_supplicant configuration file
	import re
	regex_net = re.compile(r'ssid=".+"', re.IGNORECASE)
	regex_pass = re.compile(r'psk=".+"', re.IGNORECASE)

	lines = []
	with open('/etc/wpa_supplicant/wpa_supplicant.conf.dist') as infile:
		for line in infile:
			if 'ssid' in line:
				line = regex_net.sub('ssid="%s"' % network_name, line)
			if 'psk' in line:
				line = regex_pass.sub('psk="%s"' % password, line)

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

	# Updates the hostname
	# NOTE: This operation is done last because it will force the server to reboot
	update_hostname(new_hostname)

	return NO_CONTENT


