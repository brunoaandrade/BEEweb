# coding=utf-8
import logging
from beedriver.connection import Conn as BeePrinterConn
from time import sleep

def detect_bvc_printer_connection(connection_callback):
	"""
	Thread function to check if a BVC printer was connected to a USB port

	:param connection_callback: Callback function to call when a printer is detected
	:return:
	"""
	USB_POLL_INTERVAL = 1 # seconds
	printerConnIntf = BeePrinterConn()

	_logger = logging.getLogger()

	_logger.info("Starting BVC Printer connection monitor...")
	while True:
		printers = printerConnIntf.getPrinterList()

		if len(printers) > 0: # printer found
			_logger.info("BVC Printer detected. Starting connection...")
			connection_callback()
			return

		sleep (USB_POLL_INTERVAL)
