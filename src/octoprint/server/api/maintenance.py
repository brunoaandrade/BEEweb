# coding=utf-8
from __future__ import absolute_import
import re

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"

from flask import request, make_response, jsonify

from octoprint.server import printer, NO_CONTENT
from octoprint.server.util.flask import restricted_access, get_json_command_from_request
from octoprint.server.api import api


@api.route("/maintenance/start_heating", methods=["POST"])
@restricted_access
def startHeating():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	valid_commands = {
		"target": ["targets"]
	}
	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	validation_regex = re.compile("tool\d+")

	##~~ temperature
	if command == "target":
		targets = data["targets"]

		# make sure the targets are valid and the values are numbers
		validated_values = {}
		for tool, value in targets.iteritems():
			if re.match(validation_regex, tool) is None:
				return make_response("Invalid target for setting temperature: %s" % tool, 400)
			if not isinstance(value, (int, long, float)):
				return make_response("Not a number for %s: %r" % (tool, value), 400)
			validated_values[tool] = value

		# perform the actual temperature commands
		for tool in validated_values.keys():
			printer.set_temperature(tool, validated_values[tool])

	return NO_CONTENT


@api.route("/maintenance/temperature", methods=["GET"])
def getTemperature():
	current_temp = printer.get_current_temperature()
	return jsonify({
		"temperature": current_temp
	})

@api.route("/maintenance/unload", methods=["POST"])
@restricted_access
def unloadFilament():

	printer.unload()

	return NO_CONTENT

@api.route("/maintenance/load", methods=["POST"])
@restricted_access
def loadFilament():

	printer.load()

	return NO_CONTENT


@api.route("/maintenance/save_filament", methods=["POST"])
@restricted_access
def saveFilament():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	valid_commands = {
		"filament": ["filamentStr"]
	}
	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	filamentStr = data['filamentStr']

	resp = printer.setFilamentString(filamentStr)

	return jsonify({
		"response": resp
	})

@api.route("/maintenance/start_calibration", methods=["POST"])
@restricted_access
def startCalibration():

	printer.startCalibration()

	return NO_CONTENT

@api.route("/maintenance/calibration_next", methods=["POST"])
@restricted_access
def nextCalibrationStep():

	printer.nextCalibrationStep()

	return NO_CONTENT