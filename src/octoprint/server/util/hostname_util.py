# coding=utf-8
import os
import re

HOSTNAME_UPDATE_SCRIPT = 'hostname_upd.sh'

def get_hostname():
	"""
	Returns the current configured hostname in /etc/hostname
	:return:
	"""
	import os.path
	if os.path.isfile('/etc/hostname'):
		with open('/etc/hostname', 'r') as hostname_file:
			for line in hostname_file:
				if line:
					return line.strip()
	else:
		return 'beewebpi'


def update_hostname(new_hostname):
	"""
	Updates the machine's hostname to a new value

	:param new_hostname:
	:return:
	"""

	if new_hostname is not None:
		lines_buffer = []
		with open('/etc/hosts') as hosts_file:
			for line in hosts_file:
				if '127.0.0.1' in line:
					line = '127.0.0.1        ' + new_hostname
				lines_buffer.append(line)

		from os.path import expanduser
		home = expanduser("~")
		with open(home + '/hosts_update', 'w') as hosts_outfile:
			for line in lines_buffer:
				hosts_outfile.write(line)

		# writes the file that will replace /etc/hostname
		with open(home + '/hostname_update', 'w') as hostname_outfile:
			hostname_outfile.write(new_hostname)

		# Executes the shell script to update the hostname
		import os.path
		script_path = home + '/' + HOSTNAME_UPDATE_SCRIPT
		if os.path.isfile(script_path):
			try:
				import subprocess
				subprocess.call([script_path])
			except:
				print ('Error executing hostname update script.')

		return True
	else:
		return False


def is_valid_hostname(hostname):
	"""
	Validates a hostname string
	:param hostname:
	:return:
	"""
	if len(hostname) > 255:
		return False

	if hostname[-1] == ".":
		hostname = hostname[:-1] # strip exactly one dot from the right, if present

	allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
	return all(allowed.match(x) for x in hostname.split("."))
