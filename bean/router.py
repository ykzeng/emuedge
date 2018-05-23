import XenAPI, logging, sys, subprocess
from abc import ABCMeta, abstractmethod

sys.path.insert(0, './')

from node import node
from node import node_type
from helper import autolog as log
from helper import info_exe
from netif import router_if as rif
from netif import netns

# we currently assume all to be local
# TODO: if need to enable remote, we have to make adapter for ssh to have 
# the same interface or we need a if condition for each operation
class prouter(node, netns):
	# @if_json: network interface data in json obj
	# keys include: ip, id
	def __init__(self, did, name, if_json, neighbors):
		node.__init__(self, did, name, dtype=node_type.PROUTER)
		# init interfaces on the router
		size=len(if_json)

		self.ns=netns(name, size)
		for i in range(0, size):
			# create the interfaces
			newif=rif(self.name, if_json[i]['id'])
			self.ns.add_if(newif, if_json[i]['id'])
			newif.set_ip(if_json[i]['ip'])

		self.neighbors={}
		for neigh in neighbors:
			self.neighbors[neigh['id']]=neigh['ifid']

	def get_iflst(self):
		return self.ns.if_lst

	def start(self, dev_lst):
		for did in self.neighbors:
			ifid=self.neighbors[did]
			self.start_if(ifid, dev_lst[did].name)		
		if_lst=self.get_iflst()
		for x in if_lst:
			x.start()

	def start_if(self, ifid, switch_name):
		if_lst=self.get_iflst()
		cmd="ovs-vsctl add-port "+switch_name+" "+if_lst[ifid].get_out_if().name
		info_exe(cmd)
		log(cmd)

	def shutdown(self):
		if_lst=self.get_iflst()
		for r_if in if_lst:
			r_if.stop()

	def uninstall(self):
		#for r_if in self.if_lst:
		#	r_if.delete()
		self.ns.delete()

	def connect2switch(self, switch):
		if_lst=self.get_iflst()
		vif_id=self.neighbors[switch.did]
		r_if=if_lst[vif_id]
		return r_if