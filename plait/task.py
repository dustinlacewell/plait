import inspect
import sys, traceback
from StringIO import StringIO
from functools import partial
from threading import local, current_thread

from twisted.internet.threads import blockingCallFromThread as blockingCFT
from twisted.internet import threads, reactor

from plait.thread import deferToDaemonThread

class NoSuchTaskError(Exception): pass

class Task(object):
    """
    Executes a function with the given arguments in a thread.
    """
    def __init__(self, worker, task_name, task_func, args, kwargs):
        self.name = task_name
        # bake a partial for the task
        self.func = task_func
        self.args = args
        self.kwargs = kwargs
        self.partial = partial(task_func, worker, args, kwargs)

    def run(self):
        d = deferToDaemonThread(self.partial)
        return d

    @property
    def tag(self):
        args = " ".join(self.args)
        kwargs = " ".join("{}={}".format(k, v) for k, v in self.kwargs.items())
        return " ".join([self.name, args, kwargs])

thread_locals = local()

def task(f):
    def w(worker, args, kwargs):
        thread_locals.worker = worker
        blockingCFT(reactor, worker.bindThread, current_thread().ident)
        return f(*args, **kwargs)
    w.is_task = True
    return w
