import sys
from StringIO import StringIO
from functools import partial
from threading import current_thread
from collections import defaultdict

from twisted.internet import defer, reactor

from blinker import signal

from structlog import get_logger
log = get_logger()

from plait.spool import ThreadedSignalFile
from plait.worker import PlaitWorker
from plait.utils import timeout, retry

class PlaitRunner(object):
    def __init__(self, hosts, tasks,
                 keys=None, agent=None,
                 retries=10, timeout=2,
                 scale=0, known_hosts=None):
        self.workers = {}
        self.hosts = hosts
        self.tasks = tasks
        self.scale = int(scale)
        self.retries = int(retries)
        self.timeout = int(timeout)
        self.keys = keys
        self.agent = agent
        self.known_hosts = known_hosts

    def makeWorker(self):
        return PlaitWorker(self.tasks,
                           self.keys, self.agent,
                           self.known_hosts, self.timeout)

    @defer.inlineCallbacks
    def runWorker(self, host_string):
        worker = self.makeWorker()
        self.workers[host_string] = worker
        try:
            # try to get the worker connected to remote host
            yield retry(self.retries, lambda: worker.connect(host_string))
            # run all tasks within the worker
            yield worker.run()
        except Exception as e:
            signal('fail').send(worker, error=e)

    @defer.inlineCallbacks
    def run(self):
        scale = self.scale or len(self.hosts)
        semaphore = defer.DeferredSemaphore(scale)
        consumer = partial(semaphore.run, self.runWorker)
        workers = map(consumer, self.hosts)
        yield defer.DeferredList(workers, consumeErrors=False)
