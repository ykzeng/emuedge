from abc import ABCMeta, abstractmethod
import sys, logging

sys.path.insert(0, '../utils')

from helper import info_exe
from helper import run_in_netns
from helper import autolog as log

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
	def delete(self, session=None):
		pass

	@abstractmethod
	def start(self):
		pass

class xen_vif(netif):
	ref=''

	# init time is not ready-to-use
	# only after setup could this be used
	def __init__(self, ref):
		self.ref=ref

	def start(self, name):
		self.name=name

	def delete(session):
		session.xenapi.VIF.destroy(ref)

class linux_netif(netif):
	def __init__(self, name):
		netif.__init__(self, name)
		pass

	#@abstractmethod
	#def down():
	#	pass
	#@abstractmethod
	#def up():
	#	pass
	@abstractmethod
	def set_ip():
		pass

class netns():
	name=''

	def __init__(self, name):
		self.name=name
		self.setup()

	def setup(self):
		cmd="ip netns add "+self.name
		output=info_exe(cmd)

	def __del__(self):
		cmd="ip netns del "+self.name
		output=info_exe(cmd)

class veth(linux_netif):

	def __init__(self, name1, name2):
		self.peer=['']*2
		self.netns=[None]*2
		self.ip=['']*2

		cmd1="ip link add "+name1+" type veth peer name "+name2
		info_exe(cmd1)
		self.peer[0]=name1
		self.peer[1]=name2

	def start(self):
		for i in range(0, len(self.peer)):
			cmd=["ip link set "+self.peer[i]+" up"]
			if self.netns[i]!=None:
				run_in_netns(cmd, self.netns[i])
			else:
				info_exe(cmd)

	def stop(self):
		for i in range(0, len(self.peer)):
			cmd=["ip link set "+self.peer[i]+" down"]
			if self.netns[i]!=None:
				run_in_netns(cmd, self.netns[i])
			else:
				info_exe(cmd)

	def set_netns(self, num, netns):
		cmd="ip link set "+self.peer[num]+" netns "+netns
		info_exe(cmd)
		self.netns[num]=netns

	def delete(self):
		cmd="ip link del "+self.peer[0]
		info_exe(cmd)

	def set_ip(self, num, ip, clear=False):
		name=self.peer[num]
		ns=self.netns[num]
		# if we are going to clear all prev ip addr
		if clear:
			cmd=["ip addr flush dev "+name+";"]
		else:
			cmd=[]
		# ordinary commands
		cmd+=[ "ip addr add "+ip+" dev "+name]
		# add namespace specification if needed
		if ns!=None:
			run_in_netns(cmd, self.netns[num])
		else:
		# run the commands
			info_exe(''.join(cmd))
		self.ip[num]=ip

	#def __del__(self):
	#	self.delete()

class router_if(veth):
	def __init__(self, rname, index, ip):
		self.peer=[]
		in_if=rname+"-in"+str(index)
		out_if=rname+"-out"+str(index)

		veth.__init__(self, in_if, out_if)
		veth.set_netns(self, 0, rname)
		veth.set_ip(self, 0, ip)

	def get_out_if(self):
		return self.peer[1]

def test_veth():
	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
	return veth("test0", "test1")

def test_netns():
	return netns("test")

# testcases
#test=test_veth()
#test.set_ip(0, "10.0.0.100/24")
#test.set_ip(1, "10.0.0.3/24", True)
#test.start()
#test.stop()
#tns=test_netns('test')
#test.set_netns(0, "test")