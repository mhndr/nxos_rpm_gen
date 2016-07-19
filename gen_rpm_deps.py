import subprocess
import re
import pickle
import os
import sys
import operator
import argparse

rpm_prov_dict  = {} #libs provided by each rpm
rpm_req_dict   = {} #libs required by each rpm 
libs_prov_dict = {} #which rpm provides a given lib
libs_reqs_dict = {} #which rpms require a given lib

#final rpm to rpm mappings
rpm_client_dict 	= {} 
rpm_dependency_dict	= {}

#temporary lists for processing
component_list 		= []
resolved_list 		= []
tobe_resolved_list 	= []


parser = argparse.ArgumentParser(description='This is an utility script for indentifying dependencies across nxos components ')
parser.add_argument('--rpm',help='rpm to be queried',action='store', default="",dest='rpm_name',)
parser.add_argument('--lib',help='lib to be queried',action='store', default="",dest='lib_name',)
parser.add_argument('--required',help='',action='store_true', dest='required',)
parser.add_argument('--provided',help='',action='store_true',dest='provided',)
parser.add_argument('--dependency',help='',action='store_true',dest='dependency',)
parser.add_argument('--recurse',help='perform the operation recursively',action='store_true', default="False",dest='recurse',)


args = parser.parse_args()
rpm_name 	= args.rpm_name
lib_name 	= args.lib_name
required 	= args.required
provided 	= args.provided
dependency	= args.dependency
recurse  	 args .recurse 

"""
	given a component print what rpms is it dependent on.
	"who do I need?"
"""
def find_providers(component):
	tobe_resolved_list.append(component)
	for comp in tobe_resolved_list:
		print (comp)
		libs_required = rpm_req_dict[comp]
		for lib in libs_required:
			try:
				provider_rpm = libs_prov_dict[lib] 
			except:
				continue
				#print "unknown provider for lib:",lib	
			if not provider_rpm in resolved_list and \
			   not provider_rpm in tobe_resolved_list:
				print provider_rpm+" ",
				tobe_resolved_list.append(provider_rpm)
		print "\n__________________________________"
		resolved_list.append(comp)


"""
	given a component print what rpms are dependent on it
	"who needs me?"
"""
def find_consumers(component):
	tobe_resolved_list.append(component)
	for comp in tobe_resolved_list:
		print "the following rpms use libs given by",comp
		libs_provided = rpm_prov_dict[comp]
		for lib in libs_provided:
			try:
				consumer_rpm = libs_reqs_dict[lib] 
			except:
				continue
				#print "unknown provider for lib:",lib	
			if not consumer_rpm in resolved_list and \
			   not consumer_rpm in tobe_resolved_list:
				print consumer_rpm+" ",
				tobe_resolved_list.append(consumer_rpm)
		print "\n__________________________________"
		resolved_list.append(comp)


def print_consumer_count(dict):
	"""	
	setup_component_list()
	for comp in components_list:
		prov_list = rpm_prov_dict[comp]
		for lib in prov_list:
			
			rpm_client_dict	
	"""
	for key, value in sorted(dict.iteritems(), key=lambda (k,v): (v,k)):
		print "{:<25} {:<30}".format(key,value)	
	

def filter_list(lib_list):
	pattern = re.compile(".*\.so.*")
	filtered_list=[]
	for i in lib_list:
		if re.match(pattern,i):
			filtered_list.append(i.strip())
	return filtered_list

def setup_component_list():
	ls_cmd = "ls -A ./ins/x86e/final | xargs -n1"
	try:
		ls_result = subprocess.check_output(ls_cmd,shell=True)
	except Exception,e:
		print "Failed to collect list of components...Exiting"
		sys.exit(1)
	components_list = ls_result.split('\n')
	for component in components_list:
		if not component:
			continue
		component = component.replace('_','-')
		

