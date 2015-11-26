import sys
from functools import partial

from twisted.internet import defer, error
from twisted.conch.error import HostKeyChanged

from blinker import signal

from structlog import get_logger
log = get_logger()

from plait.spool import ThreadedSignalFile
from plait.worker import PlaitWorker
from plait.utils import retry
from plait.errors import TimeoutError, StartupError

def flipio():
    sys._stdout, sys.stdout = sys.stdout, sys._stdout
    sys._stderr, sys.stderr = sys.stderr, sys._stderr

def write(msg):
    flipio()
    print msg
    flipio()

class PlaitRunner(object):
    def __init__(self, hosts, tasks, settings):
        self.workers = {}
        self.hosts = hosts
        self.tasks = tasks
        self.scale = int(settings.scale)
        self.retries = int(settings.retries)
        self.timeout = int(settings.timeout)
        self.keys = settings.keys
        self.agent = settings.agent_endpoint
        self.known_hosts = settings.known_hosts

    def installThreadIO(self):
        pass
        # redirect standard IO to threaded signal files
        sys._stdout = sys.stdout
        sys._stderr = sys.stderr
        sys.flip = flipio
        sys.write = write
        sys.stdout = ThreadedSignalFile('stdout')
        sys.stderr = ThreadedSignalFile('stderr')

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
            signal('worker_finish').send(worker)
        except (TimeoutError, error.ConnectingCancelledError) as e:
            msg = "Connection timedout after {} {}-second tries."
            msg = msg.format(self.retries + 1, self.timeout)
            signal('worker_failure').send(worker, failure=TimeoutError(msg))
        except HostKeyChanged as e:
            msg = "Host key has changed: {} lineno {}".format(e.path.path, e.lineno)
            signal('worker_failure').send(worker, failure=StartupError(msg))
        except Exception as e:
            signal('worker_failure').send(worker, failure=e)

    @defer.inlineCallbacks
    def run(self):
        self.installThreadIO()
        signal('runner_start').send(self)
        scale = self.scale or len(self.hosts)
        semaphore = defer.DeferredSemaphore(scale)
        consumer = partial(semaphore.run, self.runWorker)
        workers = map(consumer, self.hosts)
        yield defer.DeferredList(workers, consumeErrors=False)
        signal('runner_finish').send(self)
