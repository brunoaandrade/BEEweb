# coding=utf-8
WIFI_CMODE_SCRIPT = 'wifi_client_mode.sh'
WIFI_AP_SCRIPT = 'wifi_ap_mode.sh'
RM_WPA_SUPPLICANT_CONF = 'remove_wpa_supplicant_conf.sh'

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

	# starts the wifi connectivity thread
	#if wifi_conn_thread is None:
	#	wifi_conn_thread.start()


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
