import sys
import codecs
from threading import current_thread
from collections import defaultdict
from StringIO import StringIO

from twisted.internet.error import ProcessTerminated
from twisted.internet.defer import Deferred
from twisted.internet.protocol import  Protocol

import blinker

from plait.utils import clean_utf8

class SignalFile(object):
    """
    Routes any writes to signal emissions by the specified sender.
    """
    def __init__(self, signal_name, sender=None):
        self.signal = blinker.signal(signal_name)
        self.sender = sender or self

    def write(self, data):
        self.signal.send(self.sender, data=data)

class ThreadedSignalFile(SignalFile):
    """
    Routes any writes to signal emissions by the current thread.
    """
    def __init__(self, *args, **kwargs):
        super(ThreadedSignalFile, self).__init__(*args, **kwargs)
        self.softspaces = defaultdict(lambda: 0)

    def write(self, data):
        t = current_thread()
        self.signal.send(t.ident, data=data)

    @property
    def softspace(self):
        t = current_thread()
        return self.softspaces[t]

    @softspace.setter
    @property
    def softspace(self, value):
        t = current_thread()
        self.softspaces[t] = value

class LineSpool(object):
    """
    File wrapper that only writes to the child file in whole
    lines, buffering until at least one is available.
    """
    def __init__(self, target):
        self.target = target # child file
        self.spool = "" # internal buffer

    def write(self, data):
        """
        Take in bytes. Write any fully formed lines to child.
        """
        self.spool += data
        while self.spool:
            try:
                line, self.spool = self.spool.split('\n', 1)
            except ValueError as e:
                return
            else:
                self.target.write(line + "\n")

    def flush(self):
        """
        Write any spooled bytes to child file.
        """
        self.target.write(self.spool)
        self.spool = ""

class SignalProtocol(Protocol):
    """
    Routes incomming bytes to specified signals.
    """
    def __init__(self, stdout, stderr, line_mode=True, sender=None):
        self.stdout = SignalFile(stdout, sender=sender or self)
        self.stderr = SignalFile(stderr, sender=sender or self)
        if line_mode:
            self.stdout = LineSpool(self.stdout)
            self.stderr = LineSpool(self.stderr)
        self.buffer = ""
        self.finished = None

    def dataReceived(self, data):
        data = clean_utf8(data)
        self.stdout.write(data)

    def extReceived(self, fd, data):
        data = clean_utf8(data)
        self.stderr.write(data)

    def connectionLost(self, reason):
        self.finished.callback(None)

class SpoolingProtocol(Protocol):
    """
    File that spools all writes to in-memory buffers in addition to
    normal handling which is flushable.
    """
    def __init__(self):
        self.outbuf = ""
        self.errbuf = ""

    def dataReceived(self, data):
        self.outbuf += clean_utf8(data)

    def extReceived(self, fd, data):
        self.errbuf += clean_utf8(data)

    def flush(self):
        _out, self.outbuf = self.outbuf, ""
        _err, self.errbuf = self.errbuf, ""
        return _out, _err

class SpoolingSignalProtocol(Protocol):
    def __init__(self, *args, **kwargs):
        self.spooling = SpoolingProtocol()
        self.signaling = SignalProtocol(*args, **kwargs)
        self.finished = None

    def connectionMade(self):
        self.finished = Deferred()

    def connectionLost(self, reason):
        if reason.type is ProcessTerminated:
            self.finished.errback(reason.value)
        else:
            self.finished.callback(reason.value)

    def dataReceived(self, data):
        self.signaling.dataReceived(data)
        self.spooling.dataReceived(data)

    def extReceived(self, fd, data):
        self.signaling.extReceived(fd, data)
        self.spooling.extReceived(fd, data)

    def flush(self):
        return self.spooling.flush()
