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
        self.empty = True

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
        data = str(data)
        if self.task and data:
            self.task.stdout.write(data)
            self.empty = False

    def stderr(self, data):
        """Write to current task stderr"""
        data = str(data)
        if self.task and data:
            self.task.stderr.write(data)
            self.empty = False


class TerminalApp(PlaitApp):
    """
    A basic PlaitApp that prints colored Task results to stdout.
    """

    # space because unicode is literally wide
    fail_glyph = t.bold_red(u"⚡ ")
    warn_glyph = t.bold_yellow(u"✗ ")
    success_glyph = t.bold_green(u"✓ ")
    task_glyph = t.blue(u"↪  ")

    def __init__(self, error_filter, grep_filter, quiet_filter,
                 report=False, report_only=False):
        super(TerminalApp, self).__init__()
        # track the out of tasks for each remote host session
        self.sessions = dict()
        # whether to filter for errors
        self.error_filter = error_filter
        # text based filter
        self.grep_filter = grep_filter
        # filter tasks with no output
        self.quiet_filter = quiet_filter
        # whether to emit a report
        self.report = report
        self.report_only = report_only
        # track progress
        self.successes = 0
        self.failures = 0
        self.warnings = 0
        self.empties = 0
        self.results = 0

    def printReport(self):
        report = u"{} {}{}/{}/{}, {}{}, {}{}"
        report = report.format(
            self.task_glyph,
            self.success_glyph,
            self.results, self.empties, self.successes,
            self.warn_glyph, self.warnings,
            self.fail_glyph, self.failures
        )
        print t.bold_white("Plait results:")
        print report.encode('utf8')

    def run(self, runner):
        """
        Start the runner and block on the reactor.
        """
        @defer.inlineCallbacks
        def _(_):
            yield runner.run()
            if self.report or self.report_only:
                self.printReport()
        try:
            task.react(_)
        except (SystemExit, KeyboardInterrupt):
            # clean up terminating line upon exit
            print "\033[1F"

    def stop(self):
        """
        Stop the reactor and exit.
        """
        raise SystemExit(1)

    def sessionFor(self, worker):
        """
        Get the session data for the given worker. It is created if it does not
        already exist. The session data consists of the output of each Task for
        the Worker.
        """
        session = self.sessions.get(worker, SessionData(worker))
        self.sessions[worker] = session
        return session

    def grepSession(self, session):
        if not session.tasks:
            return True

        for task in session.tasks:
            if self.grep_filter(task.stdout.getvalue()):
                return True
            if self.grep_filter(task.stderr.getvalue()):
                return True
        return False

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
                lines += [self.task_glyph + task.task.tag,
                            task.stdout.getvalue(),
                            task.stderr.getvalue()]
        lines = [s.strip() for s in lines]
        # remove any consecutive newlines to condense output
        output = collapseLines(u"\n".join(lines) + u"\n")
        # return the utf8 encoded response
        output = output.encode('utf8')
        return output

    def printRender(self, render):
        if reactor.running and not self.report_only:
            print render

    # runner event handlers

    def on_worker_failure(self, worker, failure=None):
        """
        A worker's session has failed. If it was a TaskError, render the session
        with the output of each Task that was executed. Otherwise, simply render
        the failure.
        """
        session = self.sessionFor(worker)
        # only print if errors haven't been disabled and the output matches the
        # current regex filter
        no_filter = self.error_filter is None
        matches_filter = bool(self.error_filter and self.grepSession(session))
        if no_filter or matches_filter:
            render = self.renderSession(session, self.fail_glyph, failure=failure)
            self.printRender(render)
        self.failures += 1

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
        no_filter = self.error_filter is None
        matches_filter = bool(self.error_filter and self.grepSession(session))
        should_show = (not self.quiet_filter) or (not session.empty)
        if (no_filter or matches_filter) and should_show:
            render = self.renderSession(session, self.warn_glyph)
            self.printRender(render)
        self.warnings += 1

    def on_task_finish(self, worker, task=None, result=None):
        """
        A Task has finished so write the result to the session log.
        """
        session = self.sessionFor(worker)
        if not result:
            result = ''
        result = str(result).strip()
        session.stdout(result)

    def on_worker_finish(self, worker):
        """
        A Worker has completed all Tasks so print the results.
        """
        session = self.sessionFor(worker)
        should_show = (not self.quiet_filter) or (not session.empty)
        if (not self.error_filter) and self.grepSession(session) and should_show:
            render = self.renderSession(session, self.success_glyph)
            self.printRender(render)
        self.successes += 1
        if session.empty:
            self.empties += 1
        else:
            self.results += 1

