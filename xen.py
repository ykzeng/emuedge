import os
import subprocess
import logging, sys
import XenAPI
from sets import Set
import time

sys.path.insert(0, './bean')
sys.path.insert(0, './utils')

from vm import vm
from dev import dev
from topo import topo
import helper
from helper import autolog as log
from xswitch import xswitch
from xswitch import xrouter
from node import node_type as ntype
from link import switch2node
from router import prouter
from link import prouter2switch

# session: xen session
# ssh: ssh session
class xen_net:
	def __init__(self, uname, pwd, template_lst):
		# ASSUME: we got sudo
		helper.info_exe('chmod +x ./bash/*')
		# a list of 'dev' instances
		self.node_list=[]
		# a dict that stores <name, template_ref(vm_ref)> pairs
		self.template_dict={}
		self.emp_ids=[0]
		self.session=xen_net.init_session(uname, pwd)
		self.init_templates(template_lst)
		self.switch_set=Set()
		self.dev_set=Set()
		self.router_set=Set()
		self.ssh=xen_net.init_shell('localhost', uname, pwd)
		# init a dummy bridge
		self.dummy=self.create_new_xbr('dummy', record=False)
		pass

	@staticmethod
	def init_session(uname, pwd, local=True):
		# TODO: enable the init of a possibly remote session
		if local:
			session=XenAPI.xapi_local()
			session.xenapi.login_with_password(uname, pwd)
		else:
			log('currently not support remote connection')
		return session

	# for remote connection
	#from pexpect import pxssh
	# need autolog support
	# session usage:
	# session.sendline ('ls -l')
	# session.prompt()         # match the prompt
	# print session.before     # print everything before the prompt.
	@staticmethod
	def init_shell(host, uname, pwd, local=True):
		if local:
			return 'localhost'
		else:
			log('currently not support remote connection')
			return None
		#    session=pxssh.pxssh()
		#    if not session.login(host, uname, pwd):
		#        autolog("SSH session failed: " + str(session))
		#        return None
		#    else:
		#        autolog("SSH session login successful")
		#        return session

	def init_templates(self, tname_arr):
		for tname in tname_arr:
			lst=self.session.xenapi.VM.get_by_name_label(tname)
			count=len(lst)
			if count==1:
				self.template_dict[tname]=lst[0]
				continue
			elif(count<1):
				msg="too less templates (" + str(count) + ") found for " + tname
			else:
				msg="too many templates (" + str(count) + ") found for " + tname
			log(msg)

	# ATTENTION: when no empty slot is found, open a new slot for the new id, which need
	# to be used immediately
	def get_new_id(self):
		if len(self.emp_ids)==1:
			did=self.emp_ids[0]
			self.node_list.append(None)
			self.emp_ids[0]+=1
			return did
		else:
			last=len(self.emp_ids)-1
			did=self.emp_ids[last]
			self.emp_ids=self.emp_ids[:-1]

	# the only entry to delete node
	def del_node(self, did):
		node=self.node_list[did]

		if node.dtype==ntype.SWITCH:
			self.switch_set.remove(did)
		elif node.dtype==ntype.DEV:
			self.dev_set.remove(did)
		else:
			log("unsupported node type " + str(node.dtype))

		node.uninstall()
		self.emp_ids.append(did)

	def get_node(self, did):
		return self.node_list[did]

	# the 1st entry to create node
	def create_new_dev(self, tname, name, override, did=-1, vcpu=0, mem=0):
		if did==-1:
			did=self.get_new_id()
		template=self.template_dict[tname]
		node=vm(self.session, did, template, name)
		if override:
			node.set_fixed_VCPUs(self.session, vcpu)
			node.set_memory(self.session, mem)
		self.node_list[did]=node
		self.dev_set.add(did)
		return node

	# TODO: what to return? did or the newly created obj
	# the 2nd entry to create node
	def create_new_xbr(self, name, did=-1, record=True):
		if did==-1 and record:
			did=self.get_new_id()
		br=xswitch(self.session, did, name)
		if record:
			self.node_list[did]=br
			self.switch_set.add(did)
		return br

	def create_new_xrouter(self, name, ipaddr, did=-1):
		if did==-1:
			did=self.get_new_id()
		router=xrouter(self.session, did, name, ipaddr)
		self.node_list[did]=router
		self.switch_set.add(did)
		return router

	def create_new_prouter(self, name, if_json, neighbors, did=-1):
		if did==-1:
			did=self.get_new_id()
		router=prouter(did, name, if_json, neighbors)
		self.node_list[did]=router
		self.router_set.add(did)
		return router

	# ATTENTION: this may cause unexpected data loss!
	# 1. try to shutdown normally 2. try to shutdown by force
	def clear(self):
		start_time=time.time()

		#for node in self.node_list:
		#	if node.dtype==ntype.DEV:
		#		if node.get_power_state(self.session)=='Running':
		#			if not node.shutdown(self.session):
		#				node.hard_shutdown(self.session)
		#		node.uninstall(self.session)
		#	elif node.dtype==ntype.ROUTER or node.dtype==ntype.SWITCH:
		#		node.uninstall(self.session)
		#	else:
		#		log("unsupported node type " + node.dtype)

		for dev_id in self.dev_set:
			dev=self.node_list[dev_id]
			if dev.get_power_state(self.session)=='Running':
				if not dev.shutdown(self.session):
					dev.hard_shutdown(self.session)
			dev.uninstall(self.session)

		for sid in self.switch_set:
			switch=self.node_list[sid]
			switch.uninstall(self.session)

		for rid in self.router_set:
			r=self.node_list[rid]
			r.uninstall()

		self.node_list=[]
		self.emp_ids=[0]
		# assume that both two sets are maintained properly, meaning uninstalled
		# devices are removed from the sets on time
		self.dev_set.clear()
		self.switch_set.clear()
		self.router_set.clear()

		self.dummy.uninstall(self.session)

		stop_time=time.time()
		log("total time (s) consumed for topology clear: " + str(stop_time-start_time))

	def start_node(self, did):
		node=self.node_list[did]
		node.start(self.session)

	def shutdown_node(self, did):
		node=self.node_list[did]
		node.shutdown(self.session)

	# start all nodes
	# ATTENTION: we may need to start router/switch first here
	# if they are involved in the future
	# TODO: rewrite this method to discriminate between switch and devices
	def start_all(self):
		# start all devices
		[self.node_list[devid].start(self.session) for devid in self.dev_set]
		# start all routers
		[self.node_list[rid].start() for rid in self.switch_set]
		# start all prouters
		[self.node_list[prid].start(self.node_list) for prid in self.router_set]

	# did in topology init process would be purely determined by topo definition
	# TODO: don't forget to update emp_ids[]
	def init_topo(self, filename):
		start_time=time.time()
		nodes=topo.read_from_json(filename)

		self.node_list=[None]*len(nodes)
		self.emp_ids[0]=len(nodes)

		graph=[[None]*len(nodes)]*len(nodes)

		# create all nodes
		for node in nodes:
			if node['type']==ntype.SWITCH:
				self.create_new_xbr(node['name'], did=node['id'])
			elif node['type']==ntype.DEV:
				self.create_new_dev(node['image'], node['name'], 
				node['override'], did=node['id'], vcpu=node['vcpus'], mem=node['mem'])
			elif node['type']==ntype.ROUTER:
				self.create_new_xrouter(node['name'], node['ipaddr'], did=node['id'])
			elif node['type']==ntype.PROUTER:
				self.create_new_prouter(node['name'], node['ifs'], node['neighbors'], did=node['id'])
			else:
				log("node type " + node['type'] + " currently not supported!")
		# create all links
		for node1info in nodes:
			id1=node1info['id']
			node1=self.node_list[id1]
			for node2 in node1info['neighbors']:
				id2=node2['id']
				node2=self.node_list[id2]
				if graph[id1][id2]==None:
					link=self.connect(node1, node2)
					graph[id1][id2]=link
					graph[id2][id1]=link
		stop_time=time.time()
		log("total time (s) consumed for topology init: " + str(stop_time-start_time))

	def connect(self, node1, node2):
		# TODO: combine router type with switch type
		#log("\nnode1 name:\t" + str(node1.name) + "\n node2 name:\t" + str(node2.name) + "\n")
		#log("\nnode1 type:\t" + str(node1.dtype) + "\n node2 type:\t" + str(node2.dtype) + "\n")
		if node1.dtype==ntype.SWITCH or node1.dtype==ntype.ROUTER:
			if node2.dtype==ntype.DEV:
				vif=node1.plug(self.session, node2)
				return switch2node(vif)
			elif node2.dtype==ntype.PROUTER:
				r_if=node2.connect2switch(node1)
				return prouter2switch(r_if)
			else:
				log("type connection between (" + str(node1.dtype) 
					+ str(node2.dtype) + ") not supported yet!")
		elif node1.dtype==ntype.PROUTER:
			if node2.dtype==ntype.SWITCH:
				r_if=node1.connect2switch(node2)
				return prouter2switch(r_if)
			else:
				log("type connection between (" + str(node1.dtype) 
					+ str(node2.dtype) + ") not supported yet!")
		elif node1.dtype==ntype.DEV:
			# TODO: combine router type with switch type
			# TODO: we may have to separate them if new router def comes in
			if node2.dtype==ntype.SWITCH or node2.dtype==ntype.ROUTER:
				vif=node2.plug(self.session, node1)
				return switch2node(vif)
			else:
				log("type connection between (" + str(node1.dtype) 
					+ str(node2.dtype) + ") not supported yet!")
		else:
			log("type connection between (" + str(node1.dtype) 
					+ str(node2.dtype) + ") not supported yet!")

	def __del__(self):
		log("in the destructor of xnet")
		self.clear()
		pass

