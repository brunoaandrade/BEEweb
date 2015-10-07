# coding=utf-8
"""
This module holds the standard implementation of the :class:`PrinterInterface` and it helpers.
"""

from __future__ import absolute_import
from octoprint.util.bee_comm import BeeCom
from octoprint.printer.standard import Printer
from octoprint.printer import PrinterInterface

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"


class BeePrinter(Printer):
    """
    BVC implementation of the :class:`PrinterInterface`. Manages the communication layer object and registers
    itself with it as a callback to react to changes on the communication layer.
    """
    _estimatedTime = None
    _elapsedTime = None
    _numberLines = None
    _executedLines = None
    _currentFeedRate = None

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

        # homes all axis
        bee_commands = self._comm.getCommandsInterface()
        if bee_commands is not None and bee_commands.isPrinting is not False:
            bee_commands.home()

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
        if progressData is not None and self._selectedFile is not None:
            self._elapsedTime = progressData['Elapsed Time'] if 'Elapsed Time' in progressData else None
            self._estimatedTime = progressData['Estimated Time'] if 'Estimated Time' in progressData else None
            self._executedLines = progressData['Executed Lines'] if 'Executed Lines' in progressData else None
            self._numberLines = progressData['Lines'] if 'Lines' in progressData else None

    def refresh_sd_files(self, blocking=False):
        """
        Refreshes the list of file stored on the SD card attached to printer (if available and printer communication
        available).
        """
        if not self._comm or not self._comm.isSdReady():
            return

        self._comm.refreshSdFiles()

    def on_comm_progress(self):
        """
         Callback method for the comm object, called upon any change in progress of the printjob.
         Triggers storage of new values for printTime, printTimeLeft and the current progress.
        """

        self._setProgressData(self.getPrintProgress(), self.getPrintFilepos(),
                              self._comm.getPrintTime(), self._comm.getCleanedPrintTime())

    def getPrintProgress(self):
        """
        Gets the current progress of the print job
        :return:
        """
        if self._numberLines is not None and self._executedLines is not None and self._numberLines > 0:
            return float(self._executedLines) / float(self._numberLines)
        else:
            return -1

    def getPrintFilepos(self):
        """
        Gets the current position in file being printed
        :return:
        """
        if self._executedLines is not None:
            return self._executedLines
        else:
            return 0

    def jog(self, axis, amount):
        """
        Jogs the tool a selected amount in the axis chosen

        :param axis:
        :param amount:
        :return:
        """
        if not isinstance(axis, (str, unicode)):
            raise ValueError("axis must be a string: {axis}".format(axis=axis))

        axis = axis.lower()
        if not axis in PrinterInterface.valid_axes:
            raise ValueError("axis must be any of {axes}: {axis}".format(axes=", ".join(PrinterInterface.valid_axes), axis=axis))
        if not isinstance(amount, (int, long, float)):
            raise ValueError("amount must be a valid number: {amount}".format(amount=amount))

        printer_profile = self._printerProfileManager.get_current_or_default()

        # if the feed rate was manually set uses it
        if self._currentFeedRate is not None:
            movement_speed = self._currentFeedRate * 60
        else:
            movement_speed = printer_profile["axes"][axis]["speed"]

        bee_commands = self._comm.getCommandsInterface()

        if axis == 'x':
            bee_commands.move(amount, 0, 0, None, movement_speed)
        elif axis == 'y':
            bee_commands.move(0, amount, 0, None, movement_speed)
        elif axis == 'z':
            bee_commands.move(0, 0, amount, None, movement_speed)

    def feed_rate(self, factor):
        """
        Updates the feed rate factor
        :param factor:
        :return:
        """
        factor = self._convert_rate_value(factor, min=50, max=200)
        self._currentFeedRate = factor

    def home(self, axes):
        """
        Moves the select axes to their home position
        :param axes:
        :return:
        """
        if not isinstance(axes, (list, tuple)):
            if isinstance(axes, (str, unicode)):
                axes = [axes]
            else:
                raise ValueError("axes is neither a list nor a string: {axes}".format(axes=axes))

        validated_axes = filter(lambda x: x in PrinterInterface.valid_axes, map(lambda x: x.lower(), axes))
        if len(axes) != len(validated_axes):
            raise ValueError("axes contains invalid axes: {axes}".format(axes=axes))

        bee_commands = self._comm.getCommandsInterface()

        if 'z' in axes:
            bee_commands.homeZ()
        elif 'x' in axes and 'y' in axes:
            bee_commands.homeXY()

    def extrude(self, amount):
        """
        Extrudes the defined amount
        :param amount:
        :return:
        """
        if not isinstance(amount, (int, long, float)):
            raise ValueError("amount must be a valid number: {amount}".format(amount=amount))

        printer_profile = self._printerProfileManager.get_current_or_default()
        extrusion_speed = printer_profile["axes"]["e"]["speed"]

        bee_commands = self._comm.getCommandsInterface()
        bee_commands.move(0, 0, 0, amount, extrusion_speed)

    def get_current_temperature(self):
        """
        Returns the current extruder temperature
        :return:
        """
        return self._comm.getCommandsInterface().getNozzleTemperature()

    def unload(self):
        """
        Unloads the filament from the printer
        :return:
        """
        return self._comm.getCommandsInterface().unload()

    def load(self):
        """
        Loads the filament to the printer
        :return:
        """
        return self._comm.getCommandsInterface().load()

    def setFilamentString(self, filamentStr):
        """
        Saves the filament reference string in the printer memory
        :return:
        """
        return self._comm.getCommandsInterface().setFilamentString(filamentStr)

    def startCalibration(self, startZ=2.0, repeat=False):
        """
        Starts the calibration procedure
        :param startZ:
        :param repeat:
        :return:
        """
        return self._comm.getCommandsInterface().startCalibration(startZ, repeat)

    def nextCalibrationStep(self):
        """
        Goes to the next calibration step
        :return:
        """
        return self._comm.getCommandsInterface().goToNextCalibrationPoint()

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

        if self._selectedFile and "estimatedPrintTime" in self._selectedFile \
                and self._selectedFile["estimatedPrintTime"]:

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
            "printTime": int(self._elapsedTime * 60) if self._elapsedTime is not None else None,
            "printTimeLeft": int(self._printTimeLeft) if self._printTimeLeft is not None else None
        })

        if progress:
            progress_int = int(progress * 100)
            if self._lastProgressReport != progress_int:
                self._lastProgressReport = progress_int
                self._reportPrintProgressToPlugins(progress_int)