import inspect
from twisted.internet import reactor
from twisted.internet.threads import blockingCallFromThread as blockingCFT

from plait.task import thread_locals

class RemoteCallError(Exception): pass

def run(cmd, fail=False):
    """
    Execute a command on the remote host.

    Blocks by calling into the main reactor thread. The result is a CFTResult
    object which will contain the stdout of the operation. It will also have
    a stderr attribute which if not empty indicates the remote command failed.
    """
    worker = thread_locals.worker
    # block until result is available or main thread dies
    result = blockingCFT(reactor, worker.execFromThread, cmd)
    if result.stderr.strip() and fail: # stderr indicates a remote error
        exception = RemoteCallError(result.stderr)
        exception.result = result
        stack = inspect.stack()[1]
        exception.error = stack[1], stack[2]
        raise exception
    return result

def sudo(cmd, *args, **kwargs):
    return run("sudo " + cmd)
