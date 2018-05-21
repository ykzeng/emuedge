from abc import ABCMeta, abstractmethod

# TODO
# 1. support for asymmetry
class link:
	__metaclass__ = ABCMeta

	link=None

	@abstractmethod
	def delete(self):
		pass

	#@abstractmethod
	#def modify(self):
	#	pass

# majorly for managing link property info
class switch2node(link):
	def __init__(self, vif):
		self.link=vif

	def delete(self, session):
		session.xenapi.VIF.destroy(self.link)

class prouter2switch(link):
	def __init__(self, veth):
		self.link=veth

	def delete():
		self.link.delete()

# TODO: two vif might no be good for switch2switch representation
# obsolete: we ASSUME there is no need for switch2switch link
class switch2switch(link):
	def __init__(self, vif1, vif2):
		self.vif1=vif1
		self.vif2=vif2
	pass