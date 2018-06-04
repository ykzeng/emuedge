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
	def __init__(self, did, name, ifs_json=None, nat_params=None, dhcp_params=None, neighbors=None):
		node.__init__(self, did, name, dtype=node_type.PROUTER)
		netns.__init__(self, name)
		if ifs_json!=None:
			self.init_ifs_json(ifs_json)
			if nat_params!=None and nat_params['is_open']==True:
				self.init_nat_json(nat_params)
			if dhcp_params!=None and dhcp_params['is_open']==True:
				self.init_dhcp_json(dhcp_params)
			if neighbors!=None:
				self.init_neighbors(neighbors)
		else:
			if nat_params['is_open'] or dhcp_params['is_open'] or neighbors!=None:
				log("must have ifs to open NAT/DHCP", logging.CRITICAL)

	def init_ifs_json(self, ifs_json):
		# init interfaces on the router
		size=len(ifs_json)
		self.setup_if(size)
		for i in range(0, size):
			# create the interfaces
			newif=rif(self.name, ifs_json[i]['id'])
			self.add_if(newif, ifs_json[i]['id'])
			newif.set_ip(ifs_json[i]['ip'])

	def init_neighbors(self, neigh_params):
		for neigh in neigh_params:
			self.neighbors[neigh['id']]=neigh['if']
			#log("get neighbor did: "+str(neigh['id'])+" through netif: "+str(neigh['if']))

	def start_nat(self, nat_if, lan_if):
		self.enable_ip_forward()
		self.masq_est_allow(nat_if)
		self.accept_from_lanif(lan_if)
		self.open_out_conn()

	def init_nat_json(self, nat_params):
		# init nat
		if nat_params['is_open']:
			nat_info=nat_params
			self.start_nat(nat_info['nat_ifs'], nat_info['lan_if'])

	def init_dhcp_json(self, dhcp_params):
		# init dhcp
		if dhcp_params['is_open']:
			dhcp_info=dhcp_params
			self.start_dhcp(dhcp_info['if'], dhcp_info['range_low'], dhcp_info['range_high'])

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