# coding=utf-8
import usb
import logging
import urllib2
from time import sleep

WIFI_CMODE_SCRIPT = 'wifi_client_mode.sh'
WIFI_AP_SCRIPT = 'wifi_ap_mode.sh'
RM_WPA_SUPPLICANT_CONF = 'remove_wpa_supplicant_conf.sh'

wifi_cthread_flag = False

def match(line, keyword):
	"""
	If the first part of line (modulo blanks) matches keyword,
    returns the end of that line. Otherwise returns None
	:param line:
	:param keyword:
	:return:
	"""

	line = line.lstrip()

	if keyword in line:
		length = len(keyword)
		if line[:length] == keyword:
			return line[length+1:]
		else:
			return None
	else:
		return None


def get_ssid_list(net_iface, out_file_path = None):
	"""
	Returns the list of SSID found in the iwlist scan execution.
	You can also pass the same output in a file
	to be parsed.

	:param net_iface: network interface to scan
	:param out_file_path: Path to the file where iwlist output was saved.
	:return:
	"""
	if out_file_path is None:
		import os
		f = os.popen('sudo iwlist ' + net_iface + ' scan')
		iwlist_output = f.readlines()
	else:
		iwlist_output = open(out_file_path, mode='r')

	networks_found=[]

	if iwlist_output is not None:
		for line in iwlist_output:
			cell_line = match(line, "ESSID")

			if cell_line is not None:
				cell_line = cell_line.strip("\"\n")
				if cell_line not in networks_found and cell_line is not '':
					networks_found.append(cell_line)

	return networks_found


def switch_wifi_client_mode(network_name, password):
	"""
	Switches the Wifi interfaces to client mode and tries to connect to the specified
	network using the system configured scripts

	:param network_name:
	:param password:
	:return:
	"""
	import re
	import os.path
	import subprocess

	regex_net = re.compile(r'ssid=".+"', re.IGNORECASE)
	regex_pass = re.compile(r'psk=".+"', re.IGNORECASE)

	lines = []
	with open('/etc/wpa_supplicant/wpa_supplicant.conf.dist') as infile:
		for line in infile:
			if 'ssid' in line:
				line = regex_net.sub('ssid="%s"' % network_name, line)
			if 'psk' in line:
				line = regex_pass.sub('psk="%s"' % password, line)

			lines.append(line)

	from os.path import expanduser
	home = expanduser("~")
	with open(home + '/wpa_supplicant_update.conf', 'w') as outfile:
		for line in lines:
			outfile.write(line)

	# Executes the shell script to change the wi-fi mode
	script_path = home + '/' + WIFI_CMODE_SCRIPT
	if os.path.isfile(script_path):
		try:
			subprocess.call([script_path])
		except:
			print ('Error executing wi-fi client mode script.')

	# Starts the wifi dongle monitor thread
	import octoprint.server.util.wifi_util as wifi_module

	if wifi_module.wifi_cthread_flag is False:
		import threading
		threading.Thread(target=check_usb_dongle_thread).start()
		wifi_module.wifi_cthread_flag = True


def switch_wifi_ap_mode():
	"""
	Switches the Wifi interface to AP mode
	:return:
	"""
	import os.path
	import subprocess
	from os.path import expanduser
	home = expanduser("~")

	# Executes the shell script to change the wi-fi mode
	script_path = home + '/' + WIFI_AP_SCRIPT
	if os.path.isfile(script_path):
		try:
			subprocess.call([script_path])
		except:
			print ('Error executing wi-fi AP mode script.')


def check_usb_dongle_thread():
	"""
	Thread function to check if usb connection with a specific Wifi dongle is detected.
	:return:
	"""
	_logger = logging.getLogger()

	USB_POLL_INTERVAL = 5 # seconds
	USB_VENDOR_ID_0 = 0x0bda
	USB_PRODUCT_ID_0 = 0x8176
	USB_VENDOR_ID_1 = 0x7392
	USB_PRODUCT_ID_1 = 0x7811

	wifi_dongle_removed = False

	_logger.info("Starting USB dongle connectivity monitor thread...")
	while True:
		dev_list = []
		for dev in usb.core.find(idVendor=USB_VENDOR_ID_0, idProduct=USB_PRODUCT_ID_0, find_all=True):
			dev_list.append(dev)

		for dev in usb.core.find(idVendor=USB_VENDOR_ID_1, idProduct=USB_PRODUCT_ID_1, find_all=True):
			dev_list.append(dev)

		# If the dongle is not found but the removed flag is False switches it to True
		if len(dev_list) == 0 and wifi_dongle_removed is False:
			_logger.info("USB dongle removed")
			wifi_dongle_removed = True

		# Detects if the dongle was reconnected and switches to the AP mode
		if len(dev_list) > 0 and wifi_dongle_removed is True:
			_logger.info("USB dongle detected. Switching to AP mode.")
			switch_wifi_ap_mode()
			wifi_dongle_removed = False

		sleep (USB_POLL_INTERVAL)

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
