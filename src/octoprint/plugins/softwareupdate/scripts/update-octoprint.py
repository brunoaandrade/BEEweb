#!/bin/env python2
from __future__ import absolute_import, division, print_function

__author__ = "Gina Haeussge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import errno
import sys
import traceback
import time
from octoprint.settings import settings
from distutils.dir_util import copy_tree
from distutils.file_util import copy_file

def _log_call(*lines):
	_log(lines, prefix=">", stream="call")


def _log_stdout(*lines):
	_log(lines, prefix=" ", stream="stdout")


def _log_stderr(*lines):
	_log(lines, prefix=" ", stream="stderr")


def _log(lines, prefix=None, stream=None):
	output_stream = sys.stdout
	if stream == "stderr":
		output_stream = sys.stderr

	for line in lines:
		to_print = _to_str(u"{} {}".format(prefix, _to_unicode(line.rstrip(), errors="replace")),
		                   errors="replace")
		print(to_print, file=output_stream)


def _to_unicode(s_or_u, encoding="utf-8", errors="strict"):
	"""Make sure ``s_or_u`` is a unicode string."""
	if isinstance(s_or_u, str):
		return s_or_u.decode(encoding, errors=errors)
	else:
		return s_or_u


def _to_str(s_or_u, encoding="utf-8", errors="strict"):
	"""Make sure ``s_or_u`` is a str."""
	if isinstance(s_or_u, unicode):
		return s_or_u.encode(encoding, errors=errors)
	else:
		return s_or_u


def _execute(command, **kwargs):
	import sarge

	if isinstance(command, (list, tuple)):
		joined_command = " ".join(command)
	else:
		joined_command = command
	_log_call(joined_command)

	kwargs.update(dict(async=True, stdout=sarge.Capture(), stderr=sarge.Capture()))

	try:
		p = sarge.run(command, **kwargs)
		while len(p.commands) == 0:
			# somewhat ugly... we can't use wait_events because
			# the events might not be all set if an exception
			# by sarge is triggered within the async process
			# thread
			time.sleep(0.01)

		# by now we should have a command, let's wait for its
		# process to have been prepared
		p.commands[0].process_ready.wait()

		if not p.commands[0].process:
			# the process might have been set to None in case of any exception
			print("Error while trying to run command {}".format(joined_command), file=sys.stderr)
			return None, [], []
	except:
		print("Error while trying to run command {}".format(joined_command), file=sys.stderr)
		traceback.print_exc(file=sys.stderr)
		return None, [], []

	all_stdout = []
	all_stderr = []
	try:
		while p.commands[0].poll() is None:
			lines = p.stderr.readlines(timeout=0.5)
			if lines:
				lines = map(lambda x: _to_unicode(x, errors="replace"), lines)
				_log_stderr(*lines)
				all_stderr += list(lines)

			lines = p.stdout.readlines(timeout=0.5)
			if lines:
				lines = map(lambda x: _to_unicode(x, errors="replace"), lines)
				_log_stdout(*lines)
				all_stdout += list(lines)

	finally:
		p.close()

	lines = p.stderr.readlines()
	if lines:
		lines = map(lambda x: _to_unicode(x, errors="replace"), lines)
		_log_stderr(*lines)
		all_stderr += lines

	lines = p.stdout.readlines()
	if lines:
		lines = map(lambda x: _to_unicode(x, errors="replace"), lines)
		_log_stdout(*lines)
		all_stdout += lines

	return p.returncode, all_stdout, all_stderr


def _get_git_executables():
	GITS = ["git"]
	if sys.platform == "win32":
		GITS = ["git.cmd", "git.exe"]
	return GITS


def _git(args, cwd, git_executable=None):
	if git_executable is not None:
		commands = [git_executable]
	else:
		commands = _get_git_executables()

	for c in commands:
		command = [c] + args
		try:
			return _execute(command, cwd=cwd)
		except EnvironmentError:
			e = sys.exc_info()[1]
			if e.errno == errno.ENOENT:
				continue

			print("Error while trying to run command {}".format(" ".join(command)), file=sys.stderr)
			traceback.print_exc(file=sys.stderr)
			return None, [], []
		except:
			print("Error while trying to run command {}".format(" ".join(command)), file=sys.stderr)
			traceback.print_exc(file=sys.stderr)
			return None, [], []
	else:
		print("Unable to find git command, tried {}".format(", ".join(commands)), file=sys.stderr)
		return None, [], []


def _python(args, cwd, python_executable, sudo=False):
	command = [python_executable] + args
	if sudo:
		command = ["sudo"] + command
	try:
		return _execute(command, cwd=cwd)
	except:
		import traceback
		print("Error while trying to run command {}".format(" ".join(command)), file=sys.stderr)
		traceback.print_exc(file=sys.stderr)
		return None, [], []


