# coding=utf-8

from __future__ import absolute_import

import logging

import time
from octoprint.util.bee_comm import BeeCom
import os
from octoprint.printer.standard import Printer
from octoprint.printer import PrinterInterface
from octoprint.settings import settings
from octoprint.server.util.connection_util import detect_bvc_printer_connection
from octoprint.events import eventManager, Events

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"


class BeePrinter(Printer):
    """
    BVC implementation of the :class:`PrinterInterface`. Manages the communication layer object and registers
    itself with it as a callback to react to changes on the communication layer.
    """

    def __init__(self, fileManager, analysisQueue, printerProfileManager):
        super(BeePrinter, self).__init__(fileManager, analysisQueue, printerProfileManager)
        self._estimatedTime = None
        self._elapsedTime = None
        self._numberLines = None
        self._executedLines = None
        self._currentFeedRate = None
        self._runningCalibrationTest = False

    def connect(self, port=None, baudrate=None, profile=None):
        """
         Connects to a BVC printer. Ignores port, baudrate parameters.
         They are kept just for interface compatibility
        """

        if self._comm is not None:
            self._comm.close()

        self._comm = BeeCom(callbackObject=self, printerProfileManager=self._printerProfileManager)
        self._comm.confirmConnection()

        bee_commands = self._comm.getCommandsInterface()

        # homes all axis
        if bee_commands is not None and bee_commands.isPrinting() is False:
            bee_commands.home()

            # checks for firmware upgrades
            self.update_firmware()

        # selects the printer profile based on the connected printer name
        printer_name = self.get_printer_name()

        # converts the name to the id
        printer_id = None
        if printer_name is not None:
            printer_id = printer_name.lower().replace(' ', '')
        self._printerProfileManager.select(printer_id)

        # if the printer is printing or in shutdown mode selects the last selected file for print
        lastFile = settings().get(['lastPrintJobFile'])
        if lastFile is not None and (self.is_shutdown() or self.is_printing()):
            self.select_file(lastFile, False)

        # subscribes the unselect_file function with the PRINT_FAILED event
        eventManager().subscribe(Events.PRINT_FAILED, self.on_print_cancelled)


    def disconnect(self):
        """
        Closes the connection to the printer.
        """
        super(BeePrinter, self).disconnect()

        # Starts the connection monitor thread
        import threading
        bvc_conn_thread = threading.Thread(target=detect_bvc_printer_connection, args=(self.connect, ))
        bvc_conn_thread.daemon = True
        bvc_conn_thread.start()

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
         Callback method for the comm object, called upon any change in progress of the print job.
         Triggers storage of new values for printTime, printTimeLeft and the current progress.
        """

        self._setProgressData(self.getPrintProgress(), self.getPrintFilepos(),
                              self._comm.getPrintTime(), self._comm.getCleanedPrintTime())

        # If the status from the printer is no longer printing runs the post-print trigger
        if self.getPrintProgress() >= 1 \
                and self._comm.getCommandsInterface().isPreparingOrPrinting() is False:

            self._comm.triggerPrintFinished()

            self._comm.getCommandsInterface().stopStatusMonitor()
            self._runningCalibrationTest = False

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

    def getCurrentProfile(self):
        """
        Returns current printer profile
        :return:
        """
        if self._printerProfileManager is not None:
            return self._printerProfileManager.get_current_or_default()
        else:
            return None

    def getPrinterName(self):
        """
        Returns the name of the connected printer
        :return:
        """
        if self._comm is not None:
            return self._comm.getConnectedPrinterName()
        else:
            return None

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


    def startHeating(self, targetTemperature=200):
        """
        Starts the heating procedure
        :param targetTemperature:
        :return:
        """
        return self._comm.getCommandsInterface().startHeating(targetTemperature)

    def cancelHeating(self):
        """
        Cancels the heating procedure
        :return:
        """
        return self._comm.getCommandsInterface().cancelHeating()

    def heatingDone(self):
        """
        Runs the necessary commands after the heating operation is finished
        :return:
        """
        return self._comm.getCommandsInterface().goToLoadUnloadPos()

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
        :param filamentStr:
        :return:
        """
        return self._comm.getCommandsInterface().setFilamentString(filamentStr)

    def getFilamentString(self):
        """
        Gets the current filament reference string in the printer memory
        :return: string
        """
        return self._comm.getCommandsInterface().getFilamentString()

    def setNozzleSize(self, nozzleSize):
        """
        Saves the selected nozzle size
        :param nozzleSize:
        :return:
        """
        return self._comm.getCommandsInterface().setNozzleSize(nozzleSize)

    def getNozzleSize(self):
        """
        Gets the current selected nozzle size in the printer memory
        :return: float
        """
        return self._comm.getCommandsInterface().getNozzleSize()

    def startCalibration(self, repeat=False):
        """
        Starts the calibration procedure
        :param repeat:
        :return:
        """
        return self._comm.getCommandsInterface().startCalibration(repeat=repeat)

    def nextCalibrationStep(self):
        """
        Goes to the next calibration step
        :return:
        """
        return self._comm.getCommandsInterface().goToNextCalibrationPoint()

    def startCalibrationTest(self):
        """
        Starts the printer calibration test
        :return:
        """
        test_gcode = CalibrationGCoder.get_calibration_gcode(self._printerProfileManager.get_current_or_default()['name'])
        lines = test_gcode.split(',')

        file_path = os.path.join(settings().getBaseFolder("uploads"), 'BEETHEFIRST_calib_test.gcode')
        calibtest_file = open(file_path, 'w')

        for line in lines:
            calibtest_file.write(line + '\n')

        calibtest_file.close()

        self.select_file(file_path, False)
        self.start_print()

        self._runningCalibrationTest = True

        return None

    def cancelCalibrationTest(self):
        """
        Cancels the running calibration test
        :return:
        """
        self.cancel_print()

        return None

    def isRunningCalibrationTest(self):
        """
        Updates the running calibration test flag
        :return:
        """
        return self._runningCalibrationTest

    def isValidNozzleSize(self, nozzleSize):
        """
        Checks if the passed nozzleSize value is valid
        :param nozzleSize:
        :return:
        """
        for k,v in settings().get(['nozzleTypes']).iteritems():
            if v['value'] == nozzleSize:
                return True

        return False

    def is_preparing_print(self):
        return self._comm is not None and self._comm.isPreparingPrint()

    def is_heating(self):
        return self._comm is not None and self._comm.isHeating()

    def is_shutdown(self):
        return self._comm is not None and self._comm.isShutdown()

    def get_state_string(self):
        """
         Returns a human readable string corresponding to the current communication state.
        """
        if self._comm is None:
            return "Attempting to connect..."
        else:
            return self._comm.getStateString()

    def select_file(self, path, sd, printAfterSelect=False, pos=None):
        super(BeePrinter, self).select_file(path, sd, printAfterSelect, pos)

        # saves the path to the selected file
        settings().set(['lastPrintJobFile'], path)
        settings().save()

    def cancel_print(self):
        """
         Cancel the current printjob.
        """
        super(BeePrinter, self).cancel_print()
        # waits a bit before unselecting the file
        import time
        time.sleep(2)
        self.unselect_file()

    def current_firmware(self):
        """
        Gets the current firmware version
        :return:
        """
        firmware_v = self._comm.getCommandsInterface().getFirmwareVersion()

        if firmware_v is not None:
            return firmware_v
        else:
            return 'Not available'

    def update_firmware(self):
        """
        Updates the printer firmware if a newer version is available
        :return: if no printer is connected just returns void
        """
        _logger = logging.getLogger()
        # get the latest firmware file for the connected printer
        conn_printer = self.getCurrentProfile()
        if conn_printer is None:
            return

        printer_name = conn_printer.get('name').replace(' ', '')

        if printer_name:
            from os import listdir
            from os.path import isfile, join

            _logger.info("Checking for firmware updates...")

            firmware_path = settings().getBaseFolder('firmware')

            for ff in listdir(firmware_path):

                if isfile(join(firmware_path, ff)):
                    firmware_file = os.path.splitext(ff)[0]
                    fname_parts = firmware_file.split('-')

                    if len(fname_parts) == 3 and printer_name == fname_parts[1]:

                        # gets the current firmware version
                        curr_version = self.current_firmware()
                        if curr_version is not "Not available":
                            curr_version_parts = curr_version.split('.')
                            file_version_parts = fname_parts[2].split('.')

                            for i in xrange(3):
                                if int(file_version_parts[i]) > int(curr_version_parts[i]):
                                    # version update found
                                    _logger.info("Updating printer firmware...")
                                    self._comm.getCommandsInterface().flashFirmware(firmware_path + '/' + ff, fname_parts[2])

                                    # waits for transfer to finish
                                    while self._comm.getCommandsInterface().getTransferCompletionState() is not None:
                                        time.sleep(0.5)

                                    _logger.info("Firmware updated to %s" % fname_parts[2])
                                    return

    def on_print_cancelled(self, event, payload):
        """
        Print cancelled callback for the EventManager.
        """
        self.unselect_file()

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

    def _getStateFlags(self):
        return {
            "operational": self.is_operational(),
            "printing": self.is_printing(),
            "closedOrError": self.is_closed_or_error(),
            "error": self.is_error(),
            "paused": self.is_paused(),
            "ready": self.is_ready(),
            "sdReady": self.is_sd_ready(),
            "heating": self.is_heating(),
            "shutdown": self.is_shutdown()
        }

