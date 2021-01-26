import sys
import subprocess
from pathlib import Path
from difflib import Differ
from argparse import ArgumentParser, RawTextHelpFormatter

# THIS IS THE ONLY PLACE YOU MIGHT NEED TO MAKE AN EDIT -- ONLY UPDATE THE BASE_TEST_LOCATION IF NECESSARY.
# YOU DO NOT NEED TO MAKE ANY CHANGES IF YOU INSTALL YOUR TESTS DIRECTORY IN THE RECOMMENDED PLACE.

BASE_TEST_LOCATION = Path("../Tests/")

#  Important Notes:
#		DO NOT CHANGE THE OUTPUT* VARIABLES
#			If you must change them, be very careful because a rm -r is used to clean those folders.
#			If you specify a different folder you may delete all or most of your files.
#
#			MAKE SURE TO VERIFY DIFF FILES MANUALLY
#
#	 	Test file names can contain ONLY 1 period
#
#		gDiff.txt and/or bDiff.txt will only be created if there are errors
#
#  Note to GA: Best to first run a command similar to this to generate the REFERENCE files:
#    python3 autogen3.py -m eplusplus -p 3 -r onlyref
#  Then run this for the STUDENT files to compare against the REF files, which are in the -d location
#    python3 autogen3.py -m eplusplus -p 3 -v -r noref -d /Users/alex/dev/UNLV-CS/cs660_compilers/ref_compiler
############################### THE REAL WORK ################################

# Clean / del from the directory
def clean(option):
	"""docstring for clean"""
	print("Clean first....")
	deleteable = (output_good_CR, output_bad_CR, output_good_C, output_bad_C, goodDiff, badDiff, diffStats)
	to_remove = []

	current_dir = Path(".")
	for index, item in enumerate(deleteable):
		if index == 0 or index == 1:
			if option == "noref":
				continue
		if index == 2 or index == 3:
			if option == "onlyref":
				continue
		rm = current_dir / item
		if rm.exists():
			to_remove.append(rm)

	if to_remove != []:
		cleancmd = f"{' '.join(str(x) for x in list(to_remove))}"
	else:
		cleancmd = "Nothing to delete"

	print ("\nDelete files:")
	for location in to_remove:
		print(f"   {location}/")

	uin = input("\n\nProceed? (y/n)...   ").strip()

	if uin[0:1].lower() == "y":
		print(f"Proceeding: {uin[0:1].lower()}")
		if to_remove != []:
			run_sys_cmd([f"rm -r {cleancmd}"])
			print("Done Cleaning...")
		else:
			print("Nothing deleted")
	else:
		print(f"{uin[0:1].lower()}")
		sys.exit("Files not deleted, program terminated.\n")


# Verify file system structure
def verifyFileSystemStructure(option):
	"""docstring for verifyFileSystemStructure"""

	print("Verifying file system layout...")
	tmp = []
	must_exist = (good_test_location, bad_test_location, compiler1, compiler2)
	option_locations = (good_test_location_plus, bad_test_location_plus, good_test_location_plpl, bad_test_location_plpl)
	creatable = (output_good_C, output_good_CR, output_bad_C, output_bad_CR)

	fullList = list(must_exist)
	fullList.extend(option_locations)
	fullList.extend(creatable)

	current_dir = Path(".")
	print("Verifying required files and directories...")

	for var in fullList:
		if var in must_exist:
			check_directory_exists(current_dir / var)

		if option == "eplus" or option == "eplusplus":
			if var in option_locations:
				check_directory_exists(current_dir / var)

		if var in creatable:
			item = current_dir / var
			if item.exists() is False:
				tmp.append(var)

	for l in tmp:
		print(f"{l}/ Doesn't exist, creating it...")
		run_sys_cmd([f"mkdir {l}"])

	print("File System Verified\n")


