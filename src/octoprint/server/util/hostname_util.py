# coding=utf-8
import os
import re

def update_hostname(new_hostname):
	"""
	Updates the machine's hostname to a new value

	:param new_hostname:
	:return:
	"""

	if new_hostname is not None:
		command = "sudo hostname " + new_hostname
		os.system(command)

		print "Hostname updated: " + new_hostname

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
