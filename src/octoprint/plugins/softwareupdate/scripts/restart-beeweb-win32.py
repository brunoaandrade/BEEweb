import win32serviceutil

def parse_arguments():
	import argparse

	parser = argparse.ArgumentParser(prog="restart-beeweb-win32.py")

	parser.add_argument("service_name", type=str,
	                    help="Specify the name of the service restart")
	args = parser.parse_args()

	return args

def main():
	args = parse_arguments()

	try:
		win32serviceutil.StopService(args.service_name)
		win32serviceutil.StartService(args.service_name)
	except Exception as ex:
		import traceback
		traceback.print_exc()

if __name__ == "__main__":
	main()