def run_test_set(user_args, num):
	result_dict = {}
	def get_test_location(key):
		locations_dict = { 	0: { 1: good_test_location, 2: bad_test_location },
							1: { 3: good_test_location_plus, 4: bad_test_location_plus},
							2: { 5: good_test_location_plpl, 6: bad_test_location_plpl}
						 }
		return locations_dict[key]

	def build_espresso_dir(location_dict, result_dict):
		## choose test directory for Espresso, Espresso+, Espresso++
		for k, loc in location_dict.items():
			try: esp = str(((str(loc)).split("/")[-2:])[0])
			except: esp = loc

			# dictionary gets updated without returning it...
			result_dict.update({esp: {}})
			return esp

	verbose = user_args.v
	ref = user_args.r
	phase = user_args.p

	for k in range(0, num-1, 1):
		loc_pair = get_test_location(k)
		esp = build_espresso_dir(loc_pair, result_dict)

		results = test_generator(loc_pair, result_dict, ref, esp, phase, verbose)

		result_dict = process_dict(results, phase)


def parse_test_file(file_name, data_dict):
	parse_data = data_dict.copy()
	class_with_main = ''
	test_file = file_rw(file_name)

	# line one of java file -- get number of lines of output
	try: output_lines = int(test_file[0].strip("/()\n"))
	except:
		print("Error finding number of output lines. Ensure first line of test file uses a similar format to //(1)")
		output_lines = 0
	parse_data["output_lines"] = output_lines

	# line 2 of java file -- get input data
	parse_data["input_data"] = (test_file[1].strip())[2:]

	# lines 3 through (2+ number of output lines) of output data
	output_data = []
	for line in test_file[2:(output_lines+2)]:
		output_data.append(line[2:].strip())
	parse_data["output_data"] = output_data

	# get the list of classes and the class with main(String...) in it (not all tests have "args[]"")
	classes_in_file = []
	for line in test_file[(output_lines+2):]:
		if "class " in line:
			new_list = line.strip("{}\n").split(" ")
			#print(new_list)
			occurrences = new_list.count("class")

			for n in range(occurrences):
				# 1+new_list.index(class...) part gives the name of the class right after the first instance of class name
				# n+(new_list.index...) adds for each subsequent occurrence of class on the same line (for TigerTeam, etc)
				class_name = (new_list[(1+new_list.index('class', (n+(new_list.index('class')))))]).strip("\",")
				classes_in_file.append(class_name)

				# if extends or implements, add them to class list
				if "extends" in new_list:
					classes_in_file.append(new_list[(1+new_list.index('extends'))])
				if "implements" in new_list:
					classes_in_file.append(new_list[(1+new_list.index('implements'))])

		if "main(String" in line.replace(" ", ""):
			class_with_main = class_name

	parse_data["classes"] = list(set(classes_in_file)) # only want unique class names
	parse_data["number_of_classes"] = len(list(set(classes_in_file)))
	parse_data["class_w_main"] = class_with_main

	return parse_data


def assemble(file_name, test_sub_dirc, data_dict):
	total_j_files = 0
	assembled_files = 0
	local_data = data_dict.copy()

	out = file_rw(file_name)

	# if the last line of the output file isn't ..."= S = U = C = C = E = S = S ="...
	if "= S = U = C = C = E = S = S =" not in str(out[-1:]):
		print("\n\t!!! FAILED TO COMPILE !!!")
		print("\tWill NOT assemble any files")

	else:
		print(f"\nAssembling... ", end='')
		for j_file in test_sub_dirc.iterdir():
			if j_file.name[-2:] == ".j":
				total_j_files += 1
				print(f" {j_file.name}", end="")
				res = run_sys_cmd(f"./jasmin {j_file}")

				if f"Generated: {j_file.name[:-2]}" in res:
					assembled_files += 1
				else:
					print(f"  !!! FAILED TO ASSEMBLE: {(j_file.name)} !!! ")

	local_data["total_j_files"] = total_j_files
	local_data["assembled_j_files"] = assembled_files
	return local_data


