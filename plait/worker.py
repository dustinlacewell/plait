import sys

from twisted.conch.ssh import _kex

_kex._kexAlgorithms = {
    "diffie-hellman-group-exchange-sha1": _kex._DHGroupExchangeSHA1(),
    "diffie-hellman-group1-sha1": _kex._DHGroup1SHA1(),
    "diffie-hellman-group14-sha1": _kex._DHGroup14SHA1(),
}

from twisted.internet import defer, reactor
from twisted.python.failure import Failure
from twisted.python.filepath import FilePath
from twisted.conch.endpoints import SSHCommandClientEndpoint, _CommandChannel
from twisted.internet.protocol import Factory, Protocol

from blinker import signal

from plait.task import Task
from plait.spool import SpoolingSignalProtocol, SpoolingProtocol
from plait.errors import TimeoutError
from plait.utils import parse_host_string, QuietConsoleUI, CFTResult, timeout

# default channel does send ext bytes to protocol (stderr)
class WorkerChannel(_CommandChannel):
    def extReceived(self, dataType, data):
        if hasattr(self._protocol, 'extReceived'):
            self._protocol.extReceived(dataType, data)

# endpoint that utilizes channel above
class WorkerEndpoint(SSHCommandClientEndpoint):
    commandConnected = defer.Deferred()
    def _executeCommand(self, connection, protocolFactory):
        commandConnected = defer.Deferred()
        def disconnectOnFailure(passthrough):
            immediate =  passthrough.check(defer.CancelledError)
            self._creator.cleanupConnection(connection, immediate)
            return passthrough
        commandConnected.addErrback(disconnectOnFailure)
        channel = WorkerChannel(
            self._creator, self._command, protocolFactory, commandConnected)
        connection.openChannel(channel)
        return commandConnected

class PlaitWorker(Factory):
    """
    Executes a sequence of tasks against a remote host.

    When run, an initial SSH connection is established to the remote host.
    For efficiency's sake, all subsequent remote operations reuse the
    same connection and execute over a new channel.

    Each task is executed in a daemon thread which will be killed when the
    main thread exits. When the task runs a remote operation it blocks on
    a call on the worker inside the main reactor thread where the network
    operations are negotiated. The result is then returned to the thread
    and it resumes execution.

    There are a number of signals emitted for workers:

      - timeout        : seconds
      - fail           : failure
      - connect        : user, host, port
      - task_start     : task
      - task_end       : result
      - stdout         : line
      - stderr         : line
      - complete       :

    """

    def __init__(self, tasks, keys, agent, known_hosts, timeout):
        self.proto = None
        self.host_string = None
        self.user = None
        self.host = None
        self.port = None
        self.tasks = tasks
        self.keys = keys
        self.agent = None
        self.known_hosts = None
        self.timeout = timeout
        self.lines = 0

    def __str__(self):
        return self.host_string

    def buildProtocol(self, addr):
        # construct protocol and wire up io signals
        self.protocol = SpoolingSignalProtocol('stdout', 'stderr', sender=self.host_string)
        return self.protocol

    def makeConnectEndpoint(self):
        """
        Endpoint for initial SSH host connection.
        """
        return WorkerEndpoint.newConnection(
            reactor, b"cat",
            self.user, self.host, self.port,
            keys=self.keys, agentEndpoint=None,
            knownHosts=None, ui=QuietConsoleUI())

    def makeCommandEndpoint(self, command):
        """
        Endpoint for remotely executing operations.
        """
        return WorkerEndpoint.existingConnection(
            self.protocol.transport.conn, command.encode('utf8'))

    @defer.inlineCallbacks
    def connect(self, host_string):
        """
        Establish initial SSH connection to remote host.
        """
        self.parse_host_string(host_string)
        endpoint = self.makeConnectEndpoint()
        try: # connect with timeout
            yield timeout(self.timeout, endpoint.connect(self))
            signal('connect').send(self)
        except TimeoutError:
            signal('timeout').send(self)

    def parse_host_string(self, host_string):
        self.host_string = host_string
        self.user, self.host, self.port = parse_host_string(host_string)

    @property
    def label(self):
        return "{}@{}".format(self.user, self.host)

    @defer.inlineCallbacks
    def run(self):
        """
        Execute each task in a Task thread.
        """
        # execute each task in sequence
        for task_name, task_func, args, kwargs in self.tasks:
            task = Task(self, task_name, task_func, args, kwargs)
            # run task which return deferred with thread info
            deferred = task.run()
            # bind the thread to the worker so we can proxy its io signals
            self.bindThread(deferred.thread)
            # execute the task
            signal('task_start').send(self, task=task)
            result = yield deferred
            signal('task_end').send(self, result=result)
        signal('finish').send(self)

    @defer.inlineCallbacks
    def execFromThread(self, command):
        """
        API for tasks to execute ssh commands.
        """
        stdout = ""
        stderr = ""
        ep = self.makeCommandEndpoint(command)
        yield ep.connect(self)
        result = yield self.protocol.finished
        # flush output from proto accumulated during execution
        stdout, stderr = self.protocol.flush()
        defer.returnValue(CFTResult(stdout, stderr))

    def stdout(self, host_string, data=None):
        signal('stdout').send(self, data=data)

    def stderr(self, host_string, data=None):
        signal('stderr').send(self, data=data)

    def bindThread(self, thread):
        """
        Subscribe to io events emitted by this worker's thread with handlers
        that will re-emit them as sent by the worker.
        """
        signal('stdout').connect(self.stdout, sender=self.host_string)
        signal('stderr').connect(self.stderr, sender=self.host_string)

