import os
import subprocess
from helper import initializer

def get_snapshot_id(name):
	cmd=("xe snapshot-list | grep -B 1 '" + name + "' | grep -v '" 
		+ name + "' | cut -d: -f2 | tr -d '[:space:]'")
	#id=os.system(cmd)
	id=subprocess.check_output(cmd, shell=True)
	if id=='':
		#print "The requested snapshot " + name + " doesn't exist!"
		return None
	else:
		return id

class vm_type():
	NODE=1
	SWITCH=2
	ROUTER=3
	
class dev:
	# device id
	did=''
	# device type
	dtype=1

	@initializer
	def __init__(self, did=1, dtype=vm_type.NODE):
		pass

	def __str__(self):
		attrs = vars(self)
		return str(', '.join("%s: %s" % item for item in attrs.items()))

class vm(dev):
	# snapshot id
	ssid=''
	# vcpu cores
	vcpu=1
	# memory in MB
	mem=1024
	# vm id
	vid=''

	@initializer
	def __init__(self, did=1, dtype=vm_type.NODE, ssid=1, vid=1, vcpu=1, mem=1024):
		dev.__init__(self, did, dtype)
		pass

	def install():
		
		pass

	def start():
		pass

	def shutdown():
		pass

class emu_edge_env:
	# list of vms in emuedge system
	vm_list=[]
	# graph for network topology

class net_graph:
	test=None

class link_prop:
	# 
	delay=10

def test_main():
	# test the get snapshot id method
	#print get_snapshot_id("mcloud v0.3")
	#print get_snapshot_id("lalalalala")
	vm_obj=vm(1, vm_type.NODE, 123, 123, 1, 1024)
	print "vm_obj"
	print vm_obj
	dev_obj=dev(1, vm_type.NODE)
	print "dev_obj"
	print dev_obj

test_main()
