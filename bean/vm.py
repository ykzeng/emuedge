#!/usr/bin/env python
import XenAPI, logging, sys

sys.path.insert(0, '../utils')
sys.path.insert(0, './')

from dev import dev
from node import node_type
from helper import autolog as log
from helper import mb2byte
from netif import xen_vif as xvif

# ATTENTION: all memory are in MB
class vm(dev):
	# snapshot id
	#ssid=''
	# template id
	#tid=''
	
	# vcpu cores
	vcpu=1
	# memory in MB
	mem=1024
	# vm reference from XenAPI
	vref=''
	# snapshot or tempalteid the vm based on
	template=''
	# domain id, useful for identifying vifs
	domid=-1
	# vifs on this vm
	# per XenServer 7.4, the limit of vif number on a VM is 7
	vif_prefix='vif'

	def __init__(self, session, did, template, name, vif_prefix='vif'):
		# TODO: may need to change node type
		dev.__init__(self, did, name, dtype=node_type.DEV)
		self.template=template
		self.vref=self.install(session, template)

		self.if_lst=[None]*7
		self.vif_prefix=vif_prefix

	# get the next vif device id
	def get_new_vif_id(self):
		# find out the empty slot in interface list as the first available vif slot
		for i in range(0, len(self.if_lst)):
			if self.if_lst[i]==None:
				return i
		log("all vif slots are occupied!", level=logging.CRITICAL)
		return None

	# create vif
	# @return vif handle in xen
	# assume
	# 2. no vif changes are made otherwhere than our system
	def create_vif_on_xbr(self, session, xswitch):
		id=str(self.get_new_vif_id())
		log(str(id))
		# construct vif args
		vif_args={ 'device': id,
			'network': xswitch.br,
			'VM': self.vref,
			'MAC': "",
			'MTU': "1500",
			"qos_algorithm_type": "",
			"qos_algorithm_params": {},
			"other_config": {} }
		vif=session.xenapi.VIF.create(vif_args)
		return vif

	def set_VCPUs_max(self, session, max_vcpu):
		platform_info=session.xenapi.VM.get_platform(self.vref)
		cores_per_sock=int(platform_info['cores-per-socket'])
		if max_vcpu%cores_per_sock!=0:
			log("max vcpu to set is not a multiple of cores-per-socket! abandon!")
			return
		log('the power state: ' + self.get_power_state(session), logging.INFO)
		if (self.get_power_state(session)=='Halted'):
			session.xenapi.VM.set_VCPUs_max(self.vref, max_vcpu)
		else:
			msg="make sure VM in halted state"
			log(msg)

	def set_VCPUs_at_startup(self, session, up_vcpu):
		platform_info=session.xenapi.VM.get_platform(self.vref)
		cores_per_sock=int(platform_info['cores-per-socket'])
		if up_vcpu%cores_per_sock!=0:
			log("startup vcpu to set is not a multiple of cores-per-socket! abandon!")
			return
		log('the power state: ' + self.get_power_state(session), logging.INFO)
		if (self.get_power_state(session)=='Halted'):
			session.xenapi.VM.set_VCPUs_at_startup(self.vref, up_vcpu)
		else:
			msg="make sure VM in halted state"
			log(msg)

	def set_fixed_VCPUs(self, session, vcpu):
		platform_info=session.xenapi.VM.get_platform(self.vref)
		cores_per_sock=int(platform_info['cores-per-socket'])
		self.set_VCPUs_at_startup(session, cores_per_sock)
		self.set_VCPUs_max(session, cores_per_sock)

		self.set_VCPUs_max(session, vcpu)
		self.set_VCPUs_at_startup(session, vcpu)

	# install the vm based on snapshot/template ssid
	# @session: XenAPI session
	# @template: can be vm/snapshot handle
	def install(self, session, template):
		vref=session.xenapi.VM.clone(template, self.name)
		session.xenapi.VM.provision(vref)
		return vref

	def provision(self, session):
		session.xenapi.VM.provision(self.vref)

	def get_static_min_mem(self, session):
		return session.xenapi.VM.get_memory_static_min(self.vref)
	def get_static_max_mem(self, session):
		return session.xenapi.VM.get_memory_static_max(self.vref)
	def get_dynamic_min_mem(self, session):
		return session.xenapi.VM.get_memory_dynamic_min(self.vref)
	def get_dynamic_max_mem(self, session):
		return session.xenapi.VM.get_memory_dynamic_max(self.vref)

	def set_fixed_min_mem(self, session, min_mem):
		self.set_static_min_mem(session, 0)
		self.set_dynamic_min_mem(session, 0)

		self.set_dynamic_min_mem(session, min_mem)
		self.set_static_min_mem(session, min_mem)

	def set_fixed_max_mem(self, session, max_mem):
		dmin=self.get_dynamic_min_mem(session)
		self.set_dynamic_max_mem(session, dmin)
		self.set_static_max_mem(session, dmin)

		self.set_static_max_mem(session, max_mem)
		self.set_dynamic_max_mem(session, max_mem)

	def set_fixed_mem(self, session, mem):
		mem=mb2byte(mem)
		log("before setting fixed min")
		self.set_fixed_min_mem(session, mem)
		log("before setting fixed max")
		self.set_fixed_max_mem(session, mem)

	def set_static_min_mem(self, session, mem):
		mem=mb2byte(mem)
		try:
			session.xenapi.VM.set_memory_static_min(self.vref, mem)
		except XenAPI.Failure as e:
			print(e)

	def set_static_max_mem(self, session, mem):
		mem=mb2byte(mem)
		try:
			session.xenapi.VM.set_memory_static_max(self.vref, mem)
		except XenAPI.Failure as e:
			print(e)

	def set_dynamic_min_mem(self, session, mem):
		mem=mb2byte(mem)
		try:
			session.xenapi.VM.set_memory_dynamic_min(self.vref, mem)
		except XenAPI.Failure as e:
			print(e)

	def set_dynamic_max_mem(self, session, mem):
		mem=mb2byte(mem)
		try:
			session.xenapi.VM.set_memory_dynamic_max(self.vref, mem)
		except XenAPI.Failure as e:
			print(e)

	def start(self, session, pause=False, force=False):
		try:
			session.xenapi.VM.start(self.vref, pause, force)
			self.domid=session.xenapi.VM.get_domid(self.vref)
			# update all vifs
			vifs=session.xenapi.VM.get_VIFs(self.vref)
			#log("length of vifs on " + self.name + ": " + str(len(vifs)))
			for vif in vifs:
				index=int(session.xenapi.VIF.get_device(vif))
				linux_name=self.vif_prefix+str(self.domid)+'.'+str(index)
				self.if_lst[index]=xvif(vif)
				self.if_lst[index].start(linux_name)
			self.print_vifs()
			return self.domid
		except XenAPI.Failure as e:
			print(e)

	def clean_shutdown(self, session):
		try:
			session.xenapi.VM.clean_shutdown(self.vref)
		except XenAPI.Failure as e:
			print(e)

	def shutdown(self, session):
		try:
			session.xenapi.VM.shutdown(self.vref)
			return True
		except XenAPI.Failure as e:
			print(e)
			return False

	def hard_shutdown(self, session):
		try:
			session.xenapi.VM.hard_shutdown(self.vref)
			return True
		except XenAPI.Failure as e:
			print(e)
			return False

	def get_power_state(self, session):
		return session.xenapi.VM.get_power_state(self.vref)

	def destroy(self, session):
		if (self.get_power_state(session)=='Halted'):
			session.xenapi.VM.destroy(self.vref)
		else:
			msg="make sure VM in halted state"
			log(msg)

	def set_memory(self, session, mem):
		mem=mb2byte(mem)
		try:
			self.set_static_min_mem(session, 0)
			session.xenapi.VM.set_memory(self.vref, mem)
		except XenAPI.Failure as e:
			print(e)

	# TODO: fix the bug in destroy certain VDI
	# how to pass the memory which exceeds the XML-RPC limits
	def uninstall(self, session):
		log("uninstalling " + self.name)
		if (self.get_power_state(session)=='Halted'):
			self.destroy_all_vbd_vdi(session)
			self.destroy(session)
		else:
			msg="make sure VM in halted state"
			log(msg)

	def destroy_all_vbd_vdi(self, session):
		vbd_list=session.xenapi.VM.get_VBDs(self.vref)
		for vbd in vbd_list:
			vdi=session.xenapi.VBD.get_VDI(vbd)
			if vdi!='OpaqueRef:NULL':
				session.xenapi.VDI.destroy(vdi)
			else:
				session.xenapi.VBD.destroy(vbd)

	def get_VBDs(self, session):
		return session.xenapi.VM.get_VBDs(self.vref)

	def print_vifs(self):
		msg=self.name + " vifs:"
		for netif in self.if_lst:
			if netif==None:
				break
			else:
				msg+=("\n"+netif.name)
		log(msg)