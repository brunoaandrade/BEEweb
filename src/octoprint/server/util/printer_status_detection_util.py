# coding=utf-8
import logging
from time import sleep

def bvc_printer_status_detection(bee_comm):
	"""
	Thread function to check the current status of a connected BVC printer

	:param bee_comm: BVC printer connection object
	:return:
	"""
	USB_POLL_INTERVAL = 3 # seconds
	_logger = logging.getLogger()

	_logger.debug("Starting BVC Printer status monitor...")
	while True:
		sleep(USB_POLL_INTERVAL)

		if bee_comm is None:
			return

		if bee_comm.getCommandsInterface() is None:
			continue

		if bee_comm.isShutdown():
			continue

		# At the moment we only want to detect possible abrupt changes to shutdown
		if bee_comm.getCommandsInterface().isShutdown():
			_logger.info("BVC Printer Shutdown detected.")
			bee_comm.setShutdownState()
