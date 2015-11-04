import sys
from threading import current_thread

from blinker import signal

from plait.spool import ThreadedSignalFile, LineSpool

class PlaitApp(object):
    """
    Base Plait application class that sets up the threaded IO needed to capture
    worker output. It also automatically connects methods starting with "on_"
    with similarlly named Signals as a convenience.
    """

    def __init__(self):
        # connect methods to signals
        self.connect_signals()
        # save original standard IO files
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        # redirect standard IO to threaded signal files
        sys.stdout = ThreadedSignalFile('stdout')
        sys.stderr = ThreadedSignalFile('stderr')

    def connect_signals(self):
        for name in dir(self):
            if not name.startswith("on_"):
                continue

            attr = getattr(self, name, None)
            if callable(attr):
                signal(name[3:]).connect(attr)
        # listen for any IO on the main thread
        signal('stdout').connect(self.main_stdout, current_thread().ident)
        signal('stderr').connect(self.main_stderr, current_thread().ident)

    # basic application interfaces
    def run(self, runner):
        pass

    def stop(self):
        pass

    # main thread IO signal handlers
    def main_stdout(self, sender, data=None):
        pass

    def main_stderr(self, sender, data=None):
        pass

