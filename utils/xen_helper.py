import logging
import subprocess
import XenAPI

from helper import autolog as log

class xen_helper:

	@staticmethod
	def get_snapshot_id(name):
		cmd=("xe snapshot-list | grep -B 1 '" + name + "' | grep -v '" 
			+ name + "' | cut -d: -f2 | tr -d '[:space:]'")
		#id=os.system(cmd)
		id=subprocess.check_output(cmd, shell=True)
		if id=='':
			#print "The requested snapshot " + name + " doesn't exist!"
			return None
		else:
			return id

	@staticmethod
	def get_vm_param(vmid, pname):
		logging.debug('A debug message!')
		logging.info('We processed %d records', 100)
		cmd=("xe vm-param-get uuid=" + str(vmid) + " param-name=" + str(pname))
		res=subprocess.check_output(cmd, shell=True)
		return res

	@staticmethod
	def set_vm_param(vmid, pname):
		cmd=("xe vm-param-set uuid=" + str(vmid) + " param-name=" + str(pname))
		res=subprocess.check_output(cmd, shell=True)
		return res

	@staticmethod
	def del_vm_by_id(vmid):
		cmd=("xe vm-uninstall force=True uuid="+str(vmid))
		res=subprocess.check_output(cmd, shell=True)
		if res=='All objects destroyed':
			return True
		else:
			return False

	@staticmethod
	def del_vm_by_name(session, name):
		vids=xen_helper.get_vid_by_name(session, name)
		if len(vids)==0:
			log("no vm named '" + name + "' exists!")
		else:
			for vid in vids:
				xen_helper.del_vm_by_id(vid)

	@staticmethod
	def get_vid_by_name(session, name):
		vms=session.xenapi.VM.get_by_name_label(name)
		for i in range(0, len(vms)):
			vms[i]=session.xenapi.VM.get_uuid(vms[i])
		return vms

	@staticmethod
	def init():
		session = XenAPI.xapi_local()
		session.xenapi.login_with_password("root", "789456123")
		return session