def execute_class_files(test_sub_dirc, data_dict):
	local_data = data_dict.copy()
	if local_data["assembled_j_files"] == 0:
		local_data["fail_to_execute"] = 1
		# not deleting all the extra parse data, but no biggie
		return local_data

	print(f"\nExecuting {local_data['class_w_main']} ...", end="")
	failures = 0

	if local_data["output_data"] != [] and local_data["input_data"] == '':
		res = run_sys_cmd(f"./espresso {local_data['class_w_main']}")
		if res:
			try: res = res.rstrip("\n").split("\n")
			except:
				print("An Unexpected Exception Occurred")
			else:
				for index, elem in enumerate(local_data["output_data"]):
					if str(elem) != str(res[index]):
						print("  !!! Failed: Expected output not present !!!")
						failures += 1
						break
			if failures == 0:
				print(" done ... Output matches as expected ... Success")
		else:
			print("  !!! Failed: Expected output not present !!!")
			failures += 1
	elif local_data["input_data"] != '':
		print(" Skipping tests that require input for now...")
	else:
		# when local_data["output_data"] is empty and no input data required...
		res = run_sys_cmd(f"./espresso {local_data['class_w_main']}")
		if res == "":
			print(" done ... Empty output as expected ... Success")
		else:
			print(" done ... Ouput present when none expected ... !!! Failed !!!")
			failures += 1

	# make debugging easier (and clear up a miniscule bit of memory)
	del local_data["output_data"]
	del local_data["input_data"]
	del local_data["classes"]
	del local_data["class_w_main"]
	del local_data["output_lines"]
	local_data["fail_to_execute"] = failures

	# move all classes into the sub directory now that we're done with them
	run_sys_cmd(f"mv *.class {test_sub_dirc}")
	return local_data


def test_generator(location_dict, result_dict, ref, esp, phase, verbose=False):
	print("\nGenerating test files...")
	good_errors = 0
	bad_errors = 0

	def get_just_filename(file_name):
		# strip off the extension
		only_name = None
		try:
			only_name = file_name.name
			name, ext = only_name.split(".")
		except:
			print(f"File {only_name} has too many parameters to split. Continuing without generating it.")
		return name, only_name


	for key, location in location_dict.items():
		print(f"\n\nGenerating files from directory: {location}")
		output_c, output_cr = get_output_locations(key)

		result_dict[esp][(str(output_c))] = {}

		for file_name in location.iterdir():
			name, only_name = get_just_filename(file_name)

			if only_name is not None:
				print(f"\n{only_name}", end="")

				if phase == 6:
					test_sub_dirc = output_c / name
					test_sub_dircr = output_cr / name

					run_sys_cmd([f"mkdir {test_sub_dirc}"])
					run_sys_cmd([f"mkdir {test_sub_dircr}"])

					out_c = test_sub_dirc / (name + ".txt")
					out_cr = test_sub_dircr / (name + ".txt")

				else:
					out_c = output_c / (name + ".txt")
					out_cr = output_cr / (name + ".txt")

				result_dict[esp][(str(output_c))][(str(out_c))] = {"build_errors": {}}

				if ref != "noref":
					run_sys_cmd([f"./{compiler2} {file_name} > {out_cr}"])
					if phase == 6:
						run_sys_cmd([f"mv *.rj {test_sub_dircr}"])

				if ref != "onlyref":

					run_sys_cmd([f"./{compiler1} {file_name} > {out_c}"])
					if phase == 6:
						run_sys_cmd([f"mv *.j {test_sub_dirc}"])

					diff_result = diff_two_files(out_cr, out_c, verbose)

					details = 0

					if diff_result[0] > 0:
						result_dict[esp][(str(output_c))][(str(out_c))]["build_errors"] = {	"errors": round(diff_result[0]),
																							"error_output": diff_result[1],
																							"added_lines": diff_result[2],
																							"removed_lines": diff_result[3],
																							"ignored_lines": diff_result[4]
																						}

				if phase == 6 and ref != "onlyref":
					result_dict[esp][(str(output_c))][(str(out_c))]["phase6_results"] = {}
					ph6_test_results = {}
					ph6_test_results = assemble(out_c, test_sub_dirc, ph6_test_results)
					ph6_test_results = parse_test_file(file_name, ph6_test_results)
					ph6_test_results = execute_class_files(test_sub_dirc, ph6_test_results)

					result_dict[esp][(str(output_c))][(str(out_c))]["phase6_results"] = ph6_test_results

					print("-----------------------------------------------------------------------------------------------------------", end = "")

	return result_dict


