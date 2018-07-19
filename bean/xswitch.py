#!/usr/bin/env python
import XenAPI, logging, sys, subprocess
from sets import Set

sys.path.insert(0, '../utils')
sys.path.insert(0, './')

from node import node
from node import node_type
from helper import autolog as log
import helper
from helper import info_exe
from netif import veth
from link import veth_link
from link import if_link

# TODO: how to set new bridge as none-automatically adding to new vms
class xswitch(node):
	# handle
	br=''

	# @default: is this bridge by default in XenServer?
	# for default bridges we cannot delete them, we use uuid for identifying default switch
	def __init__(self, session, did, name, default=False, uuid=""):
		if default:
			self.br=session.xenapi.network.get_by_uuid(uuid)
			# ignore the passed name, get name from xenserver instead
			br_name=session.xenapi.network.get_bridge(self.br)
			log("default XSwitch "+name+" in Linux: "+br_name)
			node.__init__(self, did, br_name, node_type.SWITCH)
		else:
			br_args={'assigned_ips': {}, 
					'name_label': name, 
					'name_description': '', 
					'MTU': '1500', 
					'other_config':{},
					'blobs': {}}
			self.br=session.xenapi.network.create(br_args)
			br_name=session.xenapi.network.get_bridge(self.br)
			log("XSwitch "+name+" in Linux: "+br_name)
			node.__init__(self, did, br_name, node_type.SWITCH)

		self.default=default

	def plug(self, session, dev):
		return dev.create_vif_on_xbr(session, self)

	def connect(self, node, session=None):
		link, reverse=None, None
		if node.dtype==node_type.DEV:
			vif=node.create_vif_on_xbr(session, self)
			link=if_link(self, node, vif)
			reverse=link.create_reverse_link()
		elif node.dtype==node_type.PROUTER:
			rif=node.connect2switch(self)
			link=veth_link(self, node, rif)
			reverse=link.create_reverse_link()
		elif node.dtype==node_type.SWITCH:
			veth_if=self.connect2switch(node)
			link=veth_link(self, node, veth_if)
			reverse=link.create_reverse_link()
			node.neighbors[self]=reverse.link_if
		else:
			log("type connection between (" + str(self.dtype) 
				+ str(node.dtype) + ") not supported yet!")
		return link, reverse

	def connect2switch(self, switch):
		# add switch and veth pair to dictionary
		# can only plug veth ifs on switches after xen switch is initialized
		# i.e., at least one of Xen device on this bridge is started
		peer1=self.name+"_"+switch.name
		peer2=switch.name+"_"+self.name
		veth_if=veth(peer1, peer2)
		self.neighbors[switch]=veth_if
		return veth_if

	def add_port(self, port):
		cmd="ovs-vsctl add-port "+self.name+" "+port
		info_exe(cmd)

	def uninstall(self, session):
		for neigh in self.neighbors:
			link_if=self.neighbors[neigh]
			link_if.delete()
		if not self.default:
			session.xenapi.network.destroy(self.br)
			cmd="ovs-vsctl del-br "+self.name
			info_exe(cmd)
		else:
			log("default XenSwitch "+self.name+" not being deleted!")

	def start(self, session=None):
		# xen switch automatically starts when any device 
		# connecting to it starts
		for key in self.neighbors:
			if key.dtype==node_type.SWITCH:
				self.add_port(self.neighbors[key].peer[0].name)
				# start all veth pairs on bridge, those are currently only for switch2switch connection
				self.neighbors[key].peer[0].start()
				self.neighbors[key].peer[1].start()


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
