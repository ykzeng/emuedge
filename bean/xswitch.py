#!/usr/bin/env python
import XenAPI, logging, sys, subprocess
from sets import Set

sys.path.insert(0, '../utils')
sys.path.insert(0, './')

from node import node
from node import node_type
from helper import autolog as log
from helper import info_exe

# TODO: how to set new bridge as none-automatically adding to new vms
class xswitch(node):
	# handle
	br=''

	def __init__(self, session, did, name):
		br_args={'assigned_ips': {}, 
				'name_label': name, 
				'name_description': '', 
				'MTU': '1500', 
				'other_config':{},
				'blobs': {}}
		self.br=session.xenapi.network.create(br_args)

		new_name=session.xenapi.network.get_bridge(self.br)
		log(new_name)
		node.__init__(self, did, new_name, node_type.SWITCH)

	def plug(self, session, dev):
		return dev.create_vif_on_xbr(session, self)

	def uninstall(self, session):
		session.xenapi.network.destroy(self.br)
		cmd="ovs-vsctl del-br "+self.name
		info_exe(cmd)

	def start(self, session=None):
		# xen switch automatically starts when any device 
		# connecting to it starts
		pass

class xrouter(xswitch):
	# the if name of veth external end
	external_if=''
	# if name of veth internal end in netns
	internal_if=''
	# TODO: start DHCP need subnet specification
	def __init__(self, session, did, name, ipaddr, subnet=None):
		xswitch.__init__(self, session, did, name)
		# the bridge name generated can be seen as unique identifier
		self.external_if=self.name+"-out"	#test0
		self.internal_if=self.name+"-in"	#test1
		self.ipaddr=ipaddr
		#self.ovs_br=self.name 				#xapi142
		#ns=ovs_br

	def start(self):
		path='./bash/xrouter_start.sh'
		cmd=(path+" "+self.name+" "+self.external_if+" "
			+self.internal_if+" "+self.ipaddr)
		helper.info_exe(cmd)

	def shutdown(self):
		cmd="ip netns list | grep "+self.name
		output=helper.info_exe(cmd)

		if self.name in output:
			cmd=("ip netns del "+self.name+" && "
				+"ovs-vsctl del-br "+self.name)
			helper.info_exe(cmd)
			log("deletion cmd:"+str(cmd))
		else:
			log("router netns "+self.name+" is not started")
			return
		# test if br is set
		#cmd="ovs-vsctl br-list | grep "+self.name
		

	def obsolete(self):
		# TODO: do subnet ip transformation
		cmd= """ip link add dev %s type veth peer name %s && 
				ip link set %s up && 
				ovs-vsctl add-port %s %s && 
				ip netns add %s && 
				ip link set %s netns %s && 
				ip netns exec %s ip addr add %s dev %s && 
				ip netns exec %s ip link set %s up && """ % (
					self.external_if, self.internal_if, 
					self.external_if, 
					self.name, self.external_if, 
					self.name, 
					self.internal_if, self.name, 
					self.name, ipaddr, self.internal_if, 
					self.name, self.internal_if
				)
		cmd=cmd.split(" && ")
		try:
			output=subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
		except subprocess.CalledProcessError as exc:
		    print("Status : FAIL", exc.returncode, exc.output)
		else:
		    print("Output: \n{}\n".format(output))

	def uninstall(self, session):
		# deleting netns->all if in netns also deleted, as well as the other
		# end of the veth pair
		self.shutdown()
		xswitch.uninstall(self, session)