import os
import subprocess
import logging, sys
import XenAPI
from sets import Set
import time

sys.path.insert(0, './bean/')
sys.path.insert(0, './utils/')

from vm import vm
from dev import dev
from topo import topo
import helper
from helper import autolog as log
from xswitch import xrouter
from node import node_type as ntype
#from link import switch2node
from router import prouter
from xswitch import xswitch
#from link import prouter2switch
from link import veth_link
from link import if_link
from netif import ifb

class delay_dist:
	def __init__(self, mu, sigma, rho=None):
		self.mu=mu
		self.sigma=sigma
		self.rho=rho

# session: xen session
# ssh: ssh session
class xen_net:

	def __init__(self, uname, pwd, template_lst, dist_db=None, ifb_count=0):
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
		self.controlled_link_set=Set()
		# init a dummy bridge
		#self.dummy=self.create_new_xbr('dummy', record=False)
		# TODO: here we need a change
		self.ifb_count=0
		if ifb_count>0:
			ifb.init(ifb_count)
			self.ifb_count=ifb_count
		pass
		# init distribution db
		self.dist_db=None
		if dist_db!=None:
			self.init_dist_db(dist_db)

	def init_dist_db(self, dist_db):
		self.dist_db={}

		distdb_file=open(dist_db)
		lines=distdb_file.readlines()
		dist_count=len(lines)
		i=0
		while i < dist_count:
			name=lines[i][:-1]
			mu=lines[i+1].replace(" ", "").split("=")[1][:-1]+"ms"
			sigma=lines[i+2].replace(" ", "").split("=")[1][:-1]+"ms"
			new_dist=delay_dist(mu, sigma)
			self.dist_db[name]=new_dist
			i+=4
		# for debugging
		name_list="dists loaded:"
		for dist in self.dist_db:
			name_list+=dist+"\t"
		log(name_list)

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
	def create_new_dev(self, tname, name, override, did=-1, vcpu=0, mem=0, vif_prefix=None):
		if did==-1:
			did=self.get_new_id()
		template=self.template_dict[tname]
		node=vm(self.session, did, template, name, vif_prefix=vif_prefix)
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

	def create_new_prouter(self, name, ifs_json=None, nat_json=None, dhcp_json=None, neighbors=None, did=-1):
		if did==-1:
			did=self.get_new_id()
		router=prouter(did, name, ifs_json=ifs_json, nat_params=nat_json, 
			dhcp_params=dhcp_json, neighbors=neighbors)
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

		# ATTENTION: this will consequently delete the other half of netif, qdisc rules
		for rid in self.router_set:
			r=self.node_list[rid]
			r.uninstall()
		log("cleared all virtual if, qdisc rules and netns")

		for dev_id in self.dev_set:
			dev=self.node_list[dev_id]
			if dev.get_power_state(self.session)=='Running':
				if not dev.shutdown(self.session):
					dev.hard_shutdown(self.session)
			dev.uninstall(self.session)
		for sid in self.switch_set:
			switch=self.node_list[sid]
			switch.uninstall(self.session)
		log("cleared all devices and switches")

		self.node_list=[]
		self.emp_ids=[0]
		# assume that both two sets are maintained properly, meaning uninstalled
		# devices are removed from the sets on time
		self.dev_set.clear()
		self.switch_set.clear()
		self.router_set.clear()

		#self.dummy.uninstall(self.session)
		ifb.clear()
		log("cleared all metadata, ifb")

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
		# waiting for link control to apply after all machine network functions are ready
		count=len(self.dev_set)
		tap_check=[False]*count
		log("looping to wait for network-ready on all vms before setting up traffic rules")
		while count!=0:
			i=0
			for devid in self.dev_set:
				if not tap_check[i]:
					if self.node_list[devid].check_tap():
						#log("get the "+str(i)+"th tap ready for device "+self.node_list[devid].name)
						tap_check[i]=True
						count-=1
				i+=1
		log("start applying traffic shaping rules...")
		# enable link control
		[link.shape_traffic(dist_db=self.dist_db) for link in self.controlled_link_set]


	# did in topology init process would be purely determined by topo definition
	# TODO: don't forget to update emp_ids[]
	def init_topo(self, filename):
		start_time=time.time()
		nodes=topo.read_from_json(filename)

		self.node_list=[None]*len(nodes)
		self.emp_ids[0]=len(nodes)

		self.graph=[[None for x in range(len(nodes))] for y in range(len(nodes))]

		# create all nodes
		for node in nodes:
			if node['type']==ntype.SWITCH:
				self.create_new_xbr(node['name'], did=node['id'])
			elif node['type']==ntype.DEV:
				vif_prefix='vif'
				if 'vif_prefix' in node:
					vif_prefix=node['vif_prefix']
				if node['override']:
					self.create_new_dev(node['image'], node['name'], 
					node['override'], did=node['id'], vcpu=node['vcpus'], 
					mem=node['mem'], vif_prefix=vif_prefix)
				else:
					self.create_new_dev(node['image'], node['name'], 
					node['override'], did=node['id'], vif_prefix=vif_prefix)
			elif node['type']==ntype.ROUTER:
				self.create_new_xrouter(node['name'], node['ipaddr'], did=node['id'])
			elif node['type']==ntype.PROUTER:
				self.create_new_prouter(node['name'], node['ifs'], 
					node['nat'], node['dhcp'], node['neighbors'], did=node['id'])
			else:
				log("node type " + node['type'] + " currently not supported!")

		for n1_json in nodes:
			src_nid=n1_json['id']
			src_node=self.node_list[src_nid]
			#raw_input("src from "+src_node.name)

			if 'neighbors' not in n1_json:
				continue

			for n2_json in n1_json['neighbors']:
				dest_nid=n2_json['id']
				dest_node=self.node_list[dest_nid]
				#raw_input("dest to "+dest_node.name)

				link=self.graph[src_nid][dest_nid]
				if link==None:
					#log("creating new link between:"+src_node.name+","+dest_node.name)
					link, reverse=self.connect(src_node, dest_node)
					self.graph[src_nid][dest_nid]=link
					self.graph[dest_nid][src_nid]=reverse
				if "link_control" in n2_json:
					#link.append_qos(src_node, n2_json["link_control"])
					#self.controlled_link_set.add(link)
					link.set_qos(n2_json["link_control"])
					self.controlled_link_set.add(link)
					if src_node.dtype==ntype.DEV:
						self.ifb_count+=1

		ifb.init(self.ifb_count)

		stop_time=time.time()
		log("total time (s) consumed for topology init: " + str(stop_time-start_time))

	def connect(self, node1, node2):
		# TODO: combine router type with switch type
		#log("\nnode1 name:\t" + str(node1.name) + "\n node2 name:\t" + str(node2.name) + "\n")
		#log("\nnode1 type:\t" + str(node1.dtype) + "\n node2 type:\t" + str(node2.dtype) + "\n")
		if node1.dtype==ntype.SWITCH or node1.dtype==ntype.ROUTER:
			return node1.connect(node2, session=self.session)
		elif node1.dtype==ntype.PROUTER:
			if node2.dtype==ntype.SWITCH:
				return node2.connect(node1)
			else:
				log("type connection between (" + str(node1.dtype) 
					+ str(node2.dtype) + ") not supported yet!")
		elif node1.dtype==ntype.DEV:
			# TODO: combine router type with switch type
			# TODO: we may have to separate them if new router def comes in
			if node2.dtype==ntype.SWITCH or node2.dtype==ntype.ROUTER:
				return node2.connect(node1, session=self.session)
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

def test_topo(topo, dist_db="trace/dist_db", start=True, nolog=False):
	# simple logging
	#FORMAT = "[%(levelname)s - %(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
	logger=logging.getLogger()
	logger.disabled=nolog
	# init xennet with templates we would like to use
	tlst=['tandroid', 'tcentos', 'centos-new']
	xnet=xen_net("root", "789456123", tlst, dist_db=dist_db)
	# creating test nodes
	xnet.init_topo('topo/' + topo)
	if start:
		xnet.start_all()
	return xnet

def xnet_interactive():
	tlst=['tandroid', 'tcentos']
	xnet=xen_net("root", "789456123", tlst)
	return xnet

def test_dist(dist_db='trace/dist_db', nolog=False):
	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
	logger=logging.getLogger()
	logger.disabled=nolog
	# init xennet with templates we would like to use
	tlst=['tandroid', 'tcentos', 'centos-new']
	xnet=xen_net("root", "789456123", tlst, dist_db=dist_db)