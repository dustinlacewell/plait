import codecs
from threading import current_thread
from collections import defaultdict
from StringIO import StringIO

from twisted.internet.defer import Deferred
from twisted.internet.protocol import  Protocol

class LineSpool(object):
    def __init__(self, target):
        self.target = target
        self.spool = ""

    # def write(self, data):
    #     # write data to buffer
    #     self.spool.write(str(data))
    #     # get whole buffer
    #     value = self.spool.getvalue()
    #     if "\n" in value:
    #         to_target, to_spool = self.spool.getvalue().rsplit("\n", 1)
    #         self.target.write(to_target)
    #         self.spool = StringIO(to_spool)

    def write(self, data):
        self.spool += data
        while self.spool:
            try:
                line, self.spool = self.spool.split(b'\n', 1)
            except ValueError as e:
                return
            else:
                self.target.write(line)

    def flush(self):
        self.target.write(self.spool)
        self.spool = ""

class HookedIO(object):
    def __init__(self, listener):
        self.listener = listener

    def write(self, data):
        self.listener(data)

class ThreadedHookedIO(object):
    def __init__(self):
        self.threads = dict()

    def listen(self, t, listener):
        self.threads[t] = LineSpool(HookedIO(listener))

    def write(self, data):
        t = current_thread()

        if t in self.threads:
            return self.threads[t].write(data)

class HookedProtocol(Protocol):
    def __init__(self, stdout, stderr):
        self.stdout = LineSpool(HookedIO(stdout))
        self.stderr = LineSpool(HookedIO(stderr))
        self.buffer = ""
        self.finished = None

    def connectionMade(self):
        self.finished = Deferred()

    def dataReceived(self, data):
        data = data.decode('utf8', 'replace')
        self.stdout.write(data.encode('utf8'))
        self.buffer += data.encode('utf8')

    def extReceived(self, fd, data):
        data = data.decode('utf8', 'replace')
        self.stdout.write(data.encode('utf8'))
        self.buffer += data.encode('utf8')

    def flush(self):
        self.stdout.flush()
        self.stderr.flush()
        data, self.buffer = self.buffer, ""
        return data

    def connectionLost(self, reason):
        self.finished.callback(None)
