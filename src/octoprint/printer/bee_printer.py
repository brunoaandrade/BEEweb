# coding=utf-8
"""
This module holds the standard implementation of the :class:`PrinterInterface` and it helpers.
"""

from __future__ import absolute_import
from octoprint.util.bee_comm import BeeCom
from octoprint.printer.standard import Printer

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


class BeePrinter(Printer):
	"""
	BVC implementation of the :class:`PrinterInterface`. Manages the communication layer object and registers
	itself with it as a callback to react to changes on the communication layer.
	"""
	_estimatedTime = None
	_elapsedTime = None
	_numberLines = None
	_executedLines = None

	def __init__(self, fileManager, analysisQueue, printerProfileManager):
		super(BeePrinter, self).__init__(fileManager, analysisQueue, printerProfileManager)

	def connect(self, port=None, baudrate=None, profile=None):
		"""
		 Connects to the printer. If port and/or baudrate is provided, uses these settings, otherwise autodetection
		 will be attempted.
		"""

		if self._comm is not None:
			self._comm.close()
		#self._printerProfileManager.select(profile)

		self._comm = BeeCom(callbackObject=self, printerProfileManager=self._printerProfileManager)
		self._comm.confirmConnection()

		# selects the printer profile based on the connected printer name
		printer_name = self.get_printer_name()
		self._printerProfileManager.select(printer_name)

	def updateProgress(self, progressData):
		"""
		Receives a progress data object from the BVC communication layer
		and updates the progress attributes

		:param progressData:
		:return:
		"""
		if progressData is not None:
			self._elapsedTime = progressData['Elapsed Time'] if 'Elapsed Time' in progressData else None
			self._estimatedTime = progressData['Estimated Time'] if 'Estimated Time' in progressData else None
			self._executedLines = progressData['Executed Lines'] if 'Executed Lines' in progressData else None
			self._numberLines = progressData['Lines'] if 'Lines' in progressData else None

	def on_comm_progress(self):
		"""
		 Callback method for the comm object, called upon any change in progress of the printjob.
		 Triggers storage of new values for printTime, printTimeLeft and the current progress.
		"""

		self._setProgressData(self._comm.getPrintProgress(), self._comm.getPrintFilepos(),
							  self._comm.getPrintTime(), self._comm.getCleanedPrintTime())


	def _setProgressData(self, progress, filepos, printTime, cleanedPrintTime):
		"""
		Auxiliar method to control the print progress status data
		:param progress:
		:param filepos:
		:param printTime:
		:param cleanedPrintTime:
		:return:
		"""
		estimatedTotalPrintTime = self._estimateTotalPrintTime(progress, cleanedPrintTime)
		totalPrintTime = estimatedTotalPrintTime

		if self._selectedFile and "estimatedPrintTime" in self._selectedFile and self._selectedFile["estimatedPrintTime"]:
			statisticalTotalPrintTime = self._selectedFile["estimatedPrintTime"]
			if progress and cleanedPrintTime:
				if estimatedTotalPrintTime is None:
					totalPrintTime = statisticalTotalPrintTime
				else:
					if progress < 0.5:
						sub_progress = progress * 2
					else:
						sub_progress = 1.0
					totalPrintTime = (1 - sub_progress) * statisticalTotalPrintTime + sub_progress * estimatedTotalPrintTime

		self._progress = progress
		self._printTime = printTime
		self._printTimeLeft = totalPrintTime - cleanedPrintTime if (totalPrintTime is not None and cleanedPrintTime is not None) else None

		self._stateMonitor.set_progress({
			"completion": self._progress * 100 if self._progress is not None else None,
			"filepos": filepos,
			"printTime": int(self._elapsedTime) if self._elapsedTime is not None else None,
			"printTimeLeft": int(self._printTimeLeft) if self._printTimeLeft is not None else None
		})

		if progress:
			progress_int = int(progress * 100)
			if self._lastProgressReport != progress_int:
				self._lastProgressReport = progress_int
				self._reportPrintProgressToPlugins(progress_int)