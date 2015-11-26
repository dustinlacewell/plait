# -*- coding: utf-8 -*-

import re, sys
from StringIO import StringIO

from twisted.internet import reactor, defer, task

from plait.utils import Bag, collapseLines

from plait.app.base import PlaitApp
from plait.errors import TaskError

from blessings import Terminal
t = Terminal()


class SessionData(object):
    """Tracks the output of Tasks for single session."""
    def __init__(self, worker):
        self.worker = worker
        self.tasks = []

    def addTask(self, task):
        """Create structure to track the current Task output"""
        data = Bag(task=task, stdout=StringIO(), stderr=StringIO())
        self.tasks.append(data)

    @property
    def task(self):
        if self.tasks:
            return self.tasks[-1]

    def stdout(self, data):
        """Write to current task stdout"""
        if self.task:
            self.task.stdout.write(data)

    def stderr(self, data):
        """Write to current task stderr"""
        if self.task:
            self.task.stderr.write(data)


class TerminalApp(PlaitApp):
    """
    A basic PlaitApp that prints colored Task results to stdout.
    """

    def __init__(self, error_filter, grep_filter):
        super(TerminalApp, self).__init__()
        # track the out of tasks for each remote host session
        self.sessions = dict()
        # whether to filter for errors
        self.error_filter = error_filter
        # text based filter
        self.grep_filter = grep_filter
        # track progress
        self.finished = 0

    def run(self, runner):
        """
        Start the runner and block on the reactor.
        """
        @defer.inlineCallbacks
        def _(reactor):
            yield runner.run()
            # remove strange character that gets printed on exit
            print "\r"
        task.react(_)

    def stop(self):
        """
        Stop the reactor and exit.
        """
        reactor.stop()

    def sessionFor(self, worker):
        """
        Get the session data for the given worker. It is created if it does not
        already exist. The session data consists of the output of each Task for
        the Worker.
        """
        session = self.sessions.get(worker, SessionData(worker))
        self.sessions[worker] = session
        return session

    def renderSession(self, session, glyph, failure=None):
        """
        Render the session data suitable for printing. Each session begins with a
        header denoting the connection details of the remote host with an optional
        prefix glyph for visual indication of the session's result.

        Subsequently the name, arguments and output of each executed Task are
        appended.
        """
        host = session.worker.host_string
        header = u"{glyph} {host}".format(glyph=glyph, host=host)
        lines = [header] # working list of resulting lines
        if failure:
            # if there is a session failure simply append it
            message = t.red(unicode(failure))
            lines.append(message)
        else:
            # otherwise append the name, arguments and output of each task
            for task in session.tasks:
                lines += [t.blue(u"↪  ") + task.task.tag,
                            task.stdout.getvalue(),
                            task.stderr.getvalue()]
        lines = [s.strip() for s in lines]
        # remove any consecutive newlines to condense output
        output = collapseLines(u"\n".join(lines) + u"\n")
        # return the utf8 encoded response
        return output.encode('utf8')

    def printRender(self, render):
        if self.grep_filter(render):
            print render

    # runner event handlers

    def on_worker_failure(self, worker, failure=None):
        """
        A worker's session has failed. If it was a TaskError, render the session
        with the output of each Task that was executed. Otherwise, simply render
        the failure.
        """
        try:
            session = self.sessionFor(worker)
            if isinstance(failure, TaskError):
                render = self.renderSession(session, t.bold_yellow(u"✗ "))
            else:
                render = self.renderSession(session, t.bold_red(u"⚡ "), failure=failure)
            # only print if errors haven't been disabled and the output matches the
            # current regex filter
            if self.error_filter != False:
                self.printRender(render)
        except Exception as e:
            print "ERROR", e

    def on_task_start(self, worker, task=None):
        """
        A Worker has started a new Task so add it to the session data.
        """
        session = self.sessionFor(worker)
        session.addTask(task)

    def on_worker_stdout(self, worker, data=None):
        """
        A Worker has emitted output so write it to the session log.
        """
        session = self.sessionFor(worker)
        session.stdout(data)

    def on_worker_stderr(self, worker, data=None):
        """
        A Worker has emitted output so write it to the session log.
        """
        session = self.sessionFor(worker)
        session.stderr(data)

    def on_task_failure(self, worker, task=None, failure=None):
        """
        A Task has failed so write the failure to the session log.
        """
        session = self.sessionFor(worker)
        session.stderr(t.yellow(str(failure).strip()))

    def on_task_finish(self, worker, task=None, result=None):
        """
        A Task has finished so write the result to the session log.
        """
        "FINISHED", worker.host_string, result
        session = self.sessionFor(worker)
        session.stdout(result)

    def on_worker_finish(self, worker):
        """
        A Worker has completed all Tasks so print the results.
        """
        session = self.sessionFor(worker)
        render = self.renderSession(session, t.bold_green(u"✓ "))
        if not self.error_filter:
            self.printRender(render)
