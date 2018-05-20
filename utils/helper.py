from functools import wraps
import inspect
import subprocess

def initializer(func):
    """
    Automatically assigns the parameters.

    >>> class process:
    ...     @initializer
    ...     def __init__(self, cmd, reachable=False, user='root'):
    ...         pass
    >>> p = process('halt', True)
    >>> p.cmd, p.reachable, p.user
    ('halt', True, 'root')
    """
    names, varargs, keywords, defaults = inspect.getargspec(func)

    @wraps(func)
    def wrapper(self, *args, **kargs):
        for name, arg in list(zip(names[1:], args)) + list(kargs.items()):
            setattr(self, name, arg)
            
        for name, default in zip(reversed(names), reversed(defaults)):
            if not hasattr(self, name):
                setattr(self, name, default)

        func(self, *args, **kargs)

    return wrapper

import inspect, logging
def autolog(message, level=logging.DEBUG):
    "Automatically log the current function details."
    # Get the previous frame in the stack, otherwise it would
    # be this function!!!
    func = inspect.currentframe().f_back.f_code
    # Dump the message + the name of this function to the log.
    msg="%s:%i:%s:%s" % (
            func.co_filename, 
            func.co_firstlineno,
            func.co_name,
            message
        )
    logging.log(level, msg)

def mb2byte(mem):
    return str(int(mem)*1024*1024)

def info_exe(cmd):
    try:
        output=subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        return exc.returncode
    else:
        autolog("Output: \n{}\n".format(output), logging.INFO)
        return output