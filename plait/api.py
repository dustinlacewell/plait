import inspect
from twisted.internet import reactor
from twisted.internet.threads import blockingCallFromThread as blockingCFT

from plait.task import thread_locals

class RemoteCallError(Exception): pass

def run(cmd, quiet=False):
    worker = thread_locals.worker
    log = thread_locals.log
    log("Running command: {}".format(cmd))
    result = blockingCFT(reactor, worker.execFromThread, cmd)
    if result.stderr:
        error = RemoteCallError(result.stderr)
        stack = inspect.stack()[1]
        error.file, error.lineno = stack[1], stack[2]
        log.write("STDERR:")
        log.write(error.file + ":" + error.lineno)
        raise error
    return result

def sudo(cmd, *args, **kwargs):
    return run("sudo " + cmd)