def _to_error(*lines):
	if len(lines) == 1:
		if isinstance(lines[0], (list, tuple)):
			lines = lines[0]
		elif not isinstance(lines[0], (str, unicode)):
			lines = [repr(lines[0]),]
	return u"\n".join(map(lambda x: _to_unicode(x, errors="replace"), lines))


def _rescue_changes(git_executable, folder):
	print(">>> Running: git diff --shortstat")
	returncode, stdout, stderr = _git(["diff", "--shortstat"], folder, git_executable=git_executable)
	if returncode is None or returncode != 0:
		raise RuntimeError("Could not update, \"git diff\" failed with returncode {}".format(returncode))
	if stdout and u"".join(stdout).strip():
		# we got changes in the working tree, maybe from the user, so we'll now rescue those into a patch
		import time
		import os
		timestamp = time.strftime("%Y%m%d%H%M")
		patch = os.path.join(folder, "{}-preupdate.patch".format(timestamp))

		print(">>> Running: git diff and saving output to {}".format(patch))
		returncode, stdout, stderr = _git(["diff"], folder, git_executable=git_executable)
		if returncode is None or returncode != 0:
			raise RuntimeError("Could not update, installation directory was dirty and state could not be persisted as a patch to {}".format(patch))

		import codecs
		with codecs.open(patch, "w", encoding="utf-8", errors="replace") as f:
			for line in stdout:
				f.write(line)

		return True

	return False


def update_source(git_executable, folder, target, force=False, branch=None):
	if _rescue_changes(git_executable, folder):
		print(">>> Running: git reset --hard")
		returncode, stdout, stderr = _git(["reset", "--hard"], folder, git_executable=git_executable)
		if returncode is None or returncode != 0:
			raise RuntimeError("Could not update, \"git reset --hard\" failed with returncode {}".format(returncode))

		print(">>> Running: git clean -f -d -e *-preupdate.patch")
		returncode, stdout, stderr = _git(["clean", "-f", "-d", "-e", "*-preupdate.patch"], folder, git_executable=git_executable)
		if returncode is None or returncode != 0:
			raise RuntimeError("Could not update, \"git clean -f\" failed with returncode {}".format(returncode))

	print(">>> Running: git fetch")
	returncode, stdout, stderr = _git(["fetch"], folder, git_executable=git_executable)
	if returncode is None or returncode != 0:
		raise RuntimeError("Could not update, \"git fetch\" failed with returncode {}".format(returncode))

	if branch is not None and branch.strip() != "":
		print(">>> Running: git checkout {}".format(branch))
		returncode, stdout, stderr = _git(["checkout", branch], folder, git_executable=git_executable)
		if returncode is None or returncode != 0:
			raise RuntimeError("Could not update, \"git checkout\" failed with returncode {}".format(returncode))

	print(">>> Running: git pull")
	returncode, stdout, stderr = _git(["pull"], folder, git_executable=git_executable)
	if returncode is None or returncode != 0:
		raise RuntimeError("Could not update, \"git pull\" failed with returncode {}".format(returncode))

	if force:
		reset_command = ["reset", "--hard"]
		reset_command += [target]

		print(">>> Running: git {}".format(" ".join(reset_command)))
		returncode, stdout, stderr = _git(reset_command, folder, git_executable=git_executable)
		if returncode is None or returncode != 0:
			raise RuntimeError("Error while updating, \"git {}\" failed with returncode {}".format(" ".join(reset_command), returncode))


def install_source(python_executable, folder, user=False, sudo=False):
	print(">>> Running: python setup.py clean")
	returncode, stdout, stderr = _python(["setup.py", "clean"], folder, python_executable)
	if returncode is None or returncode != 0:
		print("\"python setup.py clean\" failed with returncode {}".format(returncode))
		print("Continuing anyways")

	print(">>> Running: python setup.py install")
	args = ["setup.py", "install"]
	if user:
		args.append("--user")
	returncode, stdout, stderr = _python(args, folder, python_executable, sudo=sudo)
	if returncode is None or returncode != 0:
		raise RuntimeError("Could not update, \"python setup.py install\" failed with returncode {}".format(returncode))

