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
        self.worker = worker
        self.name = task_name
        self.func = task_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        return deferToDaemonThread(self.uid, self.func, self.worker, *self.args, **self.kwargs)

    @property
    def uid(self):
        return str(id(self))

    @property
    def tag(self):
        args = " ".join(self.args)
        kwargs = " ".join("{}={}".format(k, v) for k, v in self.kwargs.items())
        return " ".join([self.name, args, kwargs]).strip()

thread_locals = local()

def task(f):
    def w(worker, *args, **kwargs):
        thread_locals.worker = worker
        try:
            return f(*args, **kwargs)
        except BaseException as e:
            return e
    w.is_task = True
    return w