def diff_two_files(f_one, f_two, verbose=False):
	added_line = 0
	removed_line = 0
	error_num = 0
	ignored_line = 0
	error_output = {}

	only_name = f_one.name

	cr_contents = file_rw(f_one)
	c_contents = file_rw(f_two)

	# handle a missing file
	try:
		if cr_contents[1] is None or c_contents[1] is None:
			if cr_contents[1] is None: print(f"\t{cr_contents[0]}", end="")
			if c_contents[1] is None: print(f"\t{c_contents[0]}", end="")
			error_num = 0.1
			error_output["file_name"] = str(f_one)
			error_output["contents"] = "file not found"
			error_output["missing_files"] = 1

			return error_num, error_output, added_line, removed_line, ignored_line
	except: pass

	out = list(Differ().compare(cr_contents, c_contents))

	curr_line = ""
	err_remove = ""
	err_add = ""

	for line in out:
		last = ""
		if line[0] != " ":
			if "/" in line:
				try:
					last = line.split(":")[-1]
				except:
					print("Failed to split - skipping")
					continue

			if " jasmin file" in line:
				ignored_line += 1
				continue

			if line[0] == "-":
				removed_line += 1
				if last != "":
					err_remove = last

			if line[0] == "+":
				added_line += 1
				if last != "":
					err_add = last


	if added_line != removed_line or err_remove != err_add:
		print("\t!!! DIFF FAILED !!!", end="")
		if verbose:
			print(f"  |  Extra Lines: {added_line}  |  Missing Lines: {removed_line}", end="")
		error_num += 1
		error_output["file_name"] = only_name
		error_output["contents"] = out

	return error_num, error_output, added_line, removed_line, ignored_line


def process_dict(result_dict, phase):
	if result_dict == {}:
		sys.exit("Expected dictionary.")

	for key, val in result_dict.items():
		current_dir = Path()
		stats = current_dir / diffStats

		for loc, result in val.items():
			total_tests = 0
			total_err = 0
			total_add_lines = 0
			total_rem_lines = 0
			total_ign_lines = 0
			missing = 0
			missing_files = ""
			sum_all_j = 0
			total_assembled_j = 0
			total_classes = 0
			total_exe_failures = 0
			assembly_failures = 0

			file_rw(stats, mode="a+", content_chunk=f"----------------------------\n{key} -- {loc}\n")

			if loc == output_bad_C: output_f = badDiff
			else: output_f = goodDiff

			output_loc = current_dir / output_f

			for res, test in result.items():
				total_tests += 1
				if test["build_errors"] != {}:
					title = str(test["build_errors"]['error_output']['file_name'])
					out = test["build_errors"]['error_output']['contents']

					try:
						m = test["build_errors"]['error_output']['missing_files']
						missing += m
						missing_files += f"\n---{title}"
					except: pass

					file_rw(output_loc, mode="a+", content_chunk=f"\n----Failed Diff {title}----\n")
					file_rw(output_loc, mode="a+", content_chunk=out)

					total_err += test["build_errors"]['errors']
					total_add_lines += test["build_errors"]['added_lines']
					total_rem_lines += test["build_errors"]['removed_lines']
					total_ign_lines += test["build_errors"]['ignored_lines']

				if phase == 6:
					if test["phase6_results"] != {}:
						total_assembled_j += test["phase6_results"]["assembled_j_files"]
						total_classes += test["phase6_results"]["number_of_classes"]
						total_exe_failures += test["phase6_results"]["fail_to_execute"]

			out_str = (f"----------------------------\nTotal tests: {total_tests}\nTests with Diff Errors: {total_err}\n"
						f"   Added lines: {total_add_lines}\n   Removed lines: {total_rem_lines}"
						f"\n   Ignored lines: {total_ign_lines}")

			if missing: out_str += (f"\n   Missing/Untested files: {missing_files}")

			if phase == 6:
				if total_classes != total_assembled_j:
					assembly_failures = abs(total_classes - total_assembled_j)
				out_str += (f"\n\nTotal classes to assemble = {total_classes}\nAssembly failures: {assembly_failures}"
							f"\nTotal test execution failures: {total_exe_failures}")

			file_rw(stats, mode="a+", content_chunk=f"{out_str}\n\n")

	# free up some memory .. some of those tests are huge, so start fresh for the next directory...
	del result_dict[key]
	return result_dict


