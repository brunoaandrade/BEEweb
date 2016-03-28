# coding=utf-8
from __future__ import absolute_import
import re

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"

from flask import request, make_response, jsonify, url_for

from octoprint.server import printer, NO_CONTENT
from octoprint.server.util.flask import restricted_access, get_json_command_from_request
from octoprint.server.api import api
from octoprint.settings import settings as s, valid_boolean_trues
from octoprint.slicing import UnknownSlicer, SlicerNotConfigured
from octoprint.server import slicingManager

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

@api.route("/maintenance/heating_done", methods=["POST"])
def heatingDone():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	printer.heatingDone()

	return NO_CONTENT

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

@api.route("/maintenance/filament_profiles", methods=["GET"])
@restricted_access
def filamentProfiles():
	"""
	Gets the slicing profiles (Filament colors) configured for Cura engine
	:return:
	"""
	default_slicer = s().get(["slicing", "defaultSlicer"])

	profiles = _getSlicingProfilesData(default_slicer, printer.getCurrentProfile()['name'])

	return jsonify(profiles)

@api.route("/maintenance/nozzle_sizes", methods=["GET"])
@restricted_access
def nozzleSizes():
	"""
	Gets the nozzle sizes available
	:return:
	"""
	availableSizes = printer.nozzleSizes

	return jsonify(availableSizes)

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

@api.route("/maintenance/get_filament", methods=["GET"])
@restricted_access
def getFilament():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	resp = printer.getFilamentString()

	return jsonify({
		"filament": resp
	})


@api.route("/maintenance/get_nozzles_and_filament", methods=["GET"])
@restricted_access
def getNozzlesAndFilament():
	"""
	Returns the list of available nozzle, the current selected nozzle and the current selected filament
	:return:
	"""
	nozzle_list = printer.getNozzleTypes()

	if not printer.is_operational():
		return jsonify({
			"nozzle": None,
			"nozzleList": nozzle_list,
			"filament": None
		})

	filament = printer.getFilamentString()
	nozzle = printer.getNozzleSize()

	return jsonify({
		"nozzle": nozzle,
		"nozzleList": nozzle_list,
		"filament": filament
	})

@api.route("/maintenance/save_nozzle", methods=["POST"])
@restricted_access
def saveNozzle():

	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	valid_commands = {
		"nozzle": ["nozzleType"]
	}
	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	nozzle = data['nozzleType']

	if not printer.isValidNozzleSize(nozzle):
		return make_response("Invalid nozzle size", 409)

	resp = printer.setNozzleSize(nozzle)

	return jsonify({
		"response": resp
	})

@api.route("/maintenance/get_nozzle", methods=["GET"])
@restricted_access
def getSavedNozzle():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	resp = printer.getNozzleSize()

	return jsonify({
		"nozzle": resp
	})

@api.route("/maintenance/get_nozzle_list", methods=["GET"])
@restricted_access
def getNozzleList():
	if not printer.is_operational():
		return make_response("Printer is not operational", 409)

	resp = printer.getNozzleTypes()

	return jsonify({
		"nozzles": resp
	})

def _getSlicingProfilesData(slicer, printer_name, require_configured=False):

	profiles = slicingManager.all_profiles_list(slicer, require_configured=require_configured)

	result = dict()
	for name, profile in profiles.items():
		profileData = _getSlicingProfileData(slicer, name, profile, printer_name)

		if profileData["displayName"] in result:
			continue

		if printer_name is not None:
			profile_key = profileData["key"]

			if printer_name.lower() in profile_key.lower():
				# Uses the filament filtered name as the key for the results array
				result[profileData["displayName"]] = profileData
		else:
			result[profileData["displayName"]] = profileData

	return result

def _getSlicingProfileData(slicer, name, profile, printer_name):

	defaultProfiles = s().get(["slicing", "defaultProfiles"])
	result = dict(
		key=name,
		default=defaultProfiles and slicer in defaultProfiles and defaultProfiles[slicer] == name,
		resource=url_for(".slicingGetSlicerProfile", slicer=slicer, name=name, _external=True)
	)
	if profile.display_name is not None:
		result["displayName"] = profile.display_name
	if profile.description is not None:
		result["description"] = profile.description

	# filters the display name
	if printer_name is not None:
		filtered_name = result["displayName"]\
			.replace('_'+printer_name.lower(), '') \
			.replace('_medium', '').replace('_med','').replace('_low','')\
			.replace('_highplus','').replace('_high','')\
			.replace('_nz400', '').replace('_nz600', '')

		# sanitizes the string for display
		filtered_name = filtered_name.replace('_', ' ').title()
		result["displayName"] = filtered_name

	return result
