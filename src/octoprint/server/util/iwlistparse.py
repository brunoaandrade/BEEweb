# coding=utf-8
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
		iwlist_output = f.read()
	else:
		iwlist_output = open(out_file_path, mode='r')

	networks_found=[]

	if iwlist_output is not None:
		for line in iwlist_output:
			cell_line = match(line, "ESSID")

			if cell_line is not None:
				cell_line = cell_line.strip("\"\n")
				if cell_line not in networks_found:
					networks_found.append(cell_line)

	return networks_found
