import sys, logging
from node import node
from node import node_type
from abc import abstractmethod
from router import multi_if as mif

class dev(node, mif):

	def __init__(self, did, name, dtype=node_type.DEV):
		node.__init__(self, did, name, dtype)
		pass

	def __str__(self):
		attrs = vars(self)
		return str(', '.join("%s: %s" % item for item in attrs.items()))

	@abstractmethod
	def start(self, session=None):
		pass

	@abstractmethod
	def shutdown(self, session=None):
		pass

	@abstractmethod
	def create_vif_on_xbr(self, session, xswitch):
		pass