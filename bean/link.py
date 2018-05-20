from abc import ABCMeta, abstractmethod

# TODO
# 1. support for asymmetry
class link:
	__metaclass__ = ABCMeta

	@abstractmethod
	def delete(self):
		pass

	@abstractmethod
	def modify(self):
		pass

# majorly for managing link property info
class switch2node(link):
	def __init__(self, vif):
		self.vif=vif

	def delete(self, session):
		session.xenapi.VIF.destroy(self.vhandle)

	def modify(self):
		pass

# TODO: two vif might no be good for switch2switch representation
# obsolete: we ASSUME there is no need for switch2switch link
class switch2switch(link):
	def __init__(self, vif1, vif2):
		self.vif1=vif1
		self.vif2=vif2
	pass