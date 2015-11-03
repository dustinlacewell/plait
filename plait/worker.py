import sys

from twisted.internet import defer, reactor
from twisted.python.filepath import FilePath
from twisted.conch.endpoints import SSHCommandClientEndpoint, _CommandChannel
from twisted.internet.protocol import Factory, Protocol

from plait.task import Task
from plait.spool import HookedProtocol
from plait.utils import parse_host_string, QuietConsoleUI, CFTResult, timeout

class WorkerChannel(_CommandChannel):
    def extReceived(self, dataType, data):
        if hasattr(self._protocol, 'extReceived'):
            self._protocol.extReceived(dataType, data)

class WorkerEndpoint(SSHCommandClientEndpoint):

    @property
    def username(self):
        return self._creator.username

    @property
    def hostname(self):
        return self._creator.hostname

    @property
    def port(self):
        return self._creator.port

    def _executeCommand(self, connection, protocolFactory):
        commandConnected = defer.Deferred()
        def disconnectOnFailure(passthrough):
            # Close the connection immediately in case of cancellation, since
            # that implies user wants it gone immediately (e.g. a timeout):
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
    Executes each task against a single connected host in a Task thread.
    """

    def __init__(self, viewer, keys, agent, known_hosts, timeout):
        self.viewer = viewer
        self.keys = keys
        self.agent = agent
        self.known_hosts = known_hosts
        self.timeout = 2
        self.host_string = None
        self.proto = None

    def buildProtocol(self, addr):
        self.proto = HookedProtocol(self.commitWrite, self.commitWrite)
        return self.proto

    def makeConnectEndpoint(self, user, host, port):
        return WorkerEndpoint.newConnection(
            reactor, b"cat", user, host, port,
            keys=self.keys, agentEndpoint=self.agent,
            knownHosts=self.known_hosts, ui=QuietConsoleUI())

    def makeCommandEndpoint(self, command):
        return WorkerEndpoint.existingConnection(
            self.proto.transport.conn, command.encode('utf8'))

    def connect(self, host_string):
        self.host_string = host_string
        user, host, port = parse_host_string(self.host_string)
        endpoint = self.makeConnectEndpoint(user, host, port)
        return timeout(self.timeout, endpoint.connect(self))

    @defer.inlineCallbacks
    def run(self, tasks):
        """
        Execute each task in a Task thread.
        """
        for task_name, task_func, args, kwargs in tasks:
            task = Task(self, task_name, task_func, args, kwargs)
            if self.viewer.loop:
                yield task.run()


    @defer.inlineCallbacks
    def execFromThread(self, command):
        """
        API for Tasks to execute ssh commands.
        """
        ep = self.makeCommandEndpoint(command)
        self.commitWrite("Running {}".format(command))
        if self.viewer.loop:
            yield ep.connect(self)
        self.commitWrite(self.proto.buffer)
        defer.returnValue(CFTResult(self.proto.buffer))

    def commitWrite(self, data):
        self.viewer.write(self.host_string, data)

    def bindThread(self, tid):
        sys.stdout.listen(tid, self.commitWrite)
        sys.stderr.listen(tid, self.commitWrite)

