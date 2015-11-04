import urwid

from blinker import signal

from plait.app.base import PlaitApp
from plait.frame import ConsoleFrame
from plait.tabs import VerticalTabs

class WorkerLog(urwid.ListBox):
    def __init__(self):
        walker = urwid.SimpleListWalker([])
        urwid.ListBox.__init__(self, walker)

    def write(self, text):
        if text != "\n":
            text = text.replace("\n", "")
        new_text = urwid.Text(text)
        self.body.append(new_text)
        try:
            self.body.set_focus(self.body.focus + 1)
        except: pass

    def add(self, content):
        self.body.append(urwid.Text(content))
        try:
            self.body.set_focus(self.body.focus + 1)
        except: pass

class ConsoleApp(PlaitApp):

    default_palette = (
        ('reversed', 'standout', ''),
    )

    def __init__(self, title="plait"):
        self.tabs = VerticalTabs()
        local = self.tabs.addTab("localhost", WorkerLog())
        local.set_white()
        self.root = ConsoleFrame(title)
        self.loop = urwid.MainLoop(
            self.root, self.default_palette,
            handle_mouse=False, unhandled_input=self.unhandled_input,
            event_loop=urwid.TwistedEventLoop())
        self.loop.screen.set_terminal_properties(colors=256)
        self.show(self.tabs, "Remote task hosts")
        super(ConsoleApp, self).__init__()

    def run(self, runner):
        runner.run()
        for host in runner.hosts:
            self.tabs.addTab(host, WorkerLog())
        self.loop.run()

    def stop(self):
        raise urwid.ExitMainLoop

    def unhandled_input(self, key):
        if key.lower() == 'q':
            self.stop()
        self.loop.draw_screen()
        return key

    def show(self, w, header_text=""):
        self.root.show(w, header_text=header_text)

    def main_stdout(self, sender, data=None):
        tab = self.tabs.tabs["localhost"]
        tab.content.write(data)
        self.loop.draw_screen()

    def main_stderr(self, sender, data=None):
        tab = self.tabs.tabs["localhost"]
        tab.content.write(data)
        self.loop.draw_screen()

    def worker_stdout(self, worker, data=None):
        tab = self.tabs.tabs[worker.label]
        tab.content.write(data)
        self.loop.draw_screen()

    def worker_stderr(self, worker, data=None):
        tab = self.tabs.tabs[worker.label]
        tab.content.write(data)
        self.loop.draw_screen()

    def on_connect(self, worker):
        signal('stdout').connect(self.worker_stdout, sender=worker)
        signal('stderr').connect(self.worker_stderr, sender=worker)
        self.loop.draw_screen()

    def on_finish(self, worker):
        tab = self.tabs.tabs[worker.label]
        tab.set_green()

    def on_fail(self, worker, error=None):
        tab = self.tabs.tabs[worker.label]
        tab.set_red()
        self.loop.draw_screen()

    def on_task_start(self, worker, task=None):
        tab = self.tabs.tabs[worker.label]
        tab.set_cyan()
        tab.content.add(('reversed', task.tag))
        self.loop.draw_screen()

    def on_task_end(self, worker, result=None):
        tab = self.tabs.tabs[worker.label]
        tab.content.write("")
        self.loop.draw_screen()
