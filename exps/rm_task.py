import XenAPI

def init_session(uname, pwd, local=True):
	# TODO: enable the init of a possibly remote session
	if local:
		session=XenAPI.xapi_local()
		session.xenapi.login_with_password(uname, pwd)
	else:
		log('currently not support remote connection')
	return session

session=init_session("root", "789456123")
tlist=session.xenapi.task.get_all()
for t in tlist:
    session.xenapi.task.destroy(t)
