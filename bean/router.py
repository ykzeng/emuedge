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
	def __init__(self, did, rjson):
		name, if_json, neighbors=rjson['name'], rjson['ifs'], rjson['neighbors']
		node.__init__(self, did, name, dtype=node_type.PROUTER)
		# init interfaces on the router
		size=len(if_json)

		netns.__init__(self, name, size)
		for i in range(0, size):
			# create the interfaces
			newif=rif(self.name, if_json[i]['id'])
			self.add_if(newif, if_json[i]['id'])
			newif.set_ip(if_json[i]['ip'])

		self.neighbors={}
		for neigh in neighbors:
			self.neighbors[neigh['id']]=neigh['if']

		# init nat
		if rjson['nat']['is_open']:
			nat_info=rjson['nat']
			self.enable_ip_forward()
			self.masq_est_allow(nat_info['nat_ifs'])
			self.accept_from_lanif(nat_info['lan_if'])
			self.open_out_conn()
		# init dhcp
		if rjson['dhcp']['is_open']:
			dhcp_info=rjson['dhcp']
			self.start_dhcp(dhcp_info['if'], dhcp_info['range_low'], dhcp_info['range_high'])

	def get_iflst(self):
		return self.if_lst

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

	def masq_est_allow(self, wan_ifids):
		for wan_ifid in wan_ifids:
			wan_if=self.get_if_by_id(wan_ifid).get_in_if()
			wan_if.masq_nat()
			wan_if.allow_established_conn()

	def accept_from_lanif(self, lan_ifid):
		self.get_if_by_id(lan_ifid).get_in_if().accept_from_if()

	def shutdown(self):
		if_lst=self.get_iflst()
		for r_if in if_lst:
			r_if.stop()

	def uninstall(self):
		#for r_if in self.if_lst:
		#	r_if.delete()
		if_lst=self.get_iflst()
		for rif in if_lst:
			rif.delete()
		self.delete()

	def connect2switch(self, switch):
		if_lst=self.get_iflst()
		vif_id=self.neighbors[switch.did]
		r_if=if_lst[vif_id]
		return r_if