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

	printer.startHeating() # In the future we might pass the extruder identifier here in case of more than 1 extruder

	return NO_CONTENT

@api.route("/maintenance/cancel_heating", methods=["POST"])
@restricted_access
def cancelHeating():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	printer.cancelHeating()

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

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	printer.unload()

	return NO_CONTENT

@api.route("/maintenance/load", methods=["POST"])
@restricted_access
def loadFilament():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

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

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	printer.startCalibration()

	return NO_CONTENT

@api.route("/maintenance/calibration_next", methods=["POST"])
@restricted_access
def nextCalibrationStep():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	printer.nextCalibrationStep()

	return NO_CONTENT

@api.route("/maintenance/running_calibration_test", methods=["GET"])
@restricted_access
def inCalibrationTest():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	res = printer.isRunningCalibrationTest()

	return jsonify({
		"response": res
	})

@api.route("/maintenance/start_calibration_test", methods=["POST"])
@restricted_access
def startCalibrationTest():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	printer.startCalibrationTest()

	return NO_CONTENT

@api.route("/maintenance/cancel_calibration_test", methods=["POST"])
@restricted_access
def cancelCalibrationTest():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	printer.cancelCalibrationTest()

	return NO_CONTENT

@api.route("/maintenance/repeat_calibration", methods=["POST"])
@restricted_access
def repeatCalibration():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	printer.startCalibration(repeat=True)

	return NO_CONTENT