###############################   HELPERS   ################################

def file_rw(rw_file, mode="r", content_chunk=None):
	contents = ""
	try:
		with open (rw_file, str(mode)) as diff:
			if mode == "a+":
				if content_chunk is None:
					sys.exit("Nothing to write.")
				for l in content_chunk:
					diff.write(l)
			else:
				contents = list(diff)
			return contents
	except Exception as e:
		return (e, None)


def run_sys_cmd(cmd):
	# ADD IF SOURCE FILE IS NEWER THAN OUTPUT FILE, RE-RUN REF COMPILER ON THAT FILE
	try:
		proc = subprocess.Popen(cmd, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
	except Exception as e:
		sys.exit(e)

	try:
		# if this returns, the process completed
		proc.wait(timeout=10)
	except subprocess.TimeoutExpired as te:
		sys.exit(te)

	# UNCOMMENT BELOW TO SEE WHAT IS CAUSING COMMAND ERRORS
	#return_code = proc.returncode
	output, error = proc.communicate()
	#print(output, error, return_code)

	return output


def get_output_locations(key):
	current_dir = Path(".")
	if key % 2 == 0:
			output_c = current_dir / output_bad_C
			output_cr = current_dir / output_bad_CR
	else:
		output_c = current_dir / output_good_C
		output_cr = current_dir / output_good_CR

	return output_c, output_cr


def check_directory_exists(directory):
	dir_path = Path(directory)
	exists = dir_path.exists()
	if exists is False:
		sys.exit(f"Required directory/file does not exist: {dir_path}")
	return True

############################### LOCATION GENERATORS ################################
def user_def_espressocr_loc(path=None):
	global output_good_CR
	global output_bad_CR
	global protect_CR

	if path is None:
		output_good_CR = "output_good_CR"
		output_bad_CR = "output_bad_CR"
		protect_CR = False
	else:
		dir_path = Path(path)
		output_good_CR = dir_path / "output_good_CR"
		output_bad_CR = dir_path / "output_bad_CR"
		protect_CR = True


def test_location_builder(phase):
	## Test file directories
	phase_dict = {
		1: "Phase1",
		2: "Phase2",
		3: "Phase3",
		4: "Phase4",
		5: "Phase5",
		6: "Phase6"
	}
	current_phase = phase_dict.get(phase)

	## DO NOT CHANGE ANYTHING - ONLY CHANGE GLOBAL BASE AT TOP!!
	global good_test_location
	global bad_test_location
	good_test_location = BASE_TEST_LOCATION / current_phase / "Espresso/GoodTests"
	bad_test_location = BASE_TEST_LOCATION / current_phase / "Espresso/BadTests"

	global good_test_location_plus
	global bad_test_location_plus
	good_test_location_plus = BASE_TEST_LOCATION / current_phase / "Espresso+/GoodTests"
	bad_test_location_plus = BASE_TEST_LOCATION / current_phase / "Espresso+/BadTests"

	global good_test_location_plpl
	global bad_test_location_plpl
	good_test_location_plpl = BASE_TEST_LOCATION / current_phase / "Espresso++/GoodTests"
	bad_test_location_plpl = BASE_TEST_LOCATION / current_phase / "Espresso++/BadTests"

############################ MOAR GLOBALS :( #################################
#### DO NOT CHANGE THESE DECLARATIONS
## Executables
compiler1          = "espressoc"
compiler2          = "espressocr"

## Directories
output_good_C      = "output_good_C"
output_bad_C       = "output_bad_C"

## Files to hold the diff output
goodDiff           = "gDiff.txt"
badDiff            = "bDiff.txt"
diffStats          = "diffStats.txt"
###############################################################################

############################### ARG PARSER ################################
def get_args(parser, mode_opts, ref_opts):

	parser.add_argument("-m", required=True, metavar="Mode",
							help=f"{mode_opts[0]}:\tClean/delete all test files/directories\n"
							f"{mode_opts[1]}:\tVerify test locations are accessible\n"
							f"{mode_opts[2]}:\tRun Espresso basic tests only\n"
							f"{mode_opts[3]}:\tRun Espresso & Espresso+ tests\n"
							f"{mode_opts[4]}:\tRun Espresso, Espresso+, & Espresso++ tests\n"
						)
	parser.add_argument("-p", type=int, metavar="Phase", help="Number of the phase you are testing (integer 1-6)", required=True)
	parser.add_argument("-r", default=ref_opts[0], metavar="Ref Compiler",
						help=f"(Optional)\n{ref_opts[0]}:\tRun both compilers\n"
							f"{ref_opts[1]}:\tdo NOT run the reference compiler\n"
							f"{ref_opts[2]}:\tONLY runs the reference compiler")
	parser.add_argument("-d", type=str, metavar="Ref Dir",
						help="(Optional)\nAbsolute path to pre-generated EspressoCR OUTPUT files\n"
						"Example: /home/matt/CSC460/Espresso/Tests/Phase3\n"
						"Do NOT include the output_good_cr or output_bad_cr directories at the end")
	parser.add_argument("-v", action="store_true", default=False,
						help="(No Options) Include -v to turn on verbose mode during interactive output.")

	return parser.parse_args()

############################### SHALL WE BEGIN? ;) ################################
if __name__ == "__main__":
	mode_opts = ("clean", "checkfs", "ebase", "eplus", "eplusplus")
	ref_opts = ("default", "noref", "onlyref")

	parser = ArgumentParser(description="Example: python3 autogen3.py -m eplus -p 3 \n"
							"   The above command runs all the Espresso+ tests for Phase 3 on both the student and reference compilers\n",
							prog="autogen3", formatter_class=RawTextHelpFormatter)

	user_args = get_args(parser, mode_opts, ref_opts)

	# m=mode, p=phase number, v=verbose, r=ref compiler default/on/off, d=path to pre-generated espressocr ref files
	if user_args.m not in mode_opts:
		parser.print_help()
		parser.error(f"\nINVALID mode: {user_args.m}\n")

	if 1 > user_args.p or user_args.p > 6:
		parser.print_help()
		parser.error(f"\nINVALID Phase Number: {user_args.p}\n")

	if user_args.r not in ref_opts:
		parser.print_help()
		parser.error(f"\nINVALID option for reference compiler action: {user_args.r}\n")

	if user_args.d is not None:
		if check_directory_exists(user_args.d):
			user_def_espressocr_loc(user_args.d)
	else:
		user_def_espressocr_loc()

	test_location_builder(user_args.p)

	mode_num = mode_opts.index(user_args.m)

	clean(user_args.r)
	if mode_num > 0:
		verifyFileSystemStructure(user_args.m)
	if mode_num > 1:
		run_test_set(user_args, mode_num)

	print("\n\n")
	end = file_rw(diffStats)
	if end[1] == None:
		sys.exit("Check output files manually. Exiting.")
	for e in end:
		print(e.strip())
# Done!