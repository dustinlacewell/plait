import inspect
from twisted.internet import reactor
from twisted.internet.threads import blockingCallFromThread as blockingCFT

from plait.task import thread_locals

class RemoteCallError(Exception): pass

def run(cmd, quiet=False):
    """
    Execute a command on the remote host.

    Blocks by calling into the main reactor thread. The result is a CFTResult
    object which will contain the stdout of the operation. It will also have
    a stderr attribute which if not empty indicates the remote command failed.
    """
    worker = thread_locals.worker
    # block until result is available or main thread dies
    result = blockingCFT(reactor, worker.execFromThread, cmd)
    # if result.stderr.strip(): # stderr indicates a remote error
    #     # create an exception to raise so task code can respond to it
    #     error = RemoteCallError(result)
    #     # attach exception location
    #     stack = inspect.stack()[1]
    #     error.file, error.lineno = stack[1], stack[2]
    #     raise error
    return result

def sudo(cmd, *args, **kwargs):
    return run("sudo " + cmd)