"""
	queries each component rpm for libs it requires and 
	provides and pickles it.
"""
def setup():
	ls_cmd = "ls -A ./ins/x86e/final/ | xargs -n1"
	try:
		ls_result = subprocess.check_output(ls_cmd,shell=True)
	except Exception,e:
		print "Failed to collect list of components... Exiting"
	components_list = ls_result.split('\n')
	for component in components_list:
		if component and component.strip():
			print(component)
			component = component.replace('_','-')
			ls_cmd = "ls ./images/final/rpm/lib32_n9000/%s*"%component
			try:
				rpm_path = subprocess.check_output(ls_cmd,shell=True)
			except Exception,e:
				print "Failed to find rpm %s..."%component
				continue
		
			requires_cmd = "/bin/rpm -qp --requires %s 2> /dev/null"%rpm_path
			try:
				output = subprocess.check_output(requires_cmd,shell=True)
				req_libs = output.split('\n')
				#if not req_libs:
				#	raise Exception()
			except Exception,e:
				print "Failed to query rpm... Exiting"
			provides_cmd = "/bin/rpm -qp --provides %s 2> /dev/null"%rpm_path
			try:
				output = subprocess.check_output(provides_cmd,shell=True)
				prov_libs = output.split('\n')
			except Exception,e:
				print "Failed to query rpm... Exiting"
		
			req_libs = filter_list(req_libs) 	
			rpm_req_dict[component] = req_libs
			prov_libs = filter_list(prov_libs)
			rpm_prov_dict[component] = prov_libs
			for lib in prov_libs:
				libs_prov_dict[lib]=component	
			for lib in req_libs:
				try:
					if not libs_reqs_dict.has_key(lib):
						libs_reqs_dict[lib]=list() 
					libs_reqs_dict[lib].append(component)
				except:
					continue
	#pickling: store the generated info in files to save time on the next run
	with open('rpm_req_dict.pickle', 'wb') as handle:
		pickle.dump(rpm_req_dict, handle)	
	with open('libs_prov_dict.pickle', 'wb') as handle:
		pickle.dump(libs_prov_dict, handle)	
	with open('rpm_prov_dict.pickle', 'wb') as handle:
		pickle.dump(rpm_prov_dict, handle)	
	with open('libs_reqs_dict.pickle', 'wb') as handle:
		pickle.dump(libs_reqs_dict, handle)	



if __name__ == "__main__":
	if  os.path.isfile('rpm_req_dict.pickle') and \
		os.path.isfile('rpm_prov_dict.pickle') and \
		os.path.isfile('libs_reqs_dict.pickle') and \
		os.path.isfile('libs_prov_dict.pickle'):
		
		with open('rpm_req_dict.pickle', 'rb') as handle:
			rpm_req_dict=pickle.load(handle)
		with open('rpm_prov_dict.pickle', 'rb') as handle:
			rpm_prov_dict=pickle.load(handle)
		with open('libs_reqs_dict.pickle', 'rb') as handle:
			libs_reqs_dict=pickle.load(handle)
		with open('libs_prov_dict.pickle', 'rb') as handle:
			libs_prov_dict=pickle.load(handle)
	else:
		setup()
	
	if rpm_name :
		try:
			if provided:
				print rpm_prov_dict[rpm_name]
			if required:
				print rpm_req_dict[rpm_name]
		except:
			print "this component doesn't seem to exist. please check..."
	if lib_name :
		try:
			if provided:
				print libs_prov_dict[lib_name]
			if required:
				print libs_reqs_dict[lib_name]
		except:
			print "this component doesn't seem to exist. please check..."
		
#	find_providers(sys.argv[1])
#	find_consumers(sys.argv[1])

"""	ls_cmd = "ls -A ins/x86e/final | xargs -n1"
	try:
		ls_result = subprocess.check_output(ls_cmd,shell=True)
	except Exception,e:
		print "Failed to collect list of components...Exiting"
		sys.exit(1)
	components_list = ls_result.split('\n')
	for component in components_list:
		if not component:
			continue
		component = component.replace('_','-')
		print "resolving",component
		find_providers(component)		
"""











	
