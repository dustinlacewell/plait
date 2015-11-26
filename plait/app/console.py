# -*- coding: utf-8 -*-

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
        if text != "\n" and isinstance(text, basestring):
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
        self.root = ConsoleFrame(title)
        self.screen = urwid.raw_display.Screen(input=open('/dev/tty', 'r'))
        self.loop = urwid.MainLoop(
            self.root, self.default_palette,
            screen=self.screen,
            handle_mouse=False, unhandled_input=self.unhandled_input,
            event_loop=urwid.TwistedEventLoop())
        self.loop.screen.set_terminal_properties(colors=256)
        self.show(self.tabs, "Remote task hosts")
        self.failed_workers = []
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

    def on_worker_stdout(self, worker, data=None):
        tab = self.tabs.tabs[worker.label]
        for line in data.split("\n"):
            tab.content.write(line)
        self.loop.draw_screen()

    def on_worker_stderr(self, worker, data=None):
        tab = self.tabs.tabs[worker.label]
        tab.content.write(data)
        self.loop.draw_screen()

    def on_worker_connect(self, worker):
        tab = self.tabs.tabs[worker.label]
        tab.set_cyan()
        self.loop.draw_screen()

    def on_worker_finish(self, worker):
        tab = self.tabs.tabs[worker.label]
        if worker not in self.failed_workers:
            tab.set_green()
        self.loop.draw_screen()

    def on_worker_failure(self, worker, failure=None):
        if worker.label not in self.tabs.tabs:
            worker.label = "localhost"
        tab = self.tabs.tabs[worker.label]
        tab.content.write(repr(failure))
        tab.set_red()
        self.failed_workers.append(worker)
        self.loop.draw_screen()

    def on_task_start(self, worker, task=None):
        tab = self.tabs.tabs[worker.label]
        task_template = u"↪ {task.tag}".format(task=task).encode('utf8')
        task_header = ('reversed', task_template)
        tab.content.write(task_header)
        self.loop.draw_screen()

    def on_task_failure(self, worker, task=None, failure=None):
        tab = self.tabs.tabs[worker.label]
        tab.content.write(str(failure))
        tab.set_orange()
        self.failed_workers.append(worker)
        self.loop.draw_screen()

    def on_task_finish(self, worker, task=None, result=None):
        if result:
            tab = self.tabs.tabs[worker.label]
            tab.content.write(str(result))
            self.loop.draw_screen()

