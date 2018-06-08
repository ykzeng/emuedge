from abc import ABCMeta, abstractmethod
import sys, logging

sys.path.insert(0, '../utils')

from helper import info_exe
from helper import run_in_netns
from helper import autolog as log
from ipaddr import ipv4
import copy

# network interface abstraction
class netif:
	__metaclass__ = ABCMeta
	# the name in linux system
	name=''

	def __init__(self, name):
		self.name=name

	@abstractmethod
	# this session can be ssh or xenapi
	def delete(self, session=None):
		pass

	@abstractmethod
	def start(self):
		pass

	@staticmethod
	def start_dhcp_on(net_if, range_low, range_high, mask, netns=None):
	    cmd=[('dnsmasq --dhcp-range='+range_low+','+range_high
	        +','+mask+' --interface '+net_if)]
	    if netns!=None:
	        run_in_netns(cmd, netns)
	    else:
	        info_exe(cmd)

	def redirect_to(self, ifb):
		cmds=["tc qdisc add dev "+self.name+" handle ffff: ingress", 
			"tc filter add dev "+self.name+""" parent ffff: protocol ip u32 match u32 0 0 action mirred egress redirect dev """+ifb.name]
		#log(str(cmds), logging.CRITICAL)
		#raw_input("pls check the redirect commands.")
		run_in_netns(cmds)



class reversable:
	__metaclass__ = ABCMeta
	@abstractmethod
	def reverse_clone(self):
		pass

class xen_vif(netif, reversable):
	ref=''

	# init time is not ready-to-use
	# only after setup could this be used
	def __init__(self, ref):
		self.ref=ref

	def reverse_clone(self):
		return self

	def start(self, name):
		self.name=name

	def delete(session):
		session.xenapi.VIF.destroy(ref)

class linux_netif(netif):
	# netns name
	netns=None
	# ip addr with prefix size x.x.x.x/x
	ip=None
	# mask
	mask=None

	# suppose the ip is str
	def __init__(self, name, ip=None, netns=None):
		netif.__init__(self, name)
		self.ip
		self.netns=netns
		pass

	def connect2br(self, br):
		cmd=["ovs-vsctl add-port "+br+" "+self.name]
		run_in_netns(cmd)

	@staticmethod
	def create_veth_pairs(peer1, peer2):
		cmd="ip link add "+peer1+" type veth peer name "+peer2
		output=info_exe(cmd)
		if type(output) is str:
			return linux_netif(peer1), linux_netif(peer2)

	def masq_nat(self):
		cmd=["iptables -t nat -A POSTROUTING -o "+self.name+" -j MASQUERADE"]
		run_in_netns(cmd, self.netns)

	def unmasq_nat(self):
		cmd=["iptables -t nat -D POSTROUTING -o "+self.name+" -j MASQUERADE"]
		run_in_netns(cmd, self.netns)

	# TODO: maybe we don't need to undo the following ops
	def accept_from_if(self):
		cmd=["iptables -A INPUT -i "+self.name+" -j ACCEPT"]
		run_in_netns(cmd, self.netns)

	def allow_established_conn(self):
		cmd=[("iptables -A INPUT -i "+self.name
			+" -m state --state ESTABLISHED,RELATED -j ACCEPT")]
		run_in_netns(cmd, self.netns)

	def get_pure_ip(self):
		return self.ip.split('/')[0]

	def get_mask(self):
		return self.mask

	def get_ip(self):
		return self.ip

	def set_netns(self, netns):
		self.netns=netns

	def get_netns(self):
		return self.netns

	def stop(self):
		cmd=["ip link set "+self.name+" down"]
		run_in_netns(cmd, self.netns)

	def start(self):
		cmd=["ip link set "+self.name+" up"]
		run_in_netns(cmd, self.netns)

	def set_ip(self, ip, flush=False):
		cmd=[]
		if flush:
			cmd.append("ip addr flush dev "+self.name)
		cmd.append("ip addr add "+str(ip)+" dev "+self.name)
		run_in_netns(cmd, self.netns)
		self.ip=ip
		self.mask=ipv4.mask_from_suffix(ip.split('/')[1])

	def delete(self):
		cmd=["ip link del "+self.name]
		run_in_netns(cmd, self.netns)

	def start_dhcp(self, range_low, range_high):
		netif.start_dhcp_on(self.name, range_low, range_high, self.mask, self.netns)

class ifb(linux_netif):
	ifb_count=0
	ifb_total=0

	@staticmethod
	def create_new():
		if ifb.ifb_count<ifb.ifb_total:
			num=ifb.ifb_count
			ifb.ifb_count+=1
			return ifb("ifb"+str(num))
		else:
			log("creating ifb failed! ifb_total exceeded or ifb hasn't inited", logging.CRITICAL)

	# be CAREFUL: this command clears all previous existing ifb
	@staticmethod
	def init(total):
		cmds="modprobe -r ifb; modprobe ifb numifbs="+str(total)
		info_exe(cmds)
		ifb.ifb_total=total

	@staticmethod
	def clear():
		cmd="modprobe -r ifb"
		info_exe(cmd)

	def __init__(self, name):
		linux_netif.__init__(self, name)

