# coding=utf-8
from __future__ import absolute_import
import os
import threading
import time
import Queue as queue
import logging

from octoprint.settings import settings
from octoprint.events import eventManager, Events
from octoprint.util.comm import MachineCom, regex_sdPrintingByte, regex_sdFileOpened
from beedriver.connection import Conn as BeePrinterConn
from octoprint.util import comm, get_exception_string, sanitize_ascii, RepeatedTimer, parsePropertiesFile

__author__ = "BEEVC - Electronic Systems"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"

class BeeCom(MachineCom):
    STATE_WAITING_FOR_BTF = 21
    STATE_PREPARING_PRINT = 22
    STATE_HEATING = 23
    STATE_SHUTDOWN = 24

    _beeConn = None
    _beeCommands = None

    _responseQueue = queue.Queue()
    _statusQueue = queue.Queue()

    _monitor_print_progress = True
    _connection_monitor_active = True
    _prepare_print_thread = None

    def __init__(self, callbackObject=None, printerProfileManager=None):
        super(BeeCom, self).__init__(None, None, callbackObject, printerProfileManager)

        self._openConnection()

        # monitoring thread
        self._monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor, name="comm._monitor")
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()


    def _openConnection(self):
        """
        Opens a new connection using the BEEcom driver

        :return: True if the connection was successful
        """
        if self._beeConn is None:
            self._beeConn = BeePrinterConn(self._connShutdownHook)
            self._beeConn.connectToFirstPrinter()

        if self._beeConn.isConnected():
            self._beeCommands = self._beeConn.getCommandIntf()

            # change to firmware
            if self._beeCommands.getPrinterMode() == 'Bootloader':
                # checks for firmware updates
                self.update_firmware()

                self._beeCommands.goToFirmware()

            # restart connection
            self._beeConn.reconnect()

            # post connection callback
            self._onConnected()

            return True
        else:
            return False

    def current_firmware(self):
        """
        Gets the current firmware version
        :return:
        """
        firmware_v = self.getCommandsInterface().getFirmwareVersion()

        if firmware_v is not None:
            return firmware_v
        else:
            return 'Not available'

    def update_firmware(self):
        """
        Updates the printer firmware if the value in the firmware.properties file is different
        from the current printer firmware
        :return: if no printer is connected just returns void
        """
        _logger = logging.getLogger()
        # get the latest firmware file for the connected printer
        conn_printer = self.getConnectedPrinterName()
        if conn_printer is None:
            return

        printer_id = conn_printer.replace(' ', '').lower()

        if printer_id:
            from os.path import isfile, join

            _logger.info("Checking for firmware updates...")

            firmware_path = settings().getBaseFolder('firmware')
            firmware_config_file = join(firmware_path, 'firmware.properties')

            firmware_properties = parsePropertiesFile(firmware_config_file)

            firmware_file_name = firmware_properties['firmware.'+printer_id]

            if firmware_file_name is not None and isfile(join(firmware_path, firmware_file_name)):

                fname_parts = firmware_file_name.split('-')

                # gets the current firmware version
                curr_firmware = self.current_firmware()
                curr_firmware_parts = curr_firmware.split('-')

                if len(curr_firmware_parts) == 3 and curr_firmware is not "Not available":
                    curr_version_parts = curr_firmware_parts[2].split('.')
                    file_version_parts = fname_parts[2].split('.')

                    for i in xrange(3):
                        if int(file_version_parts[i]) != int(curr_version_parts[i]):
                            # version update found
                            _logger.info("Updating printer firmware...")
                            self.getCommandsInterface().flashFirmware(join(firmware_path, firmware_file_name),
                                                                      firmware_file_name)

                            _logger.info("Firmware updated to %s" % fname_parts[2])
                            return
                elif curr_firmware == '0.0.0':
                    # If curr_firmware is 0.0.0 it means something went wrong with a previous firmware update
                    _logger.info("Updating printer firmware...")
                    self.getCommandsInterface().flashFirmware(join(firmware_path, firmware_file_name),
                                                              firmware_file_name)

                    _logger.info("Firmware updated to %s" % fname_parts[2])
                    return
            else:
                _logger.error("No firmware file matching the configuration for printer %s found" % conn_printer)

            _logger.info("No firmware updates found")

    def sendCommand(self, cmd, cmd_type=None, processed=False, force=False):
        """
        Sends a custom command through the open connection
        :param cmd:
        :param cmd_type:
        :param processed:
        :param force:
        :return:
        """
        cmd = cmd.encode('ascii', 'replace')
        if not processed:
            cmd = comm.process_gcode_line(cmd)
            if not cmd:
                return

        #if self.isPrinting() and not self.isSdFileSelected():
        #    self._commandQueue.put((cmd, cmd_type))

        if self.isOperational():

            wait = None
            if "g" in cmd.lower():
                wait = "3"

            resp = self._beeCommands.sendCmd(cmd, wait)

            if resp:
                # puts the response in the monitor queue
                self._responseQueue.put(resp)

                # logs the command reply with errors
                splits = resp.rstrip().split("\n")
                for r in splits:
                    if "Error" in r:
                        self._logger.warning(r)

    def close(self, is_error=False, wait=True, timeout=10.0, *args, **kwargs):
        """
        Closes the connection to the printer if it's active
        :param is_error:
        :param wait: unused parameter (kept for interface compatibility)
        :param timeout:
        :param args:
        :param kwargs:
        :return:
        """
        if self._beeConn is not None:
            self._beeConn.close()
            self._changeState(self.STATE_CLOSED)

    def confirmConnection(self):
        """
        Confirms the connection changing the internal state of the printer
        :return:
        """
        if self._beeConn.isConnected():
            if self._beeCommands.isPrinting():
                self._changeState(self.STATE_PRINTING)
            elif self._beeCommands.isShutdown():
                self._changeState(self.STATE_SHUTDOWN)
            else:
                self._changeState(self.STATE_OPERATIONAL)
        else:
            self._changeState(self.STATE_WAITING_FOR_BTF)

    def getConnectedPrinterName(self):
        """
        Returns the current connected printer name
        :return:
        """
        if self._beeConn is not None:
            return self._beeConn.getConnectedPrinterName()
        else:
            return ""

    def getConnectedPrinterSN(self):
        """
        Returns the current connected printer serial nu,ber
        :return:
        """
        if self._beeConn is not None:
            return self._beeConn.getConnectedPrinterSN()
        else:
            return None

    def isOperational(self):
        return self._state == self.STATE_OPERATIONAL \
               or self._state == self.STATE_PRINTING \
               or self._state == self.STATE_PAUSED \
               or self._state == self.STATE_SHUTDOWN \
               or self._state == self.STATE_TRANSFERING_FILE \
               or self._state == self.STATE_PREPARING_PRINT \
               or self._state == self.STATE_HEATING

    def isClosedOrError(self):
        return self._state == self.STATE_ERROR or self._state == self.STATE_CLOSED_WITH_ERROR \
               or self._state == self.STATE_CLOSED or self._state == self.STATE_WAITING_FOR_BTF

    def isBusy(self):
        return self.isPrinting() or self.isPaused() or self.isPreparingPrint()

    def isPreparingPrint(self):
        return self._state == self.STATE_PREPARING_PRINT or self._state == self.STATE_HEATING

    def isPrinting(self):
        return self._state == self.STATE_PRINTING

    def isHeating(self):
        return self._state == self.STATE_HEATING

    def isShutdown(self):
        return self._state == self.STATE_SHUTDOWN

    def getStateString(self):
        """
        Returns the current printer state
        :return:
        """
        if self._state == self.STATE_WAITING_FOR_BTF:
            return "No printer detected. Please turn on your printer."
        elif self._state == self.STATE_PREPARING_PRINT:
            return "Preparing to print, please wait..."
        elif self._state == self.STATE_HEATING:
            return "Heating..."
        elif self._state == self.STATE_SHUTDOWN:
            return "Shutdown"
        else:
            return super(BeeCom, self).getStateString()

    def startPrint(self, pos=None):
        """
        Starts the printing operation
        :param pos: unused parameter, just to keep the interface compatible with octoprint
        """
        if not self.isOperational() or self.isPrinting():
            return

        if self._currentFile is None:
            raise ValueError("No file selected for printing")

        try:
            self._currentFile.start()

            payload = {
                "file": self._currentFile.getFilename(),
                "filename": os.path.basename(self._currentFile.getFilename()),
                "origin": self._currentFile.getFileLocation()
            }

            eventManager().fire(Events.PRINT_STARTED, payload)

            if self.isSdFileSelected():
                print_resp = self._beeCommands.startSDPrint(self._currentFile.getFilename())

                if print_resp:
                    self._sd_status_timer = RepeatedTimer(self._timeout_intervals.get("sdStatus", 1.0), self._poll_sd_status, run_first=True)
                    self._sd_status_timer.start()
            else:
                print_resp = self._beeCommands.printFile(payload['file'])

            if print_resp is True:
                self._changeState(self.STATE_PREPARING_PRINT)
                self._heatupWaitStartTime = time.time()
                self._heatupWaitTimeLost = 0.0
                self._pauseWaitStartTime = 0
                self._pauseWaitTimeLost = 0.0

                self._heating = True

                self._prepare_print_thread = threading.Thread(target=self._preparePrintThread, name="comm._preparePrint")
                self._prepare_print_thread.daemon = True
                self._prepare_print_thread.start()
            else:
                self._logger.exception("Error while preparing the printing operation.")
                self._changeState(self.STATE_ERROR)
                eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
                return

        except:
            self._logger.exception("Error while trying to start printing")
            self._errorValue = get_exception_string()
            self._changeState(self.STATE_ERROR)
            eventManager().fire(Events.ERROR, {"error": self.getErrorString()})


    def cancelPrint(self, firmware_error=None):
        """
        Cancels the print operation
        :type firmware_error: unused parameter, just to keep the interface compatible with octoprint
        """
        if not self.isOperational() or self.isStreaming():
            return

        if self._beeCommands.cancelPrint():

            self._changeState(self.STATE_OPERATIONAL)

            if self.isSdFileSelected():
                if self._sd_status_timer is not None:
                    try:
                        self._sd_status_timer.cancel()
                    except:
                        pass

            payload = {
                "file": self._currentFile.getFilename(),
                "filename": os.path.basename(self._currentFile.getFilename()),
                "origin": self._currentFile.getFileLocation(),
                "firmwareError": firmware_error
            }

            eventManager().fire(Events.PRINT_CANCELLED, payload)

            # sends usage statistics
            self._sendUsageStatistics('cancel')


    def setPause(self, pause):
        """
        Toggle Pause method
        :param pause: True to pause or False to unpause
        :return:
        """
        if self.isStreaming():
            return

        if not self._currentFile:
            return

        payload = {
            "file": self._currentFile.getFilename(),
            "filename": os.path.basename(self._currentFile.getFilename()),
            "origin": self._currentFile.getFileLocation()
        }

        if (not pause and self.isPaused()) or self.isShutdown():
            if self._pauseWaitStartTime:
                self._pauseWaitTimeLost = self._pauseWaitTimeLost + (time.time() - self._pauseWaitStartTime)
                self._pauseWaitStartTime = None

            self._changeState(self.STATE_PRINTING)

            # resumes printing
            self._beeCommands.resumePrint()

            eventManager().fire(Events.PRINT_RESUMED, payload)
        elif pause and self.isPrinting():
            if not self._pauseWaitStartTime:
                self._pauseWaitStartTime = time.time()

            self._changeState(self.STATE_PAUSED)

            # pause print
            self._beeCommands.pausePrint()

            eventManager().fire(Events.PRINT_PAUSED, payload)

    def enterShutdownMode(self):
        """
        Enters the printer shutdown mode
        :return:
        """
        if self.isStreaming():
            return

        if not self._currentFile:
            return

        payload = {
            "file": self._currentFile.getFilename(),
            "filename": os.path.basename(self._currentFile.getFilename()),
            "origin": self._currentFile.getFileLocation()
        }

        self._changeState(self.STATE_SHUTDOWN)

        # enter shutdown mode
        self._beeCommands.enterShutdown()

        eventManager().fire(Events.POWER_OFF, payload)

    def initSdCard(self):
        """
        Initializes the SD Card in the printer
        :return:
        """
        if not self.isOperational():
            return

        self._beeCommands.initSD()

        if settings().getBoolean(["feature", "sdAlwaysAvailable"]):
            self._sdAvailable = True
            self.refreshSdFiles()
            self._callback.on_comm_sd_state_change(self._sdAvailable)

    def refreshSdFiles(self):
        """
        Refreshes the list of available SD card files
        :return:
        """
        if not self.isOperational() or self.isBusy():
            return

        fList = self._beeCommands.getFileList()

        ##~~ SD file list
        if len(fList) > 0 and 'FileNames' in fList:

            for sdFile in fList['FileNames']:

                if comm.valid_file_type(sdFile, "machinecode"):
                    if comm.filter_non_ascii(sdFile):
                        self._logger.warn("Got a file from printer's SD that has a non-ascii filename (%s), that shouldn't happen according to the protocol" % filename)
                    else:
                        if not filename.startswith("/"):
                            # file from the root of the sd -- we'll prepend a /
                            filename = "/" + filename
                        self._sdFiles.append((sdFile, 0))
                    continue

    def startFileTransfer(self, filename, localFilename, remoteFilename):
        """
        Transfers a file to the printer's SD Card
        """
        if not self.isOperational() or self.isBusy():
            self._log("Printer is not operation or busy")
            return

        self._currentFile = comm.StreamingGcodeFileInformation(filename, localFilename, remoteFilename)
        self._currentFile.start()

        # starts the transfer
        self._beeCommands.transferSDFile(filename, localFilename)

        eventManager().fire(Events.TRANSFER_STARTED, {"local": localFilename, "remote": remoteFilename})
        self._callback.on_comm_file_transfer_started(remoteFilename, self._currentFile.getFilesize())

        # waits for transfer to end
        while self._beeCommands.getTransferCompletionState() > 0:
            time.sleep(2)

        remote = self._currentFile.getRemoteFilename()
        payload = {
            "local": self._currentFile.getLocalFilename(),
            "remote": remote,
            "time": self.getPrintTime()
        }

        self._currentFile = None
        self._changeState(self.STATE_OPERATIONAL)
        self._callback.on_comm_file_transfer_done(remote)
        eventManager().fire(Events.TRANSFER_DONE, payload)
        self.refreshSdFiles()

    def getPrintProgress(self):
        """
        Gets the current print progress
        :return:
        """
        if self._currentFile is None:
            return None
        return self._currentFile.getProgress()

    def _getResponse(self):
        """
        Auxiliar method to read the command response queue
        :return:
        """
        if self._beeConn is None:
            return None
        try:
            ret = self._responseQueue.get()
        except:
            self._log("Exception raised while reading from command response queue: %s" % (get_exception_string()))
            self._errorValue = get_exception_string()
            return None

        if ret == '':
            #self._log("Recv: TIMEOUT")
            return ''

        try:
            self._log("Recv: %s" % sanitize_ascii(ret))
        except ValueError as e:
            self._log("WARN: While reading last line: %s" % e)
            self._log("Recv: %r" % ret)

        return ret

    def triggerPrintFinished(self):
        """
        This method runs the post-print job code
        :return:
        """
        self._sdFilePos = 0
        self._callback.on_comm_print_job_done()
        self._changeState(self.STATE_OPERATIONAL)

        eventManager().fire(Events.PRINT_DONE, {
            "file": self._currentFile.getFilename(),
            "filename": os.path.basename(self._currentFile.getFilename()),
            "origin": self._currentFile.getFileLocation(),
            "time": self.getPrintTime()
        })
        if self._sd_status_timer is not None:
            try:
                self._sd_status_timer.cancel()
            except:
                pass

        # sends usage statistics
        self._sendUsageStatistics('stop')

    def _monitor(self):
        """
        Monitor thread of responses from the commands sent to the printer
        :return:
        """
        feedback_controls, feedback_matcher = comm.convert_feedback_controls(settings().get(["controls"]))
        feedback_errors = []
        pause_triggers = comm.convert_pause_triggers(settings().get(["printerParameters", "pauseTriggers"]))

        #exits if no connection is active
        if not self._beeConn.isConnected():
            return

        startSeen = False
        supportWait = settings().getBoolean(["feature", "supportWait"])

        while self._monitoring_active:
            try:
                line = self._getResponse()
                if line is None:
                    continue

                ##~~ debugging output handling
                if line.startswith("//"):
                    debugging_output = line[2:].strip()
                    if debugging_output.startswith("action:"):
                        action_command = debugging_output[len("action:"):].strip()

                        if action_command == "pause":
                            self._log("Pausing on request of the printer...")
                            self.setPause(True)
                        elif action_command == "resume":
                            self._log("Resuming on request of the printer...")
                            self.setPause(False)
                        elif action_command == "disconnect":
                            self._log("Disconnecting on request of the printer...")
                            self._callback.on_comm_force_disconnect()
                        else:
                            for hook in self._printer_action_hooks:
                                try:
                                    self._printer_action_hooks[hook](self, line, action_command)
                                except:
                                    self._logger.exception("Error while calling hook {} with action command {}".format(self._printer_action_hooks[hook], action_command))
                                    continue
                    else:
                        continue

                ##~~ Error handling
                line = self._handleErrors(line)

                ##~~ process oks
                if line.strip().startswith("ok") or (self.isPrinting() and supportWait and line.strip().startswith("wait")):
                    self._clear_to_send.set()
                    self._long_running_command = False

                ##~~ Temperature processing
                if ' T:' in line or line.startswith('T:') or ' T0:' in line or line.startswith('T0:') \
                        or ' B:' in line or line.startswith('B:'):

                    self._processTemperatures(line)
                    self._callback.on_comm_temperature_update(self._temp, self._bedTemp)

                ##~~ SD Card handling
                elif 'SD init fail' in line or 'volume.init failed' in line or 'openRoot failed' in line:
                    self._sdAvailable = False
                    self._sdFiles = []
                    self._callback.on_comm_sd_state_change(self._sdAvailable)
                elif 'Not SD printing' in line:
                    if self.isSdFileSelected() and self.isPrinting():
                        # something went wrong, printer is reporting that we actually are not printing right now...
                        self._sdFilePos = 0
                        self._changeState(self.STATE_OPERATIONAL)
                elif 'SD card ok' in line and not self._sdAvailable:
                    self._sdAvailable = True
                    self.refreshSdFiles()
                    self._callback.on_comm_sd_state_change(self._sdAvailable)
                elif 'Begin file list' in line:
                    self._sdFiles = []
                    self._sdFileList = True
                elif 'End file list' in line:
                    self._sdFileList = False
                    self._callback.on_comm_sd_files(self._sdFiles)
                elif 'SD printing byte' in line and self.isSdPrinting():
                    # answer to M27, at least on Marlin, Repetier and Sprinter: "SD printing byte %d/%d"
                    match = regex_sdPrintingByte.search(line)
                    self._currentFile.setFilepos(int(match.group(1)))
                    self._callback.on_comm_progress()
                elif 'File opened' in line and not self._ignore_select:
                    # answer to M23, at least on Marlin, Repetier and Sprinter: "File opened:%s Size:%d"
                    match = regex_sdFileOpened.search(line)
                    if self._sdFileToSelect:
                        name = self._sdFileToSelect
                        self._sdFileToSelect = None
                    else:
                        name = match.group(1)
                    self._currentFile = comm.PrintingSdFileInformation(name, int(match.group(2)))
                elif 'File selected' in line:
                    if self._ignore_select:
                        self._ignore_select = False
                    elif self._currentFile is not None:
                        # final answer to M23, at least on Marlin, Repetier and Sprinter: "File selected"
                        self._callback.on_comm_file_selected(self._currentFile.getFilename(), self._currentFile.getFilesize(), True)
                        eventManager().fire(Events.FILE_SELECTED, {
                            "file": self._currentFile.getFilename(),
                            "origin": self._currentFile.getFileLocation()
                        })
                elif 'Writing to file' in line:
                    # answer to M28, at least on Marlin, Repetier and Sprinter: "Writing to file: %s"
                    self._changeState(self.STATE_PRINTING)
                    self._clear_to_send.set()
                    line = "ok"

                elif 'Done saving file' in line:
                    self.refreshSdFiles()
                elif 'File deleted' in line and line.strip().endswith("ok"):
                    # buggy Marlin version that doesn't send a proper \r after the "File deleted" statement, fixed in
                    # current versions
                    self._clear_to_send.set()

                ##~~ Message handling
                elif line.strip() != '' \
                        and line.strip() != 'ok' and not line.startswith("wait") \
                        and not line.startswith('Resend:') \
                        and line != 'echo:Unknown command:""\n' \
                        and self.isOperational():
                    self._callback.on_comm_message(line)

                ##~~ Parsing for feedback commands
                if feedback_controls and feedback_matcher and not "_all" in feedback_errors:
                    try:
                        self._process_registered_message(line, feedback_matcher, feedback_controls, feedback_errors)
                    except:
                        # something went wrong while feedback matching
                        self._logger.exception("Error while trying to apply feedback control matching, disabling it")
                        feedback_errors.append("_all")

                ##~~ Parsing for pause triggers
                if pause_triggers and not self.isStreaming():
                    if "enable" in pause_triggers.keys() and pause_triggers["enable"].search(line) is not None:
                        self.setPause(True)
                    elif "disable" in pause_triggers.keys() and pause_triggers["disable"].search(line) is not None:
                        self.setPause(False)
                    elif "toggle" in pause_triggers.keys() and pause_triggers["toggle"].search(line) is not None:
                        self.setPause(not self.isPaused())
                        self.setPause(not self.isPaused())

                ### Connection attempt
                elif self._state == self.STATE_CONNECTING:
                    if "start" in line and not startSeen:
                        startSeen = True
                        self._sendCommand("M110")
                        self._clear_to_send.set()
                    elif "ok" in line:
                        self._onConnected()
                    elif time.time() > self._timeout:
                        self.close()

                ### Operational
                elif self._state == self.STATE_OPERATIONAL or self._state == self.STATE_PAUSED:
                    if "ok" in line:
                        # if we still have commands to process, process them
                        if self._resendSwallowNextOk:
                            self._resendSwallowNextOk = False
                        elif self._resendDelta is not None:
                            self._resendNextCommand()
                        elif self._sendFromQueue():
                            pass

                    # resend -> start resend procedure from requested line
                    elif line.lower().startswith("resend") or line.lower().startswith("rs"):
                        self._handleResendRequest(line)

            except:
                self._logger.exception("Something crashed inside the USB connection.")

                errorMsg = "See octoprint.log for details"
                self._log(errorMsg)
                self._errorValue = errorMsg
                self._changeState(self.STATE_ERROR)
                eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
        self._log("Connection closed, closing down monitor")


    def _statusProgressQueueCallback(self, status_obj):
        """
        Auxiliar callback method to push the status object that comes from the printer into the queue

        :param status_obj:
        :return:
        """
        # calls the Printer object to update the progress values
        self._callback.updateProgress(status_obj)
        self._callback.on_comm_progress()


    def _onConnected(self):
        """
        Post connection callback
        """

        # starts the connection monitor thread
        self._beeConn.startConnectionMonitor()

        self._temperature_timer = RepeatedTimer(self._timeout_intervals.get("temperature", 4.0), self._poll_temperature, run_first=True)
        self._temperature_timer.start()

        if self._sdAvailable:
            self.refreshSdFiles()
        else:
            self.initSdCard()

        payload = dict(port=self._port, baudrate=self._baudrate)
        eventManager().fire(Events.CONNECTED, payload)

    def _poll_temperature(self):
        """
        Polls the temperature after the temperature timeout, re-enqueues itself.

        If the printer is not operational, not printing from sd, busy with a long running command or heating, no poll
        will be done.
        """
        try:
            if self.isOperational() and not self.isStreaming() and not self._long_running_command and not self._heating:
                self.sendCommand("M105", cmd_type="temperature_poll")
        except Exception as e:
            self._log("Error polling temperature %s" % str(e))


    def getCommandsInterface(self):
        """
        Returns the commands interface for BVC printers
        :return:
        """
        return self._beeCommands


    def _connShutdownHook(self):
        """
        Function to be called by the BVC driver to shutdown the connection
        :return:
        """
        self._callback.on_comm_force_disconnect()


    def _preparePrintThread(self):
        """
        Thread code that runs while the print job is being prepared
        :return:
        """
        # waits for heating/file transfer
        while self._beeCommands.isTransferring():
            time.sleep(2)

        self._changeState(self.STATE_HEATING)

        while self._beeCommands.isHeating():
            time.sleep(2)

        self._changeState(self.STATE_PRINTING)

        # sends usage statistics
        self._sendUsageStatistics('start')

        # starts the progress status thread
        self._beeCommands.startStatusMonitor(self._statusProgressQueueCallback)

        if self._heatupWaitStartTime is not None:
            self._heatupWaitTimeLost = self._heatupWaitTimeLost + (time.time() - self._heatupWaitStartTime)
            self._heatupWaitStartTime = None
            self._heating = False

    def _sendUsageStatistics(self, operation):
        """
        Calls and external executable to send usage statistics to a remote cloud server
        :param operation: Supports 'start' (Start Print), 'cancel' (Cancel Print), 'stop' (Print finished) operations
        :return: true in case the operation was successfull or false if not
        """
        _logger = logging.getLogger()
        biExePath = settings().getBaseFolder('bi') + '/bi_azure'

        if operation != 'start' and operation != 'cancel' and operation != 'stop':
            return

        printerSN = self.getConnectedPrinterSN()

        if printerSN is None:
            return False
        else:
            if os.path.exists(biExePath) and os.path.isfile(biExePath):
                cmd = "%s %s %s" % (biExePath, printerSN, operation)
                import subprocess  ## call date command ##
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)

                (output, err) = p.communicate()

                p_status = p.wait()

                if p_status == 0 and output == 'IOTHUB_CLIENT_CONFIRMATION_OK':
                    _logger.info("Statistics sent to remote server. (Operation: %s)" % operation)
                    return True
                else:
                    _logger.info("Failed sending statistics to remote server. (Operation: %s)" % operation)

        return False
