from abc import ABCMeta, abstractmethod
import sys

sys.path.insert(0, '../utils')
sys.path.insert(0, './')

import logging
from helper import autolog as log
from node import node_type as ntype
from netif import ifb
from helper import info_exe
from helper import run_in_netns

# TODO
# 1. support for asymmetry
class link:
	__metaclass__ = ABCMeta

	link=None

	def __init__(self, node1, node2, link):
		self.link=link
		self.node_lst=[node1, node2]
		self.type_lst=[node1.dtype, node2.dtype]
		self.param_lst=[None]*len(self.node_lst)

	def append_qos(self, node, param):
		#log("appending qos to <"+str(self.node_lst[0].name)+","+str(self.node_lst[1].name)+">")
		#log("direction start:"+str(node.name)+"->")
		for i in range(0, len(self.node_lst)):
			if self.node_lst[i]==node:
				self.param_lst[i]=param

	def shape_all(self):
		if len(self.type_lst)==len(self.param_lst):
			for i in range(0, len(self.type_lst)):
				if self.param_lst[i]!=None:
					self.shape_traffic(self.type_lst[i], self.param_lst[i])
		else:
			log("cannot shape bidirectional traffic: length of type_lst: "
				+str(len(self.type_lst))+"\t param_lst: "+str(len(self.param_lst)))

	@abstractmethod
	def delete(self):
		pass

	# ASSUME: the direction of traffic shaping is defined
	# on the perspective of type
	# e.g., if we have type=SWITCH, the traffic starting from SWITCH
	# to the other end will be shaped
	@abstractmethod
	def shape_traffic(self, type, params):
		pass

	#@abstractmethod
	#def modify(self):
	#	pass

def traffic_cmd_compile(params):
	if len(params)==0:
		log("no traffic shaping param is specified!", logging.CRITICAL)
	cmds=[]
	for key in params:
		if key=="netem":
			cmds.append(netem_json2cmd(params[key]))
		elif key=="rate":
			cmds.append(tbfrate_json2cmd(params[key]))
		else:
			log("unsupported traffic control type: "+key)
	# combine cmds with prefixes
	tc_prefix="tc qdisc add dev {} "
	cmds[0]=tc_prefix+" root handle 1: "+cmds[0]
	for i in range(1, len(cmds)):
		cmds[i]=tc_prefix+" parent 1: handle "+str(i+1)+": "+cmds[i]
	return cmds

def netem_json2cmd(params):
	netem_cmd="netem "
	for key in params:
		param=params[key]
		if key=="delay":
			netem_cmd+=key+" "+param["base"]+" "
			if "variation" in param and param["variation"]!=None:
				netem_cmd+=param["variation"]+" "
				if "correlation" in param and param["correlation"]!=None:
					netem_cmd+=param["correlation"]+" "
				elif "distribution" in param and param["distribution"]!=None:
					netem_cmd+="distribution"+" "+param["distribution"]+" "
		else:
			netem_cmd+=key+" "+param["base"]+" "+param["correlation"]+" "
	return netem_cmd

def tbfrate_json2cmd(params):
	rate_cmd="tbf "
	for key in params:
		rate_cmd+=key+" "+params[key]+" "
	return rate_cmd

# majorly for managing link property info
class switch2node(link):

	def delete(self, session):
		session.xenapi.VIF.destroy(self.link)

	def shape_traffic(self, node_type, params):
		#log("shaping traffic for:"+str(self.link.name))
		cmds=traffic_cmd_compile(params)
		# determine linux system if name to apply control to
		if_name=""
		if node_type==ntype.SWITCH:
			new_ifb=ifb.create_new()
			new_ifb.start()
			self.link.redirect_to(new_ifb)
			if_name=new_ifb.name
		elif node_type==ntype.DEV:
			if_name=self.link.name
		else:
			log("unsupported node type: "+str(node_type))

		for i in range(0, len(cmds)):
			cmds[i]=(cmds[i].format(if_name))
		info_exe(cmds)

class prouter2switch(link):

	def delete(self):
		self.link.delete()

	def shape_traffic(self, node_type, params):
		cmds=traffic_cmd_compile(params)
		# determine linux system if name to apply control to
		if_name=""
		netns=None
		if node_type==ntype.PROUTER:
			if_name=self.link.get_in_if().name
			netns=self.link.get_in_if().netns
		elif node_type==ntype.SWITCH:
			if_name=self.link.get_out_if().name

		for i in range(0, len(cmds)):
			cmds[i]=(cmds[i].format(if_name))
		#log(str(cmds))
		#raw_input("before shaping the traffic")
		run_in_netns(cmds, netns)

# TODO: two vif might no be good for switch2switch representation
# obsolete: we ASSUME there is no need for switch2switch link
class switch2switch(link):
	def __init__(self, vif1, vif2):
		self.vif1=vif1
		self.vif2=vif2
	pass