import XenAPI, logging, sys, subprocess
from abc import ABCMeta, abstractmethod

sys.path.insert(0, './')

from node import node
from node import node_type
from helper import autolog as log
from helper import info_exe
from netif import router_if as rif
from netif import netns
#from helper import init_ssh

class multi_if(object):
	__metaclass__=ABCMeta
	if_lst=[]

# we currently assume all to be local
# TODO: if need to enable remote, we have to make adapter for ssh to have 
# the same interface or we need a if condition for each operation
class prouter(node, multi_if):
	ns=None
	# @if_json: network interface data in json obj
	# keys include: ip, id
	def __init__(self, did, name, if_json, neighbors):
		node.__init__(self, did, name, dtype=node_type.PROUTER)
		# create a netns same name as the router
		self.ns=netns(name)
		# init interfaces on the router
		size=len(if_json)

		self.neighbors={}
		self.if_lst=[]
		for i in range(0, size):
			# create the interfaces
			newif=rif(self.name, if_json[i]['id'], if_json[i]['ip'])
			self.if_lst.append(newif)

		for neigh in neighbors:
			self.neighbors[neigh['id']]=neigh['ifid']

	def start(self, dev_lst):
		for did in self.neighbors:
			ifid=self.neighbors[did]
			self.start_if(ifid, dev_lst[did].name)		
		for x in self.if_lst:
			x.start()

	def start_if(self, ifid, switch_name):
		cmd="ovs-vsctl add-port "+switch_name+" "+self.if_lst[ifid].get_out_if()
		info_exe(cmd)

	def shutdown(self):
		for r_if in self.if_lst:
			r_if.stop()

	def uninstall(self):
		#for r_if in self.if_lst:
		#	r_if.delete()
		del self.ns

	def connect2switch(self, switch):
		vif_id=self.neighbors[switch.did]
		r_if=self.if_lst[vif_id]
		return r_if