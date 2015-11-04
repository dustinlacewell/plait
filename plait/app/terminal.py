from collections import defaultdict

from functools import partial

from twisted.internet import reactor, defer, task

from blinker import signal

from blessings import Terminal

class BlessedWrapper(object):
    def __init__(self, term):
        self.__term = term

    def __getattr__(self, name):
        if not name.startswith("_"):
            orig = getattr(self.__term, name)
            return lambda *a: orig(" ".join(a))

t = BlessedWrapper(Terminal())

from plait.app.base import PlaitApp

def color(point, *args):
    return '%s %s \033[0m' % (point, " ".join(args))

header = partial(color, '\033[95m')
okblue = partial(color, '\033[94m')
okgreen = partial(color, '\033[92m')
warning = partial(color, '\033[93m')
fail = partial(color, '\033[91m')
bold = partial(color,'\033[1m')
underline = partial(color, '\033[4m')


class TerminalApp(PlaitApp):
    buffers = defaultdict(str)

    def check_scale(self, runner):
        if runner.scale != 1:
            print t.bold_yellow("Non-interactive mode; running with scale 1")
            runner.scale = 1

    def run(self, runner):
        self.check_scale(runner)
        @defer.inlineCallbacks
        def _(reactor):
            yield runner.run()
            # remove strange character that gets printed on exit
            print "\r"

        task.react(_)

    def stop(self):
        reactor.stop()

    def main_stdout(self, sender, data=None):
        self._stdout.write(data)

    def main_stderr(self, sender, data=None):
        self._stderr.write(data)

    def worker_stdout(self, sender, data=None):
        if data:
            self.buffers[sender] += str(data)

    def worker_stderr(self, sender, data=None):
        self._stderr.write(t.red(data))

    def on_task_start(self, sender, task=None):
        print t.bold_blue(task.tag)

    def on_task_end(self, sender, result=None):
        print self.buffers[sender]
        del self.buffers[sender]

    def on_connect(self, worker):
        print "\n", t.reverse_bold_green("Connected to:", worker.label), "\n"
        signal('stdout').connect(self.worker_stdout, sender=worker)
        signal('stderr').connect(self.worker_stderr, sender=worker)

    def on_timeout(self, sender, timeout=None):
        print "Worker timed out after {} seconds".format(timeout)
