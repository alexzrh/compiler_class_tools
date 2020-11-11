import sys
import subprocess
from pathlib import Path
from difflib import Differ
from argparse import ArgumentParser, RawTextHelpFormatter

# THIS IS THE ONLY PLACE YOU NEED TO MAKE AN EDIT -- ONLY UPDATE THE BASE_TEST_LOCATION
# you only need to change this location to point where your Tests directory is.
# the rest will be added programmaically

# example - the below base becomes /Users/bob/cs660/Espresso/Tests/Phase3/Espresso/GoodTests (plus other dirs)
# BASE_TEST_LOCATION = "/Users/bob/cs660/Espresso/Tests/"
BASE_TEST_LOCATION = Path("/Users/alex/dev/UNLV-CS/cs660_compilers/Espresso/Tests")

#	Important Notes:
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
	hasToExist = (good_test_location, bad_test_location, compiler1, compiler2)
	option_locations = (good_test_location_plus, bad_test_location_plus, good_test_location_plpl, bad_test_location_plpl)
	canCreate = (output_good_C, output_good_CR, output_bad_C, output_bad_CR)

	fullList = list(hasToExist)
	fullList.extend(option_locations)
	fullList.extend(canCreate)

	current_dir = Path(".")
	print("Verifying required files and directories...")

	for var in fullList:
		if var in hasToExist:
			check_directory_exists(current_dir / var)

		if option == "eplus" or option == "eplusplus":
			if var in option_locations:
				check_directory_exists(current_dir / var)

		if var in canCreate:
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

	verbose = user_args.v
	mode = user_args.m
	ref = user_args.r

	for k in range(0, num-1, 1):
		loc_pair = get_test_location(k)

		results = test_generator(loc_pair, result_dict, ref, verbose)
		result_dict = process_dict(results)


def test_generator(location_dict, result_dict, ref, verbose=False):
	"""docstring for generate"""
	for k, loc in location_dict.items():
		try: e = str(((str(loc)).split("/")[-2:])[0])
		except: e = loc
		result_dict.update({e: {}})

	print("\nGenerating test files...")
	good_errors = 0
	bad_errors = 0

	current_dir = Path(".")
	for key, location in location_dict.items():
		print(f"\n\nGenerating files in directory: {location}")
		if key % 2 == 0:
			output_c = current_dir / output_bad_C
			output_cr = current_dir / output_bad_CR
		else:
			output_c = current_dir / output_good_C
			output_cr = current_dir / output_good_CR

		result_dict[e][(str(output_c))] = {}

		for file_name in location.iterdir():
			try:
				only_name = file_name.name
				name, ext = only_name.split(".")
			except:
				print(f"File {only_name} has too many parameters to split. Continuing without generating it.")
				continue

			print(f"\n{only_name}", end="")

			out_cr = output_cr / (name + ".txt")
			out_c = output_c / (name + ".txt")

			if ref != "noref":
				run_sys_cmd([f"./{compiler2} {file_name} > {out_cr}"])

			if ref != "onlyref":
				run_sys_cmd([f"./{compiler1} {file_name} > {out_c}"])

				diff_result = diff_two_files(out_cr, out_c, verbose)

				details = 0

				if diff_result[0] > 0:
					result_dict[e][(str(output_c))][(str(out_c))] = {		"errors": round(diff_result[0]),
																			"error_output": diff_result[1],
																			"added_lines": diff_result[2],
																			"removed_lines": diff_result[3]
																		}
	return result_dict


def diff_two_files(f_one, f_two, verbose=False):
	added_line = 0
	removed_line = 0
	error_num = 0
	error_output = {}

	only_name = f_one.name

	cr_contents = file_rw(f_one)
	c_contents = file_rw(f_two)

	# handle a missing file
	if cr_contents[1] is False or c_contents[1] is False:
		if cr_contents[1] is False: print(f"\t{cr_contents[0]}", end="")
		if c_contents[1] is False: print(f"\t{c_contents[0]}", end="")
		error_num = 0.1
		error_output["file_name"] = str(f_one)
		error_output["contents"] = "file not found"
		error_output["missing_files"] = 1

		return error_num, error_output, added_line, removed_line

	out = list(Differ().compare(cr_contents, c_contents))

	curr_line = ""
	err_remove = ""
	err_add = ""

	for line in out:
		last = ""
		if line[0] != " ":
			if line[2] == "/":
				try:
					last = line.split(":")[-1]
				except:
					print("Failed to split - skipping")
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
		print("\t!!! TEST FAILED !!!", end="")
		if verbose:
			print(f"  Extra Lines: {added_line}  |  Missing Lines: {removed_line}", end="")
		error_num += 1
		error_output["file_name"] = only_name
		error_output["contents"] = out
		#[print(str(l) for l in error_output["contents"])]
	return error_num, error_output, added_line, removed_line


def diff_file_directory(test_cr, test_c):
	error_dict = {}
	total_errors = 0

	current_dir = Path(".")
	for file_name_cr in test_cr.iterdir():
		only_name = file_name_cr.name

		errors, error_out = diff_two_files(file_name_cr, test_c / only_name)

		total_errors += errors
		error_dict.update(error_out)

	return total_errors, error_dict