class veth(reversable):
	def __init__(self, peer1, peer2, init=True):
		# use linux_netif obj as peer array element
		self.peer=[None]*2
		#self.netns=[None]*2
		#self.ip=['']*2
		if init:
			self.peer[0], self.peer[1]=linux_netif.create_veth_pairs(peer1, peer2)
		else:
			self.peer=[peer1, peer2]

	def reverse_clone(self):
		return veth(self.peer[1], self.peer[0], init=False)

	def start(self):
		for i in range(0, len(self.peer)):
			self.peer[i].start()

	def stop(self):
		for i in range(0, len(self.peer)):
			self.peer[i].stop()

	#def set_netns(self, num, netns):
	#	cmd="ip link set "+self.peer[num]+" netns "+netns
	#	info_exe(cmd)
	#	self.netns[num]=netns

	def delete(self):
		self.peer[1].delete()

	def set_ip(self, num, ip, clear=False):
		self.peer[num].set_ip(ip, clear)

	def start_dhcp(self, num, range_low, range_high):
		self.peer[num].start_dhcp(range_low, range_high)

	#	name=self.peer[num]
	#	ns=self.netns[num]
	#	# if we are going to clear all prev ip addr
	#	if clear:
	#		cmd=["ip addr flush dev "+name+";"]
	#	else:
	#		cmd=[]
	#	# ordinary commands
	#	cmd+=[ "ip addr add "+ip+" dev "+name]
	#	# add namespace specification if needed
	#	if ns!=None:
	#		run_in_netns(cmd, self.netns[num])
	#	else:
	#	# run the commands
	#		info_exe(''.join(cmd))
	#	self.ip[num]=ip

class router_if(veth):
	def __init__(self, rname, index):
		self.peer=[]
		in_if=rname+"-in"+str(index)
		out_if=rname+"-out"+str(index)

		veth.__init__(self, in_if, out_if)

	def get_out_if(self):
		return self.peer[1]

	def get_in_if(self):
		return self.peer[0]

	def get_if_name(self):
		return self.peer[0].name

	def set_ip(self, ip):
		veth.set_ip(self, 0, ip)

	def start_dhcp(self, range_low, range_high):
		self.get_in_if().start_dhcp(range_low, range_high)

class netns():

	def __init__(self, name):
		# netns name
		self.name=name
		# interfaces in this netns
		self.if_lst=[]
		self.setup(name)

	def setup(self, name):
		cmd="ip netns add "+self.name
		info_exe(cmd)
		#if if_lst!=None:
		#	for if_name in if_lst:
		#		self.add_if(if_name)
	def setup_if(self, size):
		self.if_lst=[None]*size

	def start_dhcp(self, ifid, range_low, range_high):
		self.if_lst[ifid].start_dhcp(range_low, range_high)

	def add_if(self, rif_obj, index):
		in_if=rif_obj.get_in_if()
		cmd="ip link set "+in_if.name+" netns "+self.name
		in_if.set_netns(self.name)
		self.if_lst[index]=rif_obj
		info_exe(cmd)

	def append_if(self, rif_obj):
		in_if=rif_obj.get_in_if()
		cmd="ip link set "+in_if.name+" netns "+self.name
		in_if.set_netns(self.name)
		self.if_lst.append(rif_obj)
		info_exe(cmd)
		return (len(self.if_lst)-1)

	#def add_if(self, if_name):
	#	cmd="ip link set "+if_name+" "+self.name
	#	info_exe(cmd)

	def delete(self):
		cmd="ip netns del "+self.name
		output=info_exe(cmd)

	def normal_nat(self, wan_ifids, lan_ifid):
		lan_ip_prefix=ipaddr.ipmask2prefix(self.if_lst[lan_ifid].ip, self.if_lst[lan_ifid].mask)
		for wan_ifid in wan_ifids:
			wan_if_name=self.if_lst[wan_ifid].name
			wan_if_ip=self.if_lst[wan_ifid].ip
			cmd="""iptables -t nat -A POSTROUTING -s %s 
				-o %s -j SNAT --to %s"""%(lan_ip_prefix, wan_if_name, wan_if_ip)
			cmd_lst.append(cmd)
		log("final cmd lst for normal nat:"+str(cmd_lst))
		run_in_netns(cmd_lst, self.name)

	def get_if_by_id(self, ifid):
		return self.if_lst[ifid]

	def get_iflst(self):
		return self.if_lst
#
#	#def masq_nat(self, if_name):
#	#	cmd=["iptables -t nat -A POSTROUTING -o "+if_name+" -j MASQUERADE"]
#	#	run_in_netns(cmd, self.name)
#
#	#def unmasq_nat(self, if_name):
#	#	cmd=["iptables -t nat -D POSTROUTING -o "+if_name+" -j MASQUERADE"]
#	#	run_in_netns(cmd, self.name)
#
#	## TODO: maybe we don't need to undo the following ops
#	#def accept_from_if(self, if_name):
#	#	cmd=["iptables -A INPUT -i "+if_name+" -j ACCEPT"]
#	#	run_in_netns(cmd, self.name)
#
#	#def allow_established_conn(self, if_name):
#	#	cmd=[("iptables -A INPUT -i "+if_name
#	#		+" -m state --state ESTABLISHED,RELATED -j ACCEPT")]
	#	run_in_netns(cmd, self.name)

	# accept outgoing conn through iptables
	def open_out_conn(self):
		cmd=["iptables -A OUTPUT -j ACCEPT"]
		run_in_netns(cmd, self.name)

	def close_out_conn(self):
		cmd=["iptables -D OUTPUT -j ACCEPT"]
		run_in_netns(cmd, self.name)

	def enable_ip_forward(self):
		cmd=["echo 1 > /proc/sys/net/ipv4/ip_forward"]
		run_in_netns(cmd, self.name)

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