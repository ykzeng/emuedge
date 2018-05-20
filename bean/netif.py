from abc import ABCMeta, abstractmethod

# network interface abstraction
class netif:
	__metaclass__ = ABCMeta
	# the name in linux system
	name=''

	def __init__(self, name):
		self.name=name
		pass

	@abstractmethod
	# this session can be ssh or xenapi
	def delete(session=None):
		pass

class xen_vif(netif):
	ref=''

	def __init__(self, name, ref):
		netif.__init__(self, name)
		self.ref=ref
		pass

	def delete(session):
		session.xenapi.VIF.destroy(ref)
		pass

class linux_netif(netif):
	def __init__(self, name):
		netif.__init__(self, name)
		pass

	@abstractmethod
	def down():
		pass
	@abstractmethod
	def up():
		pass
	@abstractmethod
	def set_ipv4():
		pass

class veth(linux_netif):
	peer1=''
	peer2=''
	netns1=''
	netns2=''

	def __init__(self, name1, name2):
		self.peer1=name1
		self.peer2=name2