################################
## CUSTOM BEEWEB RELATED CODE ##
################################
def install_source_beeweb(python_executable, folder, user=False, sudo=False):
	print(">>> Running: python setup.py clean")
	returncode, stdout, stderr = _python(["setup.py", "clean"], folder, python_executable)
	if returncode is None or returncode != 0:
		print("\"python setup.py clean\" failed with returncode {}".format(returncode))
		print("Continuing anyways")

	print(">>> Running: python setup.py install")
	args = ["setup.py", "install"]
	if user:
		args.append("--user")
	returncode, stdout, stderr = _python(args, folder, python_executable, sudo=sudo)
	if returncode is None or returncode != 0:
		raise RuntimeError("Could not update, \"python setup.py install\" failed with returncode {}".format(returncode))

	# Copies the firmware files to the settings directory
	print(">>> Copying Firmware files to settings directory...")
	# folder where the installation settings files are located
	settings_folder = settings(init=True).getBaseFolder('base')
	try:
		# copies the files in the /etc directory
		copy_tree(folder + '/firmware', settings_folder + '/firmware')
	except Exception as ex:
		raise RuntimeError(
			"Could not update, copying the firmware files to respective settings directory failed with error: %s" % ex.message)
	finally:
		print("Firmware files installed.")


	# If the update is running on Windows tries to remove cache files from the client app
	if sys.platform == "win32":
		print(">>> Removing client cache files...")
		try:
			import os
			from glob import glob
			from shutil import rmtree

			pattern = 'C:\\Users\\*\\AppData\\Roaming\\beesoft-nativefier*\\Cache\\*'

			for item in glob(pattern):
				if os.path.exists(item):
					try:
						os.remove(item)
					except Exception:
						continue

		except Exception as ex:
			raise RuntimeError('Could not remove the cache files from client app: %s' % ex.strerror)


def install_support_files(folder, target_folder):
	print(">>> Copying BEEweb settings files to installation directory...")
	settings_folder_path = folder + '/src/filesystem/home/pi/.beeweb'

	try:
		# creates a backup of the user config.yaml file
		copy_file(target_folder + '/config.yaml', target_folder + '/config-backup.yaml')

		files_copied = copy_tree(settings_folder_path, target_folder)

		# overwrites the settings file from the repository with the backup
		copy_file(target_folder + '/config-backup.yaml', target_folder + '/config.yaml')

	except Exception as ex:
		raise RuntimeError(
			"Could not update, copying the files to .beeweb directory failed with error: %s" % ex.message)
	finally:
		if files_copied:
			print("BEEweb settings files copied!")

	if sys.platform != "win32" and sys.platform != "darwin":
		try:
			# copies the files in the /etc directory
			copy_tree(folder + '/src/filesystem/root/etc/default', '/etc/default')
			copy_tree(folder + '/src/filesystem/root/etc/haproxy', '/etc/haproxy')
			copy_tree(folder + '/src/filesystem/root/etc/init.d', '/etc/init.d')
			copy_tree(folder + '/src/filesystem/root/etc/init.d', '/etc/hostapd')

		except Exception as ex:
			raise RuntimeError(
				"Could not update, copying the system files to /etc directories failed with error: %s" % ex.message)
		finally:
			if files_copied:
				print("BEEwebPi system files copied!")


def parse_arguments():
	import argparse

	boolean_trues = ["true", "yes", "1"]

	parser = argparse.ArgumentParser(prog="update-octoprint.py")

	parser.add_argument("--git", action="store", type=str, dest="git_executable",
	                    help="Specify git executable to use")
	parser.add_argument("--python", action="store", type=str, dest="python_executable",
	                    help="Specify python executable to use")
	parser.add_argument("--force", action="store", type=lambda x: x in boolean_trues,
	                    dest="force", default=False,
	                    help="Set this to true to force the update to only the specified version (nothing newer, nothing older)")
	parser.add_argument("--sudo", action="store_true", dest="sudo",
	                    help="Install with sudo")
	parser.add_argument("--user", action="store_true", dest="user",
	                    help="Install to the user site directory instead of the general site directory")
	parser.add_argument("--branch", action="store", type=str, dest="branch", default=None,
	                    help="Specify the branch to make sure is checked out")
	parser.add_argument("folder", type=str,
	                    help="Specify the base folder of the OctoPrint installation to update")
	parser.add_argument("target", type=str,
	                    help="Specify the commit or tag to which to update")
	parser.add_argument("--custom-install", type=str, dest="custom_install",
	                    help="Specify the custom repository or octoprint distro to update")

	args = parser.parse_args()

	return args

def main():
	args = parse_arguments()

	git_executable = None
	if args.git_executable:
		git_executable = args.git_executable

	python_executable = sys.executable
	if args.python_executable:
		python_executable = args.python_executable
		if python_executable.startswith('"'):
			python_executable = python_executable[1:]
		if python_executable.endswith('"'):
			python_executable = python_executable[:-1]

	print("Python executable: {!r}".format(python_executable))

	folder = args.folder

	import os
	if not os.access(folder, os.W_OK):
		raise RuntimeError("Could not update, base folder is not writable")

	update_source(git_executable, folder, args.target, force=args.force, branch=args.branch)

	if args.custom_install and args.custom_install == "beeweb":
		install_source_beeweb(python_executable, folder, user=args.user, sudo=args.sudo)

	elif args.custom_install and args.custom_install == "beeweb-configurations":
		# folder where the installation settings files are located
		target_folder = settings(init=True).getBaseFolder('base')
		install_support_files(folder, target_folder)

	else:
		install_source(python_executable, folder, user=args.user, sudo=args.sudo)

if __name__ == "__main__":
	main()