class CalibrationGCoder:

    _calibration_gcode = { 'BEETHEFIRST' :'M29,'
                'M300 ;3.X.X - 2013-12-05,'
                'M206 X500		; SET ACCEL = 500mm/s^2,'
                'M107			; TURN OFF FAN,'
                'M104 S220		; HEAT DONT WAIT,'
                'G1 X-98.0 Y-20.0 Z5.0 F3000,'
                'G1 Y-68.0 Z0.3,'
                'G1 X-98.0 Y0.0 F500 E20,'
                'G92 E			;RESET FILAMENT,'
                'M106			;TURN FAN ON,'
                'M113 S1.0,'
                'M107 ; First Layer Blower OFF,'
                'M108 S12.24,'
                'M104 S205.0,'
                'G1 X-85.86957 Y-58.8909 Z0.15 F3600.0,'
                'G1 F6000.0,'
                'G1 E0.5,'
                'G1 F3600.0,'
                'M101,'
                'G1 X-85.20188 Y-59.34014 Z0.15 F648.0 E0.54773,'
                'G1 X-84.65842 Y-59.56525 E0.58262,'
                'G1 X-84.08642 Y-59.70257 E0.61751,'
                'G1 X84.08642 Y-59.70257 E10.59227,'
                'G1 X84.65842 Y-59.56525 E10.62716,'
                'G1 X85.20188 Y-59.34014 E10.66205,'
                'G1 X85.70344 Y-59.03279 E10.69694,'
                'G1 X86.15074 Y-58.65075 E10.73183,'
                'G1 X86.53279 Y-58.20344 E10.76672,'
                'G1 X86.84014 Y-57.70188 E10.80161,'
                'G1 X87.06525 Y-57.15842 E10.8365,'
                'G1 X87.20257 Y-56.58643 E10.87139,'
                'G1 X87.20257 Y56.58643 E17.58396,'
                'G1 X87.06525 Y57.15842 E17.61885,'
                'G1 X86.84014 Y57.70188 E17.65374,'
                'G1 X86.53279 Y58.20344 E17.68863,'
                'G1 X86.15074 Y58.65075 E17.72352,'
                'G1 X85.70344 Y59.03279 E17.75841,'
                'G1 X85.20188 Y59.34014 E17.7933,'
                'G1 X84.65842 Y59.56525 E17.82819,'
                'G1 X84.08642 Y59.70257 E17.86308,'
                'G1 X-84.08642 Y59.70257 E27.83783,'
                'G1 X-84.65842 Y59.56525 E27.87272,'
                'G1 X-85.20188 Y59.34014 E27.90761,'
                'G1 X-85.70344 Y59.03279 E27.9425,'
                'G1 X-86.15074 Y58.65075 E27.97739,'
                'G1 X-86.53279 Y58.20344 E28.01228,'
                'G1 X-86.84014 Y57.70188 E28.04717,'
                'G1 X-87.06525 Y57.15842 E28.08206,'
                'G1 X-87.20257 Y56.58643 E28.11695,'
                'G1 X-87.20257 Y-56.58643 E34.82952,'
                'G1 X-87.06525 Y-57.15842 E34.86441,'
                'G1 X-86.84014 Y-57.70188 E34.8993,'
                'G1 X-86.53279 Y-58.20344 E34.93419,'
                'G1 X-86.23597 Y-58.55096 E34.9613,'
                'G1 F6000.0,'
                'G1 E34.4613,'
                'G1 F648.0,'
                'M103,'
                'G1 X-86.67555 Y-58.65422 Z0.15 F6000.0,'
                'G1 F648.0,'
                'M103,'
                'M104 S0,'
                'M113 S0.0,'
                'M107,'
                'G1 F6000,'
                'G28'
    }

    def __init__(self):
        pass

    @staticmethod
    def get_calibration_gcode(printer_name):
        if printer_name in CalibrationGCoder._calibration_gcode:
            return CalibrationGCoder._calibration_gcode[printer_name]

        return None
