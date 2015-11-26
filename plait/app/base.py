import sys
from threading import current_thread

from blinker import signal

class PlaitApp(object):
    """
    Base application class responsible for starting the Runner and automatically
    listening to its events. Subclasses should utilize Runner events to display
    the progress and results of Plait's execution.
    """

    def __init__(self):
        # connect methods to signals
        self.connect_signals()
        # save original standard output files
        self._stdout = sys.stdout
        self._stderr = sys.stderr

    def connect_signals(self):
        """
        Automatically subscribe to signals based on methods named with a specific
        prefix. Also subscribe to the output events of the main thread.
        """
        for name in dir(self):
            # filter attributes by prefix
            if not name.startswith("on_"):
                continue
            attr = getattr(self, name, None)
            if callable(attr):
                # slice to remove prefix
                signal(name[3:]).connect(attr)

        # listen for any IO on the main thread
        signal('stdout').connect(self.main_stdout, current_thread().name)
        signal('stderr').connect(self.main_stderr, current_thread().name)

    # main thread IO signal handlers
    def main_stdout(self, sender, data=None):
        self._stdout.write(str(data))

    def main_stderr(self, sender, data=None):
        self._stderr.write(str(data))

    # basic application interfaces
    def run(self, runner):
        pass

    def stop(self):
        pass

