# coding=utf-8
from __future__ import absolute_import

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.server.util.wifi_util import get_ssid_list, switch_wifi_client_mode
from octoprint.server.util.hostname_util import is_valid_hostname, update_hostname, get_hostname
from octoprint.server.api import api
from octoprint.server import printer, NO_CONTENT
from flask import Blueprint, jsonify, request, make_response


#~~ BVC custom API
api = Blueprint("beeapi", __name__)

@api.route("/printer", methods=["GET"])
def getConnectedPrinter():

	if printer is not None:
		printer_name = printer.get_printer_name()
	else:
		printer_name = ''

	profile = printer.getCurrentProfile()

	return jsonify({
		"printer": printer_name,
		"profile": profile
	})


@api.route("/wifi/list", methods=["GET"])
def getAvailableHotspots():

	networks = get_ssid_list('wlan0')

	return jsonify({
		"wifi_networks": networks
	})

@api.route("/hostname", methods=["GET"])
def getCurrentHostname():

	hostname = get_hostname()

	return jsonify({
		"hostname": hostname
	})


@api.route("/netconfig/save", methods=["POST"])
def saveNetworkConfig():

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	data = request.json
	network_name = data['network']
	password = data['password']

	# validates input data
	if network_name is None:
		return make_response("Invalid network name parameter.", 406)

	# Tries to switch the Wifi configuration to client mode
	switch_wifi_client_mode(network_name, password)

	return NO_CONTENT

@api.route("/hostname/save", methods=["POST"])
def hostnameSave():

	if not "application/json" in request.headers["Content-Type"]:
		return make_response("Expected content-type JSON", 400)

	data = request.json
	new_hostname = data['hostname']

	if not new_hostname or not is_valid_hostname(new_hostname):
		return make_response("Invalid hostname parameter.", 406)

	# Updates the hostname
	# NOTE: This operation will force the server to reboot
	update_hostname(new_hostname)

	return NO_CONTENT


