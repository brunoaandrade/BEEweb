# coding=utf-8
from __future__ import absolute_import

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
		"target": ["target"]
	}
	command, data, response = get_json_command_from_request(request, valid_commands)
	if response is not None:
		return response

	##~~ temperature
	if command == "target":
		target = data["target"]

		# make sure the target is a number
		if not isinstance(target, (int, long, float)):
			return make_response("Not a number: %r" % target, 400)

		# perform the actual temperature command
		printer.set_temperature("tool", target)

	return NO_CONTENT


@api.route("/maintenance/temperature", methods=["GET"])
def getTemperature():
	current_temp = printer.get_current_temperature()
	return jsonify({
		"temperature": current_temp
	})