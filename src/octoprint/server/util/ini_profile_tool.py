#!/usr/bin/python2
# -*- coding: utf-8 -*-

import os
import sys
import glob
import argparse
import requests

def convert_ini_to_profile(input_path):
	count = 0
	# CHANGE THE KEY BEFORE USING THE SCRIPT
	headers = {'X-Api-Key': '2EBDBD9A3C224992A9B058DA2C9705C1'}

	for filename in glob.glob(input_path + "/*.ini"):
		ininame = os.path.basename(filename)
		r = requests.post("http://127.0.0.1:5000/plugin/cura/import",
						  data={'file.name': ininame, 'file.path': input_path + "/" + ininame },
						  headers=headers)

		if r.json()['description'] is not None and 'Imported' in r.json()['description']:
			count +=1

	return count

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Converts all the BEESOFT INI Cura profiles files in a given path to Octoprint compatible .profile files.")
	parser.add_argument('ini_path', metavar='INPUT_PATH', type=str, help='path where the INI files are located')
	args = parser.parse_args()

	if os.path.isfile(args.ini_path):
		print("ERROR: The given input path is a file. Please specify a path to a folder.")
		sys.exit(1)

	total_count = convert_ini_to_profile(args.ini_path)

	print(str(total_count) + " Cura profile files have been generated.")
	sys.exit(0)
