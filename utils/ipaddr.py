from abc import ABCMeta, abstractmethod
from helper import autolog as log
import logging

class ip:
	__metaclass__ = ABCMeta

class ipv4(ip):
	# the ip str standard:
	# x.x.x.x/x
	addr=-1
	mask=-1

	def __init__(self, ipstr):
		addr_arr=ipstr.split('/')[0].split('.')
		mask_bit=int(ipstr.split('/')[1])

		if mask_bit >= 32:
			log("get more than 32 bit mask " + str(mask_bit), logging.CRITICAL)
			return
		elif len(addr_arr)!=4:
			log("invalid ip addr pairs, expect 4 but got " + str(len(addr_arr)), logging.CRITICAL)
			return

		mask=['1']*int(mask_bit)
		mask+=['0']*int(32-mask_bit)

		self.mask=int(mask, 2)

		addr_bin=''
		for num in addr_arr:
			bnum=bin(int(num))[2:].zfill(8)
			addr_bin+=bnum
		self.addr=int(addr_bin, 2)

	def __str__(self):
		return bin(self.addr)[2:].zfill(32)

	@staticmethod
	def get_first_in_subnet(subnet):
		pass

	@staticmethod
	def mask_from_suffix(suffix):
		mask_bit=int(suffix)
		if mask_bit>32:
			log("get more than 32 bit mask " + str(mask_bit), logging.CRITICAL)
			return None
		elif mask_bit<0:
			log("get less than 0 bit mask " + str(mask_bit), logging.CRITICAL)
			return None
		mask=['1']*int(mask_bit)
		mask+=['0']*int(32-mask_bit)

		i=0
		mask_str=''
		while i<32:
			sub=''.join(mask[i:(i+8)])
			mask_str+=str(int(sub,2))+"."
			i=i+8
		return mask_str[:-1]

	@staticmethod
	def suffix_from_mask(mask):
		pass

#print ipv4.mask_from_suffix("1")