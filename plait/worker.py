import sys

from twisted.internet import defer, reactor, error
from twisted.python.failure import Failure
from twisted.python.filepath import FilePath
from twisted.conch.endpoints import SSHCommandClientEndpoint, _CommandChannel
from twisted.internet.protocol import Factory, Protocol

from blinker import signal

from plait.task import Task
from plait.spool import SpoolingSignalProtocol, SpoolingProtocol
from plait.errors import TimeoutError, TaskError
from plait.utils import parse_host_string, QuietConsoleUI, timeout, AttributeString

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

    def __init__(self, tasks, keys, agent, known_hosts, timeout, all_tasks=False):
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
        self.all_tasks = all_tasks
        self.lines = 0
        self.tasks_by_uid = dict()

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
        yield timeout(self.timeout, endpoint.connect(self))
        signal('worker_connect').send(self)

    def parse_host_string(self, host_string):
        self.host_string = host_string
        self.user, self.host, self.port = parse_host_string(host_string)

    @property
    def label(self):
        return "{}@{}".format(self.user, self.host)

    def stdout(self, thread_name, data=None):
        task = self.tasks_by_uid[thread_name]
        task.has_output = True
        signal('worker_stdout').send(self, data=data)

    def stderr(self, thread_name, data=None):
        task = self.tasks_by_uid[thread_name]
        task.has_output = True
        signal('worker_stderr').send(self, data=data)

    def runTask(self, task):
        # listen to the output of this task
        signal('stdout').connect(self.stdout, sender=task.uid)
        signal('stderr').connect(self.stderr, sender=task.uid)
        # signal that the task has begun
        signal('task_start').send(self, task=task)
        return task.run()

    @defer.inlineCallbacks
    def run(self):
        """
        Execute each task in a Task thread.
        """
        # execute each task in sequence
        for name, func, args, kwargs in self.tasks:
            task = Task(self, name, func, args, kwargs)
            self.tasks_by_uid[task.uid] = task
            result = yield self.runTask(task)
            # tasks will return an Exception is there was a failure
            if isinstance(result, BaseException):
                # wrap it so the runner recognizes this as an expected exception
                # and doesn't emit generic worker exception signals
                e = TaskError("Task `{}` failed.".format(name))
                e.task = task
                e.failure = result
                raise e
            # otherwise it may optionally return a completion value
            elif self.all_tasks and not (result or task.has_output):
                e = TaskError("Task returned empty result.")
                e.task = task
                e.failure = e
                raise e
            else:
                signal('task_finish').send(self, task=task, result=result)

    @defer.inlineCallbacks
    def execFromThread(self, command):
        """
        API for tasks to execute ssh commands.
        """
        ep = self.makeCommandEndpoint(command)
        yield ep.connect(self)
        failed = False
        try:
            yield self.protocol.finished
        except error.ProcessTerminated as e:
            failed = True
        # flush output from proto accumulated during execution
        stdout, stderr = self.protocol.flush()
        result = AttributeString(stdout)
        result.stderr = stderr
        result.failed = failed
        result.succeeded = not failed
        result.command = command
        defer.returnValue(result)