class link_prop:
	# 
	delay=10

def test_naive():
	# simple logging
	#FORMAT = "[%(levelname)s - %(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
	# init xennet with templates we would like to use
	tlst=['tandroid','tcentos']
	xnet=xen_net("root", "789456123", tlst)
	# creating test nodes
	test1=xnet.create_new_dev('tandroid', 'py_test1', override=True, vcpu=4, mem=2048)
	test2=xnet.create_new_dev('tcentos', 'py_test2', override=False)
	return xnet

def test_connect():
	# simple logging
	#FORMAT = "[%(levelname)s - %(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
	# init xennet with templates we would like to use
	tlst=['android-basic', 'android-terminal']
	xnet=xen_net("root", "789456123", tlst)
	# creating test nodes
	test1=xnet.create_new_dev('android-basic', 'py_test1', override=True, vcpu=4, mem=str(2048*1024*1024))
	test2=xnet.create_new_dev('android-terminal', 'py_test2', override=False)
	br1=xnet.create_new_xbr('dummy')

	xnet.connect(br1, test1)
	xnet.connect(test2, br1)
	return xnet

def test_topo(topo, start=True, nolog=False):
	# simple logging
	#FORMAT = "[%(levelname)s - %(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
	logger=logging.getLogger()
	logger.disabled=nolog
	# init xennet with templates we would like to use
	tlst=['tandroid', 'tcentos']
	xnet=xen_net("root", "789456123", tlst)
	# creating test nodes
	xnet.init_topo('topo/' + topo)
	if start:
		xnet.start_all()
	return xnet