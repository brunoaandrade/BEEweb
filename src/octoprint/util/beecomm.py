# coding=utf-8
from __future__ import absolute_import
import time

__author__ = "BEEVC - Electronic Systems "
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

from octoprint.util.comm import MachineCom
from beedriver.connection import Conn as BeeConn
from octoprint.util import comm


class BeeCom(MachineCom):
    STATE_CONNECTED_BTF = 12

    _beeConn = None
    _beeCommands = None

    def __init__(self, callbackObject=None, printerProfileManager=None):
        super(BeeCom, self).__init__(None, None, callbackObject, printerProfileManager)

        self._changeState(self.STATE_CONNECTING)

        if self._beeConn is None:
            self._beeConn = BeeConn()

        if self._beeConn.isConnected():
            self._beeComands = self._beeConn.getCommandIntf()

            # change to firmware
            self._beeComands.startPrinter()

            # restart connection
            self._beeConn.reconnect()

            time.sleep(0.5)

    def sendCommand(self, cmd, cmd_type=None, processed=False):
        cmd = cmd.encode('ascii', 'replace')
        if not processed:
            cmd = comm.process_gcode_line(cmd)
            if not cmd:
                return

        if self.isPrinting() and not self.isSdFileSelected():
        # self._commandQueue.put((cmd, cmd_type))
            pass
        elif self.isOperational():

            wait = None
            if "g" in cmd.lower():
                wait = "3"

            resp = self._beeConn.sendCmd(cmd, wait)
            # logs the command reply with errors
            splits = resp.rstrip().split("\n")
            for r in splits:
                if "Error" in r:
                    self._logger.warning(r)

    def close(self, isError = False):
        self._beeConn.close()
        self._changeState(self.STATE_CLOSED)

    def confirmConnection(self):
        if self._beeConn.isConnected():
            self._changeState(self.STATE_CONNECTED_BTF)

    def getStateString(self):
        if self._state == self.STATE_CONNECTED_BTF:
            return "Connected to BEETHEFIRST"
        else:
            super(BeeCom, self).getStateString()

    def isOperational(self):
        return self._state == self.STATE_CONNECTED_BTF or\
            self._state == self.STATE_OPERATIONAL or self._state == self.STATE_PRINTING or\
            self._state == self.STATE_PAUSED or self._state == self.STATE_TRANSFERING_FILE
