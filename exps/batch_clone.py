import logging, sys, XenAPI, os, time

sys.path.insert(0, '../../')

def init_session(uname, pwd, local=True):
	# TODO: enable the init of a possibly remote session
	if local:
		session=XenAPI.xapi_local()
		session.xenapi.login_with_password(uname, pwd)
	else:
		log('currently not support remote connection')
	return session

# ssid: snapshot id
# number: how many instances to create
def bat_clone(session, ss_ref, number):
	record=[]
	ref_lst=[]
	tot_start=time.time()
	for i in range(0, number):
		start=time.time()

		vref=session.xenapi.VM.clone(ss_ref, "test"+str(i))
		session.xenapi.VM.provision(vref)

		stop=time.time()
		elapse=stop-start
		record.append(elapse)
		ref_lst.append(vref)

	tot_stop=time.time()
	tot_elapse=tot_stop-tot_start
	record.append("Total\t "+str(tot_elapse))
	print "scale to "+str(number)+": "+"Total\t "+str(tot_elapse)+"s"
	write_1darr_file("bat_clone_res"+str(number)+".csv", record)
	bat_uninstall(session, ref_lst, number)

def async_clone(session, ss_ref, number):
	ref_lst=[]
	task_lst=[]
	tot_start=time.time()
	for i in range(0, number):
		task=session.xenapi.Async.VM.clone(ss_ref, "test"+str(i))
		task_lst.append(task)

	finished=[False]*number
	count=1
	while count<=number:
		for i in range(0, len(task_lst)):
			if not finished[i]:
				task=task_lst[i]
				res=session.xenapi.task.get_result(task)
				#print progress
				if len(res)>0:
					finished[i]=True
					vref=session.xenapi.task.get_result(task)[7:-8]
					#print vref
					session.xenapi.VM.provision(vref)
					ref_lst.append(vref)
					count+=1

	tot_stop=time.time()
	tot_elapse=tot_stop-tot_start
	#record.append("Total\t "+str(tot_elapse))
	print "scale to "+str(number)+": "+"Total\t "+str(tot_elapse)+"s"
	#write_1darr_file("bat_clone_res"+str(number)+".csv", record)
	bat_uninstall(session, ref_lst, number)

def async_clone_new(session, ss_ref, number):
	ref_lst=[]
	task_lst=[]
	tot_start=time.time()
	for i in range(0, number):
		task=session.xenapi.Async.VM.clone(ss_ref, "test"+str(i))
		task_lst.append(task)

	finished=[False]*number
	count=1
	while count<=number:
		for i in range(0, len(task_lst)):
			if not finished[i]:
				task=task_lst[i]
				res=session.xenapi.task.get_result(task)
				#print progress
				if len(res)>0:
					finished[i]=True
					vref=session.xenapi.task.get_result(task)[7:-8]
					#print vref
					session.xenapi.VM.provision(vref)
					ref_lst.append(vref)
					count+=1

	tot_stop=time.time()
	tot_elapse=tot_stop-tot_start
	#record.append("Total\t "+str(tot_elapse))
	print "scale to "+str(number)+": "+"Total\t "+str(tot_elapse)+"s"
	#write_1darr_file("bat_clone_res"+str(number)+".csv", record)
	bat_uninstall(session, ref_lst, number)


def bat_uninstall(session, ss_ref_lst, number):
	record=[]
	tot_start=time.time()
	for ss_ref in ss_ref_lst:
		start=time.time()
		destroy_disk(session, ss_ref)
		session.xenapi.VM.destroy(ss_ref)
		stop=time.time()
		elapse=stop-start
		record.append(elapse)
	tot_stop=time.time()
	tot_elapse=tot_stop-tot_start
	record.append("Total\t "+str(tot_elapse))
	write_1darr_file("bat_uninstall_result"+str(number)+".csv", record)

def destroy_disk(session, vref):
	vbd_list=session.xenapi.VM.get_VBDs(vref)
	for vbd in vbd_list:
		vdi=session.xenapi.VBD.get_VDI(vbd)
		if vdi!='OpaqueRef:NULL':
			session.xenapi.VDI.destroy(vdi)
		else:
			session.xenapi.VBD.destroy(vbd)


def write_2darr_file(fname, arr):
	if os.path.exists(fname):
		print fname+" already exists!"
		return
	file=open(fname, "w")
	for row in arr:
		for col in row:
			file.write(str(col)+"\t")
		file.write("\n")
	file.close()
	return

def write_1darr_file(fname, arr):
	if os.path.exists(fname):
		print fname+" already exists!"
		return
	file=open(fname, "w")
	for row in arr:
		file.write(str(row)+"\n")
	file.close()
	return

def main():
	session=init_session("root", "789456123")
	# test the batch install
	ss_ref=session.xenapi.VM.get_by_uuid("32f4b1a2-cd4b-e8d5-1753-51e77205c27e")
	i=0
	while i < 50:
		i+=10
		print("scaling to "+str(i)+" devices")
		#async_clone(session, ss_ref, i)
		bat_clone(session, ss_ref, i)
main()