import sys
from StringIO import StringIO
from functools import partial
from threading import current_thread
from collections import defaultdict

from twisted.internet import defer

from structlog import get_logger
log = get_logger()

from plait.spool import ThreadedHookedIO
from plait.worker import PlaitWorker
from plait.utils import timeout, retry

class PlaitRunner(object):
    def __init__(self, viewer, hosts, task_calls,
                 keys=None, agent=None,
                 retries=10, timeout=2,
                 scale=0, known_hosts=None):
        self.viewer = viewer
        self.hosts = hosts
        self.tasks = task_calls
        self.scale = scale
        self.retries = int(retries)
        self.timeout = int(timeout)
        self.keys = keys
        self.agent = agent
        self.known_hosts = known_hosts

    def makeWorker(self):
        return PlaitWorker(
            self.viewer, self.keys, self.agent, self.known_hosts, self.timeout)

    @defer.inlineCallbacks
    def runWorker(self, host_string):
        worker = self.makeWorker()
        # connect worker to host
        try:
            yield retry(self.retries, lambda: worker.connect(host_string))
            results = yield worker.run(self.tasks)
            defer.returnValue(results)
        except Exception as e:
            self.viewer.write(host_string, "Couldn't connect to %s" % host_string)
            self.viewer.write(host_string, str(e))

    @defer.inlineCallbacks
    def run(self):
        scale = self.scale or len(self.hosts)
        semaphore = defer.DeferredSemaphore(scale)
        consumer = partial(semaphore.run, self.runWorker)
        workers = map(consumer, self.hosts)

        _stdout = sys.stdout
        _stderr = sys.stderr
        sys.stdout = ThreadedHookedIO()
        sys.stderr = ThreadedHookedIO()

        # tid = current_thread()
        # sys.stdout.listen(tid, _stdout.write)
        # sys.stderr.listen(tid, _stderr.write)

        yield defer.DeferredList(workers, consumeErrors=False)
