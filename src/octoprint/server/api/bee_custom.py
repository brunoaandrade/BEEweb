# coding=utf-8
from __future__ import absolute_import

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.server.api import api
from octoprint.server import printer

#~~ BVC custom API

@api.route("/bee/printer", methods=["GET"])
def getConnectedPrinter():

	if printer is not None:
		return printer.get_printer_name()
	else:
		return None

