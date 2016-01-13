# coding=utf-8
import logging
import urllib2
from time import sleep
import usb
from octoprint.server.util.wifi_util import switch_wifi_ap_mode

def internet_on():
	"""
	Helper function to test the connection to the Internet
	:return:
	"""
	try:
		urllib2.urlopen('https://www.google.com',timeout=1)
		return True
	except urllib2.URLError as err:
		print(err.message)
		pass

	return False

def check_internet_conn_thread():
	"""
	Thread function to check if connection to the internet is detected.
	If not Internet connection is detected after 1 minute switches to the Wifi AP mode
	:return:
	"""
	_logger = logging.getLogger()
	counter = 0
	INTERNET_POLL_INTERVAL = 10 #seconds
	RETRIES_LIMIT = 6

	import os.path
	if not os.path.isfile('/etc/wpa_supplicant/wpa_supplicant.conf'):
		return # There is no point in trying the connectivity if there is no wifi configuration

	_logger.info("Starting network connectivity monitor thread...")
	while True:
		if internet_on():
			connection = True
		else:
			connection = False
			counter += 1

		# if no connection is detected after 1 minute switches the device to AP mode
		if connection is False and counter == RETRIES_LIMIT:
			_logger.warning("Internet connection not detected. Switching to AP mode...")
			switch_wifi_ap_mode()
			break

		sleep(INTERNET_POLL_INTERVAL)

def check_usb_dongle_thread():
	"""
	Thread function to check if usb connection with a specific Wifi dongle is detected.
	:return:
	"""
	_logger = logging.getLogger()

	USB_POLL_INTERVAL = 10 # seconds
	USB_VENDOR_ID = 0x0bda
	USB_PRODUCT_ID = 0x8176

	wifi_dongle_removed = False

	_logger.info("Starting USB dongle connectivity monitor thread...")
	while True:

		# If the dongle is not found but the removed flag is False switches it to True
		if usb.core.find(idVendor=USB_VENDOR_ID, idProduct=USB_PRODUCT_ID, find_all=True) is None\
				and wifi_dongle_removed is False:
			_logger.info("USB dongle removed")
			wifi_dongle_removed = True

		# Detects if the dongle was reconnected and switches to the AP mode
		if usb.core.find(idVendor=USB_VENDOR_ID, idProduct=USB_PRODUCT_ID, find_all=True) is not None\
				and wifi_dongle_removed is True:
			_logger.info("USB dongle detected. Switching to AP mode.")
			switch_wifi_ap_mode()
			wifi_dongle_removed = False

		sleep (USB_POLL_INTERVAL)
