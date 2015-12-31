# coding=utf-8
import logging
import urllib2
from time import sleep
from octoprint.server.util.wifi_util import switch_wifi_ap_mode

def internet_on():
	try:
		urllib2.urlopen('https://www.google.com',timeout=1)
		return True
	except urllib2.URLError as err:
		print(err.message)
		pass

	return False


def check_connection_thread():
	"""
	Thread function to check if connection to the internet is detected.
	It tries for 1 minute until it returns. If connection is detected it returns .
	:return:
	"""
	_logger = logging.getLogger(__name__)
	counter = 20
	connection = False

	import os.path
	if not os.path.isfile('/etc/wpa_supplicant/wpa_supplicant.conf'):
		return # There is no point in trying the connectivity if there is no wifi configuration

	_logger.info("Starting network connectivity monitor thread...")
	while counter > 0:
		if internet_on():
			_logger.info("Internet connection detected. Exiting thread...")
			connection = True
			break
		else:
			sleep(5)
			counter -= 1

	# if no connection is detected switches the device to AP mode
	if connection is False:
		_logger.warning("Internet connection not detected. Switching to AP mode...")
		switch_wifi_ap_mode()
