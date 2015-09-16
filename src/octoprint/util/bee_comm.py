# coding=utf-8
from __future__ import absolute_import
import os
import threading
import time
import Queue as queue

from octoprint.settings import settings
from octoprint.events import eventManager, Events
from octoprint.util.comm import MachineCom, get_interval
from beedriver.connection import Conn as BeeConn
from octoprint.util import comm, get_exception_string, sanitize_ascii, RepeatedTimer

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"

class BeeCom(MachineCom):
    STATE_WAITING_FOR_BTF = 21
    STATE_PREPARING_PRINT = 22

    _beeConn = None
    _beeCommands = None

    _responseQueue = queue.Queue()
    _statusQueue = queue.Queue()

    _monitor_print_progress = True
    _connection_monitor_active = True

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
        Opens a new connection using the BeeVC driver

        :return: True if the connection was successful
        """
        if self._beeConn is None:
            self._beeConn = BeeConn()
            self._beeConn.connectToFirstPrinter()

        if self._beeConn.isConnected():
            self._beeCommands = self._beeConn.getCommandIntf()

            # change to firmware
            if self._beeCommands.getPrinterMode() == 'Bootloader':
                self._beeCommands.goToFirmware()

            # restart connection
            self._beeConn.reconnect()

            # connection status thread
            self.conn_status_thread = threading.Thread(target=self._connectionMonitor, name="comm._conn_monitor")
            self.conn_status_thread.daemon = True
            self.conn_status_thread.start()

            # post connection callback
            self._onConnected()

            return True
        else:
            return False


    def sendCommand(self, cmd, cmd_type=None, processed=False):
        """
        Sends a custom command through the open connection
        :param cmd:
        :param cmd_type:
        :param processed:
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

            resp = self._beeConn.sendCmd(cmd, wait)

            if resp:
                # puts the response in the monitor queue
                self._responseQueue.put(resp)

                # logs the command reply with errors
                splits = resp.rstrip().split("\n")
                for r in splits:
                    if "Error" in r:
                        self._logger.warning(r)

    def close(self, isError = False):
        """
        Closes the connection if its active
        :param isError:
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

    def isOperational(self):
        return self._state == self.STATE_OPERATIONAL \
               or self._state == self.STATE_PRINTING or self._state == self.STATE_PAUSED \
               or self._state == self.STATE_TRANSFERING_FILE or self._state == self.STATE_PREPARING_PRINT

    def isClosedOrError(self):
        return self._state == self.STATE_ERROR or self._state == self.STATE_CLOSED_WITH_ERROR \
               or self._state == self.STATE_CLOSED or self._state == self.STATE_WAITING_FOR_BTF


    def getStateString(self):
        """
        Returns the current printer state
        :return:
        """
        if self._state == self.STATE_WAITING_FOR_BTF:
            return "No printer detected. Please turn on your printer and press Connect."
        elif self._state == self.STATE_PREPARING_PRINT:
            return "Preparing to print, please wait..."
        else:
            return super(BeeCom, self).getStateString()

    def startPrint(self):
        """
        Starts the printing operation
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

            self._changeState(self.STATE_PREPARING_PRINT)

            if self.isSdFileSelected():
                print_resp = self._beeCommands.startSDPrint(self._currentFile.getFilename())

                if print_resp:
                    self._sd_status_timer = RepeatedTimer(lambda: get_interval("sdStatus", default_value=1.0),
                                                          self._poll_sd_status, run_first=True)
                    self._sd_status_timer.start()
            else:
                print_resp = self._beeCommands.printFile(payload['file'],
                                                         statusCallback=self._statusProgressQueueCallback)

            if not print_resp is True:
                self._logger.exception("Error while preparing the printing operation.")
                self._changeState(self.STATE_ERROR)
                eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
            else:
                self._heatupWaitStartTime = time.time()
                self._heatupWaitTimeLost = 0.0
                self._pauseWaitStartTime = 0
                self._pauseWaitTimeLost = 0.0

            # waits for heating/file transfer
            while self._beeCommands.isTransferring():
                time.sleep(2)

            self._changeState(self.STATE_PRINTING)

            # starts the progress status thread
            self._beeCommands.startStatusMonitor()

            if self._heatupWaitStartTime is not None:
                self._heatupWaitTimeLost = self._heatupWaitTimeLost + (time.time() - self._heatupWaitStartTime)
                self._heatupWaitStartTime = None
                self._heating = False

        except:
            self._logger.exception("Error while trying to start printing")
            self._errorValue = get_exception_string()
            self._changeState(self.STATE_ERROR)
            eventManager().fire(Events.ERROR, {"error": self.getErrorString()})


    def cancelPrint(self):
        """
        Cancels the print operation
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
            "origin": self._currentFile.getFileLocation()
        }

        self.sendGcodeScript("afterPrintCancelled", replacements=dict(event=payload))
        eventManager().fire(Events.PRINT_CANCELLED, payload)


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

        if not pause and self.isPaused():
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
        self.sendCommand("M20")

    def startSdFileTransfer(self, filename):
        """
        Transfers a file to the SD card
        :param filename:
        :return:
        """
        if not self.isOperational() or self.isBusy():
            return

        self._changeState(self.STATE_TRANSFERING_FILE)
        self.sendCommand("M28 %s" % filename.lower())

    def endSdFileTransfer(self, filename):
        """
        Finishes the file transfer to the SD file
        :param filename:
        :return:
        """
        if not self.isOperational() or self.isBusy():
            return

        self.sendCommand("M29 %s" % filename.lower())
        self._changeState(self.STATE_OPERATIONAL)
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

    def _monitor(self):
        """
        Monitor thread of responses from the commands sent to the printer
        :return:
        """
        feedback_controls, feedback_matcher = comm.convert_feedback_controls(settings().get(["controls"]))
        feedback_errors = []
        pause_triggers = comm.convert_pause_triggers(settings().get(["printerParameters", "pauseTriggers"]))

        disable_external_heatup_detection = not settings().getBoolean(["feature", "externalHeatupDetection"])

        #exits if no connection is active
        if not self._beeConn.isConnected():
            return

        try_hello = not settings().getBoolean(["feature", "waitForStartOnConnect"])

        #Start monitoring the communication.
        self._timeout = comm.get_new_timeout("communication")

        startSeen = False
        supportRepetierTargetTemp = settings().getBoolean(["feature", "repetierTargetTemp"])
        supportWait = settings().getBoolean(["feature", "supportWait"])

        # enqueue an M105 first thing
        if try_hello:
            self._sendCommand("M110")
            self._clear_to_send.set()

        while self._monitoring_active:
            try:
                line = self._getResponse()
                if line is None:
                    continue

                if line.strip() is not "":
                    self._timeout = comm.get_new_timeout("communication")

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

                ##~~ SD file list
                # if we are currently receiving an sd file list, each line is just a filename, so just read it and abort processing
                if self._sdFileList and "End file list" in line:
                    preprocessed_line = line.strip().lower()
                    fileinfo = preprocessed_line.rsplit(None, 1)
                    if len(fileinfo) > 1:
                        # we might have extended file information here, so let's split filename and size and try to make them a bit nicer
                        filename, size = fileinfo
                        try:
                            size = int(size)
                        except ValueError:
                            # whatever that was, it was not an integer, so we'll just use the whole line as filename and set size to None
                            filename = preprocessed_line
                            size = None
                    else:
                        # no extended file information, so only the filename is there and we set size to None
                        filename = preprocessed_line
                        size = None

                    if comm.valid_file_type(filename, "machinecode"):
                        if comm.filter_non_ascii(filename):
                            self._logger.warn("Got a file from printer's SD that has a non-ascii filename (%s), that shouldn't happen according to the protocol" % filename)
                        else:
                            if not filename.startswith("/"):
                                # file from the root of the sd -- we'll prepend a /
                                filename = "/" + filename
                            self._sdFiles.append((filename, size))
                        continue

                ##~~ process oks
                if line.strip().startswith("ok") or (self.isPrinting() and supportWait and line.strip().startswith("wait")):
                    self._clear_to_send.set()
                    self._long_running_command = False

                ##~~ Temperature processing
                if ' T:' in line or line.startswith('T:') or ' T0:' in line or line.startswith('T0:') or ' B:' in line or line.startswith('B:'):
                    if not disable_external_heatup_detection and not line.strip().startswith("ok") and not self._heating:
                        self._logger.debug("Externally triggered heatup detected")
                        self._heating = True
                        self._heatupWaitStartTime = time.time()

                    self._processTemperatures(line)
                    self._callback.on_comm_temperature_update(self._temp, self._bedTemp)

                elif supportRepetierTargetTemp and ('TargetExtr' in line or 'TargetBed' in line):
                    matchExtr = self._regex_repetierTempExtr.match(line)
                    matchBed = self._regex_repetierTempBed.match(line)

                    if matchExtr is not None:
                        toolNum = int(matchExtr.group(1))
                        try:
                            target = float(matchExtr.group(2))
                            if toolNum in self._temp.keys() and self._temp[toolNum] is not None and isinstance(self._temp[toolNum], tuple):
                                (actual, oldTarget) = self._temp[toolNum]
                                self._temp[toolNum] = (actual, target)
                            else:
                                self._temp[toolNum] = (None, target)
                            self._callback.on_comm_temperature_update(self._temp, self._bedTemp)
                        except ValueError:
                            pass
                    elif matchBed is not None:
                        try:
                            target = float(matchBed.group(1))
                            if self._bedTemp is not None and isinstance(self._bedTemp, tuple):
                                (actual, oldTarget) = self._bedTemp
                                self._bedTemp = (actual, target)
                            else:
                                self._bedTemp = (None, target)
                            self._callback.on_comm_temperature_update(self._temp, self._bedTemp)
                        except ValueError:
                            pass

                #If we are waiting for an M109 or M190 then measure the time we lost during heatup, so we can remove that time from our printing time estimate.
                if 'ok' in line and self._heatupWaitStartTime:
                    self._heatupWaitTimeLost = self._heatupWaitTimeLost + (time.time() - self._heatupWaitStartTime)
                    self._heatupWaitStartTime = None
                    self._heating = False

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
                    match = self._regex_sdPrintingByte.search(line)
                    self._currentFile.setFilepos(int(match.group(1)))
                    self._callback.on_comm_progress()
                elif 'File opened' in line and not self._ignore_select:
                    # answer to M23, at least on Marlin, Repetier and Sprinter: "File opened:%s Size:%d"
                    match = self._regex_sdFileOpened.search(line)
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
                elif 'Done printing file' in line and self.isSdPrinting():
                    # printer is reporting file finished printing
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

                ### Printing
                elif self._state == self.STATE_PRINTING:
                    if line == "" and time.time() > self._timeout:
                        if not self._long_running_command:
                            self._log("Communication timeout during printing, forcing a line")
                            self._sendCommand("M105")
                            self._clear_to_send.set()
                        else:
                            self._logger.debug("Ran into a communication timeout, but a command known to be a long runner is currently active")

                    if "ok" in line or (supportWait and "wait" in line):
                        # a wait while printing means our printer's buffer ran out, probably due to some ok getting
                        # swallowed, so we treat it the same as an ok here teo take up communication again
                        if self._resendSwallowNextOk:
                            self._resendSwallowNextOk = False

                        elif self._resendDelta is not None:
                            self._resendNextCommand()

                        else:
                            if self._sendFromQueue():
                                pass
                            elif not self.isSdPrinting():
                                self._sendNext()

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


    def _connectionMonitor(self):
        """
        Monitor thread to check if the connection to the printer is still active
        :return:
        """
        while self._connection_monitor_active is True:
            time.sleep(5)

            if self._state == self.STATE_OPERATIONAL:
                if self._beeConn.ping() is True:
                    continue
                else:
                    self.close()
                    break

    def _onConnected(self):
        """
        Post connection callback
        """
        self._temperature_timer = RepeatedTimer(lambda: get_interval("temperature", default_value=4.0), self._poll_temperature, run_first=True)
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

        if self.isOperational() and not self.isStreaming() and not self._long_running_command and not self._heating:
            self.sendCommand("M105", cmd_type="temperature_poll")