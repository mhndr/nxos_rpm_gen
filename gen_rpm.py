import re
import os
import sys
import subprocess
import argparse

# unused for now
source  = "source /auto/andatc/independent/shellrc-files/current/rc/.bashrc.build"
vbe     = "vbe 5.1.8.1"

parser = argparse.ArgumentParser(description='This is an utility script for generating rpms out of nxos components ')
parser.add_argument('--all',help='rpm-izes all components in ins/x86e/final',action='store_true', default=False,dest='build_all',)
parser.add_argument('--component',help='specify individual component to be built',action='store', default="",dest='comp_to_bld',)
parser.add_argument('--group',help='specify group component to be built',type=list,action='store', default="",dest='group')
parser.add_argument('--group_name',help='specify a name for the components being grouped ',action='store', default="",dest='group_name')
parser.add_argument('--build',help='specify gdb or final',action='store', default="final",dest='build_type',)
parser.add_argument('--version',help='specify rpm version',action='store', default="1.0.1",dest='version',)
parser.add_argument('--clean',help='delete all rpms',action='store_true', default=False,dest='clean',)
parser.add_argument('--validate',help='checks the rpms for duplicate files',action='store_true', default=False,dest='validate',)


args 		= parser.parse_args()
build_all	= args.build_all
bld_comp 	= args.comp_to_bld
# unused for now
group_list	= args.group
group_name 	= args.group_name
build_type	= args.build_type
version 	= args.version
clean 		= args.clean
validate 	= args.validate

pkg_mk_files=[ 
#	"./defs/images/core_n9000_pkg.mk",
	"./defs/images/eth_n9000_pkg.mk"]

# don't build these components
ignore_list=["platform"]

"""
The fields that are of interest:
TODO: may need to include more
"""
keys=[
	"PACKAGE_FILES_FROM_TREE",
	"PACKAGE_FILES_NOT_IN_TREE",
	"BUILD_AND_PACKAGE_PI_FILES",
	"BUILD_AND_PACKAGE_PD_FILES",
	"BUILD_BUT_DONT_PACKAGE",
	"BUILD_AND_PACKAGE_CONTAINER_FILES"]

dict={}

def read_pkg_mk(pkg_file):
	f = open(pkg_file)
	f_contents=f.read().replace("\\\n"," ")
	f_contents=f_contents.replace("\"","")
	lines = f_contents.splitlines()
	return lines

def setup():
	final_list=[]
	for key in keys:
		dict[key]=[]
		pattern = re.compile(key)
		for file in pkg_mk_files:
			lines = read_pkg_mk(file)
			for line in lines:
				match = re.match(pattern, line)
				if match:
					file_list=line.split(" ")	
					for entry in file_list:
						entry = entry.strip()
						if re.match(re.compile("file"),entry):
							dict[key].append(entry)	


def remove_lines(moved_lines):
	# We'll need to remove lines from eth/core when we
	# add it to the new component's pkg.mk file to avoid
	# having duplicates in the final rpms.
	for mk_file in pkg_mk_files:
		for line in moved_lines:
			line= line.replace('/','\/')
			sed_cmd = "sed -i '/{0}/d' {1}".format(line,mk_file)    	
			try:
				subprocess.call(sed_cmd,shell=True)
			except Exception,e:
				print e
				print "Failed to delete duplicate entries from {0}".format(mk_file)
				
	
def populate(component):
	new_pkg_mk = "defs/images/"+component+"_n9000_pkg.mk"
	if not os.path.isfile(new_pkg_mk):
		print "file %s doesn't exist...Exiting"%new_pkg_mk
		sys.exit(1)
	# will have to use the original component name when searching
	# in each and core
	comp_name = component.replace('-','_')
	pattern  = re.compile(".*/.*"+comp_name+".*/.*")
	
	with open(new_pkg_mk, 'r') as f:
		new_pkg_mk_lines = f.readlines()
	
	moved_lines = []
	files_packaged = False
	for key in keys:
		for idx,line in enumerate(new_pkg_mk_lines):
			if re.match(re.compile(key),line):
				break				
		file_list = dict[key]
		for entry in file_list:
			if re.match(pattern,entry):
				idx += 1
				new_pkg_mk_lines.insert(idx,"\""+entry+"\" \\\n")
				moved_lines.append(entry)
				files_packaged = True
	
	if not files_packaged: 
		# looks like this component is not being packaged from either
		# eth or core. So it is best not to create an rpm for this comp.
		# to stop rpm from being created we only need to delet the pkg.mk 
		# and .bb files created by gen-rpm.sh
		bb_path="satori/meta-cisco-nxos/recipes-core/nxos/%s_1.0.0.bb"%component	
		print "\tNot creating  rpm for %s"%component
		del_mk_cmd = 'rm %s '%new_pkg_mk
		del_bb_cmd = 'rm %s '%bb_path
		try:
			subprocess.call(del_mk_cmd,shell=True)
			subprocess.call(del_bb_cmd,shell=True)
		except Exception,e:
			print e
			print "Failed to delete pkg.mk and .bb file for component %s..."%component
		return None
	
	try:
		with open(new_pkg_mk, 'w') as f:
		    f.writelines(new_pkg_mk_lines)
		return moved_lines
	except:
		print "Couldn't create new pkg.mk for %s, permission denied"%component
		return None

def build_rpm(component):
	if component in ignore_list:
		"Component listed in ignore list...Ignoring."
		return
	# need to replace '_', because it interferes with the logic
	# in build-rpmdeps.py ,which has its own interpretation for '_'
	# this affects only the name of the pkg.mk file created for the
	# component, will have to use the original name when searching in
	# eth and core pkg.mk files
	component = component.replace('_','-')
	print "Building rpm for %s"%component
	gen_rpm_cmd = 'sh ./gen-rpm.sh %s n9000'%component
	try:
		result = subprocess.call(gen_rpm_cmd,shell=True)
	except Exception,e:
		print e
		print "Failed to generate pkg.mk file for component...Exiting"
		sys.exit(1)

	if result == 0:
		moved_lines = populate(component)
	if moved_lines:
		gmake_cmd = 'gmake -j4 images/final/%s_n9000-imaging-only &> /dev/null'%component
		try:
			build_result = subprocess.call(gmake_cmd,shell=True)
		except Exception,e:
			print e
			print "Failed to build rpm for component...Exiting"
			sys.exit(1)
		if build_result != 0:
			print "\trpm build failed for %s"%component
		else: 	
			remove_lines(moved_lines)

if __name__  == "__main__":
	"""
	Rough Sketch of the Algorithm:
	for each key  #setup
		look for line with key in core and eth
		create a combined list of filenames
	create template pkg_mk for the new component
	for each key #populate
		-look for all files belonging to the comp
			in the file list of this key
		-construct a line is the right format that
			can be inserted into the new pkg.mk
		-replace line containing the key with the
			constructed line in the new pkg.mk
	un gmake on the new_pkg 
	"""
	setup()
	if bld_comp:
		build_rpm(bld_comp)
	elif build_all:
		ls_cmd = "ls -A ins/x86e/final | xargs -n1"
		try:
			ls_result = subprocess.check_output(ls_cmd,shell=True)
		except Exception,e:
			print e
			print "Failed to collect list of components...Exiting"
			sys.exit(1)
		components_list = ls_result.split('\n')
		for component in components_list:
			build_rpm(component)
