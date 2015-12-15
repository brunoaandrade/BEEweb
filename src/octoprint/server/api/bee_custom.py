# coding=utf-8
from __future__ import absolute_import

import time
from octoprint.server.util.iwlistparse import get_ssid_list

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.server.api import api
from octoprint.server import printer, NO_CONTENT
from flask import Blueprint, jsonify

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

	return NO_CONTENT


