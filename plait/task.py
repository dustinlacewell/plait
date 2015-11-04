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
    def __init__(self, worker, task_name, task_func, args, kwargs):
        self.task_name = task_name
        self.task_func = partial(task_func, worker, args, kwargs)

    def run(self):
        return deferToDaemonThread(self.task_func)

thread_locals = local()

def task_logname():
    return "/tmp/{}.log".format(thread_locals.worker.host_string).replace('@', '_')

def task_log(msg):
    log = open(task_logname(), 'a')
    log.write(msg + " ")
    log.close()

def task(f):
    def w(worker, args, kwargs):
        thread_locals.worker = worker
        thread_locals.log = task_log
        open(task_logname(), 'w').close()
        task_log("BINDING THREAD")
        if not worker.viewer.loop:
            return
        blockingCFT(reactor, worker.bindThread, current_thread())
        task_log("WORKING")
        if not worker.viewer.loop:
            return
        f(*args, **kwargs)
        task_log("TASK FINISHED")
    w.is_task = True
    return w