'''
def diff_pregen_output(verbose=False):
	"""docstring for diff_all_output"""

	#print(f"Generating diff from good test files, stored in {goodDiff}")

	current_dir = Path(".")
	good_cr = current_dir / output_good_CR
	good_c = current_dir / output_good_C
	#print("\n\nChecking Pre-Generated GOOD Tests")
	#print("---------------------------", end="")
	good_errors, error_out_good = diff_file_directory(good_cr, good_c)


	bad_cr = current_dir / output_bad_CR
	bad_c = current_dir / output_bad_C
	#print("\n\nChecking Pre-Generated BAD Tests")
	#print("---------------------------", end="")
	bad_errors, error_out_bad = diff_file_directory(bad_cr, bad_c)

	print(f"\n\nGOOD FILES WITH OUTPUT ERRORS = {good_errors}", end="")
	if verbose:
		print("")
	print(f"BAD FILES WITH OUTPUT ERRORS = {bad_errors}")

	print("Diffs Generated\n")
	'''


def process_dict(result_dict):
	if result_dict == {}:
		sys.exit("Expected dictionary.")

	for key, val in result_dict.items():

		current_dir = Path()
		stats = current_dir / diffStats

		for loc, result in val.items():
			total_err = 0
			total_add_lines = 0
			total_rem_lines = 0
			missing = 0
			missing_files = ""

			file_rw(stats, mode="a+", content_chunk=f"----------------------------\n{key} -- {loc}\n")

			if loc == output_bad_C: output_f = badDiff
			else: output_f = goodDiff

			output_loc = current_dir / output_f

			for res, test in result.items():
				#print(test['error_output'])
				title = str(test['error_output']['file_name'])
				out = test['error_output']['contents']

				try:
					m = test['error_output']['missing_files']
					missing += m
					missing_files += f"\n---{title}"
				except: pass

				file_rw(output_loc, mode="a+", content_chunk=f"\n----Failed Diff {title}----\n")
				file_rw(output_loc, mode="a+", content_chunk=out)

				total_err += test['errors']
				total_add_lines += test['added_lines']
				total_rem_lines += test['removed_lines']

			out_str = (f"----------------------------\nFiles with Errors: {total_err}\n"
						f"   Added lines: {total_add_lines}\n   Removed lines: {total_rem_lines}")

			if missing: out_str += (f"\n   Missing/Untested files: {missing_files}")

			file_rw(stats, mode="a+", content_chunk=f"{out_str}\n\n")

	del result_dict[key]
	return result_dict


###############################   HELPERS   ################################

def file_rw(rw_file, mode="r", content_chunk=None):
	try:
		with open (rw_file, str(mode)) as diff:
			if mode == "a+":
				if content_chunk is None:
					sys.exit("Nothing to write.")
				for l in content_chunk:
					diff.write(l)
				contents = ""
			else:
				contents = list(diff)
	except Exception as e:
		return (e, False)

	return contents


def run_sys_cmd(cmd):
	# ADD IF SOURCE FILE IS NEWER THAN OUTPUT FILE, RE-RUN REF COMPILER

	try:
		proc = subprocess.Popen(cmd, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	except Exception as e:
		sys.exit(e)

	try:
		# if this returns, the process completed
		proc.wait(timeout=10)
	except subprocess.TimeoutExpired as te:
		sys.exit(te)

	# UNCOMMENT BELOW TO SEE WHAT IS CAUSING COMMAND ERRORS
	#return_code = proc.returncode
	#output, error = proc.communicate()
	#print(output, error) #, return_code)


def check_directory_exists(directory):
	dir_path = Path(directory)
	exists = dir_path.exists()
	if exists is False:
		sys.exit(f"Required directory does not exist: {dir_path}")
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
## Executables
compiler1          = "espressoc"
compiler2          = "espressocr"

## Directories
## DO NOT CHANGE THESE DECLARATIONS
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
							#f"{mode_opts[5]}:\tDiff previously created espressoc & espressocr output files\n"
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

############################### FAKE MAIN :) ################################

def main():
	mode_opts = ("clean", "checkfs", "ebase", "eplus", "eplusplus", "diff")
	ref_opts = ("default", "noref", "onlyref")
	#ref_opts = ("default", "noref", "onlyref")

	parser = ArgumentParser(description="Example: python3 autogen3.py -m eplus -p 3 \n"
							"   The above command runs all the Espresso+ tests for Phase 3 on both the student and reference compilers\n",
							prog="autogen3", formatter_class=RawTextHelpFormatter)

	user_args = get_args(parser, mode_opts, ref_opts)

	# m=mode, p=phase number, v=verbose, r=ref compiler default/on/off, d=path to pre-generated espressocr ref files
	if user_args.m not in mode_opts:
		parser.print_help()
		parser.error(f"\nINVALID mode: {user_args.m}\n")

	if 1 > user_args.p  or user_args.p > 6:
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

	if mode_num == 5:
		#diff_pregen_output(user_args.v)
		pass
	else:
		clean(user_args.r)
		if mode_num > 0:
			verifyFileSystemStructure(user_args.m)
		if mode_num > 1:
			run_test_set(user_args, mode_num)
	print("\n\n")
	end = file_rw(diffStats)
	if end[1] == False:
		sys.exit("diffStats file not found. Exiting.")
	for e in end:
		print(e.strip())
############################### SHALL WE BEGIN? ;) ################################

if __name__ == "__main__":
	main()
