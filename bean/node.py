import sys, logging
from abc import ABCMeta, abstractmethod

class node_type:
	SWITCH=0
	# currently only supports VM
	DEV=1
	# xrouter implemented based on ovs switch
	ROUTER=2
	# pure router based on linux netns
	PROUTER=3
	# mininet host
	MN=4


class node:
	__metaclass__ = ABCMeta

	def __init__(self, did, name, dtype):
		# device id
		self.did=did
		# device type
		self.dtype=dtype
		# device name
		self.name=name
		# neighbor of the node
		self.neighbors={}
		pass

	@abstractmethod
	def uninstall(self):
		pass

	@abstractmethod
	def start(self, session=None):
		pass